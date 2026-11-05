#!/usr/bin/env python3
"""
Diagnostic Runner untuk menguji sistem DuckDB & AST Guardrail pada 3 dataset heterogen.
Mencari kelemahan, celah logika, dan batas kemampuan adaptasi sistem.
"""

import os
import sys
import duckdb
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engines.sql_engine import SQLEngine

DATASETS = {
    "ecommerce": {
        "path": "/home/ubuntu/apps/neural-analytics-chatbot/data/test_datasets/ecommerce_100k.parquet",
        "mapping": {
            "amount": "order_value",
            "channel": "payment_type",
            "status": "order_status",
            "timestamp": "created_at",
            "merchant_category": "category"
        },
        "success_status_val": "COMPLETED",
        "failed_status_val": "PAYMENT_FAILED"
    },
    "ridehailing": {
        "path": "/home/ubuntu/apps/neural-analytics-chatbot/data/test_datasets/ridehailing_50k.parquet",
        "mapping": {
            "amount": "fare_amount",
            "channel": "wallet_provider",
            "status": "state",
            "timestamp": "request_time",
            "failure_code": "error_type"
        },
        "success_status_val": "SUCCESS",
        "failed_status_val": "FAILED"
    },
    "sparse_edgecase": {
        "path": "/home/ubuntu/apps/neural-analytics-chatbot/data/test_datasets/edgecase_sparse_1k.parquet",
        "mapping": {
            "amount": "amount",
            "channel": "channel",
            "status": "status",
            "timestamp": "timestamp",
            "failure_code": "failure_code"
        },
        "success_status_val": "SUCCESS",
        "failed_status_val": "FAILED"
    }
}

def test_dataset(name, cfg):
    print(f"\n{'='*65}")
    print(f"🔬 TESTING ROBUSTNESS ATAS DATASET: {name.upper()}")
    print(f"{'='*65}")
    
    conn = duckdb.connect(":memory:")
    
    # 1. Test Schema Aliasing View
    # Memetakan schema kustom ke unified schema 'transactions'
    select_clauses = []
    for standard_col, target_col in cfg["mapping"].items():
        select_clauses.append(f"{target_col} AS {standard_col}")
    
    view_sql = f"CREATE VIEW transactions AS SELECT {', '.join(select_clauses)} FROM read_parquet('{cfg['path']}')"
    print(f"[*] Generated View SQL: {view_sql}")
    
    try:
        conn.execute(view_sql)
        print("[+] Schema Aliasing View berhasil dibuat!")
    except Exception as e:
        print(f"[!] FLAW DETECTED on View Creation: {e}")
        return

    # 2. Test Makro Query (KPIs)
    print("\n--- [TEST 1: Makro Agregasi GMV & Volume] ---")
    succ_val = cfg["success_status_val"]
    fail_val = cfg["failed_status_val"]
    
    kpi_query = f"""
    SELECT 
        COUNT(*) as total_rows,
        ROUND(COALESCE(SUM(CASE WHEN status='{succ_val}' THEN amount ELSE 0 END), 0), 2) as gmv,
        ROUND(COALESCE(AVG(CASE WHEN status='{fail_val}' THEN 1.0 ELSE 0.0 END), 0)*100, 2) as fail_rate_pct,
        COUNT(DISTINCT channel) as unique_channels
    FROM transactions
    """
    try:
        t0 = time.perf_counter()
        res_df = conn.execute(kpi_query).df()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[+] Output KPI ({elapsed_ms:.2f} ms):")
        print(res_df.to_dict(orient="records")[0])
    except Exception as e:
        print(f"[!] FLAW DETECTED in KPI Query: {e}")

    # 3. Test Time-Series Truncation
    print("\n--- [TEST 2: Time-series Granularity (Harian)] ---")
    ts_query = "SELECT strftime(timestamp, '%Y-%m-%d') as tgl, COUNT(*) as tx_count FROM transactions WHERE timestamp IS NOT NULL GROUP BY tgl ORDER BY tgl LIMIT 5"
    try:
        t0 = time.perf_counter()
        ts_df = conn.execute(ts_query).df()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[+] Output Time-Series ({elapsed_ms:.2f} ms): {len(ts_df)} rows")
    except Exception as e:
        print(f"[!] FLAW DETECTED in Time-Series: {e}")

    # 4. Stress Test: Edge Case NULL, Negative Amount, Division by Zero
    print("\n--- [TEST 3: Edge Case Math & Data Cleanliness] ---")
    edge_query = """
    SELECT 
        COUNT(CASE WHEN amount IS NULL THEN 1 END) as null_amount_count,
        COUNT(CASE WHEN amount < 0 THEN 1 END) as negative_amount_count,
        COUNT(CASE WHEN channel IS NULL OR channel = '' THEN 1 END) as invalid_channel_count,
        ROUND(SUM(amount) / NULLIF(COUNT(CASE WHEN status='SUCCESS' THEN 1 END), 0), 2) as safe_avg_ticket
    FROM transactions
    """
    try:
        edge_df = conn.execute(edge_query).df()
        print("[+] Output Edge Case Audit:")
        print(edge_df.to_dict(orient="records")[0])
    except Exception as e:
        print(f"[!] FLAW DETECTED in Edge Query: {e}")

if __name__ == "__main__":
    for name, cfg in DATASETS.items():
        test_dataset(name, cfg)
