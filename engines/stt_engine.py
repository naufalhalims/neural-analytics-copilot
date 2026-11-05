"""
engines/stt_engine.py
Modul Dedicated Transkripsi Suara (Speech-to-Text) menggunakan Gemini Flash Audio via 9router/OpenAI-compatible Audio API.
"""

import time
import base64
import httpx
from typing import Dict, Any


async def transcribe_audio_stream(
    audio_bytes: bytes,
    filename: str,
    router_url: str,
    router_model: str,
    router_key: str
) -> Dict[str, Any]:
    """Mentranskripsikan audio rekaman pengguna secara presisi dengan lexicon perbankan dan fintech."""
    if not audio_bytes:
        raise ValueError("File audio kosong")

    ext = filename.split(".")[-1].lower() if filename and "." in filename else "webm"
    if ext in ["weba", "webm"]:
        format_type = "webm"
    elif ext in ["ogg", "oga"]:
        format_type = "ogg"
    elif ext in ["wav"]:
        format_type = "wav"
    elif ext in ["mp3"]:
        format_type = "mp3"
    elif ext in ["m4a", "mp4"]:
        format_type = "mp4"
    else:
        format_type = "webm"

    b64_audio = base64.b64encode(audio_bytes).decode("ascii")

    stt_prompt = (
        "Transkripsikan rekaman suara percakapan ini ke dalam teks secara presisi (Bahasa Indonesia atau English). "
        "Penting: Pertahankan keakuratan istilah pembayaran, nama kanal, dan metrik sistem perbankan: "
        "VA BCA, Mandiri, BRI, BNI, GoPay, OVO, QRIS, Indomaret, Alfamart, failure rate, GMV, settlement, gantung, "
        "refund, timeout, ERR_GATEWAY_TIMEOUT, ERR_SYSTEM_MALFUNCTION, Z-score, postmortem, SOP, DuckDB, Parquet, Qdrant. "
        "HANYA hasilkan kalimat teks transkripsi murni tanpa tanda petik, tanpa kalimat pembuka/penjelas, dan tanpa komentar percakapan."
    )

    payload = {
        "model": router_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": stt_prompt},
                {"type": "input_audio", "input_audio": {"data": b64_audio, "format": format_type}}
            ]
        }],
        "stream": False
    }

    t0 = time.time()
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(
            router_url,
            json=payload,
            headers={"Authorization": f"Bearer {router_key}", "Content-Type": "application/json"}
        )

    if resp.status_code != 200:
        raise RuntimeError(f"STT Upstream error {resp.status_code}: {resp.text[:120]}")

    data = resp.json()
    transcribed_text = data["choices"][0]["message"]["content"].strip()
    latency_ms = round((time.time() - t0) * 1000)

    return {
        "text": transcribed_text,
        "latency_ms": latency_ms,
        "model": f"{router_model} (Gemini Flash Audio STT)"
    }
