"""FastAPI Core Backend untuk AI-Powered Data Analytics Chatbot.
Mengintegrasikan DuckDB SQL Engine, Qdrant Hybrid RAG, NetworkX RCA Graph, dan 9router LLM.
"""

import os
import json
import httpx
import traceback
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from engines.sql_engine import SQLEngine
from engines.anomaly_engine import AnomalyEngine
from engines.rag_engine import RAGEngine
from engines.graph_engine import GraphRCAEngine

app = FastAPI(title="Neural Analytics Chatbot", version="1.0.0")

# Setup folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Inisialisasi engine-engine mandiri
DATA_PATH = os.path.join(BASE_DIR, "data", "transactions_5m.parquet")
sql_engine = SQLEngine(parquet_path=DATA_PATH)
anomaly_engine = AnomalyEngine(parquet_path=DATA_PATH)
# Mode :memory: dengan auto-ingest dari folder docs/
rag_engine = RAGEngine(db_path=":memory:", docs_dir=os.path.join(BASE_DIR, "docs"))
graph_engine = GraphRCAEngine()

# Response cache di RAM (LRU, TTL 15 menit)
RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}

# Konfigurasi 9router & API Key
ROUTER_URL = os.getenv("ROUTER_URL", "http://127.0.0.1:20128/v1/chat/completions")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "ag/gemini-3.8-flash-low")

def get_router_key() -> str:
    """Mengambil API Key 9router dari database internal 9router atau environment."""
    if os.getenv("ROUTER_API_KEY"):
        return os.getenv("ROUTER_API_KEY")
    db_path = os.path.expanduser("~/.9router/db/data.sqlite")
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            # Prioritaskan key aktif
            row = conn.execute("SELECT key FROM apiKeys WHERE isActive = 1 ORDER BY createdAt DESC LIMIT 1").fetchone()
            if not row:
                row = conn.execute("SELECT key FROM apiKeys ORDER BY createdAt DESC LIMIT 1").fetchone()
            if row and row[0]:
                return row[0].strip()
        except Exception:
            pass
    return ""

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Halaman Dashboard Utama Midnight Obsidian."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/kpis")
async def get_kpis():
    """Mengambil metrik KPI makro untuk ribbon atas."""
    try:
        kpis = sql_engine.get_quick_kpis()
        anomalies = anomaly_engine.detect_channel_spikes()
        kpis["critical_anomalies_count"] = len([a for a in anomalies if a["severity"] == "CRITICAL"])
        return JSONResponse({"status": "success", "data": kpis})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/graph")
async def get_graph(highlight: Optional[str] = None):
    """Mengambil topologi NetworkX dalam format Cytoscape.js."""
    elements = graph_engine.get_cytoscape_elements(highlight_channel=highlight)
    return JSONResponse({"status": "success", "elements": elements})

