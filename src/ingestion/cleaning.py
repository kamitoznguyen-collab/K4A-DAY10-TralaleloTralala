from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
]

_TEXT_COLUMNS = ["paper_id", "title", "summary", "primary_category", "abs_url", "pdf_url", "comment"]


def _normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return normalize_whitespace(str(value))


def _normalize_list(values: object) -> list[str]:
    """Normalize each item and drop empties/duplicates while keeping order."""
    if not isinstance(values, (list, tuple)):
        values = [values] if _normalize_text(values) else []
    return list(dict.fromkeys(item for item in (_normalize_text(v) for v in values) if item))


def _normalize_date(value: object) -> str:
    """Return `YYYY-MM-DD`, or `""` when the value cannot be parsed."""
    parsed = pd.to_datetime(_normalize_text(value) or None, errors="coerce", utc=True)
    return "" if pd.isna(parsed) else parsed.date().isoformat()


def _age_days(published: str, run_day: date) -> int:
    if not published:
        return -1
    return (run_day - date.fromisoformat(published)).days


def build_text_for_embedding(row: pd.Series | dict) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding.

    Text is whitespace-normalized, dates become `YYYY-MM-DD` strings (`""` when missing, since ChromaDB
    metadata rejects Timestamp/None), rows without `paper_id`/`title` are dropped, duplicates on
    `paper_id` keep the most recently updated copy, and the result is sorted newest first.
    """
    df = pd.DataFrame([asdict(record) for record in records], columns=CLEAN_COLUMNS[:11])

    for column in _TEXT_COLUMNS:
        df[column] = df[column].map(_normalize_text)
    df["authors"] = df["authors"].map(_normalize_list)
    df["categories"] = df["categories"].map(_normalize_list)
    df["primary_category"] = [
        primary or (categories[0] if categories else "")
        for primary, categories in zip(df["primary_category"], df["categories"])
    ]
    df["published"] = df["published"].map(_normalize_date)
    df["updated"] = df["updated"].map(_normalize_date)
    df["updated"] = df["updated"].where(df["updated"] != "", df["published"])

    df = df[(df["paper_id"] != "") & (df["title"] != "")]
    df = df.sort_values(["paper_id", "updated"], ascending=[True, False], kind="stable")
    df = df.drop_duplicates(subset="paper_id", keep="first")

    run_day = run_date.date()
    df["age_days"] = df["published"].map(lambda published: _age_days(published, run_day)).astype(int)
    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len().astype(int)
    df["text_for_embedding"] = df.apply(build_text_for_embedding, axis=1)

    df = df.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
    return df[CLEAN_COLUMNS].reset_index(drop=True)
