import time
import datetime
from redis import Redis
from pymongo import MongoClient
from db_config import SessionLocal
from models import Incident
from strategy import get_alert_strategy

# -------------------------
# CONNECTIONS (Docker-safe)
# -------------------------

# decode_responses must be False — RQ serialises job data as bytes internally.
redis_conn = Redis(host="redis", port=6379, decode_responses=False)

mongo_client = MongoClient("mongodb://mongodb:27017/")
mongo_db = mongo_client["ims_db"]
signals_collection = mongo_db["signals"]

# -------------------------
# METRICS
# -------------------------

signal_count = 0
start_time = time.time()

# -------------------------
# RETRY
# -------------------------

def retry(fn, retries=3):
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            print(f"[RETRY {i+1}] {e}")
            time.sleep(1)
    return None

# -------------------------
# DEBOUNCE
# -------------------------

def is_duplicate(component_id):
    key = f"debounce:{component_id}"
    count = redis_conn.incr(key)
    redis_conn.expire(key, 10)
    return count > 1

# -------------------------
# MAIN WORKER
# -------------------------

def process_signal(signal):
    global signal_count, start_time

    signal_count += 1
    if time.time() - start_time >= 5:
        print(f"📊 Signals/sec: {signal_count / 5}")
        signal_count = 0
        start_time = time.time()

    component_id = signal.get("component_id")

    # 1. RAW LOG (MongoDB)
    signals_collection.insert_one(signal)

    # 2. DEBOUNCE
    if is_duplicate(component_id):
        print(f"⛔ Debounced: {component_id}")
        return

    # 3. STRATEGY
    strategy = get_alert_strategy(component_id)
    severity = strategy.severity()

    db = SessionLocal()

    # 4. CREATE INCIDENT — db session always closed via finally
    try:
        def create():
            incident = Incident(
                component_id=component_id,
                severity=severity,
                status="OPEN",
                start_time=datetime.datetime.utcnow()
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)
            return incident

        incident = retry(create)
        if incident:
            print(f"🟢 Incident created: {incident.id}")
            redis_conn.set(f"incident:{incident.id}", b"ACTIVE", ex=3600)
    finally:
        db.close()
