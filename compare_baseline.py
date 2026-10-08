"""Compare saved Custom Search results with new SERP API results."""

from urllib.parse import urlparse


def normalize(url: str) -> str:
    parts = urlparse(url)
    key = parts.netloc.lower().removeprefix("www.") + parts.path.rstrip("/")
    return key + ("?" + parts.query if parts.query else "")


def top_k_overlap(old_links: list, new_links: list, k: int = 10) -> float:
    """Share of the old top-k URLs that also appear in the new top-k."""
    old = {normalize(link) for link in old_links[:k]}
    new = {normalize(link) for link in new_links[:k]}
    return len(old & new) / len(old) if old else 1.0
