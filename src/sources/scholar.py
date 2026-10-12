import calendar
from datetime import date, datetime, timezone

from ..config_loader import env
from .base import Paper
from .http import request_json

BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "citationCount,influentialCitationCount"
SEARCH_FIELDS = (
    "title,abstract,year,publicationDate,citationCount,influentialCitationCount,"
    "authors,externalIds,openAccessPdf,url,venue"
)
BATCH_LIMIT = 500


def _headers():
    headers = {}
    api_key = env("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def fetch_citations(papers, enabled=True):
    if not enabled:
        return 0
    targets = [(p, p.s2_id) for p in papers if p.s2_id]
    if not targets:
        return 0
    enriched = 0
    for start in range(0, len(targets), BATCH_LIMIT):
        chunk = targets[start : start + BATCH_LIMIT]
        payload = {"ids": [s2_id for _, s2_id in chunk]}
        results = request_json(
            BATCH_URL,
            params={"fields": FIELDS},
            json_body=payload,
            headers=_headers(),
            timeout=90,
        )
        if not isinstance(results, list):
            raise RuntimeError(f"Unexpected Semantic Scholar response: {type(results).__name__}")
        for (paper, _), entry in zip(chunk, results):
            if not entry:
                continue
            paper.citations = int(entry.get("citationCount") or 0)
            paper.influential_citations = int(entry.get("influentialCitationCount") or 0)
            enriched += 1
    return enriched


def months_ago_date(months):
    today = datetime.now(timezone.utc).date()
    index = today.year * 12 + (today.month - 1) - months
    year, month = divmod(index, 12)
    day = min(today.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day)


def search_top_cited(query, months=3, limit=25):
    start = months_ago_date(months)
    end = datetime.now(timezone.utc).date()
    params = {
        "query": query,
        "fields": SEARCH_FIELDS,
        "sort": "citationCount:desc",
        "publicationDateOrYear": f"{start.isoformat()}:{end.isoformat()}",
    }
    payload = request_json(
        SEARCH_URL, params=params, headers=_headers(), timeout=90, retries=5
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Semantic Scholar search response: {type(payload).__name__}")
    rows = payload.get("data") or []
    return [Paper.from_semantic_scholar(r) for r in rows[:limit]]