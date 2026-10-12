from datetime import datetime, timezone

from ..config_loader import MAX_ABSTRACT_CHARS
from .base import Paper
from .http import clean_text, request_json

API_URL = "https://huggingface.co/api/daily_papers"


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def discover_huggingface(domain, max_results=25):
    payload = request_json(API_URL, params={"limit": max(max_results * 4, 100)})
    papers = []
    for entry in payload:
        raw = entry.get("paper") or {}
        arxiv_id = clean_text(raw.get("id") or "")
        title = clean_text(raw.get("title") or entry.get("title") or "")
        abstract = clean_text(raw.get("summary") or entry.get("summary") or "")
        if not arxiv_id or not title or not abstract:
            continue
        papers.append(
            Paper(
                id=arxiv_id,
                title=title,
                abstract=abstract[:MAX_ABSTRACT_CHARS],
                authors=[clean_text(a.get("name", "")) for a in raw.get("authors", []) if a.get("name")],
                published=_parse_datetime(raw.get("publishedAt") or entry.get("publishedAt")),
                url=f"https://arxiv.org/abs/{arxiv_id}",
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
                source="huggingface",
                upvotes=int(raw.get("upvotes") or entry.get("upvotes") or 0),
            )
        )
    return papers