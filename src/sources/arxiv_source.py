import arxiv

from .base import Paper


def discover_arxiv(domain, max_results=25):
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
    return [Paper.from_arxiv(r) for r in client.results(search)]