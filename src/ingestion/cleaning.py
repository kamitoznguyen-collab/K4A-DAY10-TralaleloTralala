from __future__ import annotations

from datetime import datetime
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
    """Clean raw records thành DataFrame chuẩn hóa sẵn sàng để embed và đánh giá.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tính age_days = (run_date - published).days.
    4. Tạo các cột helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding (cấu trúc 5 phần: Title, Authors, Published, Categories, Summary)
    5. Drop duplicates theo paper_id và lọc các dòng lỗi (thiếu id/title hoặc summary quá ngắn).
    6. Sort DataFrame và trả về kết quả.
    """
    rows: list[dict] = []
    run_date_val = run_date.date() if isinstance(run_date, datetime) else run_date

    for r in records:
        paper_id = r.paper_id.strip()
        title = " ".join(r.title.split()).strip()
        summary = " ".join(r.summary.split()).strip()
        authors = [" ".join(a.split()).strip() for a in r.authors if a.strip()]
        categories = [" ".join(c.split()).strip() for c in r.categories if c.strip()]
        primary_category = (
            r.primary_category.strip()
            if r.primary_category
            else (categories[0] if categories else "General")
        )
        published = r.published.strip()
        updated = r.updated.strip() if r.updated else published
        abs_url = r.abs_url.strip()
        pdf_url = r.pdf_url.strip()
        comment = r.comment.strip()

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        summary_chars = len(summary)

        # Tính age_days dựa trên ngày xuất bản
        try:
            pub_date = datetime.fromisoformat(published[:10]).date()
            age_days = max(0, (run_date_val - pub_date).days)
        except Exception:
            age_days = 0

        # Ghép text_for_embedding theo mẫu chuẩn 5 phần
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 5. Drop duplicates và filter row xấu
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["paper_id"].notna() & (df["paper_id"] != "")]
    df = df[df["title"].notna() & (df["title"] != "")]
    df = df[df["summary_chars"] >= 30]

    # 6. Sort dataframe
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
