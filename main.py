from fastapi import FastAPI, Request
from queue_config import queue
from db_config import SessionLocal
from models import Incident
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

app = FastAPI()

# -------------------------
# CORS
# -------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# RATE LIMITING
# -------------------------

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc):
    return JSONResponse(status_code=429, content={"error": "rate limit exceeded"})

# -------------------------
# HEALTH
# -------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------
# SIGNAL INGESTION
# -------------------------

@app.post("/signals")
@limiter.limit("10/second")
def ingest(signal: dict, request: Request):
    queue.enqueue("worker.process_signal", signal)
    return {"status": "queued"}

# -------------------------
# INCIDENT LIST
# -------------------------

@app.get("/incidents")
def incidents():
    db = SessionLocal()
    rows = db.query(Incident).all()
    result = []
    for i in rows:
        result.append({
            "id": i.id,
            "component_id": i.component_id,
            "severity": i.severity,
            "status": i.status,
            "start_time": i.start_time,
            "end_time": i.end_time,
            "mttr_seconds": i.mttr_seconds
        })
    db.close()
    return result

# -------------------------
# STATUS UPDATE
# -------------------------

@app.put("/incidents/{id}/status")
def update(id: int, new_status: str):
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == id).first()
    if not inc:
        return {"error": "not found"}

    transitions = {
        "OPEN": ["INVESTIGATING"],
        "INVESTIGATING": ["RESOLVED"],
        "RESOLVED": ["CLOSED"]
    }

    if new_status not in transitions.get(inc.status, []):
        return {"error": "invalid transition"}

    # RCA enforcement — must be filed before closing
    if new_status == "CLOSED":
        if not inc.root_cause or not inc.fix_applied:
            return {"error": "RCA required"}

    # MTTR is only meaningful when the incident is resolved
    if new_status == "RESOLVED":
        inc.end_time = datetime.utcnow()
        inc.mttr_seconds = (inc.end_time - inc.start_time).total_seconds()

    inc.status = new_status
    db.commit()
    db.close()
    return {"status": "updated"}

# -------------------------
# RCA
# -------------------------

@app.post("/incidents/{id}/rca")
def rca(id: int, data: dict):
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == id).first()
    if not inc:
        return {"error": "not found"}
    inc.root_cause = data.get("root_cause")
    inc.fix_applied = data.get("fix_applied")
    inc.prevention = data.get("prevention")
    db.commit()
    db.close()
    return {"status": "rca saved"}
