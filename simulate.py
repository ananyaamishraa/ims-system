import requests
import random
import time
import threading

API_URL = "http://127.0.0.1:8000/signals"

COMPONENTS = [
    "RDBMS_MAIN",
    "CACHE_CLUSTER_01",
    "API_GATEWAY",
    "MCP_HOST_01",
    "NOSQL_DB"
]

# -------------------------
# SINGLE SIGNAL SENDER
# -------------------------
def send_signal(i):
    signal = {
        "component_id": random.choice(COMPONENTS),
        "error_type": random.choice([
            "latency_spike",
            "timeout",
            "connection_error",
            "memory_leak"
        ]),
        "timestamp": time.time(),
        "payload": f"error_event_{i}"
    }

    try:
        res = requests.post(API_URL, json=signal)
        print(res.json())
    except Exception as e:
        print("Error sending signal:", e)

# -------------------------
# BURST SIMULATION
# -------------------------
def burst_simulation(count=1000, concurrency=50):
    threads = []

    for i in range(count):
        t = threading.Thread(target=send_signal, args=(i,))
        threads.append(t)
        t.start()

        # limit concurrency
        if len(threads) >= concurrency:
            for t in threads:
                t.join()
            threads = []

# -------------------------
# FAILURE SIMULATION (RDBMS STRESS)
# -------------------------
def rdbms_failure_simulation():
    for i in range(200):
        signal = {
            "component_id": "RDBMS_MAIN",
            "error_type": "db_crash",
            "timestamp": time.time(),
            "payload": f"rdbms_failure_{i}"
        }

        try:
            requests.post(API_URL, json=signal)
        except Exception as e:
            print(e)

        time.sleep(0.01)

# -------------------------
# MAIN RUNNER
# -------------------------
if __name__ == "__main__":
    print("🚀 Starting IMS Simulation...")

    # Phase 1: Normal load
    print("📡 Normal load simulation")
    burst_simulation(300)

    time.sleep(2)

    # Phase 2: RDBMS failure storm
    print("🔥 Simulating RDBMS failure storm")
    rdbms_failure_simulation()

    time.sleep(2)

    # Phase 3: High burst again
    print("⚡ High burst traffic")
    burst_simulation(700)

    print("✅ Simulation complete")
