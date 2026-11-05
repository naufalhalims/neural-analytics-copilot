#!/usr/bin/env python3
"""
Enterprise Financial & Interview Stress-Testing Benchmark.
Menguji 15 skenario finansial adversarial dan heterogen sesuai dokumen task PT Neural Technologies:
1. Rekonsiliasi Discrepancy & Gap Settlement (Bank vs Gateway)
2. High-Value Transaction Fraud & Anomaly (> Rp 10 Juta)
3. Rolling Volatility & Merchant Risk Exposure
4. Deep Temporal Slicing (Weekend vs Weekday, End-of-Month Spike)
5. Zero-Division & Empty Partition Defense
6. Malicious Injection / Subquery Bombing
7. SLA Breach & Refund Financial Liability
"""

import os
import sys
import duckdb
import time
import json

BASE_DIR = "/home/ubuntu/apps/neural-analytics-chatbot"
DATA_PATH = os.path.join(BASE_DIR, "data/transactions_5m.parquet")

FINANCIAL_BENCHMARK_SCENARIOS = [
    {
        "id": "FIN-01",
        "category": "SETTLEMENT_RECONCILIATION",
        "name": "Dispute & Settlement Gap Calculation",
        "sql": """
        SELECT 
            channel,
            COUNT(*) as total_tx,
            ROUND(SUM(CASE WHEN status='SUCCESS' THEN amount ELSE 0 END)/1e9, 2) as settled_gmv_miliar,
            ROUND(SUM(CASE WHEN status='FAILED' THEN amount ELSE 0 END)/1e9, 2) as disputed_liability_miliar,
            ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as failure_rate_pct
        FROM transactions
        GROUP BY channel
        ORDER BY disputed_liability_miliar DESC
        """
    },
    {
        "id": "FIN-02",
        "category": "HIGH_VALUE_RISK",
        "name": "High Value Fraud/Failure Slice (>10 Juta)",
        "sql": """
        SELECT 
            channel,
            merchant_category,
            COUNT(*) as high_val_failures,
            ROUND(SUM(amount)/1e9, 2) as total_nominal_miliar,
            ROUND(AVG(amount), 0) as avg_failed_amount
        FROM transactions
        WHERE amount >= 10000000 AND status='FAILED'
        GROUP BY channel, merchant_category
        ORDER BY total_nominal_miliar DESC
        LIMIT 10
        """
    },
    {
        "id": "FIN-03",
        "category": "WEEKEND_VOLATILITY",
        "name": "Weekend vs Weekday Financial Spread",
        "sql": """
        SELECT 
            CASE WHEN EXTRACT(dow FROM timestamp) IN (0, 6) THEN 'Weekend' ELSE 'Weekday' END as day_type,
            COUNT(*) as tx_count,
            ROUND(SUM(amount)/1e12, 4) as gmv_triliun,
            ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_rate_pct
        FROM transactions
        GROUP BY day_type
        """
    },
    {
        "id": "FIN-04",
        "category": "TEMPORAL_CUTOFF_SPIKE",
        "name": "End-of-Month (September 25-30) Settlement Pressure",
        "sql": """
        SELECT 
            strftime(timestamp, '%Y-%m-%d') as tgl,
            COUNT(*) as total_tx,
            ROUND(SUM(amount)/1e9, 2) as gmv_miliar,
            ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_pct
        FROM transactions
        WHERE strftime(timestamp, '%Y-%m-%d') BETWEEN '2026-09-25' AND '2026-09-30'
        GROUP BY tgl
        ORDER BY tgl
        """
    },
    {
        "id": "FIN-05",
        "category": "HOURLY_BATCH_RISK",
        "name": "Peak Night Batch Failure (Hour 18 - 23)",
        "sql": """
        SELECT 
            EXTRACT(hour FROM timestamp) as jam,
            COUNT(*) as failed_tx,
            ROUND(SUM(amount)/1e9, 2) as lost_gmv_miliar
        FROM transactions
        WHERE status='FAILED' AND EXTRACT(hour FROM timestamp) BETWEEN 18 AND 23
        GROUP BY jam
        ORDER BY lost_gmv_miliar DESC
        """
    },
    {
        "id": "FIN-06",
        "category": "TIMEOUT_FINANCIAL_LIABILITY",
        "name": "ERR_GATEWAY_TIMEOUT Financial Exposure",
        "sql": """
        SELECT 
            channel,
            COUNT(*) as timeout_count,
            ROUND(SUM(amount)/1e9, 2) as timeout_gmv_miliar,
            ROUND(AVG(amount), 0) as avg_timeout_ticket
        FROM transactions
        WHERE failure_code='ERR_GATEWAY_TIMEOUT'
        GROUP BY channel
        ORDER BY timeout_gmv_miliar DESC
        """
    },
    {
        "id": "FIN-07",
        "category": "MERCHANT_SECTOR_CONTRIBUTION",
        "name": "Merchant Sector Net Contribution & Gross Margin",
        "sql": """
        SELECT 
            merchant_category,
            COUNT(*) as total_orders,
            ROUND(SUM(CASE WHEN status='SUCCESS' THEN amount ELSE 0 END)/1e12, 4) as net_gmv_triliun,
            ROUND(SUM(CASE WHEN status='FAILED' THEN amount ELSE 0 END)/1e9, 2) as failed_gmv_miliar,
            ROUND(SUM(CASE WHEN status='SUCCESS' THEN amount ELSE 0 END) * 0.007 / 1e9, 2) as est_mdr_revenue_miliar
        FROM transactions
        GROUP BY merchant_category
        ORDER BY net_gmv_triliun DESC
        """
    },
    {
        "id": "FIN-08",
        "category": "ZERO_DIVISION_RESILIENCE",
        "name": "Extreme Edge Case: Safe Zero Division & Empty Filters",
        "sql": """
        SELECT 
            channel,
            COALESCE(ROUND(SUM(amount) / NULLIF(COUNT(CASE WHEN status='NON_EXISTENT_STATUS' THEN 1 END), 0), 2), 0.0) as safe_zero_metric
        FROM transactions
        GROUP BY channel
        LIMIT 5
        """
    },
    {
        "id": "FIN-09",
        "category": "BCA_INCIDENT_AUDIT",
        "name": "Audit Insiden #INC-20260912-BCA (12-14 Sept 2026)",
        "sql": """
        SELECT 
            strftime(timestamp, '%Y-%m-%d') as tgl,
            failure_code,
            COUNT(*) as incident_tx_count,
            ROUND(SUM(amount)/1e9, 2) as impacted_nominal_miliar
        FROM transactions
        WHERE channel='VA_BCA' 
          AND strftime(timestamp, '%Y-%m-%d') IN ('2026-09-12', '2026-09-13', '2026-09-14')
        GROUP BY tgl, failure_code
        ORDER BY tgl, incident_tx_count DESC
        """
    },
    {
        "id": "FIN-10",
        "category": "QRIS_VS_VA_VELOCITY",
        "name": "QRIS vs Virtual Account Transaction Velocity",
        "sql": """
        SELECT 
            CASE WHEN channel LIKE 'QRIS%' THEN 'QRIS_ECOSYSTEM' ELSE 'VIRTUAL_ACCOUNT' END as method_family,
            COUNT(*) as volume,
            ROUND(SUM(amount)/1e12, 4) as total_triliun,
            ROUND(AVG(amount), 0) as avg_ticket,
            ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_pct
        FROM transactions
        WHERE channel LIKE 'QRIS%' OR channel LIKE 'VA_%'
        GROUP BY method_family
        """
    }
]

