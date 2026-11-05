#!/usr/bin/env python3
"""
scripts/generate_scanned_pdf_sample.py
Membuat dokumen PDF sintetis bergaya scan/faktur audit operasional perbankan
dengan resolusi digital dan metadata teks tersemat untuk uji ekstraksi dokumen.
"""

from fpdf import FPDF
import os

def create_scanned_style_pdf():
    os.makedirs("docs", exist_ok=True)
    pdf_path = "docs/Audit_Insiden_Settlement_Bank_Mandiri_Scan.pdf"
    
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title / Header
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(0, 8, "LEMBAR AUDIT REKONSILIASI & INSIDEN SETTLEMENT (BANK MANDIRI)", ln=True, align="C")
    pdf.set_font("Helvetica", style="I", size=10)
    pdf.cell(0, 6, "Nomor Berkas: AUDIT/2026/Q3/MANDIRI-0891 - Sifat: RAHASIA / INTERNAL", ln=True, align="C")
    pdf.ln(5)
    
    # Section 1
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 6, "1. Informasi Umum Audit & Anomali Sistem", ln=True)
    pdf.set_font("Helvetica", size=9)
    info_text = (
        "Tanggal Pelaksanaan Audit: 20 September 2026\n"
        "Entitas Teraudit: Payment Switcher & VA Host Bank Mandiri\n"
        "Tujuan: Menginvestigasi anomali selisih saldo settlement pada periode lonjakan kendala September 2026.\n"
        "Status Validasi: Selesai diuji petik pada 50.000 transaksi acak."
    )
    pdf.multi_cell(0, 5, info_text)
    pdf.ln(4)
    
    # Section 2: Prosedur Resolusi Mandiri
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 6, "2. Prosedur Khusus Resolusi Dispute & Settlement Gantung Mandiri", ln=True)
    pdf.set_font("Helvetica", size=9)
    sop_mandiri = (
        "Ketentuan Rekonsiliasi Saldo Gantung Bank Mandiri:\n"
        "a. Apabila terjadi status PENDING lebih dari 15 menit pada kanal VA_MANDIRI akibat time-out port koneksi host,\n"
        "   tim Settlement Wajib menjalankan kueri inquiry status ganda (Dual-Inquiry API v3) sebelum trigger auto-reversal.\n"
        "b. Jika nasabah telah didebet tetapi mutasi kredit di merchant belum terbentuk, batas SLA settlement manual\n"
        "   maksimal 1x12 jam hari kerja (H+1 Pukul 12:00 WIB).\n"
        "c. Eskalasi level insiden diarahkan langsung ke Service Desk Mandiri Enterprise melalui saluran dedicated hotline."
    )
    pdf.multi_cell(0, 5, sop_mandiri)
    pdf.ln(4)
    
    # Section 3: Ringkasan Temuan
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 6, "3. Catatan Temuan Rekonsiliasi Kuartal 3", ln=True)
    pdf.set_font("Helvetica", size=9)
    audit_findings = (
        "Berdasarkan sampel audit, tingkat kegagalan Mandiri secara umum berada dalam toleransi wajar (3.4% - 3.8%).\n"
        "Tidak ditemukan anomali hardware sistemik di sisi Mandiri, berbeda dengan lonjakan anomali masif pada mitra VA BCA.\n"
        "Rekomendasi auditor: Memperpanjang batas waktu timeout inquiry dari 5.000 ms menjadi 8.000 ms pada jam sibuk (11:00 - 14:00 WIB)."
    )
    pdf.multi_cell(0, 5, audit_findings)
    pdf.ln(6)
    
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.cell(0, 5, "-- Salinan Resmi Tervalidasi oleh Divisi Internal Audit PT Neural Technologies Indonesia --", align="C")
    
    pdf.output(pdf_path)
    print(f"[+] Berhasil membuat PDF audit sintetis: {pdf_path}")

if __name__ == "__main__":
    create_scanned_style_pdf()
