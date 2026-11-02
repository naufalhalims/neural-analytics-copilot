"""Script generator data transaksi sintetis skala besar (Apache Parquet).
Standar Adyen / PaySim: 100.000 (default) hingga 1.000.000+ baris transaksi.
Dilengkapi anomali terencana pada kanal VA_BCA (12-15 September 2026).
"""

import argparse
import datetime
import random
import uuid
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def generate_transactions(num_rows: int = 100000, output_file: str = "data/transactions.parquet"):
    print(f"[*] Mulai men-generate {num_rows:,} baris transaksi perbankan...")
    
    start_date = datetime.datetime(2026, 7, 1, 0, 0, 0)
    end_date = datetime.datetime(2026, 9, 30, 23, 59, 59)
    total_seconds = int((end_date - start_date).total_seconds())
    
    # Distribusi kanal
    channels = ["VA_BCA", "VA_MANDIRI", "QRIS_GOPAY", "CREDIT_CARD", "EWALLET_OVO"]
    channel_weights = [0.35, 0.25, 0.20, 0.12, 0.08]
    
    # Kategori merchant
    categories = ["Retail", "Gaming_Digital", "Bill_Payment", "Travel_Hospitality"]
    category_weights = [0.45, 0.25, 0.20, 0.10]
    
    # Random timestamps
    random_seconds = np.random.randint(0, total_seconds, size=num_rows)
    timestamps = [start_date + datetime.timedelta(seconds=int(s)) for s in random_seconds]
    
    selected_channels = np.random.choice(channels, size=num_rows, p=channel_weights)
    selected_categories = np.random.choice(categories, size=num_rows, p=category_weights)
    
    # Nominal transaksi (Log-normal distribution: Rp 10.000 - Rp 25.000.000)
    mu, sigma = 11.5, 1.2
    raw_amounts = np.random.lognormal(mu, sigma, num_rows)
    amounts = np.clip(raw_amounts, 10000, 25000000).round(-2)  # Dibulatkan ke ratusan terdekat
    
    statuses = []
    failure_codes = []
    
    # Waktu anomali BCA: 12 Sep 2026 14:00 s/d 15 Sep 2026 10:00
    bca_anomaly_start = datetime.datetime(2026, 9, 12, 14, 0, 0)
    bca_anomaly_end = datetime.datetime(2026, 9, 15, 10, 0, 0)
    
    for i in range(num_rows):
        ts = timestamps[i]
        ch = selected_channels[i]
        
        # Kondisi Anomali 1: Insiden Switch Core BCA
        if ch == "VA_BCA" and (bca_anomaly_start <= ts <= bca_anomaly_end):
            # Failure rate loncat ke ~28.4%
            is_failed = random.random() < 0.284
            if is_failed:
                statuses.append("FAILED")
                # 92% adalah ERR_GATEWAY_TIMEOUT
                if random.random() < 0.92:
                    failure_codes.append("ERR_GATEWAY_TIMEOUT")
                else:
                    failure_codes.append("SYSTEM_MALFUNCTION")
            else:
                statuses.append("SUCCESS")
                failure_codes.append("NONE")
                
        # Kondisi Normal Transaksi
        else:
            # Baseline normal failure rate ~3.5%
            is_failed = random.random() < 0.035
            if is_failed:
                statuses.append("FAILED")
                # Distribusi error umum
                err = random.choices(
                    ["INSUFFICIENT_FUNDS", "INVALID_PIN", "ERR_GATEWAY_TIMEOUT", "SYSTEM_MALFUNCTION"],
                    weights=[0.50, 0.30, 0.12, 0.08]
                )[0]
                failure_codes.append(err)
            else:
                statuses.append("SUCCESS")
                failure_codes.append("NONE")
                
    # Buat UUID transaksi
    tx_ids = [f"TXN-2026-{uuid.uuid4().hex[:8].upper()}" for _ in range(num_rows)]
    
    df = pd.DataFrame({
        "transaction_id": tx_ids,
        "timestamp": timestamps,
        "channel": selected_channels,
        "merchant_category": selected_categories,
        "amount": amounts,
        "status": statuses,
        "failure_code": failure_codes
    })
    
    # Urutkan berdasarkan waktu
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    # Simpan ke format Parquet dengan kompresi ZSTD
    table = pa.Table.from_pandas(df)
    pq.write_table(table, output_file, compression="zstd")
    
    print(f"[+] Selesai! File tersimpan di '{output_file}' ({len(df):,} baris).")
    print(f"    - Rentang Tanggal: {df['timestamp'].min()} s/d {df['timestamp'].max()}")
    print(f"    - Distribusi Status: {dict(df['status'].value_counts())}")
    
    # Cek anomali BCA
    bca_spike = df[(df['channel'] == 'VA_BCA') & (df['timestamp'] >= bca_anomaly_start) & (df['timestamp'] <= bca_anomaly_end)]
    bca_fail_rate = (bca_spike['status'] == 'FAILED').mean() * 100
    print(f"    - Verifikasi Failure Rate VA_BCA saat insiden 12-15 Sep: {bca_fail_rate:.2f}% (Target: ~28%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100000, help="Jumlah baris data transaksi")
    parser.add_argument("--out", type=str, default="data/transactions_100k.parquet", help="Path file output Parquet")
    args = parser.parse_args()
    
    generate_transactions(num_rows=args.rows, output_file=args.out)
