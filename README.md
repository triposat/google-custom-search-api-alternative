# Google Custom Search JSON API Alternative

Google closed the Custom Search JSON API to new customers, with existing customers' access ending January 1, 2027. This repo moves Custom Search code to Google results fetched through the [Bright Data SERP API](https://brightdata.com/products/serp-api), with `cse.list()`-style parameters and `items` responses.

## Files

| File | What it does |
|---|---|
| `cse_to_serp.py` | `cse_list()` accepts Custom Search parameters and returns a response in Custom Search format (`items`, `queries.nextPage`) |
| `serp_batch.py` | Runs many queries in parallel, with a concurrency setting, a deadline per query, a cache, and counters for cache hits, empty results, and failures |
| `langchain_tool.py` | A LangChain tool that replaces `GoogleSearchAPIWrapper.results()` |
| `compare_baseline.py` | Scores each query from 0 to 1, by the share of saved Custom Search URLs that still appear in the new top 10 |
| `ai_overview_example.py` | Reads the AI Overview and People Also Ask questions from one query |
| `tests/` | Offline tests with a mocked HTTP transport. They need no API key |

## Setup

You need a free [Bright Data account](https://brightdata.com/cp/start), a SERP API zone, and an API key. The [SERP API quickstart](https://docs.brightdata.com/products/serp-api/quickstart) shows where to create the zone and find the key. Keep the zone's data format at Raw HTML, because the code asks for parsed JSON in each request.

The adapter runs on Python 3.9 and later. The LangChain tool needs Python 3.10 or later, and `requirements-langchain.txt` pins `langchain-core>=1.0,<2`.

```bash
python3 -m venv .venv && source .venv/bin/activate
export BRIGHTDATA_API_KEY="your-api-key"
export BRIGHTDATA_SERP_ZONE="serp_api1"
python -m pip install -r requirements.txt
```

On Windows PowerShell, use this block instead.

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
$env:BRIGHTDATA_API_KEY = "your-api-key"
$env:BRIGHTDATA_SERP_ZONE = "serp_api1"
python -m pip install -r requirements.txt
```

Replace both values with your own. `.env.example` lists the same two variables, for tools that load a `.env` file. For the LangChain tool, install `requirements-langchain.txt` instead.

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

| Custom Search JSON API | Google, through the SERP API |
|---|---|
| `q` | `q` |
| `num` (maximum 10) | Removed by Google. Each Google page contains about 10 results, so the adapter requests more pages |
| `start` (counts from 1) | `start` (counts from 0, in steps of 10) |
| `gl` (boosts results from a country) | `gl` (runs the search as a user in that country) |
| `hl` | `hl` |
| `siteSearch=example.com` | `site:example.com` added to `q` (`-site:` with `siteSearchFilter=e`) |
| `exactTerms=a b` | `"a b"` added to `q` |
| `excludeTerms=a` | `-"a"` added to `q` |
| `fileType=pdf` | `filetype:pdf` added to `q` |
| `dateRestrict=d7` | `tbs=qdr:d7`, and the same for `w`, `m`, and `y` |
| `safe=active` | `safe=active` |
| `searchType=image` | `udm=2` (Google Images) |

The adapter ignores `cx` with a warning, because Google search has no engine ID. If your engine searched a fixed list of sites, put them in the query as `(site:a.com OR site:b.com)`.

## Tests

The tests replace the HTTP transport with a mock, so they run without an API key and without network access.

```bash
python -m pip install pytest
python -m pytest
```
