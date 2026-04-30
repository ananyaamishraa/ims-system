from redis import Redis
from rq import Queue

redis_conn = Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    health_check_interval=30
)

queue = Queue("default", connection=redis_conn) 
