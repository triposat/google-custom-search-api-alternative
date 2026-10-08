"""Offline tests for cse_to_serp.py. No API key or network needed."""

import json

import httpx
import pytest

import cse_to_serp


def fake_google(pages=5, per_page=9):
    """Return a handler that serves parsed Google pages of `per_page` results."""
    calls = []

    def handler(request):
        url = json.loads(request.content)["url"]
        start = int(url.split("start=")[1].split("&")[0]) if "start=" in url else 0
        calls.append(start)
        page = start // 10
        organic = [
            {"title": f"r{page}-{i}", "link": f"https://example.com/{page}/{i}"}
            for i in range(per_page)
        ] if page < pages else []
        nxt = (page + 1) * 10 if page + 1 < pages else None
        body = {"general": {}, "organic": organic,
                "pagination": {"next_page_start": nxt}}
        return httpx.Response(200, json=body)

    return handler, calls


@pytest.fixture
def transport(monkeypatch):
    def install(handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(cse_to_serp.httpx, "post", client.post)
        monkeypatch.setattr(cse_to_serp.time, "sleep", lambda s: None)
    return install


@pytest.mark.parametrize("num", [10, 5, 3, 20])
def test_next_page_chain_returns_every_result_once(transport, num):
    handler, _ = fake_google()
    transport(handler)
    seen, start = [], 1
    while start:
        res = cse_to_serp.cse_list(q="x", num=num, start=start)
        seen += [item["link"] for item in res["items"]]
        start = (res["queries"].get("nextPage") or [{}])[0].get("startIndex")
    assert len(seen) == 45
    assert len(set(seen)) == 45


def test_num_10_costs_one_request_per_call(transport):
    handler, calls = fake_google()
    transport(handler)
    res = cse_to_serp.cse_list(q="x", num=10)
    assert len(calls) == 1
    assert res["queries"]["nextPage"] == [{"startIndex": 11}]


def test_unmapped_parameter_raises(transport):
    transport(fake_google()[0])
    with pytest.raises(ValueError):
        cse_to_serp.cse_list(q="x", exactTerms="y")


def test_cx_is_ignored(transport):
    transport(fake_google()[0])
    assert cse_to_serp.cse_list(q="x", cx="abc")["items"]


def test_error_header_is_retried(transport):
    responses = iter([
        httpx.Response(200, text="error", headers={"x-brd-error": "test error"}),
        httpx.Response(200, json={"general": {}, "organic": [
            {"title": "t", "link": "https://a.com"}], "pagination": {}}),
    ])
    transport(lambda request: next(responses))
    assert cse_to_serp.cse_list(q="x")["items"][0]["link"] == "https://a.com"


def test_bad_key_fails_fast(transport):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, text="Invalid token")

    transport(handler)
    with pytest.raises(httpx.HTTPStatusError):
        cse_to_serp.cse_list(q="x")
    assert len(calls) == 1


def test_image_search_slices_one_response(transport):
    images = [{"original_image": f"https://img.example.com/{i}.jpg",
               "image_alt": f"alt {i}"} for i in range(100)]
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["url"])
        return httpx.Response(200, json={"general": {}, "images": images})

    transport(handler)
    res = cse_to_serp.cse_list(q="x", searchType="image", num=10, start=11)
    assert [i["link"] for i in res["items"]][0].endswith("/10.jpg")
    assert "udm=2" in calls[0] and len(calls) == 1
