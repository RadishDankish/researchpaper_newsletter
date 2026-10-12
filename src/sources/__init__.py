from .arxiv_source import discover_arxiv
from .base import Paper
from .biorxiv_source import discover_biorxiv
from .hf_source import discover_huggingface
from .scholar import fetch_citations, search_top_cited

__all__ = [
    "Paper",
    "discover_arxiv",
    "discover_biorxiv",
    "discover_huggingface",
    "fetch_citations",
    "search_top_cited",
]