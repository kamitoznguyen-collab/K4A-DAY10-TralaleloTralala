from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import json
import logging
from pathlib import Path
import re
import time

import requests

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_USER_AGENT = "day10-data-observability-lab/0.1 (student project)"
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)

CROSSREF_API_URL = "https://api.crossref.org/works"
DEFAULT_USER_AGENT = "DataObservabilityLab/1.0 (mailto:student@lab.edu)"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw_text: str | None) -> str:
    """Loại bỏ thẻ XML/HTML (như <jats:p>) và giải mã ký tự đặc biệt."""
    if not raw_text:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_text)
    text = html.unescape(text)
    return " ".join(text.split()).strip()


def _extract_date(item: dict) -> str:
    """Trích xuất ngày tháng ISO YYYY-MM-DD từ các trường ngày của Crossref."""
    for field in ["published", "published-print", "published-online", "issued", "created"]:
        val = item.get(field)
        if isinstance(val, dict):
            parts = val.get("date-parts")
            if parts and len(parts) > 0 and len(parts[0]) > 0:
                p = parts[0]
                year = int(p[0])
                month = int(p[1]) if len(p) > 1 else 1
                day = int(p[2]) if len(p) > 2 else 1
                return f"{year:04d}-{month:02d}-{day:02d}"
            dt = val.get("date-time")
            if dt and isinstance(dt, str) and len(dt) >= 10:
                return dt[:10]
        elif isinstance(val, str) and len(val) >= 10:
            return val[:10]
    return "1970-01-01"


def _extract_authors(item: dict) -> list[str]:
    """Trích xuất danh sách họ tên tác giả từ Crossref."""
    raw_authors = item.get("author") or item.get("authors") or []
    authors: list[str] = []
    for a in raw_authors:
        if isinstance(a, dict):
            given = str(a.get("given", "")).strip()
            family = str(a.get("family", "")).strip()
            name = str(a.get("name", "")).strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
            elif name:
                authors.append(name)
        elif isinstance(a, str) and a.strip():
            authors.append(a.strip())
    return authors


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload thành danh sách PaperRecord chuẩn hóa.

    1. Duyệt qua items trong payload.
    2. Lấy DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuẩn hóa text và lọc bỏ các record không hợp lệ.
    4. Trả về list PaperRecord.
    """
    message = payload.get("message", {})
    if isinstance(message, dict):
        items = message.get("items", [])
    elif isinstance(payload.get("items"), list):
        items = payload["items"]
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    records: list[PaperRecord] = []
    for it in items:
        if not isinstance(it, dict):
            continue

        paper_id = str(it.get("DOI") or it.get("doi") or "").strip()
        raw_title = it.get("title", "")
        if isinstance(raw_title, list):
            title = " ".join(raw_title[0].split()).strip() if raw_title else ""
        else:
            title = " ".join(str(raw_title).split()).strip()

        # Bỏ qua record nếu thiếu DOI hoặc tiêu đề
        if not paper_id or not title:
            continue

        summary = _clean_abstract(it.get("abstract") or it.get("summary") or "")

        authors = _extract_authors(it)

        raw_cats = it.get("subject") or it.get("categories") or []
        if isinstance(raw_cats, str):
            raw_cats = [raw_cats]
        categories = [str(c).strip() for c in raw_cats if str(c).strip()]
        primary_category = categories[0] if categories else "General"

        pub_date = _extract_date(it)
        abs_url = str(it.get("URL") or f"https://doi.org/{paper_id}").strip()
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=pub_date,
                updated=pub_date,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gửi request tới Crossref API, lưu raw response, parse thành records.
    Hỗ trợ chế độ offline fallback từ local snapshot nếu mất mạng hoặc gặp lỗi API (429, 503).

    1. Nếu refresh_source=False và đã có local snapshot, nạp trực tiếp từ snapshot.
    2. Nếu cần kéo từ API, tạo params và gửi request có retry và polite User-Agent.
    3. Lưu raw response vào settings.paths.raw_api_response.
    4. Parse payload bằng parse_crossref_payload.
    5. Lưu records vào settings.paths.raw_records_json.
    """
    raw_api_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    payload: dict | None = None

    # Chế độ Dev / Offline: ưu tiên nạp từ local snapshot có sẵn nếu không yêu cầu refresh
    if not settings.refresh_source and raw_api_path.exists():
        logger.info("Dev/Offline mode: Loading Crossref response from local snapshot %s", raw_api_path)
        with raw_api_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
        }

        max_retries = 3
        last_error: Exception | None = None

        logger.info("Fetching Crossref records from %s with params %s", CROSSREF_API_URL, params)
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    CROSSREF_API_URL,
                    params=params,
                    headers=headers,
                    timeout=15,
                )
                if response.status_code == 200:
                    payload = response.json()
                    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
                    with raw_api_path.open("w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                        f.write("\n")
                    logger.info("Successfully fetched and saved raw response to %s", raw_api_path)
                    break
                if response.status_code in {429, 500, 502, 503, 504}:
                    wait_time = 2**attempt
                    logger.warning(
                        "Crossref API returned %s (attempt %d/%d). Retrying in %ds...",
                        response.status_code,
                        attempt + 1,
                        max_retries,
                        wait_time,
                    )
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
            except Exception as err:
                last_error = err
                logger.warning("Error fetching from Crossref API (attempt %d/%d): %s", attempt + 1, max_retries, err)
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)

        # Fallback về snapshot nếu API request thất bại
        if payload is None:
            if raw_api_path.exists():
                logger.warning("Live API failed. Falling back to offline snapshot %s: %s", raw_api_path, last_error)
                with raw_api_path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
            else:
                raise RuntimeError(
                    f"Failed to fetch Crossref records and no local snapshot available at {raw_api_path}"
                ) from last_error

    records = parse_crossref_payload(payload)

    # Lưu raw records đã parse để bảo toàn lineage
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_records_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info("Saved %d raw parsed records to %s", len(records), raw_records_path)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map thành danh sách PaperRecord."""
    target_path = Path(path)
    if not target_path.exists():
        raise FileNotFoundError(f"Raw records snapshot not found at: {target_path}")

    with target_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list of records in {target_path}, got {type(data).__name__}")

    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=item.get("primary_category", "General"),
                published=item["published"],
                updated=item.get("updated", item["published"]),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    return records
