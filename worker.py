import time
from redis import Redis
from pymongo import MongoClient
from db_config import SessionLocal
from models import Incident

# -------------------------
# OBSERVABILITY (signals/sec)
# -------------------------
signal_count = 0
start_time = time.time()

# Redis
redis_conn = Redis(host="localhost", port=6379)

# MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["ims_db"]
signals_collection = mongo_db["signals"]

# -------------------------
# STRATEGY PATTERN
# -------------------------
def get_severity(component_id):
    if "RDBMS" in component_id:
        return "P0"
    elif "CACHE" in component_id:
        return "P2"
    elif "API" in component_id:
        return "P1"
    else:
        return "P3"

# -------------------------
# RETRY LOGIC
# -------------------------
def save_incident_with_retry(db, incident, retries=3):
    for attempt in range(retries):
        try:
            db.add(incident)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Retry {attempt+1} failed:", e)
            time.sleep(1)

    print("Failed to save incident after retries")
    return False

# -------------------------
# MAIN WORKER FUNCTION
# -------------------------
def process_signal(signal):
    global signal_count, start_time

    # Observability logging
    signal_count += 1
    if time.time() - start_time >= 5:
        print(f"Signals/sec: {signal_count / 5}")
        signal_count = 0
        start_time = time.time()

    component_id = signal.get("component_id")

    # Strategy pattern used here
    severity = get_severity(component_id)

    # 1. Store raw signal in MongoDB
    signals_collection.insert_one(signal)

    # 2. Debounce logic
    current_window = int(time.time() / 10)
    key = f"debounce:{component_id}:{current_window}"

    db = SessionLocal()

    if redis_conn.exists(key):
        print(f"[DEBOUNCED] Existing incident for {component_id}")
    else:
        redis_conn.set(key, "1", ex=10)

        # Create incident
        incident = Incident(
            component_id=component_id,
            severity=severity,
            status="OPEN"
        )

        success = save_incident_with_retry(db, incident)

        if success:
            print(f"[NEW INCIDENT] Stored in DB for {component_id}")

            # Cache (hot path)
            redis_conn.set(f"incident:{incident.id}", "ACTIVE")

    db.close()

    print("Signal stored in MongoDB:", signal)
