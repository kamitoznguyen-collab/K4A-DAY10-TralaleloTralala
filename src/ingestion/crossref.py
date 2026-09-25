from __future__ import annotations

import html
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_USER_AGENT = "day10-data-observability-lab/0.1 (student project)"
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_REQUEST_TIMEOUT_SECONDS = 30


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


_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: object) -> str:
    """Strip JATS/HTML tags, unescape entities and collapse whitespace."""
    if value is None:
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    text = html.unescape(_TAG_RE.sub(" ", str(value)))
    return normalize_whitespace(text)


def _author_name(author: dict) -> str:
    name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
    return _clean_text(name or author.get("name"))


def _date_parts_to_iso(field: object) -> str:
    """Convert Crossref `{"date-parts": [[Y, M, D]]}` to `YYYY-MM-DD` (missing parts default to 1)."""
    if not isinstance(field, dict):
        return ""
    parts = (field.get("date-parts") or [[]])[0] or []
    if not parts or parts[0] is None:
        return ""
    year, month, day = (list(parts) + [1, 1])[:3]
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def _date_time_to_iso(field: object) -> str:
    """Take the date portion of a Crossref `{"date-time": "...T..Z"}` field."""
    if not isinstance(field, dict):
        return ""
    return str(field.get("date-time") or "")[:10]


def _first_date(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _date_parts_to_iso(item.get(key)) or _date_time_to_iso(item.get(key))
        if value:
            return value
    return ""


def _pdf_link(item: dict) -> str:
    for link in item.get("link") or []:
        if isinstance(link, dict) and "pdf" in str(link.get("content-type", "")).lower():
            url = str(link.get("URL") or "").strip()
            if url:
                return url
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref `/works` payload into a list of `PaperRecord`.

    Records without a DOI, title or abstract are dropped, as are duplicate DOIs.
    """
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    seen: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _clean_text(item.get("DOI"))
        title = _clean_text(item.get("title"))
        summary = _clean_text(item.get("abstract"))
        if not doi or not title or not summary or doi.lower() in seen:
            continue
        seen.add(doi.lower())

        authors = [name for name in (_author_name(a) for a in item.get("author") or [] if isinstance(a, dict)) if name]
        categories = list(dict.fromkeys(c for c in (_clean_text(s) for s in item.get("subject") or []) if c))

        published = _first_date(item, ("published", "published-print", "published-online", "issued", "created"))
        updated = _first_date(item, ("updated", "deposited", "indexed", "created")) or published

        abs_url = str(item.get("URL") or "").strip() or f"https://doi.org/{doi}"
        pdf_url = _pdf_link(item) or abs_url

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {doi}",
            )
        )

    return records


def _request_crossref(settings: Settings) -> dict:
    """Call the Crossref `/works` endpoint, retrying on rate limits and transient server errors."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                CROSSREF_WORKS_URL,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code not in _RETRY_STATUS_CODES:
                response.raise_for_status()
            last_error = requests.HTTPError(f"Crossref returned HTTP {response.status_code}", response=response)
            retry_after = response.headers.get("Retry-After", "")
            if attempt < _MAX_ATTEMPTS and retry_after.isdigit():
                time.sleep(min(int(retry_after), 30))
                continue
        if attempt < _MAX_ATTEMPTS:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Crossref request failed after {_MAX_ATTEMPTS} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Load Crossref records, preserving the raw response and the parsed records in `data/raw/`.

    By default the offline snapshot at `settings.paths.raw_api_response` is used so every run sees the
    same corpus. With `REFRESH_SOURCE=1` the live API is called; a successful response overwrites the
    snapshot, and any failure (network, 429/503 after retries) falls back to the existing snapshot.
    """
    snapshot_path = settings.paths.raw_api_response
    payload: dict | None = None

    if settings.refresh_source or not snapshot_path.exists():
        try:
            payload = _request_crossref(settings)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            if not snapshot_path.exists():
                raise RuntimeError(f"Crossref API unavailable and no snapshot at {snapshot_path}") from exc
            print(f"[crossref] API unavailable ({exc}); falling back to snapshot {snapshot_path}")
        else:
            write_json(snapshot_path, payload)

    if payload is None:
        payload = read_json(snapshot_path)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read a JSON list written by `fetch_source_records` back into `PaperRecord` objects."""
    return [PaperRecord(**row) for row in read_json(path)]