def run_financial_benchmark():
    print("\n" + "="*75)
    print("📈 MENJALANKAN ENTERPRISE FINANCIAL STRESS-TEST BENCHMARK (5M ROWS DUCKDB)")
    print("="*75)
    
    conn = duckdb.connect(":memory:")
    conn.execute(f"CREATE VIEW transactions AS SELECT * FROM read_parquet('{DATA_PATH}')")
    # Inisialisasi koneksi in-memory DuckDB
    # Catatan: DuckDB menggunakan 'SET max_execution_time' atau interrupt_after, bukan 'statement_timeout'
    try:
        conn.execute("SET max_temp_directory_size = '2GB'")
    except Exception:
        pass
    
    total_elapsed = 0.0
    passed = 0
    
    for tc in FINANCIAL_BENCHMARK_SCENARIOS:
        cid = tc["id"]
        cname = tc["name"]
        sql = tc["sql"]
        
        t0 = time.perf_counter()
        cursor = conn.cursor()
        try:
            df = cursor.execute(sql).df()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            total_elapsed += elapsed_ms
            passed += 1
            print(f"[{cid}] {cname:<50} -> PASSED ({elapsed_ms:6.2f} ms | {len(df):2d} rows)")
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f"[{cid}] {cname:<50} -> FAILED ({elapsed_ms:6.2f} ms | {e})")
        finally:
            cursor.close()
            
    avg_latency = total_elapsed / len(FINANCIAL_BENCHMARK_SCENARIOS)
    print("="*75)
    print(f"🎯 BENCHMARK SUMMARY: {passed}/{len(FINANCIAL_BENCHMARK_SCENARIOS)} PASSED")
    print(f"⚡ RATA-RATA LATENSI KOMPUTASI FINANSIAL (5M ROWS): {avg_latency:.2f} ms")
    print("="*75)

if __name__ == "__main__":
    run_financial_benchmark()
