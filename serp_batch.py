"""Run many Google queries through the Bright Data SERP API.

Adds bounded concurrency, a deadline per query, a cache with a time
limit, and counters for empty and failed queries.
"""

import asyncio
import os
import time
from urllib.parse import urlencode

import httpx

API_URL = "https://api.brightdata.com/request"
API_KEY = os.environ["BRIGHTDATA_API_KEY"]
ZONE = os.environ.get("BRIGHTDATA_SERP_ZONE", "serp_api1")
RETRY_STATUSES = {429, 500, 502, 503, 504}

CACHE: dict[str, tuple[float, dict]] = {}  # swap in Redis to share it across workers
STATS = {"queries": 0, "cache_hits": 0, "empty": 0, "failed": 0}


async def fetch(client: httpx.AsyncClient, params: dict, ttl: int) -> dict:
    url = "https://www.google.com/search?" + urlencode(params)
    cached = CACHE.get(url)
    if cached and time.monotonic() - cached[0] < ttl:
        STATS["cache_hits"] += 1
        return cached[1]
    body = {"zone": ZONE, "url": url, "format": "raw"}
    for attempt in range(4):
        try:
            resp = await client.post(API_URL, json=body)
        except httpx.TransportError:  # timeout or dropped connection
            if attempt == 3:
                raise
            await asyncio.sleep(16 + attempt * 10)
            continue
        error = (resp.headers.get("x-brd-error")  # API-level errors
                 or resp.headers.get("x-brd-err-msg"))  # proxy-level errors
        if resp.status_code == 200 and not error:
            page = resp.json()
            if "general" not in page:  # not a parsed results page
                raise ValueError("Unexpected response: " + resp.text[:200])
            if page.get("organic"):
                CACHE[url] = (time.monotonic(), page)
            else:
                STATS["empty"] += 1
            return page
        fatal = not error and resp.status_code not in RETRY_STATUSES
        if fatal or attempt == 3:
            resp.raise_for_status()
            break
        await asyncio.sleep(16 + attempt * 10)  # back off before retrying
    code = (resp.headers.get("x-brd-error-code")  # maps to the error catalog
            or resp.headers.get("x-brd-err-code"))
    raise RuntimeError(f"SERP API error {code}: {error or resp.status_code}")


async def search_many(queries, concurrency=20, deadline=150,
                      ttl=6 * 3600, **params) -> dict:
    """Return {query: parsed page or None}. None means it failed."""
    limit = asyncio.Semaphore(concurrency)
    headers = {"Authorization": f"Bearer {API_KEY}"}

    async def one(client, query):
        STATS["queries"] += 1
        async with limit:
            try:
                page = await asyncio.wait_for(
                    fetch(client, {"q": query, "brd_json": 1, **params}, ttl),
                    timeout=deadline,  # caps the total time for one query
                )
                return query, page
            except (asyncio.TimeoutError, httpx.HTTPError, ValueError,
                    RuntimeError):
                STATS["failed"] += 1
                return query, None

    async with httpx.AsyncClient(headers=headers, timeout=60) as client:
        pairs = await asyncio.gather(*(one(client, q) for q in queries))
    return dict(pairs)


if __name__ == "__main__":
    queries = [
        "httpx timeout configuration", "python asyncio semaphore",
        "postgres connection pooling", "redis cache ttl",
        "kubernetes liveness probe", "nginx rate limiting",
        "python dataclass vs pydantic", "git rebase vs merge",
        "docker multi stage build", "sql window functions",
    ]
    asyncio.run(search_many(queries, gl="us", hl="en"))
    asyncio.run(search_many(queries, gl="us", hl="en"))  # cache pass
    print(STATS)
