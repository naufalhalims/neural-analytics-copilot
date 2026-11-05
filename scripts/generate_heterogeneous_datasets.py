#!/usr/bin/env python3
"""
Heterogeneous Dataset Stress-Test & Portability Suite.
Membuat 3 skenario dataset berbeda untuk menguji robustness & menemukan logical flaw:
1. Dataset A: E-Commerce Retail Marketplace (100k rows, naming: order_id, order_value, payment_type, order_status, created_at).
2. Dataset B: Ride-Hailing & Logistics Fintech (50k rows, naming: trip_id, fare_amount, wallet_provider, state, error_type).
3. Dataset C: Minimal Sparse / Anomaly Edge-Case (1k rows, banyak NULL, nilai negatif, format ISO timestamp tak lazim).

Menguji:
- Schema portability & automated DuckDB aliasing view.
- AST Guardrail resilience.
- Agregasi edge-case (NULL handling, division by zero, empty filters).
"""

import os
import duckdb
import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta

DATA_DIR = "/home/ubuntu/apps/neural-analytics-chatbot/data/test_datasets"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_ecommerce_dataset(n=100000):
    """Dataset Marketplace: order_id, customer_id, order_value, payment_type, order_status, created_at, category"""
    print(f"[*] Generating E-Commerce dataset ({n} rows)...")
    np.random.seed(42)
    start_date = datetime(2026, 8, 1)
    
    categories = ["Fashion", "Electronics", "Groceries", "Home_Living", "Beauty"]
    payment_types = ["SHOPEEPAY", "GOPAY", "BCA_ONEKLIK", "COD", "CREDIT_CARD"]
    statuses = ["COMPLETED", "CANCELLED", "PAYMENT_FAILED", "REFUNDED"]
    
    dates = [start_date + timedelta(seconds=int(s)) for s in np.random.randint(0, 60*86400, n)]
    
    df = pd.DataFrame({
        "order_id": [f"ORD-{i:07d}" for i in range(1, n + 1)],
        "customer_id": [f"CUST-{np.random.randint(1000, 9999)}" for _ in range(n)],
        "order_value": np.random.exponential(scale=150000, size=n).round(0) + 10000,
        "payment_type": np.random.choice(payment_types, size=n, p=[0.35, 0.25, 0.20, 0.10, 0.10]),
        "order_status": np.random.choice(statuses, size=n, p=[0.88, 0.04, 0.06, 0.02]),
        "category": np.random.choice(categories, size=n),
        "created_at": dates
    })
    path = os.path.join(DATA_DIR, "ecommerce_100k.parquet")
    df.to_parquet(path, index=False)
    print(f"[+] Saved E-Commerce dataset to {path}")
    return path

def generate_ridehailing_dataset(n=50000):
    """Dataset Ride-Hailing: trip_id, fare_amount, wallet_provider, state, error_type, request_time"""
    print(f"[*] Generating Ride-Hailing dataset ({n} rows)...")
    np.random.seed(99)
    start_date = datetime(2026, 9, 1)
    
    providers = ["OVO_BALANCE", "GOPAY_WALLET", "DANA_LINKED", "CASH", "JAGO_POCKET"]
    states = ["SUCCESS", "FAILED", "EXPIRED"]
    errors = ["INSUFFICIENT_FUNDS", "PIN_BLOCKED", "SYSTEM_TIMEOUT", "USER_ABORTED", "NONE"]
    
    dates = [start_date + timedelta(seconds=int(s)) for s in np.random.randint(0, 30*86400, n)]
    
    states_choices = np.random.choice(states, size=n, p=[0.92, 0.06, 0.02])
    error_choices = []
    for s in states_choices:
        if s == "SUCCESS":
            error_choices.append("NONE")
        else:
            error_choices.append(np.random.choice(["INSUFFICIENT_FUNDS", "PIN_BLOCKED", "SYSTEM_TIMEOUT", "USER_ABORTED"]))
            
    df = pd.DataFrame({
        "trip_id": [f"TRIP-{i:06d}" for i in range(1, n + 1)],
        "fare_amount": np.random.uniform(15000, 120000, size=n).round(-2),
        "wallet_provider": np.random.choice(providers, size=n),
        "state": states_choices,
        "error_type": error_choices,
        "request_time": dates
    })
    path = os.path.join(DATA_DIR, "ridehailing_50k.parquet")
    df.to_parquet(path, index=False)
    print(f"[+] Saved Ride-Hailing dataset to {path}")
    return path

def generate_sparse_edgecase_dataset(n=1000):
    """Dataset Sparse & Edge Cases: NULL values, 0 amount, duplicate timestamps, unknown statuses"""
    print(f"[*] Generating Sparse Edge-Case dataset ({n} rows)...")
    np.random.seed(777)
    
    amounts = np.random.choice([0.0, 1000.0, 50000.0, np.nan, -500.0], size=n, p=[0.1, 0.4, 0.3, 0.15, 0.05])
    channels = np.random.choice(["VA_TEST", None, "UNKNOWN_METHOD", ""], size=n, p=[0.6, 0.2, 0.1, 0.1])
    statuses = np.random.choice(["SUCCESS", "FAILED", None, "PENDING", "UNKNOWN"], size=n, p=[0.5, 0.3, 0.1, 0.05, 0.05])
    
    df = pd.DataFrame({
        "id": list(range(1, n + 1)),
        "amount": amounts,
        "channel": channels,
        "status": statuses,
        "failure_code": [None if s == "SUCCESS" else "ERR_TEST" for s in statuses],
        "timestamp": [datetime(2026, 9, 15) if i % 10 == 0 else datetime(2026, 9, 1) + timedelta(minutes=i) for i in range(n)]
    })
    path = os.path.join(DATA_DIR, "edgecase_sparse_1k.parquet")
    df.to_parquet(path, index=False)
    print(f"[+] Saved Sparse dataset to {path}")
    return path

if __name__ == "__main__":
    generate_ecommerce_dataset()
    generate_ridehailing_dataset()
    generate_sparse_edgecase_dataset()
