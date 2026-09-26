# ai-generated: 100% - Codex wrote HTTP acceptance tests from the contract and additional boundary cases.
import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest

BASE = os.getenv("SVCDESK_URL", "http://svcdesk:8080").rstrip("/")
T1 = "2026-10-14T10:00:00Z"

def call(path, method="GET", body=None, clock=T1):
    headers = {"Content-Type": "application/json"}
    if clock is not None:
        headers["X-Test-Clock"] = clock
    request = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers, method=method)
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        assert response.headers.get_content_type() == "application/json"
        return response.status, json.load(response)

def create(impact=1, urgency=1, clock=T1, **extra):
    body = {"title": "Contract test", "reporter": {"name": "Test reporter"},
            "impact": impact, "urgency": urgency, **extra}
    status, ticket = call("/tickets", "POST", body, clock)
    assert status == 201, ticket
    return ticket

def action(ticket, name, clock=T1, expected=200):
    status, result = call(f"/tickets/{ticket['id']}/{name}", "POST", clock=clock)
    assert status == expected, result
    if expected >= 400:
        assert isinstance(result["error"], dict)
    return result

def resolve(ticket, when=T1):
    action(ticket, "ack")
    action(ticket, "start")
    return action(ticket, "resolve", when)

def sla(ticket, clock):
    status, result = call(f"/tickets/{ticket['id']}/sla", clock=clock)
    assert status == 200
    return result

def test_health():
    assert call("/health") == (200, {"status": "ok", "service": "svcdesk"})

@pytest.mark.parametrize("impact,urgency,priority", [(1,1,"P1"),(1,2,"P2"),(1,3,"P3"),(2,1,"P2"),(2,2,"P3"),(2,3,"P4"),(3,1,"P3"),(3,2,"P4"),(3,3,"P4")])
def test_matrix(impact, urgency, priority):
    assert create(impact, urgency)["priority"] == priority

@pytest.mark.parametrize("impact,urgency,clock,ack,due", [
    (1,1,T1,"2026-10-14T10:15:00Z","2026-10-14T14:00:00Z"),
    (2,2,"2026-10-16T13:30:00Z","2026-10-19T09:30:00Z","2026-10-21T13:30:00Z"),
    (1,1,"2026-10-16T15:00:00Z","2026-10-16T15:15:00Z","2026-10-16T19:00:00Z"),
    (1,2,"2026-10-17T10:00:00Z","2026-10-19T07:00:00Z","2026-10-19T14:00:00Z"),
    (3,3,"2027-01-14T14:30:00Z","2027-01-15T14:30:00Z","2027-01-27T14:30:00Z"),
    (1,1,"2027-01-15T15:50:00Z","2027-01-15T16:05:00Z","2027-01-15T19:50:00Z"),
    (1,2,T1,"2026-10-14T11:00:00Z","2026-10-15T10:00:00Z"),
    (2,2,"2026-10-23T13:00:00Z","2026-10-26T10:00:00Z","2026-10-28T14:00:00Z")])
def test_all_sla_vectors(impact, urgency, clock, ack, due):
    assert create(impact, urgency, clock)["sla"] == {"ack_due_at": ack, "resolve_due_at": due}

@pytest.mark.parametrize("changes", [{"title":""},{"title":"x"*201},{"description":"x"*4001},
    {"reporter":{}},{"reporter":{"name":"x"*101}},{"impact":True},{"impact":1.0},
    {"impact":"1"},{"impact":0},{"impact":4},{"urgency":"high"},{"urgency":None}])
def test_validation(changes):
    body = {"title":"test", "reporter":{"name":"Test"}, "impact":1, "urgency":1, **changes}
    status, response = call("/tickets", "POST", body)
    assert status in (400,422)
    assert isinstance(response["error"], dict)

def test_owned_fields_and_vip():
    ticket = create(3,3,reporter={"name":"VIP", "vip":True}, priority="P1", id="fake", state="closed", nonsense=12)
    assert ticket["priority"] == "P4"
    assert ticket["id"] != "fake" and ticket["state"] == "new"
    assert ticket["reporter"]["vip"] is True
    assert create(reporter={"name":"VIP", "vip":True})["priority"] == "P1"

