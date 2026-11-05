#!/usr/bin/env python3
"""
scripts/test_pdf_export_and_citation_modal.py
Menguji endpoint /api/export-pdf dan struktur payload citations untuk modal preview
"""

import httpx

API_CHAT = "http://127.0.0.1:8508/api/chat"
API_PDF = "http://127.0.0.1:8508/api/export-pdf"

def test_full_loop():
    print("=" * 80)
    print("🧪 PENGUJIAN QA LOOP: FITUR EXECUTIVE PDF & CITATION MODAL")
    print("=" * 80)

    client = httpx.Client(timeout=35.0)

    # 1. Jalankan Chat Query Investigasi
    q = "Bagaimana akar masalah lonjakan kegagalan di VA BCA tanggal 12 September dan apa rujukan dokumennya?"
    print(f"▶ 1. Menguji Kueri Chat: \"{q}\"")
    res_chat = client.post(API_CHAT, json={"message": q, "history": []})
    assert res_chat.status_code == 200, f"Chat failed: {res_chat.text}"
    chat_data = res_chat.json()
    print("  ✅ Chat Status 200 OK")
    
    # 2. Verifikasi Data Citation Modal Preview
    cits = chat_data.get("citations", [])
    print(f"  ✅ Citations Diterima: {len(cits)} buah")
    assert len(cits) > 0, "Citations kosong!"
    for i, c in enumerate(cits, 1):
        print(f"    - Cit {i}: {c.get('title')} | Bab: {c.get('section')} | Score: {c.get('score')} | Panjang Teks: {len(c.get('content', ''))} char")
        assert "content" in c and len(c["content"]) > 10, "Field content untuk modal preview tidak ada!"

    # 3. Uji Endpoint Export PDF
    print("\n▶ 2. Menguji Endpoint /api/export-pdf")
    chat_data["query"] = q
    res_pdf = client.post(API_PDF, json=chat_data)
    assert res_pdf.status_code == 200, f"PDF export failed: {res_pdf.text}"
    assert res_pdf.headers.get("content-type") == "application/pdf", "Content-Type bukan PDF!"
    pdf_bytes = len(res_pdf.content)
    print(f"  ✅ PDF Berhasil Digenerate: {pdf_bytes:,} bytes")
    assert pdf_bytes > 2000, "Ukuran file PDF terlalu kecil!"

    print("\n" + "=" * 80)
    print("🎉 SELURUH PENGUJIAN QA LOOP SELESAI & VALID (100% PASS)")
    print("=" * 80)

if __name__ == "__main__":
    test_full_loop()
