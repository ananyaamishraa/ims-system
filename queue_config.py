from redis import Redis
from rq import Queue

# decode_responses must be False — RQ serialises job data as bytes internally.
# Setting it to True causes Redis to return strings, breaking RQ's job encoding.
redis_conn = Redis(
    host="redis",
    port=6379,
    decode_responses=False,
    health_check_interval=30
)

queue = Queue("default", connection=redis_conn)
