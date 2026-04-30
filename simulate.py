import requests
import time

url = "http://127.0.0.1:8000/signals"

for i in range(50):
    data = {
        "component_id": "CACHE_CLUSTER_01",
        "severity": "P2",
        "message": "Cache timeout"
    }
    requests.post(url, json=data)
    time.sleep(0.1) 
