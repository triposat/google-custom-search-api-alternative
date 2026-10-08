# Google Custom Search JSON API alternative

Companion code for the Bright Data article [Is There a Google Search API? Options After Custom Search](https://brightdata.com/blog/web-data/is-there-a-google-search-api).

Google closed the Custom Search JSON API to new customers, and existing customers lose access on January 1, 2027. This repo moves Custom Search code to Google results fetched through the [Bright Data SERP API](https://brightdata.com/products/serp-api), with the same request parameters and response shape where possible.

## Files

| File | What it does |
|---|---|
| `cse_to_serp.py` | `cse_list()` accepts Custom Search parameters and returns a Custom Search-shaped response (`items`, `queries.nextPage`) |
| `serp_batch.py` | Runs many queries with a concurrency limit, a deadline per query, a cache, and counters for empty and failed queries |
| `langchain_tool.py` | A LangChain tool that replaces `GoogleSearchAPIWrapper.results()` |
| `compare_baseline.py` | Scores how many saved Custom Search URLs still appear in the new top 10 |
| `ai_overview_example.py` | Reads the AI Overview and People Also Ask blocks from one query |
| `tests/` | Offline tests with a mocked HTTP transport. They need no API key |

## Setup

You need a Bright Data account, a SERP API zone, and an API key. The [SERP API quickstart](https://docs.brightdata.com/products/serp-api/send-your-first-request) shows where to create the zone and find the key.

The adapter needs Python 3.9 or newer. The LangChain tool needs Python 3.10 or newer, because `langchain-core` does.

```bash
export BRIGHTDATA_API_KEY="your-api-key"
export BRIGHTDATA_SERP_ZONE="serp_api1"
python -m pip install -r requirements.txt
```

Replace both values with your own. `.env.example` lists the same two variables. For the LangChain tool, install `requirements-langchain.txt` instead.

## Usage

Run the adapter's sample query:

```bash
python cse_to_serp.py
```

Swap a Custom Search call site:

```python
from cse_to_serp import cse_list

# Before: Google API client
# res = service.cse().list(q=query, cx=CX, num=10).execute()

# After: same items shape, no engine ID, gl and hl set explicitly
res = cse_list(q=query, num=10, gl="us", hl="en")
for item in res["items"]:
    print(item["title"], item["link"])
```

## Parameter mapping

| Custom Search JSON API | Google search URL through the SERP API |
|---|---|
| `q` | `q` |
| `num` (maximum 10) | No equivalent. Google returns about 10 results per page, so the adapter requests more pages |
| `start` (counts from 1) | `start` (counts from 0, in steps of 10) |
| `gl` (boosts results from a country) | `gl` (runs the search as that country) |
| `hl` | `hl` |
| `siteSearch=example.com` | `site:example.com` added to `q` |
| `dateRestrict=d7` | `tbs=qdr:d7` |
| `safe=active` | `safe=active` |
| `searchType=image` | `udm=2` (Google Images) |

The adapter ignores `cx`, because there is no engine on the Google side. If your engine searched a fixed list of sites, put them in the query as `(site:a.com OR site:b.com)`.

## Behavior to know

- The code reads Bright Data's `x-brd-error` headers before parsing and retries after at least 15 seconds, as the [SERP API error catalog](https://docs.brightdata.com/products/serp-api/debugging) describes.
- With `num=10`, following `nextPage` costs 1 request per call.
- Catch `httpx.HTTPError`, `ValueError`, and `RuntimeError` where you previously caught `HttpError` from the Google client.

## Tests

The tests replace the HTTP transport with a mock, so they run without an API key and without network access:

```bash
python -m pip install pytest
python -m pytest
```
