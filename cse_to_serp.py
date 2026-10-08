"""Replace Google Custom Search JSON API calls with the Bright Data SERP API.

Same cse.list() parameters and items shape.
"""

import os
import time
from urllib.parse import urlencode, urlparse

import httpx

API_URL = "https://api.brightdata.com/request"
API_KEY = os.environ["BRIGHTDATA_API_KEY"]
ZONE = os.environ.get("BRIGHTDATA_SERP_ZONE", "serp_api1")
RETRY_STATUSES = {429, 500, 502, 503, 504}


def fetch_serp(params: dict, attempts: int = 4, timeout: float = 60) -> dict:
    """Fetch one Google results page as parsed JSON."""
    url = "https://www.google.com/search?" + urlencode(params)
    body = {"zone": ZONE, "url": url, "format": "raw"}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    for attempt in range(attempts):
        resp = httpx.post(API_URL, json=body, headers=headers, timeout=timeout)
        error = (resp.headers.get("x-brd-error")  # API-level errors
                 or resp.headers.get("x-brd-err-msg"))  # proxy-level errors
        if resp.status_code == 200 and not error:
            page = resp.json()
            if "general" not in page:  # not a parsed results page
                raise ValueError("Unexpected response: " + resp.text[:200])
            return page
        if not error and resp.status_code not in RETRY_STATUSES:
            break  # wrong key, zone, or URL: retrying will not help
        if attempt < attempts - 1:
            # Back off before resending the same query.
            time.sleep(16 + attempt * 10)
    resp.raise_for_status()
    raise RuntimeError(f"SERP API error: {error or resp.status_code}")


def cse_list(q, num=10, start=1, gl=None, hl=None, siteSearch=None,
             siteSearchFilter="i", exactTerms=None, excludeTerms=None,
             fileType=None, dateRestrict=None, safe="off", searchType=None,
             attempts=4, timeout=60, **extra):
    """Accept cse.list() parameters, return a cse.list()-shaped dict."""
    extra.pop("cx", None)  # no engine ID: every call searches Google
    if extra:  # fail loudly instead of dropping a filter
        raise TypeError(f"No mapping for: {sorted(extra)}")
    if exactTerms:  # Custom Search filters become Google search operators
        q = f'{q} "{exactTerms}"'
    if excludeTerms:
        q = f'{q} -"{excludeTerms}"'
    if fileType:
        q = f"{q} filetype:{fileType}"
    if siteSearch:
        exclude = "-" if siteSearchFilter == "e" else ""
        q = f"{q} {exclude}site:{siteSearch}"
    params = {"q": q, "brd_json": 1}  # brd_json=1 returns parsed JSON
    if gl:
        params["gl"] = gl
    if hl:
        params["hl"] = hl
    if safe == "active":
        params["safe"] = "active"
    if dateRestrict:  # "d7" -> qdr:d7 (past 7 days), "m6" -> qdr:m6
        params["tbs"] = "qdr:" + dateRestrict
    if searchType == "image":
        return image_list(params, num, start, attempts, timeout)
    if searchType:
        raise ValueError(f"No mapping for: searchType={searchType}")

    # Custom Search counts from 1 (start=11 is page 2), Google from 0
    # (start=10 is page 2). Track each result's Google position.
    first = start - 1
    offset = first // 10 * 10  # the Google page that holds `start`
    items, next_start = [], None
    for _ in range(-(-(num + first - offset) // 10)):  # 1 request per page
        params["start"] = offset
        page = fetch_serp(params, attempts, timeout)
        for i, result in enumerate(page.get("organic", [])):
            position = offset + i
            if position < first or not result.get("link"):
                continue
            if len(items) == num:
                next_start = position + 1  # back to 1-based
                break
            items.append({
                "title": result.get("title", ""),
                "link": result["link"],
                "snippet": result.get("description", ""),
                "displayLink": urlparse(result["link"]).netloc,
            })
        if next_start:
            break
        offset = (page.get("pagination") or {}).get("next_page_start")
        if not offset:  # Google has no further pages for this query
            break
    else:
        next_start = offset + 1  # continue at the next Google page

    response = {"items": items, "queries": {}}
    if next_start:
        response["queries"]["nextPage"] = [{"startIndex": next_start}]
    return response


def image_list(params, num, start, attempts, timeout):
    """Google Images: one request returns the whole image grid."""
    params["udm"] = 2
    page = fetch_serp(params, attempts, timeout)
    images = [i for i in page.get("images") or [] if i.get("original_image")]
    items = [{
        "title": image.get("image_alt", ""),
        "link": image["original_image"],
        "snippet": image.get("image_alt", ""),
        "displayLink": urlparse(image["original_image"]).netloc,
    } for image in images[start - 1:start - 1 + num]]
    response = {"items": items, "queries": {}}
    if start - 1 + num < len(images):
        response["queries"]["nextPage"] = [{"startIndex": start + num}]
    return response


if __name__ == "__main__":
    res = cse_list("httpx timeout configuration", num=10,
                   gl="us", hl="en")
    for i, item in enumerate(res["items"], start=1):
        print(i, item["displayLink"], "|", item["title"][:60])