def test_state_path_and_immutable_closure():
    ticket = create()
    action(ticket,"start",expected=409)
    action(ticket,"resolve",expected=409)
    action(ticket,"ack")
    action(ticket,"ack",expected=409)
    action(ticket,"resolve",expected=409)
    action(ticket,"start")
    action(ticket,"close",expected=409)
    action(ticket,"resolve")
    closed = action(ticket,"close")
    for name in ["ack","start","resolve","close","reopen"]:
        action(ticket,name,expected=409)
    assert call(f"/tickets/{ticket['id']}")[1] == closed
    assert create(related_to=ticket["id"])["related_to"] == ticket["id"]

@pytest.mark.parametrize("when,expected", [("2026-10-21T10:00:00Z",200),("2026-10-21T10:00:01Z",409)])
def test_reopen_boundary(when, expected):
    ticket = create()
    resolve(ticket)
    result = action(ticket,"reopen",when,expected)
    if expected == 200:
        assert result["sla"] == ticket["sla"]
        assert result["resolved_at"] is None and result["closed_at"] is None
        assert sla(ticket,when)["resolve_breached"] is True

def test_exact_due_and_late_ack():
    ticket = create()
    assert sla(ticket,"2026-10-14T10:15:00Z")["ack_breached"] is False
    assert sla(ticket,"2026-10-14T10:15:01Z")["ack_breached"] is True
    action(ticket,"ack","2026-10-14T10:15:01Z")
    assert sla(ticket,"2026-10-14T11:00:00Z")["ack_breached"] is True

def test_timely_events_stay_timely():
    ticket = create()
    action(ticket,"ack","2026-10-14T10:15:00Z")
    action(ticket,"start")
    action(ticket,"resolve","2026-10-14T14:00:00Z")
    status = sla(ticket,"2026-10-17T10:00:00Z")
    assert not status["ack_breached"] and not status["resolve_breached"] and not status["paused"]

@pytest.mark.parametrize("when,paused", [("2026-10-19T05:59:59Z",True),("2026-10-19T06:00:00Z",False),("2026-10-19T14:00:00Z",True),("2026-10-17T10:00:00Z",True)])
def test_pause_boundaries(when, paused):
    assert sla(create(2,2),when)["paused"] is paused
    assert sla(create(),when)["paused"] is False

def test_filters_and_unique_ids():
    first, second = create(), create(3,3)
    assert first["id"] != second["id"]
    action(first,"ack")
    status, tickets = call("/tickets?state=acknowledged&priority=P1")
    assert status == 200 and first["id"] in {t["id"] for t in tickets}
    assert all(t["state"] == "acknowledged" and t["priority"] == "P1" for t in tickets)
    assert call("/tickets?state=unknown")[1] == []

@pytest.mark.parametrize("clock", ["yesterday","2026-10-14T10:00:00","2026-02-30T10:00:00Z"])
def test_invalid_clock(clock):
    status, result = call("/tickets", "POST", {"title":"test","reporter":{"name":"Test"},"impact":1,"urgency":1},clock)
    assert status in (400,422) and isinstance(result["error"],dict)

def test_request_clock_isolation_and_offsets():
    ticket = create(clock="2026-10-14T12:00:00+02:00")
    assert ticket["created_at"] == T1
    action(ticket,"ack","2020-01-01T00:00:00Z")
    before = datetime.now(timezone.utc)
    actual = create(clock=None)
    after = datetime.now(timezone.utc)
    assert before <= datetime.fromisoformat(actual["created_at"].replace("Z","+00:00")) <= after

@pytest.mark.parametrize("path,method", [("/missing","GET"),("/tickets/missing","GET"),("/tickets/missing/sla","GET"),("/tickets/missing/ack","POST")])
def test_not_found(path,method):
    status,result = call(path,method)
    assert status == 404 and isinstance(result["error"],dict)
