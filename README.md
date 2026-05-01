# 🚨 IMS — Incident Management System

A production-grade, event-driven **Incident Management System** built with **FastAPI**, **Redis (RQ)**, **PostgreSQL**, and **MongoDB**. It ingests signals from infrastructure components, deduplicates them, classifies their severity, creates incidents, and tracks them through a strict lifecycle — all containerized with Docker Compose.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [API Reference](#api-reference)
- [Incident Lifecycle](#incident-lifecycle)
- [Severity Classification](#severity-classification)
- [Getting Started](#getting-started)
- [Frontend Dashboard](#frontend-dashboard)
- [Running the Simulation](#running-the-simulation)
- [Design Patterns](#design-patterns)
- [Docker & Dependency Notes](#docker--dependency-notes)

---

## Overview

IMS is a backend system designed to handle real-time alert signals from infrastructure components (databases, APIs, cache clusters, etc.). When a signal arrives, it is:

1. Queued asynchronously via Redis (RQ)
2. Logged to MongoDB as a raw event
3. Deduplicated per component using a Redis-based debounce window
4. Classified by severity using the Strategy pattern
5. Persisted as an Incident in PostgreSQL
6. Tracked through a stateful lifecycle: `OPEN → INVESTIGATING → RESOLVED → CLOSED`

A simple HTML frontend is included for viewing and managing incidents.

---

## Architecture

```
                        ┌────────────────────┐
   POST /signals ──────▶│   FastAPI Backend   │
                        │     (main.py)       │
                        └────────┬───────────┘
                                 │ enqueue
                                 ▼
                        ┌────────────────────┐
                        │    Redis (RQ)       │
                        │  queue_config.py    │
                        └────────┬───────────┘
                                 │ process_signal
                                 ▼
                        ┌────────────────────┐
                        │    Worker           │
                        │    (worker.py)      │
                        └──┬─────────┬───────┘
                           │         │
               ┌───────────▼──┐  ┌───▼──────────────┐
               │   MongoDB    │  │   PostgreSQL       │
               │  (raw logs)  │  │  (incidents table) │
               └──────────────┘  └────────────────────┘
```

---

## Features

- **Asynchronous Signal Ingestion** — Signals are queued via Redis RQ for non-blocking processing
- **Rate Limiting** — API endpoint capped at 10 requests/second per IP using `slowapi`
- **Redis Debounce** — Suppresses duplicate signals for the same component within a 10-second window
- **Dual Database Architecture** — MongoDB for raw signal logs, PostgreSQL for structured incident records
- **Strategy Pattern Severity Classification** — Component type determines incident priority (P0–P3)
- **State Machine Lifecycle** — Enforced one-way transitions: `OPEN → INVESTIGATING → RESOLVED → CLOSED`
- **RCA Enforcement** — Incidents cannot be closed without a Root Cause Analysis (root cause + fix applied)
- **MTTR Tracking** — Mean Time To Resolution calculated automatically on status update
- **Retry Logic** — Database writes are retried up to 3 times on failure
- **CORS Enabled** — Frontend can communicate with the backend from any origin
- **Load Simulation** — Built-in `simulate.py` for burst and failure scenario testing

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (Python) |
| Task Queue | Redis + RQ (Redis Queue) |
| Relational DB | PostgreSQL + SQLAlchemy |
| Document Store | MongoDB + PyMongo |
| Rate Limiting | slowapi |
| Containerization | Docker (multi-stage, slim) + Docker Compose |
| Frontend | HTML/CSS/JS (static) |

---

## Project Structure

```
ims-system/
│
├── main.py              # FastAPI app — signal ingestion, incident CRUD, RCA endpoints
├── worker.py            # RQ worker — signal processing, debounce, incident creation
├── models.py            # SQLAlchemy ORM model for the Incident table
├── db_config.py         # PostgreSQL engine and session configuration
├── queue_config.py      # Redis connection and RQ queue setup
├── strategy.py          # Strategy pattern — severity classification by component type
├── state.py             # State pattern — valid lifecycle transitions per state
├── init_db.py           # Database initializer — creates tables from ORM models
├── simulate.py          # Load simulator — burst traffic and RDBMS failure scenarios
│
├── Dockerfile           # Multi-stage Python 3.10-slim image — builder + secure runtime
├── requirements.txt     # Pinned Python dependencies for reproducible builds
├── docker-compose.yml   # Orchestrates: Redis, PostgreSQL, MongoDB, backend, worker
│
└── frontend/
    └── index.html       # Static HTML dashboard for viewing/managing incidents
```

---

## Data Model

### `Incident` (PostgreSQL)

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-incremented incident ID |
| `component_id` | String | Identifier of the affected component |
| `severity` | String | Priority level: `P0`, `P1`, `P2`, or `P3` |
| `status` | String | Current lifecycle state (default: `OPEN`) |
| `start_time` | DateTime | Timestamp of incident creation |
| `end_time` | DateTime | Timestamp of resolution (nullable) |
| `mttr_seconds` | Float | Mean Time To Resolution in seconds (nullable) |
| `root_cause` | Text | RCA — description of root cause (nullable) |
| `fix_applied` | Text | RCA — description of fix applied (nullable) |
| `prevention` | Text | RCA — future prevention notes (nullable) |

### Raw Signals (MongoDB — `ims_db.signals`)

Each signal document contains:
- `component_id` — source component
- `error_type` — e.g., `latency_spike`, `timeout`, `connection_error`, `memory_leak`
- `timestamp` — Unix epoch of the signal
- `payload` — arbitrary event identifier string

---

## API Reference

### `GET /health`
Returns service health status.

**Response:**
```json
{ "status": "ok" }
```

---

### `POST /signals`
Ingests an alert signal. Rate-limited to **10 requests/second** per IP. The signal is queued for async processing.

**Request Body:**
```json
{
  "component_id": "RDBMS_MAIN",
  "error_type": "latency_spike",
  "timestamp": 1714500000.0,
  "payload": "error_event_1"
}
```

**Response:**
```json
{ "status": "queued" }
```

---

### `GET /incidents`
Returns all incidents from PostgreSQL.

**Response:**
```json
[
  {
    "id": 1,
    "component_id": "RDBMS_MAIN",
    "severity": "P0",
    "status": "OPEN",
    "start_time": "2024-01-01T10:00:00",
    "end_time": null,
    "mttr_seconds": null
  }
]
```

---

### `PUT /incidents/{id}/status?new_status=INVESTIGATING`
Transitions an incident to the next valid state.

**Valid Transitions:**
- `OPEN` → `INVESTIGATING`
- `INVESTIGATING` → `RESOLVED`
- `RESOLVED` → `CLOSED` *(requires RCA to be filed first)*

**Response (success):**
```json
{ "status": "updated" }
```

**Response (invalid transition):**
```json
{ "error": "invalid transition" }
```

**Response (missing RCA on CLOSED):**
```json
{ "error": "RCA required" }
```

---

### `POST /incidents/{id}/rca`
Files a Root Cause Analysis for an incident. Required before closing.

**Request Body:**
```json
{
  "root_cause": "Connection pool exhaustion due to long-running queries",
  "fix_applied": "Increased pool size and killed idle connections",
  "prevention": "Add query timeout and connection pool monitoring"
}
```

**Response:**
```json
{ "status": "rca saved" }
```

---

## Incident Lifecycle

```
  OPEN
   │
   ▼
INVESTIGATING
   │
   ▼
RESOLVED
   │  (RCA must be filed first)
   ▼
CLOSED
```

Transitions are strictly one-directional and enforced both via the API (`main.py`) and the state classes (`state.py`). An incident cannot skip states or move backwards.

---

## Severity Classification

Severity is assigned automatically based on the `component_id` of the incoming signal, using the **Strategy pattern**:

| Component Type | Severity | Description |
|---|---|---|
| Contains `RDBMS` | **P0** | Critical — database failure |
| Contains `API` | **P1** | High — API gateway issue |
| Contains `CACHE` | **P2** | Medium — cache cluster problem |
| All others | **P3** | Low — general/unknown component |

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed
- Python 3.10+ (only needed if running `simulate.py` locally outside Docker)

### 1. Clone the repository

```bash
git clone https://github.com/ananyaamishraa/ims-system.git
cd ims-system
```

### 2. (Optional) Install dependencies locally

Only required if you want to run `simulate.py` or any script outside of Docker:

```bash
pip install -r requirements.txt
```

### 3. Start all services

```bash
docker compose up --build
```

This starts five containers: `redis`, `postgres`, `mongodb`, `backend`, and `worker`.

| Service | Port |
|---|---|
| FastAPI Backend | `http://localhost:8000` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| MongoDB | `localhost:27017` |

### 4. Initialize the database

On first run, the `backend` container handles table creation automatically. To run it manually:

```bash
docker compose exec backend python init_db.py
```

### 5. Verify the service

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### 6. Open the frontend

See the [Frontend Dashboard](#frontend-dashboard) section below for full details.

---

## Frontend Dashboard

The frontend is a lightweight, zero-dependency static HTML page located at `frontend/index.html`. It requires no build step or package manager — just open it directly in a browser while the backend is running.

### How to open it

```bash
# Option A — open directly in browser (no server needed)
open frontend/index.html       # macOS
xdg-open frontend/index.html   # Linux

# Option B — serve via Python for cleaner local dev
python -m http.server 3000 --directory frontend
# then visit http://localhost:3000
```

> The backend must be running on `http://localhost:8000` for the dashboard to work. Start it with `docker compose up` first.

### What it does

The dashboard communicates with the FastAPI backend over the REST API and provides a single-page interface for:

**Viewing all incidents** — fetches `GET /incidents` on load and renders a table showing each incident's ID, component, severity, current status, start time, and MTTR (once resolved).

**Updating incident status** — allows transitioning an incident through its lifecycle (`OPEN → INVESTIGATING → RESOLVED → CLOSED`) via `PUT /incidents/{id}/status`. Invalid transitions are rejected by the backend and surfaced as error messages.

**Filing an RCA** — provides a form to submit root cause, fix applied, and prevention notes via `POST /incidents/{id}/rca`. Required before an incident can be closed.

### What it does NOT do

The frontend does not send signals — that is the job of `simulate.py` or your own integrations via `POST /signals`. The dashboard is purely a management and review interface.

### Connecting to a different backend URL

If you're running the backend on a different host or port, update the `API_URL` constant at the top of `frontend/index.html`:

```javascript
const API_URL = "http://127.0.0.1:8000"; // change this to your backend address
```

---

## Running the Simulation

`simulate.py` sends synthetic alert signals to stress-test the system in three phases:

```bash
# Run from outside Docker (requires the backend to be running on port 8000)
python simulate.py
```

**Simulation Phases:**

| Phase | Description | Volume |
|---|---|---|
| Normal Load | Random signals across all components | 300 signals |
| RDBMS Failure Storm | Sustained `db_crash` signals for `RDBMS_MAIN` | 200 signals |
| High Burst | Random high-concurrency traffic | 700 signals |

The simulator uses **50 concurrent threads** per burst cycle. The worker logs throughput approximately every 5 seconds (`Signals/sec`).

---

## Design Patterns

### Strategy Pattern (`strategy.py`)
Severity classification is decoupled from the worker. Each component type has its own strategy class (`RDBMSAlert`, `APIAlert`, `CacheAlert`) that implements a common `severity()` interface. Adding new component types requires no changes to the core processing logic.

### State Pattern (`state.py`)
Each incident state (`OpenState`, `InvestigatingState`, `ResolvedState`, `ClosedState`) holds an `allowed` list of valid next states. The `can_transition()` method enforces the directed lifecycle graph.

### Worker / Queue Pattern (`worker.py` + `queue_config.py`)
Signal ingestion is fully decoupled from processing. The API enqueues a job and returns immediately; the RQ worker consumes it asynchronously. This prevents API latency from growing under load.

---

## Environment Notes

The following environment values are hardcoded for local/Docker use and should be moved to environment variables before any production deployment:

- PostgreSQL: `postgresql://postgres:postgres@postgres:5432/ims_db`
- Redis: `redis:6379`
- MongoDB: `mongodb://mongodb:27017/`

CORS is currently open to all origins (`allow_origins=["*"]`). Restrict this in production.

---

## Docker & Dependency Notes

The Dockerfile uses a **multi-stage build** (`builder` + `runtime`) based on `python:3.10-slim` to keep the final image lean. The `builder` stage compiles all packages (including native extensions for `psycopg2`), and only the resulting install artifacts are copied into the runtime image — no compilers or build tools ship in production.

The container runs as a **non-root user** (`appuser`) for basic security hardening.

All Python dependencies are declared in `requirements.txt` with **pinned versions** to ensure reproducible builds across environments:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.111.0 | Web framework |
| `uvicorn[standard]` | 0.29.0 | ASGI server |
| `slowapi` | 0.1.9 | Rate limiting |
| `redis` | 5.0.4 | Redis client |
| `rq` | 1.16.2 | Task queue |
| `sqlalchemy` | 2.0.30 | ORM for PostgreSQL |
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver |
| `pymongo` | 4.7.2 | MongoDB driver |
| `requests` | 2.31.0 | HTTP client (simulate.py) |

To upgrade a dependency, update its version in `requirements.txt` and rebuild: `docker compose up --build`.
