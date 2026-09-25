from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def run_phase1(settings: Settings | None = None) -> dict[str, Any]:
    """Execute the Baseline Pipeline (Phase 1 / CP3) End-to-End.

    Flow:
    1. Load settings and configuration paths.
    2. Load raw paper records (from local snapshot or fetch from Crossref API).
    3. Clean and standardize dataset (build 5-layer text_for_embedding and age_days).
    4. Save clean dataset to CSV and JSON artifacts.
    5. Build ChromaDB baseline vector index ('papers-baseline') with MiniLM embeddings.
    6. Generate / refresh benchmark evaluation test set (10 questions across 4 categories).
    7. Evaluate RAG retrieval & QA pipeline (calculate Retrieval Hit Rate, Token F1, LLM judge).
    8. Run Great Expectations 1.x data quality checks and verify Freshness SLA.
    9. Generate Phase 1 markdown baseline report (phase1_report.md).
    10. Execute agent demo on sample questions and save demonstration answers.

    Args:
        settings: Application settings. If None, loaded automatically.

    Returns:
        Dictionary containing pipeline artifacts, metrics, and quality reports.
    """
    settings = settings or load_settings()
    print("=" * 70)
    print("  DAY 10 — PHASE 1: BASELINE PIPELINE (CP3)")
    print("=" * 70)

    # 1 & 2. Ingestion: load or fetch raw records
    raw_records_path = settings.paths.raw_records_json
    if raw_records_path.exists() and not settings.refresh_source:
        logger.info("Loading raw records from snapshot %s", raw_records_path)
        records = load_raw_records(raw_records_path)
        source_desc = "Local Raw Snapshot (Fallback)"
    else:
        logger.info("Fetching raw records from Crossref API...")
        records = fetch_source_records(settings)
        source_desc = settings.source_api

    print(f"[CP3] [1/8] Ingestion: {len(records)} raw records loaded from {source_desc}.")

    # 3. Clean data
    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    print(f"[CP3] [2/8] Cleaning: {len(df)} records cleaned (5-part text_for_embedding, age_days).")

    # 4. Save clean artifacts
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"[CP3] [3/8] Artifacts: Saved clean CSV to '{settings.paths.clean_csv}' and JSON to '{settings.paths.clean_json}'.")

    # 5. Build Chroma baseline vector index
    print(f"[CP3] [4/8] Indexing: Building ChromaDB vector collection '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"[CP3]       ChromaDB collection '{settings.baseline_collection_name}' indexed with {len(df)} documents.")

    # 6. Evaluation test set
    test_set_path = settings.paths.eval_testset
    test_set = build_test_set(df, test_set_path)
    print(f"[CP3] [5/8] Test Set: Generated {len(test_set)} benchmark questions at '{test_set_path}'.")

    # 7. Evaluate RAG baseline pipeline
    print(f"[CP3] [6/8] Evaluation: Running evaluation over {len(test_set)} test questions...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = eval_bundle.summary
    hit_rate = metrics.get("retrieval_hit_rate", 0.0)
    token_f1 = metrics.get("mean_token_f1", 0.0)
    judge_acc = metrics.get("judge_accuracy", 0.0)
    print(
        f"[CP3]       Baseline Metrics: Retrieval Hit Rate = {hit_rate:.1%}, "
        f"Token F1 = {token_f1:.4f}, Judge Accuracy = {judge_acc:.1%}"
    )

    # 8. Observability: Great Expectations 1.x Quality Checks & Freshness SLA
    print("[CP3] [7/8] Observability: Executing Great Expectations 1.x Quality Gate & Freshness SLA...")
    quality_report = run_data_quality_checks(
        df=df,
        settings=settings,
        report_name=settings.paths.baseline_quality_report,
    )
    freshness_report = build_freshness_report(
        df=df,
        settings=settings,
        report_path=settings.paths.freshness_report,
    )
    gx_status = "PASSED" if quality_report.get("success") else "FAILED"
    fresh_status = "COMPLIANT" if freshness_report.get("is_fresh") else "VIOLATED"
    print(f"[CP3]       GX 1.x Quality Gate: {gx_status} (Success = {quality_report.get('success')})")
    print(f"[CP3]       Freshness SLA: {fresh_status} (Stale ratio: {freshness_report.get('stale_ratio', 0.0):.1%})")

    # 9. Reporting: generate Phase 1 Markdown report
    source_summary = {
        "total_records": len(df),
        "source": source_desc,
        "raw_records_path": str(settings.paths.raw_records_json),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"[CP3] [8/8] Report: Baseline report generated at '{settings.paths.baseline_report}'.")

    # 10. Optional Agent demonstration
    demo_answers: list[dict[str, Any]] = []
    try:
        agent = build_agent(settings, index)
        sample_questions = [
            f"What is the summary of the paper '{df.iloc[0]['title']}'?",
            f"Who authored the paper '{df.iloc[1]['title']}'?",
        ]
        for q in sample_questions:
            ans = run_agent_question(agent, q)
            demo_answers.append({"question": q, "answer": ans})
        write_json(settings.paths.demo_answers, demo_answers)
        logger.info("Saved %d agent demo answers to %s", len(demo_answers), settings.paths.demo_answers)
    except Exception as exc:
        logger.info("Agent live demo pass skipped or encountered non-critical error: %s", exc)

    print("=" * 70)
    print("  [CP3] PHASE 1 BASELINE PIPELINE COMPLETED SUCCESSFULLY! (Exit Code 0)")
    print("=" * 70)

    return {
        "clean_df": df,
        "index": index,
        "test_set": test_set,
        "metrics": metrics,
        "quality": quality_report,
        "freshness": freshness_report,
        "demo_answers": demo_answers,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_phase1()


if __name__ == "__main__":
    main()
