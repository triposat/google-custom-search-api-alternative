# Google Custom Search JSON API alternative

Companion code for [Is There a Google Search API? Options After Custom Search](https://brightdata.com/blog/web-data/is-there-a-google-search-api) on the Bright Data blog.

Google closed the Custom Search JSON API to new customers, with access for existing customers ending on January 1, 2027. This repo moves Custom Search code to Google results fetched through the [Bright Data SERP API](https://brightdata.com/products/serp-api), with `cse.list()`-style parameters and `items` responses.

## Files

| File | What it does |
|---|---|
| `cse_to_serp.py` | `cse_list()` accepts Custom Search parameters and returns a Custom Search-shaped response (`items`, `queries.nextPage`) |
| `serp_batch.py` | Runs many queries in parallel, with a concurrency setting, a deadline per query, a cache, and counters for cache hits, empty results, and failures |
| `langchain_tool.py` | A LangChain tool that replaces `GoogleSearchAPIWrapper.results()` |
| `compare_baseline.py` | Scores how many saved Custom Search URLs still appear in the new top 10 |
| `ai_overview_example.py` | Reads the AI Overview and People Also Ask blocks from one query |
| `tests/` | Offline tests with a mocked HTTP transport. They need no API key |

## Setup

You need a Bright Data account, a SERP API zone, and an API key. The [SERP API quickstart](https://docs.brightdata.com/products/serp-api/quickstart) shows where to create the zone and find the key.

The adapter runs on Python 3.9 and later. For the LangChain tool, `requirements-langchain.txt` pins `langchain-core>=1.0,<2`, and pip checks your Python version against it.

```bash
python -m venv .venv && source .venv/bin/activate
export BRIGHTDATA_API_KEY="your-api-key"
export BRIGHTDATA_SERP_ZONE="serp_api1"
python -m pip install -r requirements.txt
```

Replace both values with your own. `.env.example` lists the same two variables. For the LangChain tool, install `requirements-langchain.txt` instead.

## Usage

Run the adapter's sample query.

```bash
python cse_to_serp.py
```

Replace a Custom Search call site.

```python
from cse_to_serp import cse_list

# Before, with the Google API client
# res = service.cse().list(q=query, cx=CX, num=10).execute()

# After, with the same core items fields, no engine ID, and gl and hl set
res = cse_list(q=query, num=10, gl="us", hl="en")
for item in res["items"]:
    print(item["title"], item["link"])
```

Where you caught `HttpError`, catch `(httpx.HTTPError, ValueError, RuntimeError)` instead.

## Parameter mapping

| Custom Search JSON API | Google search URL through the SERP API |
|---|---|
| `q` | `q` |
| `num` (maximum 10) | Dropped by Google. Each Google page holds about 10 results, so the adapter requests more pages |
| `start` (counts from 1) | `start` (counts from 0, in steps of 10) |
| `gl` (boosts results from a country) | `gl` (runs the search as that country) |
| `hl` | `hl` |
| `siteSearch=example.com` | `site:example.com` added to `q` (`-site:` with `siteSearchFilter=e`) |
| `exactTerms=a b` | `"a b"` added to `q` |
| `excludeTerms=a` | `-"a"` added to `q` |
| `fileType=pdf` | `filetype:pdf` added to `q` |
| `dateRestrict=d7` | `tbs=qdr:d7` |
| `safe=active` | `safe=active` |
| `searchType=image` | `udm=2` (Google Images) |

The adapter ignores `cx` with a warning, because there is no engine on the Google side. If your engine searched a fixed list of sites, put them in the query as `(site:a.com OR site:b.com)`.

## Tests

The tests replace the HTTP transport with a mock, so they run without an API key and without network access.

```bash
python -m pip install pytest
python -m pytest
```
