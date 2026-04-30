from fastapi import FastAPI
import requests
import random
import numpy as np
import os
import time

app = FastAPI()

CACHE_URL = os.getenv("CACHE_URL", "http://cache_service:8000/query")

ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5"]
QUERY_TYPES = ["Q1", "Q2", "Q3", "Q4", "Q5"]

def generate_uniform_query():
    query_type = random.choice(QUERY_TYPES)

    if query_type == "Q4":
        zone_a, zone_b = random.sample(ZONES, 2)
        return {
            "type": "Q4",
            "params": {
                "zone_a": zone_a,
                "zone_b": zone_b,
                "confidence_min": random.choice([0.0, 0.5, 0.7])
            }
        }

    if query_type == "Q5":
        return {
            "type": "Q5",
            "params": {
                "zone_id": random.choice(ZONES),
                "bins": random.choice([5, 10])
            }
        }

    return {
        "type": query_type,
        "params": {
            "zone_id": random.choice(ZONES),
            "confidence_min": random.choice([0.0, 0.5, 0.7])
        }
    }

def generate_zipf_zone():
    ranks = np.arange(1, len(ZONES) + 1)
    probs = 1 / ranks
    probs = probs / probs.sum()
    return np.random.choice(ZONES, p=probs)

def generate_zipf_query():
    query_type = random.choice(QUERY_TYPES)
    main_zone = generate_zipf_zone()

    if query_type == "Q4":
        other_zone = random.choice([z for z in ZONES if z != main_zone])
        return {
            "type": "Q4",
            "params": {
                "zone_a": main_zone,
                "zone_b": other_zone,
                "confidence_min": random.choice([0.0, 0.5, 0.7])
            }
        }

    if query_type == "Q5":
        return {
            "type": "Q5",
            "params": {
                "zone_id": main_zone,
                "bins": random.choice([5, 10])
            }
        }

    return {
        "type": query_type,
        "params": {
            "zone_id": main_zone,
            "confidence_min": random.choice([0.0, 0.5, 0.7])
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/run")
def run_traffic(payload: dict):
    distribution = payload.get("distribution", "uniform")
    n_requests = int(payload.get("n_requests", 100))

    responses = []
    start = time.perf_counter()

    for _ in range(n_requests):
        if distribution == "zipf":
            query = generate_zipf_query()
        else:
            query = generate_uniform_query()

        resp = requests.post(CACHE_URL, json=query, timeout=10)
        responses.append(resp.json())

    total_time = time.perf_counter() - start
    throughput = n_requests / total_time if total_time > 0 else 0

    return {
        "distribution": distribution,
        "n_requests": n_requests,
        "elapsed_seconds": total_time,
        "throughput": throughput,
        "sample": responses[:5]
    }
