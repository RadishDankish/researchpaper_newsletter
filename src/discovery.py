import math
import time
from datetime import datetime, timezone

from .config_loader import (
    ESTABLISHED_MONTHS,
    ESTABLISHED_PER_DOMAIN,
    Domain,
)
from .sources import (
    discover_arxiv,
    discover_biorxiv,
    discover_huggingface,
    search_top_cited,
)

MAX_RESULTS_PER_DOMAIN = 25

# Ranking weights — tune these to change how papers are scored.
KEYWORD_WEIGHT = 2.0
RECENCY_WEIGHT = 3.0
RECENCY_DECAY_DAYS = 30.0
CATEGORY_BONUS = 1.5
CITATION_WEIGHT = 3.0
UPVOTE_WEIGHT = 1.5
CITATION_SATURATION_LOG10 = 2.0
UPVOTE_SATURATION_LOG10 = 1.5
EXTERNAL_MIN_KEYWORD_HITS = 1
SCHOLAR_REQUEST_SPACING_SECONDS = 2.0

SOURCE_DISPATCH = {
    "arxiv": discover_arxiv,
    "huggingface": discover_huggingface,
    "biorxiv": discover_biorxiv,
    "medrxiv": discover_biorxiv,
}


def keyword_hits(paper, domain):
    text = f"{paper.title} {paper.abstract}".lower()
    return sum(1 for kw in domain.keywords if kw in text)


def _is_relevant(paper, domain):
    if paper.source == "arxiv":
        return True
    return keyword_hits(paper, domain) >= EXTERNAL_MIN_KEYWORD_HITS


def _dedupe(papers):
    merged = {}
    for paper in papers:
        existing = merged.get(paper.id)
        if existing is None:
            merged[paper.id] = paper
            continue
        existing.upvotes = max(existing.upvotes, paper.upvotes)
        existing.citations = max(existing.citations, paper.citations)
        if existing.source != "arxiv" and paper.source == "arxiv":
            paper.upvotes = existing.upvotes
            paper.citations = existing.citations
            merged[paper.id] = paper
    return list(merged.values())


def discover(domain: Domain, max_results=MAX_RESULTS_PER_DOMAIN):
    papers = []
    for source_name in domain.sources:
        fetch = SOURCE_DISPATCH.get(source_name)
        if fetch is None:
            print(f"[{domain.name}] unknown source '{source_name}', skipping")
            continue
        kwargs = {"server": source_name} if source_name in ("biorxiv", "medrxiv") else {}
        try:
            found = fetch(domain, max_results=max_results, **kwargs)
        except Exception as exc:
            print(f"[{domain.name}] {source_name} discovery failed: {exc}")
            continue
        relevant = [p for p in found if _is_relevant(p, domain)]
        print(f"[{domain.name}] {source_name}: {len(relevant)} relevant of {len(found)}")
        papers.extend(relevant)
    return _dedupe(papers)


def matched_domain(paper, domains):
    for domain in domains:
        if paper.primary_category and paper.primary_category in domain.categories:
            return domain.name
    for domain in domains:
        if keyword_hits(paper, domain):
            return domain.name
    return domains[0].name if domains else ""


def discover_established(domains, months=ESTABLISHED_MONTHS, per_domain=ESTABLISHED_PER_DOMAIN):
    papers = {}
    for index, domain in enumerate(domains):
        if index:
            time.sleep(SCHOLAR_REQUEST_SPACING_SECONDS)
        query = domain.query or domain.name
        try:
            found = search_top_cited(query, months=months, limit=per_domain)
        except Exception as exc:
            print(f"[{domain.name}] top-cited search failed: {exc}")
            continue
        kept = 0
        for paper in found:
            if paper is None:
                continue
            if paper.id not in papers:
                papers[paper.id] = paper
                kept += 1
        print(f"[{domain.name}] top-cited: {kept} new of {len(found)}")
    print(f"[established] {len(papers)} unique candidates from the last {months} month(s)")
    return list(papers.values())


def rank_established(papers):
    return sorted(
        papers,
        key=lambda p: (p.citations, p.influential_citations, p.upvotes),
        reverse=True,
    )


def select_established(papers, domains, already_sent):
    for paper in rank_established(papers):
        if paper.id not in already_sent:
            return paper, matched_domain(paper, domains)
    return None, None


def score_paper(paper, domain, now=None):
    now = now or datetime.now(timezone.utc)
    age_days = max((now - paper.published).days, 0) if paper.published else 0
    recency_score = max(0.0, 1.0 - age_days / RECENCY_DECAY_DAYS)
    category_bonus = CATEGORY_BONUS if paper.primary_category in domain.categories else 0.0
    citation_score = min(math.log10(paper.citations + 1) / CITATION_SATURATION_LOG10, 1.0)
    upvote_score = min(math.log10(paper.upvotes + 1) / UPVOTE_SATURATION_LOG10, 1.0)
    return (
        keyword_hits(paper, domain) * KEYWORD_WEIGHT
        + recency_score * RECENCY_WEIGHT
        + category_bonus
        + citation_score * CITATION_WEIGHT
        + upvote_score * UPVOTE_WEIGHT
    )


def rank_papers(papers, domains):
    best = {}
    for paper in papers:
        scored = [score_paper(paper, d) for d in domains] or [0.0]
        score = max(scored)
        matched = ""
        if domains:
            matched = next(d.name for d, s in zip(domains, scored) if s == score)
        best[paper.id] = (score, matched, paper)
    ranked = sorted(best.values(), key=lambda t: t[0], reverse=True)
    return [(paper, round(score, 2), matched) for score, matched, paper in ranked]