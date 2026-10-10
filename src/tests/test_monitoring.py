# ai-generated: 100% - Codex wrote controlled upstream and histogram regression tests.
import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from svcdesk import main
from svcdesk.monitoring import REQUEST_DURATION


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "tickets.db"))
    with TestClient(main.app) as client:
        yield client


def instrumented_count(route, status):
    for family in REQUEST_DURATION.collect():
        for sample in family.samples:
            if sample.name.endswith("_count") and sample.labels["http_route"] == route and sample.labels["http_response_status_code"] == str(status):
                return sample.value
    return 0


def test_search_exactly_one_encoded_call_and_pass_through(client):
    calls = []
    hits = [{"id": "a", "title": "An unchanged result", "score": 0.123}]
    async def upstream(request):
        calls.append(request)
        await asyncio.sleep(0.015)
        return httpx.Response(200, json={"hits": hits})
    replacement = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    original = main.app.state.kb_client
    main.app.state.kb_client = replacement
    before = instrumented_count("/kb/search", 200)
    try:
        response = client.get("/kb/search", params={"q": "vpn & wifi / café"})
        assert response.status_code == 200
        assert response.json() == {"query": "vpn & wifi / café", "hits": hits}
        assert len(calls) == 1 and calls[0].url.params["q"] == "vpn & wifi / café"
        assert instrumented_count("/kb/search", 200) == before + 1
    finally:
        main.app.state.kb_client = original
        asyncio.run(replacement.aclose())


@pytest.mark.parametrize("q", [None, "", "x" * 201])
def test_bad_query_observed_as_template(client, q):
    before = instrumented_count("/kb/search", 422)
    response = client.get("/kb/search", params={} if q is None else {"q": q})
    assert response.status_code == 422 and "error" in response.json()
    assert instrumented_count("/kb/search", 422) == before + 1


@pytest.mark.parametrize("failure", ["503", "timeout", "connection"])
def test_upstream_failures_no_retry(client, failure):
    calls = []
    async def upstream(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("test", request=request)
        if failure == "connection":
            raise httpx.ConnectError("test", request=request)
        return httpx.Response(503)
    replacement = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    original = main.app.state.kb_client
    main.app.state.kb_client = replacement
    try:
        response = client.get("/kb/search?q=force-error-test")
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "upstream_unavailable"
        assert len(calls) == 1
    finally:
        main.app.state.kb_client = original
        asyncio.run(replacement.aclose())


def test_metric_labels_have_no_ids_or_query_values(client):
    client.get("/tickets/private-ticket-id")
    client.get("/not-real/private-route-id")
    client.get("/health?private-query=value")
    response = client.get("/metrics", headers={"Accept": "text/plain;version=0.0.4"})
    assert response.headers["content-type"].startswith("text/plain")
    assert 'http_route="/tickets/{ticket_id}"' in response.text
    assert 'http_route="unmatched"' in response.text
    assert all(secret not in response.text for secret in ["private-ticket-id", "private-route-id", "private-query"])
