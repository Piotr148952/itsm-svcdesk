<!-- ai-generated: 100% - Codex drafted this specification from the supplied course requirements and API contract. -->
# svcdesk specification before implementation

## Purpose and authority

Build an HTTP service desk for a small organisation, replacing spreadsheet tracking with explicit ticket states and reproducible SLA deadlines. API.md defines the exact interface; REQUIREMENTS.md supplies R-01 through R-25; CHECKS.md supplies published acceptance checks. This document resolves the contradictory requirements before application code exists. Implementation begins only after the course bot accepts the specs receipt. No external services or runtime downloads are required.

## Declared conflict resolutions

### C1: wallclock — R-13 versus R-14

Both P1 deadlines run continuously: acknowledgement within 15 minutes and resolution within four hours. Reject only R-13's application to P1; retain business hours for P2–P4. An organisation-wide work stoppage remains urgent overnight. The Service Desk product owner must accept the cost of arranging out-of-hours coverage; a continuously running deadline alone cannot provide staffing. Customers receive an honest measure of elapsed critical outage time instead of a clock that conceals a weekend outage.

### C2: immutable — R-09 versus R-10

Closed tickets cannot reopen or otherwise change. Further work uses a new ticket with related_to pointing to the earlier ticket. Reject only R-10's permission to reopen closed tickets. Resolved tickets remain reopenable through exactly seven elapsed days after resolution. The Service Desk process owner owns closure and reporting policy: closure represents a confirmed outcome and should remain stable for audit. Reporters must create a linked ticket after closure, accepting additional effort in exchange for a stable record. Reopening a resolved ticket never resets its SLA targets.

### C3: matrix — R-05 versus R-06

Priority depends exclusively on impact and urgency. Store reporter.vip but do not use it to change priority. Reject R-06's VIP priority floor, retaining reporter metadata and the complete R-04 matrix. The Service Desk product owner owns triage policy and the consequence that an executive's cosmetic problem remains P4. Scarce response capacity follows disruption to work; VIP reporters receive the same objective assessment as other reporters.

## HTTP and data contract (R-01–R-06, R-17–R-20, R-25)

Use Python 3.13 and FastAPI. Listen on 0.0.0.0:8080. All responses, including errors, are JSON. GET /health returns 200 with status ok and service svcdesk. POST /tickets returns 201 and a complete ticket. GET /tickets returns an array of every matching ticket, with optional exact-match state and priority filters applied together. GET /tickets/{id} returns a ticket or 404 with an error object. Unknown routes return JSON 404; wrong methods may return 405.

Required creation fields: title string of 1–200 characters, reporter.name string of 1–100 characters, impact and urgency strict integers from 1 through 3. Booleans, floats and numeric strings are not integers for input validation. Optional description is a string of at most 4000 characters, default empty; reporter.email is a string or null, default null; reporter.vip is boolean, default false; related_to is a string or null, default null and not checked for existence. Ignore unknown fields and server-owned fields, including id, priority, state, timestamps and sla. Reject invalid bodies with 422 and a top-level error object.

Assign opaque unique UUID identifiers. The matrix rows for impact 1, 2, 3 are respectively [P1,P2,P3], [P2,P3,P4], [P3,P4,P4]. New tickets have state new, created_at and computed sla.ack_due_at and sla.resolve_due_at. acknowledged_at, resolved_at and closed_at start null. Emit UTC RFC3339 timestamps ending in Z.

## State transitions (R-07–R-11)

POST /tickets/{id}/ack: new to acknowledged, recording acknowledged_at. /start: acknowledged to in_progress. /resolve: in_progress to resolved, recording resolved_at. /close: resolved to closed, recording closed_at. /reopen: resolved to in_progress only when now <= resolved_at + seven days, clearing resolved_at and closed_at. Successful actions return 200 and the full ticket. Every other transition, duplicate action or expired reopen window returns 409 with error object; an unknown id returns 404. A reopened ticket preserves created_at, acknowledged_at and both original due instants. Do not impose monotonic request time.

