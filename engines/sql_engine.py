"""SQL Execution Engine dengan AST-level Security Guardrail via SQLGlot.
Hanya mengizinkan query SELECT, menolak mutasi DDL/DML, dan membatasi LIMIT demi keamanan memori.
"""

import duckdb
import sqlglot
from sqlglot import exp
from typing import Dict, Any, List

class SQLEngine:
    def __init__(self, parquet_path: str = "data/transactions_100k.parquet"):
        self.parquet_path = parquet_path
        # Buat koneksi in-memory DuckDB
        self.conn = duckdb.connect(":memory:")
        # Registrasikan file parquet sebagai view 'transactions'
        self.conn.execute(f"CREATE VIEW transactions AS SELECT * FROM read_parquet('{self.parquet_path}')")
        
    def validate_and_sanitize(self, raw_sql: str) -> str:
        """Memeriksa integritas keamanan kueri SQL menggunakan Abstract Syntax Tree (AST)."""
        clean_sql = raw_sql.strip().rstrip(";")
        
        # Parse AST SQL
        try:
            parsed = sqlglot.parse_one(clean_sql, read="duckdb")
        except Exception as e:
            raise ValueError(f"SQL Syntax Error: {e}")
            
        # 1. Tolak keras segala bentuk mutasi data (DML/DDL)
        forbidden_nodes = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
            exp.Create, exp.Command, exp.Transaction
        )
        for node in parsed.walk():
            if isinstance(node, forbidden_nodes):
                raise PermissionError(f"Security Alert: Operasi mutasi '{type(node).__name__}' dilarang keras!")
                
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
            df = self.conn.execute(sanitized_sql).df()
            
            # Format datetime ke string ISO agar serializable ke JSON
            for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                df[col] = df[col].astype(str)
                
            return {
                "success": True,
                "sql_executed": sanitized_sql,
                "row_count": len(df),
                "columns": list(df.columns),
                "data": df.to_dict(orient="records"),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "sql_executed": sql_query,
                "row_count": 0,
                "columns": [],
                "data": [],
                "error": str(e)
            }
            
    def get_quick_kpis(self) -> Dict[str, Any]:
        """Mengambil KPI makro cepat untuk banner dashboard."""
        query = """
        SELECT 
            COUNT(*) as total_transactions,
            ROUND(SUM(amount), 2) as total_volume,
            ROUND(AVG(CASE WHEN status = 'SUCCESS' THEN 1.0 ELSE 0.0 END) * 100, 2) as success_rate,
            ROUND(AVG(CASE WHEN status = 'FAILED' THEN 1.0 ELSE 0.0 END) * 100, 2) as failure_rate
        FROM transactions
        """
        res = self.conn.execute(query).df().to_dict(orient="records")[0]
        
        # Cari top failed channel
        top_fail_query = """
        SELECT channel, COUNT(*) as failed_count 
        FROM transactions 
        WHERE status = 'FAILED' 
        GROUP BY channel 
        ORDER BY failed_count DESC 
        LIMIT 1
        """
        top_fail_res = self.conn.execute(top_fail_query).df().to_dict(orient="records")
        res["top_failed_channel"] = top_fail_res[0]["channel"] if top_fail_res else "None"
        
        return res
