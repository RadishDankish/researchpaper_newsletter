import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..config_loader import MAX_ABSTRACT_CHARS
from .http import clean_text


@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    authors: list = field(default_factory=list)
    published: datetime = None
    url: str = ""
    pdf_url: str = ""
    categories: list = field(default_factory=list)
    primary_category: str = ""
    source: str = "arxiv"
    doi: str = ""
    citations: int = 0
    influential_citations: int = 0
    upvotes: int = 0

    @property
    def s2_id(self):
        if self.doi:
            return f"DOI:{self.doi}"
        if self.source in ("arxiv", "huggingface"):
            return f"arXiv:{re.sub(r'v[0-9]+$', '', self.id)}"
        return ""

    @classmethod
    def from_arxiv(cls, result):
        short_id = result.get_short_id()
        return cls(
            id=short_id,
            title=clean_text(result.title),
            abstract=clean_text(result.summary)[:MAX_ABSTRACT_CHARS],
            authors=[a.name for a in result.authors],
            published=result.published,
            url=f"https://arxiv.org/abs/{short_id}",
            pdf_url=result.pdf_url,
            categories=list(result.categories or []),
            primary_category=result.primary_category,
            source="arxiv",
        )

    @classmethod
    def from_semantic_scholar(cls, row):
        external = row.get("externalIds") or {}
        arxiv_id = external.get("ArXiv")
        doi = external.get("DOI") or ""
        abstract = clean_text(row.get("abstract") or "")
        title = clean_text(row.get("title") or "")
        if not title or not abstract:
            return None
        published = None
        date_value = row.get("publicationDate") or (f"{row['year']}-01-01" if row.get("year") else None)
        if date_value:
            try:
                published = datetime.fromisoformat(date_value).replace(tzinfo=timezone.utc)
            except ValueError:
                published = None
        oa = row.get("openAccessPdf") or {}
        return cls(
            id=arxiv_id or doi or row.get("paperId", ""),
            title=title,
            abstract=abstract[:MAX_ABSTRACT_CHARS],
            authors=[clean_text(a.get("name", "")) for a in row.get("authors", []) if a.get("name")],
            published=published,
            url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (oa.get("url") or row.get("url") or ""),
            pdf_url=oa.get("url") or "",
            source="semanticscholar",
            doi=doi,
            citations=int(row.get("citationCount") or 0),
            influential_citations=int(row.get("influentialCitationCount") or 0),
        )

    def __repr__(self):
        return f"Paper({self.id!r}, {self.title!r})"


def utc_today():
    return datetime.now(timezone.utc).date()