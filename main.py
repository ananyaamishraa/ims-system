from fastapi import FastAPI
from queue_config import queue
from db_config import SessionLocal
from models import Incident
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# INGEST SIGNAL (QUEUE)
# -------------------------
@app.post("/signals")
@limiter.limit("10/second")
def ingest_signal(request: Request, signal: dict):
    queue.enqueue("worker.process_signal", signal)
    return {"message": "signal queued"}


# -------------------------
# GET ALL INCIDENTS
# -------------------------
@app.get("/incidents")
def get_incidents():
    db = SessionLocal()
    incidents = db.query(Incident).all()

    result = []

    for i in incidents:
        mttr = None
        if i.end_time:
            mttr = (i.end_time - i.start_time).total_seconds()

        result.append({
            "id": i.id,
            "component_id": i.component_id,
            "status": i.status,
            "severity": i.severity,
            "start_time": str(i.start_time),
            "end_time": str(i.end_time) if i.end_time else None,
            "mttr_seconds": mttr,
            "root_cause": i.root_cause,
            "fix_applied": i.fix_applied,
            "prevention": i.prevention
        })

    db.close()
    return result


# -------------------------
# UPDATE INCIDENT STATUS
# -------------------------
@app.put("/incidents/{incident_id}/status")
def update_status(incident_id: int, new_status: str):
    db = SessionLocal()
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

    # State transition rules
    valid_transitions = {
        "OPEN": ["INVESTIGATING"],
        "INVESTIGATING": ["RESOLVED"],
        "RESOLVED": ["CLOSED"],
    }

    # Check valid transition
    if new_status not in valid_transitions.get(incident.status, []):
        db.close()
        return {"error": f"Invalid transition from {incident.status} to {new_status}"}

    # Enforce RCA before closing
    if new_status == "CLOSED":
        if not incident.root_cause or not incident.fix_applied:
            db.close()
            return {"error": "RCA required before closing"}

    incident.status = new_status
    db.commit()
    db.close()

    return {"message": "Status updated successfully"}


# -------------------------
# SUBMIT RCA
# -------------------------
@app.post("/incidents/{incident_id}/rca")
def submit_rca(incident_id: int, rca: dict):
    db = SessionLocal()
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

    # Save RCA fields
    incident.root_cause = rca.get("root_cause")
    incident.fix_applied = rca.get("fix_applied")
    incident.prevention = rca.get("prevention")

    # Set end time (used for MTTR)
    incident.end_time = datetime.utcnow()

    db.commit()
    db.close()

    return {"message": "RCA submitted successfully"} 
