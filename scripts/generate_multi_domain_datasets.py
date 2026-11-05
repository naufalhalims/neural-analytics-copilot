#!/usr/bin/env python3
"""
Generator Dataset Multi-Domain untuk Showcase Portabilitas:
1. BPJS Healthcare Claims (100.000 klaim RS, INA-CBG, status, dispute, audit)
2. B2B SaaS API Gateway (100.000 log API billing, latency, tenant, status HTTP)
3. Handayani Wisma Jaya POS (25.000 kasir fisik tunai)
"""

import os
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DATA_DIR = "/home/ubuntu/apps/neural-analytics-chatbot/data/multi_domain"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_bpjs_claims(n=100000):
    print(f"[*] Generating BPJS Healthcare Claims ({n} records)...")
    np.random.seed(42)
    start_date = datetime(2026, 1, 1)
    
    ina_cbg_codes = [
        ("I-4-10-I", "Gagal Jantung Kongestif Ringan", 4800000, 4200000, "Kardiologi"),
        ("I-4-10-II", "Gagal Jantung Kongestif Sedang", 7500000, 6800000, "Kardiologi"),
        ("E-4-10-I", "Diabetes Melitus Tanpa Komplikasi", 3200000, 3100000, "Penyakit Dalam"),
        ("J-4-16-I", "Pneumonia Ringan", 4100000, 3900000, "Paru"),
        ("O-6-10-I", "Persalinan Sesar Ringan", 6200000, 5800000, "Kebidanan"),
        ("K-4-12-I", "Apendisitis Akut Tanpa Penyulit", 5100000, 4900000, "Bedah Umum"),
        ("N-4-10-I", "Gagal Ginjal Kronik Cuci Darah", 1200000, 1150000, "Nefrologi")
    ]
    
    hospitals = [
        ("RSUP Dr. Sardjito", "Tipe A", "Yogyakarta"),
        ("RSUP Persahabatan", "Tipe A", "Jakarta"),
        ("RSUD Kota Bekasi", "Tipe B", "Bekasi"),
        ("RS Handayani Pratama", "Tipe C", "Jawa Barat"),
        ("RS Mitra Keluarga", "Tipe B", "Jawa Barat")
    ]
    
    statuses = ["APPROVED", "DISPUTED", "REJECTED", "PENDING_VERIFIKASI"]
    dispute_reasons = [
        None, None, None, None, None, None,
        "Berkas Resume Medis Tidak Lengkap",
        "Ketidaksesuaian Koding ICD-10 dengan INA-CBG",
        "Plafon Hari Rawat Inap Melampaui Batas (LOS Exceeded)",
        "Obat di Luar Formularium Nasional (Fornas)"
    ]
    
    data = []
    for i in range(1, n + 1):
        tgl = start_date + timedelta(seconds=int(np.random.randint(0, 180 * 86400)))
        diag = ina_cbg_codes[np.random.choice(len(ina_cbg_codes))]
        rs = hospitals[np.random.choice(len(hospitals))]
        st = np.random.choice(statuses, p=[0.82, 0.10, 0.05, 0.03])
        
        # Biaya tagihan riil RS vs Klaim Plafon Tarif INA-CBG
        biaya_rs = int(diag[2] * np.random.uniform(0.85, 1.30))
        plafon_bpjs = diag[3]
        
        disp = None
        if st in ["DISPUTED", "REJECTED"]:
            disp = np.random.choice([r for r in dispute_reasons if r is not None])
            
        data.append({
            "transaction_id": f"CLM-BPJS-{i:06d}",
            "timestamp": tgl,
            "hospital_name": rs[0],
            "hospital_type": rs[1],
            "channel": rs[1], # map to standard column channel
            "ina_cbg_code": diag[0],
            "diagnosis_name": diag[1],
            "department": diag[4],
            "merchant_category": diag[4], # map to standard merchant_category
            "hospital_bill_amount": biaya_rs,
            "amount": plafon_bpjs if st == "APPROVED" else biaya_rs,
            "status": "SUCCESS" if st == "APPROVED" else ("FAILED" if st == "REJECTED" else "PENDING"),
            "raw_status": st,
            "failure_code": disp if disp else ""
        })
        
    df = pd.DataFrame(data)
    out_path = os.path.join(DATA_DIR, "bpjs_claims_100k.parquet")
    df.to_parquet(out_path, index=False)
    print(f"[+] Berhasil membuat {out_path} ({len(df)} rows)")

def generate_saas_api_logs(n=100000):
    print(f"[*] Generating B2B SaaS API Gateway Logs ({n} records)...")
    np.random.seed(42)
    start_date = datetime(2026, 1, 1)
    
    tenants = [
        ("TNT-ECOM-01", "Tokopedia / GoTo", "Enterprise Tier"),
        ("TNT-FIN-02", "DANA Indonesia", "Enterprise Tier"),
        ("TNT-LOG-03", "J&T Express", "Growth Tier"),
        ("TNT-HLT-04", "Halodoc", "Growth Tier"),
        ("TNT-SME-05", "Warung Pintar", "Starter Tier")
    ]
    
    endpoints = [
        ("/v1/payments/charge", 1500, "Payment Gateway"),
        ("/v1/kyc/verify-identity", 3500, "Identity Verification"),
        ("/v1/disbursement/transfer", 2000, "Payout Engine"),
        ("/v1/credit-scoring/evaluate", 5000, "Risk Intelligence")
    ]
    
    http_statuses = [200, 200, 200, 200, 200, 200, 200, 429, 500, 504]
    
    data = []
    for i in range(1, n + 1):
        tgl = start_date + timedelta(seconds=int(np.random.randint(0, 180 * 86400)))
        tnt = tenants[np.random.choice(len(tenants))]
        ep = endpoints[np.random.choice(len(endpoints))]
        code = np.random.choice(http_statuses, p=[0.90, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01])
        
        status = "SUCCESS" if code == 200 else "FAILED"
        err = ""
        if code == 429:
            err = "ERR_RATE_LIMIT_EXCEEDED"
        elif code == 504:
            err = "ERR_GATEWAY_TIMEOUT"
        elif code == 500:
            err = "ERR_INTERNAL_SERVER_ERROR"
            
        data.append({
            "transaction_id": f"REQ-{i:07d}",
            "timestamp": tgl,
            "tenant_name": tnt[1],
            "channel": tnt[2], # Tier
            "endpoint": ep[0],
            "merchant_category": ep[2], # Service Category
            "amount": ep[1], # Fee per API call (Rp)
            "status": status,
            "http_code": code,
            "failure_code": err
        })
        
    df = pd.DataFrame(data)
    out_path = os.path.join(DATA_DIR, "saas_api_logs_100k.parquet")
    df.to_parquet(out_path, index=False)
    print(f"[+] Berhasil membuat {out_path} ({len(df)} rows)")

if __name__ == "__main__":
    generate_bpjs_claims()
    generate_saas_api_logs()
