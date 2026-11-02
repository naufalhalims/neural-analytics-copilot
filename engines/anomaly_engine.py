"""Statistical Outlier & Anomaly Detection Engine.
Mendeteksi lonjakan kegagalan (spike) menggunakan rolling Z-score & group variance.
Berjalan dalam hitungan milidetik di CPU tanpa membebani LLM.
"""

import duckdb
import numpy as np
import pandas as pd
from typing import Dict, Any, List

class AnomalyEngine:
    def __init__(self, parquet_path: str = "data/transactions_5m.parquet"):
        self.parquet_path = parquet_path
        self.conn = duckdb.connect(":memory:")
        self.conn.execute(f"CREATE VIEW transactions AS SELECT * FROM read_parquet('{self.parquet_path}')")
        
        # Caching hasil Z-score agar tidak scan 5 juta data berulang-ulang di setiap request
        self._cached_spikes = None
        
    def detect_channel_spikes(self, z_threshold: float = 2.5) -> List[Dict[str, Any]]:
        """Mendeteksi tanggal dan kanal yang mengalami lonjakan tingkat kegagalan secara statistik."""
        if self._cached_spikes is not None:
            return self._cached_spikes
        query = """
        SELECT 
            strftime(timestamp, '%Y-%m-%d') as tx_date,
            channel,
            COUNT(*) as total_tx,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_tx,
            ROUND(AVG(CASE WHEN status = 'FAILED' THEN 1.0 ELSE 0.0 END) * 100, 2) as fail_rate_pct
        FROM transactions
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
        df = self.conn.execute(query).df()
        
        anomalies = []
        
        # Analisis Z-Score per kanal
        for channel_name in df['channel'].unique():
            ch_df = df[df['channel'] == channel_name].copy()
            rates = ch_df['fail_rate_pct'].values
            
            if len(rates) < 5:
                continue
                
            mean = np.mean(rates)
            std = np.std(rates)
            
            if std == 0:
                continue
                
            ch_df['z_score'] = (ch_df['fail_rate_pct'] - mean) / std
            
            # Cari baris yang melampaui z_threshold
            outliers = ch_df[ch_df['z_score'] >= z_threshold]
            for _, row in outliers.iterrows():
                # Query kode error paling dominan di tanggal dan kanal ini
                top_err_query = f"""
                SELECT failure_code, COUNT(*) as cnt 
                FROM transactions 
                WHERE strftime(timestamp, '%Y-%m-%d') = '{row['tx_date']}' 
                  AND channel = '{channel_name}' 
                  AND status = 'FAILED'
                GROUP BY 1 
                ORDER BY cnt DESC 
                LIMIT 1
                """
                top_err = self.conn.execute(top_err_query).df().to_dict(orient="records")
                primary_code = top_err[0]['failure_code'] if top_err else "UNKNOWN"
                
                anomalies.append({
                    "date": row['tx_date'],
                    "channel": channel_name,
                    "fail_rate_pct": float(row['fail_rate_pct']),
                    "baseline_mean_pct": round(float(mean), 2),
                    "z_score": round(float(row['z_score']), 2),
                    "failed_count": int(row['failed_tx']),
                    "primary_failure_code": primary_code,
                    "severity": "CRITICAL" if row['z_score'] >= 4.0 else "WARNING"
                })
                
        # Urutkan berdasarkan z_score tertinggi
        anomalies.sort(key=lambda x: x['z_score'], reverse=True)
        self._cached_spikes = anomalies
        return anomalies