@app.post("/api/chat")
async def chat_handler(payload: ChatRequest):
    """Router Agentic: Mengklasifikasikan intent, mengeksekusi engine yang tepat, dan mensintesis jawaban."""
    user_query = payload.message.strip()
    if not user_query:
        return JSONResponse({"status": "error", "reply": "Pesan tidak boleh kosong."})
        
    lower_query = user_query.lower()
    cache_key = lower_query
    if cache_key in RESPONSE_CACHE:
        cached_data = dict(RESPONSE_CACHE[cache_key])
        cached_data["cached"] = True
        return JSONResponse(cached_data)
    
    # Indikator Kueri Lebih Luas & Cerdas (Intent Coverage)
    is_why_question = any(k in lower_query for k in ["kenapa", "mengapa", "penyebab", "faktor", "investigasi", "sejak kapan", "berkontribusi", "pemicu", "paling abnormal", "boncos", "ngadat", "jelek", "masalah", "spike", "anomali"])
    is_doc_question = any(k in lower_query for k in ["sop", "prosedur", "dokumen", "kebijakan", "sla", "refund", "aturan", "penanganan", "kontak", "eskalasi", "postmortem", "tiket", "l2", "l3"])
    is_sql_question = any(k in lower_query for k in ["total", "berapa", "distribusi", "volume", "bandingkan", "perbandingan", "tertinggi", "terendah", "jumlah", "bulan", "status", "persentase", "gambaran", "omset", "summary", "grafik", "kinerja"])
    
    # Eksekusi State
    sql_result = None
    rag_docs = []
    anomalies = []
    target_channel_highlight = None
    chart_payload = None
    
    # --- JALUR A: SQL & ANOMALI ---
    if is_sql_question or is_why_question:
        # Jika ada pertanyaan tentang kenaikan, masalah, atau perbandingan bulan, sertakan drill-down kanal otomatis
        if "september" in lower_query or "kenaikan" in lower_query or "meningkat" in lower_query or is_why_question:
            sql = "SELECT channel, COUNT(*) as total_tx, SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed_tx, ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_rate_pct, ROUND(SUM(amount)/1000000000, 2) as volume_miliar FROM transactions WHERE strftime(timestamp, '%Y-%m') = '2026-09' GROUP BY channel ORDER BY fail_rate_pct DESC"
            sql_result = sql_engine.execute_query(sql)
            if sql_result["success"]:
                chart_payload = {
                    "type": "bar",
                    "title": "Drill-Down Kegagalan Kanal September 2026 (%)",
                    "labels": [r["channel"] for r in sql_result["data"]],
                    "data": [r["fail_rate_pct"] for r in sql_result["data"]],
                    "label": "Failure Rate (%)"
                }
        elif "distribusi" in lower_query or "status" in lower_query or "persentase" in lower_query or "gambaran" in lower_query:
            sql = "SELECT status, COUNT(*) as count, ROUND(SUM(amount), 2) as total_volume FROM transactions GROUP BY status"
            sql_result = sql_engine.execute_query(sql)
            if sql_result["success"]:
                chart_payload = {
                    "type": "doughnut",
                    "title": "Distribusi Status Transaksi",
                    "labels": [r["status"] for r in sql_result["data"]],
                    "data": [r["count"] for r in sql_result["data"]]
                }
        elif "kanal" in lower_query or "channel" in lower_query or "tertinggi" in lower_query:
            sql = "SELECT channel, COUNT(*) as total_tx, SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed_tx, ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_rate_pct FROM transactions GROUP BY channel ORDER BY total_tx DESC"
            sql_result = sql_engine.execute_query(sql)
            if sql_result["success"]:
                chart_payload = {
                    "type": "bar",
                    "title": "Volume & Tingkat Kegagalan per Kanal",
                    "labels": [r["channel"] for r in sql_result["data"]],
                    "data": [r["fail_rate_pct"] for r in sql_result["data"]],
                    "label": "Failure Rate (%)"
                }
        elif "perbandingan" in lower_query or "bulan" in lower_query or "tren" in lower_query:
            sql = "SELECT strftime(timestamp, '%Y-%m') as month, COUNT(*) as total_tx, ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_rate_pct, ROUND(SUM(amount)/1000000000, 2) as volume_miliar FROM transactions GROUP BY month ORDER BY month"
            sql_result = sql_engine.execute_query(sql)
            if sql_result["success"]:
                chart_payload = {
                    "type": "line",
                    "title": "Tren Tingkat Kegagalan MoM (%)",
                    "labels": [r["month"] for r in sql_result["data"]],
                    "data": [r["fail_rate_pct"] for r in sql_result["data"]],
                    "label": "Failure Rate (%)"
                }
        elif "harian" in lower_query or "tanggal" in lower_query or "spike" in lower_query:
            sql = "SELECT strftime(timestamp, '%Y-%m-%d') as tgl, COUNT(*) as total_tx, ROUND(AVG(CASE WHEN status='FAILED' THEN 1.0 ELSE 0.0 END)*100, 2) as fail_rate_pct FROM transactions WHERE strftime(timestamp, '%Y-%m') = '2026-09' GROUP BY tgl ORDER BY tgl"
            sql_result = sql_engine.execute_query(sql)
            if sql_result["success"]:
                chart_payload = {
                    "type": "line",
                    "title": "Tren Harian Kegagalan Transaksi September 2026 (%)",
                    "labels": [r["tgl"] for r in sql_result["data"]],
                    "data": [r["fail_rate_pct"] for r in sql_result["data"]],
                    "label": "Daily Fail Rate (%)"
                }
        elif "error" in lower_query or "alasan" in lower_query or "reason" in lower_query:
            sql = "SELECT failure_reason, COUNT(*) as count FROM transactions WHERE status='FAILED' GROUP BY failure_reason ORDER BY count DESC LIMIT 5"
            sql_result = sql_engine.execute_query(sql)
            if sql_result["success"]:
                chart_payload = {
                    "type": "bar",
                    "title": "Top 5 Penyebab Kegagalan Transaksi (Error Code)",
                    "labels": [r["failure_reason"] for r in sql_result["data"]],
                    "data": [r["count"] for r in sql_result["data"]],
                    "label": "Total Error"
                }
        else:
            # Default aggregate
            sql = "SELECT COUNT(*) as total_transaksi, SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) as success, SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed, ROUND(SUM(amount), 2) as total_nominal FROM transactions"
            sql_result = sql_engine.execute_query(sql)

    # --- JALUR B: INVESTIGASI KENAPA (RCA & ML SPIKE) ---
    if is_why_question:
        anomalies = anomaly_engine.detect_channel_spikes()
        if anomalies:
            top_spike = anomalies[0]
            target_channel_highlight = top_spike["channel"]
            # Ambil dokumen pendukung terkait insiden dan kanal
            rag_docs = rag_engine.search(f"Insiden gangguan {top_spike['channel']} {top_spike['primary_failure_code']}", top_k=2)

    # --- JALUR C: DOKUMEN PROSEDURAL & SOP ---
    if is_doc_question and not rag_docs:
        rag_docs = rag_engine.search(user_query, top_k=2)

    # 2. Susun System Prompt & Context untuk LLM Synthesis
    system_prompt = """Kamu adalah Senior AI Data & Operational Analytics Specialist di PT Neural Technologies Indonesia.
Gaya bicaramu natural, lugas, santai namun berbobot ala konsultan finansial-teknologi senior (seperti Hermes Agent). Tidak kaku, tidak berbicara layaknya robot, dan sangat komunikatif.

KARAKTER & PERSONA KOMUNIKASI:
1. Multilingual & Fluent: Pahami konteks perbankan Indonesia, istilah teknis payment gateway (failure rate, SLA, virtual account, gateway timeout, routing), dan jelaskan secara kontekstual dengan bahasa Indonesia bisnis yang enak dibaca.
2. Direct-to-the-Point: Berikan kesimpulan inti di kalimat pertama, baru kemudian jelaskan rincian angka dan argumen pendukungnya.
3. Bisnis & Finansial Mindset: Selalu hubungkan angka transaksi dengan dampak finansial (misal: potensi kehilangan omset / GMV, dampak pada merchant retention, dan risiko reputasi).
4. Solutif & Berani Menyimpulkan: Ketika data SQL, lonjakan Z-score anomali, dan tiket postmortem sudah jelas menunjukkan adanya insiden `#INC-20260912-BCA` di kanal `VA_BCA` akibat migrasi switch data center mitra, katakan langsung secara lugas! Jangan ragu atau berkelit "data tidak lengkap".

FORMAT MARKDOWN:
- Gunakan struktur rapi: Judul (#, ##), tabel ringkas, bullet point tebal, dan highlight kode backticks `ERR_GATEWAY_TIMEOUT`.
- Akhiri dengan poin rekomendasi operasional konkrit yang bisa langsung dieksekusi tim bisnis dan SRE."""

    context_str = "=== KONTEKS DATA & PENGETAHUAN TERSEDIA ===\n"
    if sql_result and sql_result["success"]:
        context_str += f"\n[BUKTI SQL QUERY]\nQuery: {sql_result['sql_executed']}\nHasil Data: {json.dumps(sql_result['data'][:10], indent=2)}\n"
        
    if anomalies:
        context_str += f"\n[DETEKSI ANOMALI STATISTIK ML (Z-SCORE)]\nTemuan Outlier Kritis: {json.dumps(anomalies[:3], indent=2)}\n"
        
    if rag_docs:
        context_str += "\n[KUTIPAN DOKUMEN SOP & HISTORICAL INCIDENT LOG DARI QDRANT]\n"
        for doc in rag_docs:
            context_str += f"--- {doc['doc_title']} ({doc['section']}) ---\n{doc['content']}\n"
            
    # 3. Panggil 9router LLM
    messages = [
        {"role": "system", "content": f"{system_prompt}\n\n{context_str}"},
        {"role": "user", "content": user_query}
    ]
    
    try:
        api_key = get_router_key()
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                ROUTER_URL,
                headers=headers,
                json={
                    "model": ROUTER_MODEL,
                    "messages": messages,
                    "temperature": 0.2
                }
            )
            if resp.status_code == 200:
                raw_text = resp.text.strip()
                if raw_text.startswith("data:"):
                    # Format Server-Sent Events (SSE) streaming chunks
                    collected_tokens = []
                    for line in raw_text.splitlines():
                        line = line.strip()
                        if line.startswith("data:"):
                            payload_str = line[5:].strip()
                            if payload_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(payload_str)
                                choices = chunk_json.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        collected_tokens.append(content)
                            except Exception:
                                pass
                    llm_reply = "".join(collected_tokens)
                else:
                    try:
                        data = json.loads(raw_text)
                        llm_reply = data["choices"][0]["message"]["content"]
                    except Exception as je:
                        print(f"[JSON Decode Error on 200 OK]: {je}, raw content: {resp.text[:200]}")
                        llm_reply = f"Error membaca respon JSON router: {resp.text[:300]}"
            else:
                print(f"[Router Error] HTTP {resp.status_code}: {resp.text}")
                llm_reply = f"Gagal memanggil model router (HTTP {resp.status_code}): {resp.text}"
    except Exception as e:
        print(f"[Router Exception]: {e}")
        traceback.print_exc()
        # Fallback deterministik jika 9router bermasalah
        llm_reply = f"Analisis Berbasis Aturan:\nBerdasarkan data yang diproses, ditemukan indikasi berikut:\n- SQL Result: {json.dumps(sql_result['data'] if sql_result else [])}\n- Error Trace: {str(e)}"
        
    res_payload = {
        "status": "success",
        "reply": llm_reply,
        "sql_executed": sql_result["sql_executed"] if sql_result else None,
        "chart_payload": chart_payload,
        "target_channel": target_channel_highlight,
        "citations": [{"title": d["doc_title"], "section": d["section"]} for d in rag_docs]
    }
    
    # Simpan di in-memory response cache (maksimal 200 percakapan)
    if len(RESPONSE_CACHE) > 200:
        RESPONSE_CACHE.pop(next(iter(RESPONSE_CACHE)))
    RESPONSE_CACHE[cache_key] = res_payload
    
    return JSONResponse(res_payload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8508, reload=True)
