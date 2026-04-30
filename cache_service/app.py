from fastapi import FastAPI, HTTPException
import redis
import requests
import json
import os
import time
import csv

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
RESPONSE_GENERATOR_URL = os.getenv("RESPONSE_GENERATOR_URL", "http://response_generator:8001/query")
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))
METRICS_FILE = "/app/metrics/metrics.csv"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def build_cache_key(payload):
    query_type = payload["type"]
    params = json.dumps(payload.get("params", {}), sort_keys=True)
    return f"{query_type}:{params}"

def save_metric(event_type, query_type, latency_ms, cache_key):
    file_exists = os.path.exists(METRICS_FILE)

    with open(METRICS_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists or os.path.getsize(METRICS_FILE) == 0:
            writer.writerow(["event_type", "query_type", "latency_ms", "cache_key", "timestamp"])

        writer.writerow([
            event_type,
            query_type,
            round(latency_ms, 3),
            cache_key,
            time.time()
        ])

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query")
def query_cache(payload: dict):
    start = time.perf_counter()

    try:
        cache_key = build_cache_key(payload)
        query_type = payload["type"]

        cached_value = r.get(cache_key)

        if cached_value is not None:
            latency_ms = (time.perf_counter() - start) * 1000
            save_metric("hit", query_type, latency_ms, cache_key)
            return {
                "source": "cache",
                "cache_key": cache_key,
                "data": json.loads(cached_value),
                "latency_ms": latency_ms
            }

        response = requests.post(RESPONSE_GENERATOR_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        r.setex(cache_key, CACHE_TTL, json.dumps(result))

        latency_ms = (time.perf_counter() - start) * 1000
        save_metric("miss", query_type, latency_ms, cache_key)

        return {
            "source": "response_generator",
            "cache_key": cache_key,
            "data": result,
            "latency_ms": latency_ms
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error llamando a response_generator: {str(e)}")