## SLA calculations (R-12–R-16)

Acknowledgement/resolution targets are P1: 15 minutes/4 hours; P2: 1/8 hours; P3: 4/24 hours; P4: 8/72 hours. Both targets begin at creation. P1 adds elapsed durations in UTC. P2–P4 consume only Monday–Friday [08:00,16:00) in Europe/Warsaw. Move an out-of-hours starting instant to the next opening, consume each business window, and skip weekends. Holidays remain business days. Use the IANA timezone database to account for CET/CEST changes. If a target consumes exactly the remaining window, it is due at that day's 16:00, not the next opening.

GET /tickets/{id}/sla returns priority, both due instants, ack_breached, resolve_breached and paused. Each breach compares its recorded event time with the deadline, or now if that event has not happened. Only strictly later counts as breached. Reopening makes resolution pending again. Paused is true only for an unresolved/unclosed business-clock ticket outside a business window; P1 is never paused. A late acknowledgement stays breached after the event, while a timely acknowledgement never becomes breached merely because time passes.

## Acceptance vectors from API.md

| Vector | Priority | Created UTC | Acknowledge due UTC | Resolve due UTC |
|---|---|---|---|---|
| T1 | P1 | 2026-10-14T10:00:00Z | 2026-10-14T10:15:00Z | 2026-10-14T14:00:00Z |
| T2 | P3 | 2026-10-16T13:30:00Z | 2026-10-19T09:30:00Z | 2026-10-21T13:30:00Z |
| T3 | P1 | 2026-10-16T15:00:00Z | 2026-10-16T15:15:00Z | 2026-10-16T19:00:00Z |
| T4 | P2 | 2026-10-17T10:00:00Z | 2026-10-19T07:00:00Z | 2026-10-19T14:00:00Z |
| T5 | P4 | 2027-01-14T14:30:00Z | 2027-01-15T14:30:00Z | 2027-01-27T14:30:00Z |
| T6 | P1 | 2027-01-15T15:50:00Z | 2027-01-15T16:05:00Z | 2027-01-15T19:50:00Z |
| T7 | P2 | 2026-10-14T10:00:00Z | 2026-10-14T11:00:00Z | 2026-10-15T10:00:00Z |
| T8 | P3 | 2026-10-23T13:00:00Z | 2026-10-26T10:00:00Z | 2026-10-28T14:00:00Z |

## Request clock (R-21)

When SVCDESK_TEST_CLOCK is 1 or true, use an offset-aware RFC3339 X-Test-Clock value as now for that request only. Reject malformed or naive timestamps with 400 or 422. Without the header use actual UTC time; when disabled ignore the header. Never retain a global test clock or compare successive request clocks. Listing and fetching tickets do not recompute stored fields.

## Runtime, persistence and delivery (R-22–R-24)

Compose defines svcdesk with build context inside this repository, SVCDESK_TEST_CLOCK set, container port 8080 and a healthcheck. Install dependencies during image build. Use SQLite in a Docker named volume so tickets survive container restarts. Persist each mutation transactionally. No bind mounts in any service or override. Start and answer health within 120 seconds without external network access.

After the specs receipt, implement and document decisions in DECISIONS.md with the five required labels per conflict. Add independent pytest HTTP tests behind the tests Compose profile, reading SVCDESK_URL, covering all vectors, exact boundaries, invalid inputs, state transitions, request clock isolation and reopening without extended deadlines. At least ten tests must pass; the final stdout line is ITSMLAB-TESTS: passed=<n> failed=0. Save CONVERGE.md comparing actual behaviour with requirement ids after implementation. These provide Stretch S3 and S1. Run the published checker, inspect its observations, verify a clean committed tree, then create a fresh annotated lab1/v1 tag. Never move a receipted tag. Include accurate AI disclosure headers in every checked file.
