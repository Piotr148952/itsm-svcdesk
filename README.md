<!-- ai-generated: 35% - Course overview retained; Codex added the implemented Lab 3 monitoring workflow. -->
# svcdesk - ITSM 2026/27 course repository

This repository was created from the course template. It holds your `svcdesk` service for the whole semester:
built in Lab 1, extended in the later labs. Keep it public, and keep personal data out of it.

## The one command

    ./itsmlab.sh verify 3            # Linux, macOS
    .\itsmlab.ps1 verify 3           # Windows PowerShell

It runs the published Tier A checker (a container) against this directory: builds and starts your service with
`docker compose`, runs the published checks, prints a table, and exits 0 when every Core spec passes. Add
`--json report.json` to keep the machine-readable report. Tier A runs are unlimited and never count as attempts.

The repository and profile login are configured for Piotr148952. Run from this directory with Docker Desktop
using Linux containers. Previous submissions remain available at immutable tags lab1/v1 and lab2/v1.

## Run the monitoring stack

    docker compose --profile observability up -d --build
    docker compose --profile tests run --rm --build tests

svcdesk listens on localhost:8080, Prometheus on localhost:9090, and Grafana on localhost:3000.
The provisioned dashboard "svcdesk — knowledge-base SLO" is in the svcdesk folder. Generate traffic with
`GET /kb/search?q=vpn`; empty graphs before requests and multiple scrapes are expected. The public metrics
endpoint is `GET /metrics`. The observability ports are bound to loopback.

Use `itsmlab load 3` through the platform wrapper to repeat the account-specific direct load. The initial
measurement and before-measurement AI proposal are documented in ai-first-draft.md; objectives, budgets and
bucket design are in slo.md. The genai and gap directories contain reproduction instructions for the two
completed Stretch experiments. Local model inference should be stopped during latency measurement.

To check alert fixtures directly:

    docker compose --profile observability run --rm --entrypoint promtool prometheus test rules /etc/prometheus/alerts_test.yml

To stop the stack while retaining ticket data, run `docker compose --profile observability --profile gap down`.

## Layout

| path | what it is |
|---|---|
| `docker-compose.yml` | svcdesk, seeded kb-index, persistent ticket volume; optional tests, observability and gap profiles |
| `prometheus/`, `grafana/` | scrape configuration, burn-rate rules and tests, provisioned SLO dashboard |
| `slo.md`, `ai-first-draft.md` | measured design, request budgets and preserved initial AI proposal |
| `genai/`, `gap.json`, `gap/` | actual instrumented local model call and measured proxy latency experiment |
| `Dockerfile.example` | a Python 3.13 image skeleton; copy to `Dockerfile` or replace for your language |
| `DECISIONS.md` | your reasoning artifact: front matter with the three decisions, three sections, five labels each |
| `itsmlab.yaml` | lab number, baselines, your repository, the submissions repository, the checker image |
| `itsmlab.sh`, `itsmlab.ps1` | wrappers that run the checker container |
| `specs/` | your specifications, published and receipted before any code |
| `src/` | your implementation |
| `.github/workflows/tier-a.yml` | runs the checker on every push and publishes `report.json` as an artifact with a step summary |
| `.gitignore` | keeps `report.json`, virtual environments and local data out of git |
| `.gitattributes` | LF line endings on every system, so the checker's git sees a clean tree on Windows too; keep it |

## Every push runs the checker

The workflow `tier-a` runs on every push and on demand (Actions tab, "Run workflow"). It needs no secrets. The
job is red when a Core spec fails; the step summary shows which checks, and `report.json` is attached as an
artifact.
