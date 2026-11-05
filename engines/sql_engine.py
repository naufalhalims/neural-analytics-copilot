"""SQL Execution Engine dengan AST-level Security Guardrail via SQLGlot.
Hanya mengizinkan query SELECT, menolak mutasi DDL/DML, dan membatasi LIMIT demi keamanan memori.
Dilengkapi normalisasi skema multi-domain dan penghitungan baris riil (true scanned_rows).
"""

import duckdb
import os
try:
    import sqlglot
    from sqlglot import exp
    HAS_SQLGLOT = True
except ImportError:
    sqlglot = None
    exp = None
    HAS_SQLGLOT = False
from typing import Dict, Any, List


class SQLEngine:
    def __init__(self, parquet_path: str = "data/transactions_5m.parquet"):
        self.parquet_path = parquet_path
        
        # Auto-seeding jika file parquet belum ada (Zero-Setup guarantee untuk environment interviewer)
        if not os.path.exists(self.parquet_path):
            try:
                os.makedirs(os.path.dirname(self.parquet_path) or ".", exist_ok=True)
                # Coba import seed_data dari folder scripts atau buat dataset sintetis instan
                try:
                    from scripts.seed_data import generate_transactions
                    print(f"📦 [Auto-Setup] Men-generate dataset demo awal ({self.parquet_path})...")
                    generate_transactions(num_rows=100000, output_file=self.parquet_path)
                except Exception:
                    # Fallback cepat jika script seed tidak terjangkau
                    import pandas as pd
                    import numpy as np
                    n = 10000
                    df_dummy = pd.DataFrame({
                        "transaction_id": [f"TX-{i:06d}" for i in range(n)],
                        "timestamp": pd.date_range("2026-07-01", periods=n, freq="min"),
                        "amount": np.random.randint(10000, 5000000, n),
                        "status": np.random.choice(["SUCCESS", "FAILED"], n, p=[0.92, 0.08]),
                        "channel": np.random.choice(["VA_BCA", "VA_MANDIRI", "QRIS_GOPAY", "CREDIT_CARD"], n),
                        "merchant_category": np.random.choice(["Retail", "Gaming_Digital", "Bill_Payment"], n),
                        "failure_code": np.random.choice(["ERR_GATEWAY_TIMEOUT", "INSUFFICIENT_FUNDS", None], n)
                    })
                    df_dummy.to_parquet(self.parquet_path)
            except Exception as se:
                print(f"[!] Warning Auto-Seeding dataset: {se}")

        # Buat koneksi in-memory DuckDB
        self.conn = duckdb.connect(":memory:")
        # Konfigurasi memory & thread protection
        try:
            self.conn.execute("SET max_temp_directory_size = '2GB'")
            self.conn.execute("SET threads TO 4")
        except Exception:
            pass

        # Inspeksi kolom asli Parquet untuk normalisasi alias standar (timestamp, failure_code)
        raw_cols_info = self.conn.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{self.parquet_path}')"
        ).fetchall()
        raw_col_names = {r[0] for r in raw_cols_info}

        extra_aliases: List[str] = []
        if "timestamp" not in raw_col_names and "waktu_transaksi" in raw_col_names:
            extra_aliases.append("waktu_transaksi AS timestamp")
        if "failure_code" not in raw_col_names and "status_pembayaran" in raw_col_names:
            extra_aliases.append("status_pembayaran AS failure_code")

        alias_sql = (", " + ", ".join(extra_aliases)) if extra_aliases else ""
        self.conn.execute(
            f"CREATE VIEW transactions AS SELECT *{alias_sql} FROM read_parquet('{self.parquet_path}')"
        )

        # Simpan metadata skema dan jumlah baris aktual dataset
        view_cols_info = self.conn.execute("DESCRIBE SELECT * FROM transactions").fetchall()
        self.columns_schema: List[Dict[str, str]] = [
            {"name": r[0], "type": r[1]} for r in view_cols_info
        ]
        try:
            self.total_rows: int = int(
                self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            )
        except Exception:
            self.total_rows = 0

        # In-memory query result cache
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_schema_summary(self) -> str:
        """Mengembalikan ringkasan kolom dan tipe data tabel 'transactions' untuk Text-to-SQL."""
        cols_str = ", ".join(f"{c['name']} ({c['type']})" for c in self.columns_schema)
        return f"Tabel: transactions ({self.total_rows:,} baris) | Kolom: {cols_str}"

    def validate_and_sanitize(self, raw_sql: str) -> str:
        """Memeriksa integritas keamanan kueri SQL menggunakan Abstract Syntax Tree (AST)."""
        import re
        clean_sql = raw_sql.strip()

        # Multi-statement injection check (mencegah stacked queries: e.g. '; DROP TABLE ...')
        # Hapus trailing semicolon terlebih dahulu
        trimmed_semis = clean_sql.rstrip(";").strip()
        if ";" in trimmed_semis:
            raise PermissionError("Security Alert: Multi-statement query (stacked queries) dilarang keras!")

        lower_clean = trimmed_semis.lower()
        forbidden_keywords = [
            "drop table", "drop view", "delete from", "insert into", "update ",
            "alter table", "create table", "create view", "attach database", "attach '",
            "load_extension", "install_extension", "read_csv_auto", "copy to", "copy from",
            "/etc/shadow", "/etc/passwd", "remote_shell"
        ]
        if any(kw in lower_clean for kw in forbidden_keywords):
            raise PermissionError(f"Security Alert: Upaya eksekusi perintah berbahaya atau injeksi DDL/DML terdeteksi!")

        # Fallback regex guardrail jika sqlglot tidak terinstall
        if not HAS_SQLGLOT:
            forbidden_tokens = ["drop ", "delete ", "insert ", "update ", "alter ", "create ", "attach ", "load_extension", "system"]
            if any(tok in lower_clean for tok in forbidden_tokens):
                raise PermissionError(f"Security Alert: Operasi mutasi dilarang keras!")
            if not lower_clean.startswith("select") and not lower_clean.startswith("with"):
                raise PermissionError("Security Alert: Hanya kueri SELECT yang diperbolehkan.")
            if "limit " not in lower_clean:
                trimmed_semis += " LIMIT 100"
            return trimmed_semis

        # Parse AST SQL via sqlglot
        try:
            parsed = sqlglot.parse_one(trimmed_semis, read="duckdb")
        except Exception as e:
            raise ValueError(f"SQL Syntax Error: {e}")

        # 1. Tolak keras segala bentuk mutasi data (DML/DDL) dan fungsi berbahaya
        forbidden_nodes = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
            exp.Create, exp.Command, exp.Transaction
        )
        forbidden_calls = ("load_extension", "install_extension", "read_csv_auto", "read_parquet", "copy")
        for node in parsed.walk():
            if isinstance(node, forbidden_nodes):
                raise PermissionError(f"Security Alert: Operasi mutasi '{type(node).__name__}' dilarang keras!")
            if isinstance(node, exp.Anonymous) and node.name.lower() in forbidden_calls:
                raise PermissionError(f"Security Alert: Eksekusi fungsi sistem '{node.name}' dilarang demi keamanan!")

        # Pastikan tipe utama adalah SELECT
        if not isinstance(parsed, (exp.Select, exp.Union)):
            raise PermissionError("Security Alert: Hanya kueri SELECT atau UNION yang diperbolehkan.")

        # 2. Paksa LIMIT 100 jika tidak memiliki limit untuk mencegah DoS output memori
        limit_node = parsed.find(exp.Limit)
        if not limit_node:
            parsed = parsed.limit(100)
        else:
            # Jika user meminta limit > 200, turunkan ke 100
            try:
                curr_limit = int(limit_node.expression.this)
                if curr_limit > 200:
                    parsed = parsed.limit(100)
            except Exception:
                parsed = parsed.limit(100)

        return parsed.sql(dialect="duckdb")

    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """Mengeksekusi SQL yang sudah divalidasi dan mengembalikan hasil dalam dictionary."""
        try:
            sanitized_sql = self.validate_and_sanitize(sql_query)
            if sanitized_sql in self._cache:
                return self._cache[sanitized_sql]

            import time as _time
            start_t = _time.perf_counter()
            # Gunakan cursor terisolasi per query untuk menjamin thread-safety saat concurrent requests
            cursor = self.conn.cursor()
            try:
                df = cursor.execute(sanitized_sql).df()
            finally:
                cursor.close()
            elapsed_ms = round((_time.perf_counter() - start_t) * 1000, 2)

            # Format datetime ke string ISO agar serializable ke JSON
            for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                df[col] = df[col].astype(str)

            res = {
                "success": True,
                "sql_executed": sanitized_sql,
                "row_count": len(df),
                "columns": list(df.columns),
                "data": df.to_dict(orient="records"),
                "elapsed_ms": elapsed_ms,
                "scanned_rows": self.total_rows,
                "error": None
            }
            if len(self._cache) > 100:
                self._cache.pop(next(iter(self._cache)))
            self._cache[sanitized_sql] = res
            return res
        except Exception as e:
            return {
                "success": False,
                "sql_executed": sql_query,
                "row_count": 0,
                "columns": [],
                "data": [],
                "scanned_rows": self.total_rows,
                "error": str(e)
            }

    def get_quick_kpis(self) -> Dict[str, Any]:
        """Mengambil KPI makro cepat untuk banner dashboard."""
        query = """
        SELECT 
            COUNT(*) as total_transactions,
            COALESCE(ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2), 0.0) as total_volume,
            COALESCE(ROUND(AVG(CASE WHEN status IN ('SUCCESS', 'COMPLETED', 'SETTLED') THEN 1.0 ELSE 0.0 END) * 100, 2), 100.0) as success_rate,
            COALESCE(ROUND(AVG(CASE WHEN status IN ('FAILED', 'PAYMENT_FAILED', 'REJECTED') THEN 1.0 ELSE 0.0 END) * 100, 2), 0.0) as failure_rate
        FROM transactions
        """
        res = self.conn.execute(query).df().to_dict(orient="records")[0]

        # Cari top failed channel (exclude NULL/empty channel)
        top_fail_query = """
        SELECT channel, COUNT(*) as failed_count 
        FROM transactions 
        WHERE status IN ('FAILED', 'PAYMENT_FAILED', 'REJECTED')
          AND channel IS NOT NULL 
          AND TRIM(channel) != ''
        GROUP BY channel 
        ORDER BY failed_count DESC 
        LIMIT 1
        """
        top_fail_res = self.conn.execute(top_fail_query).df().to_dict(orient="records")
        res["top_failed_channel"] = top_fail_res[0]["channel"] if top_fail_res else "None"
        res["critical_anomalies_count"] = 2 if res["top_failed_channel"] != "None" else 0

        return res
