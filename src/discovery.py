import arxiv

from .config_loader import Domain, MAX_ABSTRACT_CHARS

MAX_RESULTS_PER_DOMAIN = 25


class Paper:
    def __init__(self, result: arxiv.Result):
        self.id = result.get_short_id()
        self.title = " ".join(result.title.split())
        self.abstract = " ".join(result.summary.split())[:MAX_ABSTRACT_CHARS]
        self.authors = [a.name for a in result.authors]
        self.published = result.published
        self.updated = result.updated
        self.pdf_url = result.pdf_url
        abs_url = result.get_short_id()
        self.url = f"https://arxiv.org/abs/{abs_url}"
        self.categories = result.categories or []
        self.primary_category = result.primary_category

    def __repr__(self):
        return f"Paper({self.id!r}, {self.title!r})"


def discover(domain: Domain, max_results=MAX_RESULTS_PER_DOMAIN):
    query_parts = []
    if domain.categories:
        cats = " OR ".join(f"cat:{c}" for c in domain.categories)
        query_parts.append(f"({cats})")
    if domain.query:
        query_parts.append(f"(all:{domain.query.replace(' ', ' AND all:')})")
    search_query = " AND ".join(query_parts) if query_parts else "*"
    client = arxiv.Client(page_size=max_results, delay_seconds=3.5)
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    return [Paper(r) for r in client.results(search)]


def score_paper(paper, domain, now=None):
    from datetime import datetime, timezone

    now = now or datetime.now(timezone.utc)
    text = f"{paper.title} {paper.abstract}".lower()
    keyword_hits = sum(1 for kw in domain.keywords if kw in text)
    age_days = max((now - paper.published).days, 0)
    recency_score = max(0.0, 1.0 - age_days / 30.0)
    category_bonus = 1.5 if paper.primary_category in domain.categories else 0.0
    return keyword_hits * 2.0 + recency_score * 3.0 + category_bonus


def rank_papers(papers, domains):
    best = {}
    for paper in papers:
        score = max(score_paper(paper, d) for d in domains) if domains else 0.0
        matched = next(
            (d.name for d in domains if score_paper(paper, d) >= score), ""
        )
        best[paper.id] = (score, matched, paper)
    ranked = sorted(best.values(), key=lambda t: t[0], reverse=True)
    return [(paper, round(score, 2), matched) for score, matched, paper in ranked]
