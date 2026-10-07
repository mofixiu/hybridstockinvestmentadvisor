"""Compatibility stub for legacy experiments; simulated sentiment is disabled."""


def scrape_twitter_mock(query: str) -> list[dict]:
    """Return no posts so synthetic content cannot enter signal research."""
    del query
    return []
