from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, safe_slug, write_json


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, report_name: str
) -> dict[str, Any]:
    """Run data quality checks using Great Expectations 1.x ephemeral context.

    Expectations verified:
    1. ExpectTableRowCountToBeBetween: 20 to 30 rows.
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding.
    3. ExpectColumnValuesToBeUnique: paper_id.
    4. ExpectColumnValueLengthsToBeBetween:
       - summary: min 30 chars
       - title: min 8 chars

    Args:
        df: Clean or corrupted DataFrame to validate.
        settings: Application settings.
        report_name: Identifier for report, saved to data/quality/<report_name>.json.

    Returns:
        Dictionary containing overall 'success' flag, statistics, and individual expectation results.
    """
    clean_name = safe_slug(str(report_name).replace(".json", ""))

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{clean_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{clean_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_suite_{clean_name}")

    # 1. Row count expectation (baseline has 24 rows, corrupted drops to ~19)
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=20, max_value=30))

    # 2. Non-null expectations on critical fields
    for col in ["paper_id", "title", "text_for_embedding"]:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    # 3. Uniqueness expectation on primary key
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))

    # 4. Length constraints on summary and title
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8))

    val_result = batch.validate(suite)

    expectation_details: list[dict[str, Any]] = []
    for r in val_result.results:
        cfg = getattr(r, "expectation_config", None)
        exp_type = getattr(cfg, "type", str(cfg))
        kwargs = dict(getattr(cfg, "kwargs", {}))
        result_info = getattr(r, "result", {})
        expectation_details.append(
            {
                "expectation_type": exp_type,
                "kwargs": kwargs,
                "success": bool(r.success),
                "result": result_info,
            }
        )

    stats = getattr(val_result, "statistics", {})
    if hasattr(stats, "to_json_dict"):
        stats_dict = stats.to_json_dict()
    elif isinstance(stats, dict):
        stats_dict = stats
    else:
        stats_dict = {
            "evaluated_expectations": getattr(stats, "evaluated_expectations", len(expectation_details)),
            "successful_expectations": getattr(
                stats, "successful_expectations", sum(1 for e in expectation_details if e["success"])
            ),
            "unsuccessful_expectations": getattr(
                stats, "unsuccessful_expectations", sum(1 for e in expectation_details if not e["success"])
            ),
            "success_percent": getattr(stats, "success_percent", 100.0 if val_result.success else 0.0),
        }

    overall_success = bool(val_result.success)

    report_payload: dict[str, Any] = {
        "report_name": str(report_name),
        "success": overall_success,
        "statistics": stats_dict,
        "expectations": expectation_details,
        "evaluated_at": now_utc().isoformat(),
        "total_rows": len(df),
    }

    # Resolve output path
    if isinstance(report_name, Path):
        output_path = report_name
    else:
        file_name = f"{report_name}.json" if not str(report_name).endswith(".json") else str(report_name)
        output_path = settings.paths.quality_dir / Path(file_name).name

    write_json(output_path, report_payload)
    return report_payload


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None
) -> dict[str, Any]:
    """Calculate freshness metrics and verify against the Freshness SLA.

    SLA Rule:
        A dataset is deemed fresh (is_fresh = True) if the ratio of stale rows
        (where age_days > 180) is <= 25% (0.25).

    Args:
        df: DataFrame containing at least 'published' and preferably 'age_days'.
        settings: Application settings.
        report_path: Optional explicit output path for the JSON report.

    Returns:
        Dictionary with freshness summary metrics and SLA status.
    """
    total_rows = len(df)
    threshold = getattr(settings, "freshness_threshold_days", 180)

    if total_rows == 0:
        payload = {
            "latest_published": "",
            "oldest_published": "",
            "threshold_days": threshold,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
            "generated_at": now_utc().isoformat(),
        }
    else:
        published_series = (
            df["published"].dropna().astype(str) if "published" in df.columns else pd.Series([], dtype=str)
        )
        latest_published = str(published_series.max()) if not published_series.empty else ""
        oldest_published = str(published_series.min()) if not published_series.empty else ""

        if "age_days" in df.columns:
            stale_count = int((pd.to_numeric(df["age_days"], errors="coerce").fillna(0) > threshold).sum())
        elif not published_series.empty:
            today = now_utc().date()

            def _parse_age(d_str: str) -> int:
                try:
                    return (today - datetime.strptime(d_str[:10], "%Y-%m-%d").date()).days
                except Exception:
                    return 0

            ages = published_series.map(_parse_age)
            stale_count = int((ages > threshold).sum())
        else:
            stale_count = 0

        stale_ratio = float(stale_count / total_rows)
        is_fresh = bool(stale_ratio <= 0.25)

        payload = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "threshold_days": threshold,
            "stale_rows": stale_count,
            "total_rows": total_rows,
            "stale_ratio": round(stale_ratio, 4),
            "is_fresh": is_fresh,
            "generated_at": now_utc().isoformat(),
        }

    target = Path(report_path) if report_path else settings.paths.freshness_report
    write_json(target, payload)
    return payload
