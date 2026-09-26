# ai-generated: 100% - Codex implemented the API from the receipted specification.
"""JSON ticket API with transactional, persistent SQLite storage."""
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from starlette.exceptions import HTTPException
from .clock import business_open, deadlines, parse_instant, stamp

DB_PATH = os.getenv("SVCDESK_DB", "/data/svcdesk.db")


@contextmanager
def database(write=False):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    try:
        if write:
            connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(app):
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with database() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


class Reporter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    email: StrictStr | None = None
    vip: StrictBool = False


class TicketInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Annotated[StrictStr, Field(min_length=1, max_length=200)]
    description: Annotated[StrictStr, Field(max_length=4000)] = ""
    reporter: Reporter
    impact: Annotated[StrictInt, Field(ge=1, le=3)]
    urgency: Annotated[StrictInt, Field(ge=1, le=3)]
    related_to: StrictStr | None = None


def error(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    messages = [f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in exc.errors()]
    return error(422, "validation", "; ".join(messages))


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error(exc.status_code, "not_found" if exc.status_code == 404 else "request_error", str(exc.detail))


def request_now(request: Request) -> datetime:
    value = request.headers.get("X-Test-Clock")
    if value is not None and os.getenv("SVCDESK_TEST_CLOCK", "").lower() in {"1", "true"}:
        try:
            return parse_instant(value)
        except ValueError:
            raise HTTPException(422, "X-Test-Clock must be an RFC3339 instant with timezone offset")
    return datetime.now(timezone.utc)


def fetch(connection, ticket_id):
    row = connection.execute("SELECT body FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Ticket not found")
    return json.loads(row[0])


@app.get("/health")
def health(now: datetime = Depends(request_now)):
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
def create_ticket(body: TicketInput, now: datetime = Depends(request_now)):
    priority = f"P{min(body.impact + body.urgency - 1, 4)}"
    ticket = body.model_dump()
    ticket.update(id=str(uuid4()), priority=priority, state="new", created_at=stamp(now),
                  acknowledged_at=None, resolved_at=None, closed_at=None, sla=deadlines(now, priority))
    with database(write=True) as connection:
        connection.execute("INSERT INTO tickets VALUES (?, ?)", (ticket["id"], json.dumps(ticket)))
    return ticket


@app.get("/tickets")
def list_tickets(state: str | None = None, priority: str | None = None,
                 now: datetime = Depends(request_now)):
    with database() as connection:
        tickets = [json.loads(row[0]) for row in connection.execute("SELECT body FROM tickets")]
    return [ticket for ticket in tickets if (state is None or ticket["state"] == state)
            and (priority is None or ticket["priority"] == priority)]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, now: datetime = Depends(request_now)):
    with database() as connection:
        return fetch(connection, ticket_id)


@app.get("/tickets/{ticket_id}/sla")
def get_sla(ticket_id: str, now: datetime = Depends(request_now)):
    with database() as connection:
        ticket = fetch(connection, ticket_id)
    def breached(event, due):
        actual = parse_instant(ticket[event]) if ticket[event] else now
        return actual > parse_instant(ticket["sla"][due])
    return {"priority": ticket["priority"], **ticket["sla"],
            "ack_breached": breached("acknowledged_at", "ack_due_at"),
            "resolve_breached": breached("resolved_at", "resolve_due_at"),
            "paused": ticket["state"] not in {"resolved", "closed"}
            and ticket["priority"] != "P1" and not business_open(now)}


TRANSITIONS = {"ack": ("new", "acknowledged", "acknowledged_at"),
               "start": ("acknowledged", "in_progress", None),
               "resolve": ("in_progress", "resolved", "resolved_at"),
               "close": ("resolved", "closed", "closed_at")}


@app.post("/tickets/{ticket_id}/{action}")
def transition(ticket_id: str, action: str, now: datetime = Depends(request_now)):
    if action not in TRANSITIONS and action != "reopen":
        raise HTTPException(404, "Action not found")
    with database(write=True) as connection:
        ticket = fetch(connection, ticket_id)
        if action == "reopen":
            if ticket["state"] != "resolved":
                return error(409, "invalid_transition", "Only resolved tickets can reopen; closed tickets are immutable")
            if now > parse_instant(ticket["resolved_at"]) + timedelta(days=7):
                return error(409, "reopen_window_expired", "The seven-day reopen window has expired")
            ticket.update(state="in_progress", resolved_at=None, closed_at=None)
        else:
            expected, target, timestamp = TRANSITIONS[action]
            if ticket["state"] != expected:
                return error(409, "invalid_transition", f"{action} requires state {expected}")
            ticket["state"] = target
            if timestamp:
                ticket[timestamp] = stamp(now)
        connection.execute("UPDATE tickets SET body = ? WHERE id = ?", (json.dumps(ticket), ticket_id))
    return ticket


@app.post("/dora/metrics")
async def dora_metrics(request: Request):
    from .dora import calculate
    try:
        return calculate(await request.json())
    except (ValueError, TypeError, OverflowError) as exc:
        return error(422, "invalid_log", str(exc))


@app.get("/dora/ticket-events")
def ticket_events():
    phases = {"created_at": ("created", "new"), "acknowledged_at": ("acknowledged", "acknowledged"),
              "resolved_at": ("resolved", "resolved"), "closed_at": ("closed", "closed")}
    with database() as connection:
        tickets = [json.loads(row[0]) for row in connection.execute("SELECT body FROM tickets")]
    events = [{"ticket_id": ticket["id"], "at": ticket[field], "phase": phase,
               "priority": ticket["priority"], "state": state}
              for ticket in tickets for field, (phase, state) in phases.items() if ticket.get(field)]
    return sorted(events, key=lambda event: (parse_instant(event["at"]), event["ticket_id"]))
