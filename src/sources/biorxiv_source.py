from datetime import datetime, timedelta, timezone

from ..config_loader import MAX_ABSTRACT_CHARS
from .base import Paper, utc_today
from .http import request_json, strip_markup

API_URL = "https://api.biorxiv.org/details/{server}/{start}/{end}/{cursor}"
PAGE_SIZE = 30
LOOKBACK_DAYS = 2
MAX_PAGES = 3


NEW_RESULT_TYPES = ("new result", "new results")


def _parse_datetime(value):
    if not value or str(value).strip().upper() in ("NA", "N/A", "NONE"):
        return None
    for fmt in (None, "%Y-%m-%d"):
        try:
            if fmt is None:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            else:
                parsed = datetime.strptime(str(value)[:10], fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def discover_biorxiv(domain, max_results=25, server="biorxiv"):
    end = utc_today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    papers = []
    for cursor in range(0, MAX_PAGES * PAGE_SIZE, PAGE_SIZE):
        url = API_URL.format(server=server, start=start, end=end, cursor=cursor)
        payload = request_json(url)
        collection = payload.get("collection") or []
        for raw in collection:
            if raw.get("type") not in NEW_RESULT_TYPES:
                continue
            doi = (raw.get("doi") or "").strip()
            title = strip_markup(raw.get("title"))
            abstract = strip_markup(raw.get("abstract"))
            if not doi or not title or not abstract:
                continue
            authors = [a.strip() for a in (raw.get("authors") or "").split(",") if a.strip()]
            published = _parse_datetime(raw.get("published")) or _parse_datetime(raw.get("date"))
            papers.append(
                Paper(
                    id=doi,
                    title=title,
                    abstract=abstract[:MAX_ABSTRACT_CHARS],
                    authors=authors,
                    published=published,
                    url=f"https://www.biorxiv.org/content/{doi}",
                    categories=[raw["category"]] if raw.get("category") else [],
                    primary_category=raw.get("category") or "",
                    source=server,
                    doi=doi,
                )
            )
        if len(papers) >= max_results or len(collection) < PAGE_SIZE:
            break
    return papers