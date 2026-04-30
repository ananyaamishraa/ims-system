import time
from redis import Redis
from pymongo import MongoClient
from db_config import SessionLocal
from models import Incident

signal_count = 0
start_time = time.time() 

redis_conn = Redis(host="localhost", port=6379)

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["ims_db"]
signals_collection = mongo_db["signals"]

def process_signal(signal):
    global signal_count, start_time

    signal_count += 1

    if time.time() - start_time >= 5:
        print(f"Signals/sec: {signal_count / 5}")
        signal_count = 0
        start_time = time.time()

    component_id = signal.get("component_id")
    severity = signal.get("severity", "P2")

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

        # 3. Create Incident in PostgreSQL
        incident = Incident(
            component_id=component_id,
            severity=severity,
            status="OPEN"
        )

        def save_incident_with_retry(db, incident, retries=3):
            for attempt in range(retries):
                try:
                    db.add(incident)
                    db.commit()
                    return
                except Exception as e:
                    db.rollback()
                    print(f"Retry {attempt+1} failed:", e)
                    time.sleep(1)

    print("Failed to save incident after retries") 

        print(f"[NEW INCIDENT] Stored in DB for {component_id}")
        redis_conn.set(f"incident:{incident.id}", "ACTIVE") 

    db.close()

    print("Signal stored in MongoDB:", signal)

def get_severity(component):
    mapping = {
        "RDBMS": "P0",
        "CACHE": "P2"
    }
    return mapping.get(component, "P3") 
