from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings

logger = logging.getLogger(__name__)


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tạo bộ data quality checks theo chuẩn Great Expectations 1.x kết hợp Freshness SLA.

    1. Khởi tạo Ephemeral Data Context của GX 1.x (chạy trên RAM, nhanh và không để lại rác).
    2. Cấu hình Data Source, Data Asset, Batch Definition và trích xuất Batch từ df.
    3. Định nghĩa 4 Expectations thiết yếu:
       - ExpectTableRowCountToBeBetween: Số lượng bản ghi nằm trong [5, 5000].
       - ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding không được rỗng.
       - ExpectColumnValuesToBeUnique: paper_id là duy nhất.
       - ExpectColumnValueLengthsToBeBetween: summary có độ dài tối thiểu 30 ký tự.
    4. Thực hiện batch.validate(suite).
    5. Kiểm tra Freshness SLA bằng age_days (tỉ lệ stale > 180 ngày <= 25%).
    6. Lưu kết quả JSON vào thư mục data/quality/ và trả về report dictionary.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_quality_suite_{report_name}")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_results = batch.validate(suite)

    # Kiểm tra Freshness SLA (ngưỡng freshness_threshold_days, mặc định 180 ngày)
    threshold = settings.freshness_threshold_days
    stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df.columns else 0
    total_rows = len(df)
    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    gx_success = bool(validation_results.success)
    overall_success = gx_success and is_fresh

    # Xác định đường dẫn file report tương ứng
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    report: dict[str, Any] = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": is_fresh,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "statistics": validation_results.statistics,
        "details": validation_results.to_json_dict(),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    logger.info("Quality check report for '%s' saved to %s (success=%s)", report_name, report_path, overall_success)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Tổng hợp freshness report.

    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale (> freshness_threshold_days).
    3. Tạo payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - stale_ratio
       - freshness_threshold_days
       - is_fresh
    4. Ghi JSON report vào report_path.
    """
    published_series = (
        df["published"].dropna().astype(str) if "published" in df.columns else pd.Series(dtype=str)
    )
    latest_published = str(published_series.max()) if not published_series.empty else "N/A"
    oldest_published = str(published_series.min()) if not published_series.empty else "N/A"

    threshold = settings.freshness_threshold_days
    stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df.columns else 0
    total_rows = len(df)
    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    target_path = Path(report_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    logger.info("Freshness report saved to %s (is_fresh=%s)", target_path, is_fresh)
    return payload
