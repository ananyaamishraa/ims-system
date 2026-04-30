import time
from redis import Redis
from pymongo import MongoClient
from db_config import SessionLocal
from models import Incident

redis_conn = Redis(host="localhost", port=6379)

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["ims_db"]
signals_collection = mongo_db["signals"]

def process_signal(signal):
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

        db.add(incident)
        db.commit()

        print(f"[NEW INCIDENT] Stored in DB for {component_id}")

    db.close()

    print("Signal stored in MongoDB:", signal)  
