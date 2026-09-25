from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import run_phase1
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def _format_pct(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        f = float(val)
        return f"{f * 100:.1f}%"
    except (ValueError, TypeError):
        return str(val)


def _format_score(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.4f}"
    except (ValueError, TypeError):
        return str(val)


def run_corruption_flow(settings: Settings | None = None) -> dict[str, Any]:
    """Execute the Corruption, Degradation Measurement, and Idempotent Repair Flow (CP4 + CP5).

    Flow:
    1. Load baseline metrics and clean dataset (run Phase 1 if not already executed).
    2. Inject synthetic data corruption suite (6 error types) via corrupt_clean_dataframe().
    3. Save corrupted artifacts (CSV, JSON, corruption_log.json).
    4. Build corrupted ChromaDB index ('papers-corrupted') and evaluate degradation on benchmark test set.
    5. Run Great Expectations 1.x Quality Gate & Freshness SLA on corrupted data (demonstrating gate alarm).
    6. Execute Idempotent Repair: cleanly reconstruct dataset from raw snapshot (crossref_records.json).
    7. Save repaired artifacts (CSV, JSON, repaired embeddings manifest).
    8. Build repaired ChromaDB index ('papers-repaired') and evaluate full recovery.
    9. Run Great Expectations 1.x & Freshness checks on repaired dataset (confirming gate pass).
    10. Generate comprehensive 3-State Markdown Comparison Report (corruption_report.md).
    11. Display terminal comparison matrix across Baseline vs Corrupted vs Repaired.

    Args:
        settings: Application settings. If None, loaded automatically.

    Returns:
        Dictionary containing all metrics, quality reports, and artifacts for the 3 states.
    """
    settings = settings or load_settings()
    print("=" * 80)
    print("  DAY 10 — PHASE 2: SYNTHETIC DATA CORRUPTION & IDEMPOTENT REPAIR (CP4 + CP5)")
    print("=" * 80)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 1: Ensure Baseline Exists
    # ──────────────────────────────────────────────────────────────────────────
    baseline_metrics_path = settings.paths.baseline_metrics
    clean_json_path = settings.paths.clean_json
    test_set_path = settings.paths.eval_testset

    if not baseline_metrics_path.exists() or not clean_json_path.exists() or not test_set_path.exists():
        print("[CP5] [1/6] Baseline artifacts missing. Running Phase 1 to establish baseline...")
        run_phase1(settings)
    else:
        print("[CP5] [1/6] Baseline artifacts verified (baseline_metrics.json, papers_clean.json).")

    clean_df = pd.read_json(clean_json_path)
    baseline_metrics = read_json(baseline_metrics_path)
    baseline_quality_path = settings.paths.baseline_quality_report
    baseline_quality = read_json(baseline_quality_path) if baseline_quality_path.exists() else {"success": True}
    baseline_freshness_path = settings.paths.freshness_report
    baseline_freshness = read_json(baseline_freshness_path) if baseline_freshness_path.exists() else {"is_fresh": True}

    b_hit = baseline_metrics.get("retrieval_hit_rate", 1.0)
    b_f1 = baseline_metrics.get("mean_token_f1", 1.0)
    print(f"      Baseline Benchmarks: Hit Rate = {_format_pct(b_hit)}, Token F1 = {_format_score(b_f1)}")

    # ──────────────────────────────────────────────────────────────────────────
    # Step 2: Inject Synthetic Data Corruption (CP4)
    # ──────────────────────────────────────────────────────────────────────────
    print("[CP5] [2/6] Injecting synthetic corruption suite (6 scenarios)...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(
        f"      Saved corrupted dataset ({len(corrupted_df)} rows) to '{settings.paths.corrupted_clean_csv}' "
        f"and log to '{settings.paths.corruption_log}'."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Step 3: Index Corrupted Data & Measure Silent Failure
    # ──────────────────────────────────────────────────────────────────────────
    print(f"[CP5] [3/6] Indexing corrupted dataset into ChromaDB collection '{settings.corrupted_collection_name}'...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    print("      Evaluating RAG pipeline on corrupted index to quantify degradation...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    print(
        f"      Corrupted Benchmarks: Hit Rate = {_format_pct(c_hit)} (delta: {_format_pct(c_hit - b_hit)}), "
        f"Token F1 = {_format_score(c_f1)} (delta: {_format_score(c_f1 - b_f1)})"
    )

    # Observability checks on corrupted data
    corrupted_quality = run_data_quality_checks(
        df=corrupted_df,
        settings=settings,
        report_name=settings.paths.corrupted_quality_report,
    )
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(
        df=corrupted_df,
        settings=settings,
        report_path=corrupted_freshness_path,
    )
    print(
        f"      Corrupted Observability: GX 1.x Quality Gate = {'PASSED' if corrupted_quality.get('success') else 'FAILED'} "
        f"| Freshness SLA = {'COMPLIANT' if corrupted_freshness.get('is_fresh') else 'VIOLATED'} "
        f"(Stale ratio: {_format_pct(corrupted_freshness.get('stale_ratio', 0.0))})"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Step 4: Idempotent Repair from Raw Snapshot (CP5)
    # ──────────────────────────────────────────────────────────────────────────
    print("[CP5] [4/6] Executing Idempotent Repair from raw snapshot lineage...")
    raw_records_path = settings.paths.raw_records_json
    if raw_records_path.exists():
        raw_records = load_raw_records(raw_records_path)
    else:
        raw_records = fetch_source_records(settings)

    run_date = now_utc()
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(
        f"      Repaired data cleanly rebuilt ({len(repaired_df)} rows). "
        f"Saved to '{settings.paths.repaired_clean_csv}'."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Step 5: Index Repaired Data & Evaluate Full Recovery
    # ──────────────────────────────────────────────────────────────────────────
    print(f"[CP5] [5/6] Indexing repaired dataset into ChromaDB collection '{settings.repaired_collection_name}'...")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    print("      Evaluating RAG pipeline on repaired index to verify recovery...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)
    print(f"      Repaired Benchmarks: Hit Rate = {_format_pct(r_hit)}, Token F1 = {_format_score(r_f1)}")

    # Observability checks on repaired data
    repaired_quality_path = settings.paths.quality_dir / "repaired_quality_report.json"
    repaired_quality = run_data_quality_checks(
        df=repaired_df,
        settings=settings,
        report_name=repaired_quality_path,
    )
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(
        df=repaired_df,
        settings=settings,
        report_path=repaired_freshness_path,
    )
    print(
        f"      Repaired Observability: GX 1.x Quality Gate = {'PASSED' if repaired_quality.get('success') else 'FAILED'} "
        f"| Freshness SLA = {'COMPLIANT' if repaired_freshness.get('is_fresh') else 'VIOLATED'}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Step 6: Generate 3-State Comparison Markdown Report
    # ──────────────────────────────────────────────────────────────────────────
    print(f"[CP5] [6/6] Generating comprehensive 3-State Comparison Report at '{settings.paths.comparison_report}'...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Print Beautiful 3-State Terminal Comparison Table
    # ──────────────────────────────────────────────────────────────────────────
    b_acc = baseline_metrics.get("judge_accuracy", 1.0)
    c_acc = corrupted_metrics.get("judge_accuracy", 0.0)
    r_acc = repaired_metrics.get("judge_accuracy", 1.0)

    print("\n" + "=" * 80)
    print("  DATA OBSERVABILITY & 3-STATE COMPARISON MATRIX (CP5)")
    print("=" * 80)
    print(f"  {'Metric / Indicator':<28} | {'Baseline':<14} | {'Corrupted':<14} | {'Repaired':<14}")
    print("  " + "-" * 76)
    print(f"  {'Record Count':<28} | {len(clean_df):<14} | {len(corrupted_df):<14} | {len(repaired_df):<14}")
    print(
        f"  {'GX 1.x Quality Gate':<28} | "
        f"{'PASSED' if baseline_quality.get('success') else 'FAILED':<14} | "
        f"{'PASSED' if corrupted_quality.get('success') else 'FAILED (Alarm)':<14} | "
        f"{'PASSED' if repaired_quality.get('success') else 'FAILED':<14}"
    )
    print(
        f"  {'Freshness SLA (180d)':<28} | "
        f"{'COMPLIANT' if baseline_freshness.get('is_fresh') else 'VIOLATED':<14} | "
        f"{'COMPLIANT' if corrupted_freshness.get('is_fresh') else 'VIOLATED':<14} | "
        f"{'COMPLIANT' if repaired_freshness.get('is_fresh') else 'VIOLATED':<14}"
    )
    print(
        f"  {'Retrieval Hit Rate':<28} | "
        f"{_format_pct(b_hit):<14} | "
        f"{_format_pct(c_hit):<14} | "
        f"{_format_pct(r_hit):<14}"
    )
    print(
        f"  {'Answer Mean Token F1':<28} | "
        f"{_format_score(b_f1):<14} | "
        f"{_format_score(c_f1):<14} | "
        f"{_format_score(r_f1):<14}"
    )
    print(
        f"  {'LLM Judge Accuracy':<28} | "
        f"{_format_pct(b_acc):<14} | "
        f"{_format_pct(c_acc):<14} | "
        f"{_format_pct(r_acc):<14}"
    )
    print("=" * 80)
    recovered = (
        (r_hit, r_f1, r_acc) == (b_hit, b_f1, b_acc)
        and bool(repaired_quality.get("success"))
        and bool(repaired_freshness.get("is_fresh"))
    )
    if recovered:
        print("  [CP5] IDEMPOTENT REPAIR VERIFIED: REPAIRED STATE 100% RECOVERS BASELINE PERFORMANCE")
    else:
        print("  [CP5] WARNING: REPAIRED STATE DOES NOT FULLY MATCH BASELINE — CHECK THE REPORT")
    print("=" * 80 + "\n")

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_metrics,
        "repaired_metrics": repaired_metrics,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corrupted_freshness": corrupted_freshness,
        "repaired_freshness": repaired_freshness,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_corruption_flow()


if __name__ == "__main__":
    main()
