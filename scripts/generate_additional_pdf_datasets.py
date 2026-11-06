#!/usr/bin/env python3
"""
scripts/generate_additional_pdf_datasets.py
Membuat 2 dataset PDF baru untuk Dedicated Vault:
1. Non-Scan PDF Digital Native: SOP Keamanan Siber, Disaster Recovery & Failover API Gateway.
2. Scanned-Style PDF (dengan embedded OCR layer simulasi dokumen scan audit fisik):
   Surat Keputusan Audit Forensik & Verifikasi Rekonsiliasi Switcher QRIS Nasional.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfgen import canvas

def create_non_scan_digital_pdf(output_path: str):
    """Membuat PDF Non-Scan (Digital Native) modern dengan teks tajam, metadata, dan tabel."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#0f172a'),
        alignment=0
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor('#334155')
    )

    story = []
    story.append(Paragraph("SOP-SEC-2026-V4: STANDAR OPERASIONAL KEAMANAN SIBER & FAILOVER GATEWAY", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Dokumen Resmi Divisi Security Operations Center (SOC) & Infrastructure Reliability &bull; Klasifikasi: Internal Enterprise", meta_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("1. Ruang Lingkup dan Kebijakan Otomatisasi Failover API", h2_style))
    story.append(Paragraph(
        "Standar ini menetapkan protokol mitigasi apabila terjadi penurunan availability API Gateway perbankan di bawah threshold 98.5% dalam jendela observasi 5 menit berturut-turut. "
        "Sistem monitoring otomatis (Sentinel Hub) akan memicu auto-rerouting traffic pembayaran ke secondary switching provider (Backup Switcher B) untuk menghindari penumpukan antrean transaksi pending.",
        body_style
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Matriks Rerouting & Batas Ambang Eskalasi", h2_style))
    table_data = [
        ["Kanal Transaksi", "Threshold Kegagalan", "Aksi Otomatis", "SLA Resolusi Target"],
        ["Virtual Account BCA", "Failure Rate > 12.0%", "Reroute ke Backup Gateway Mandiri", "5 Menit"],
        ["QRIS Cross-Border", "Response Time > 8.000 ms", "Circuit Breaker Active (Auto Decline)", "3 Menit"],
        ["E-Wallet Topup", "HTTP 504 Timeout > 50 trx/m", "Drain Connection Pool & Restart Worker", "10 Menit"],
        ["Kartu Debit Online", "3DS Verification Timeout", "Bypass ke Second-Tier Clearing", "15 Menit"]
    ]
    t = Table(table_data, colWidths=[120, 120, 160, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Prosedur Disaster Recovery & Pemulihan Database (RPO/RTO)", h2_style))
    story.append(Paragraph(
        "RPO (Recovery Point Objective) ditetapkan maksimum 0 detik untuk transaksi berstatus PAID dengan replikasi synchronous Raft consensus. "
        "RTO (Recovery Time Objective) untuk sistem recovery kluster transaksi adalah maksimal 120 detik sejak kegagalan master database terkonfirmasi.",
        body_style
    ))
    
    doc.build(story)
    print(f"[+] Berhasil membuat PDF Non-Scan: {output_path}")

def create_scanned_style_pdf(output_path: str):
    """
    Membuat PDF bergaya hasil SCAN dokumen fisik otentik:
    - Memiliki background stempel/watermark dan header nomor berkas surat resmi
    - Diberi teks terstruktur (embedded OCR text layer) sehingga mesin ekstraksi dokumen PyMuPDF
      dapat memverifikasi teks audit fisik dengan akurasi 100%.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # Background tint simulasi kertas scanner (warm light cream)
    c.setFillColor(colors.HexColor('#fafaf9'))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Watermark stempel 'AUDIT RESMI TERVERIFIKASI'
    c.saveState()
    c.setFont('Helvetica-Bold', 36)
    c.setFillColor(colors.HexColor('#fecdd3')) # Soft red
    c.rotate(35)
    c.drawString(200, 150, "HASIL AUDIT SCAN - RAHASIA")
    c.restoreState()

    # Border frame garis ganda tipis khas berkas scanner resmi
    c.setStrokeColor(colors.HexColor('#64748b'))
    c.setLineWidth(1)
    c.rect(25, 25, width - 50, height - 50, fill=False, stroke=True)
    c.setLineWidth(0.5)
    c.rect(28, 28, width - 56, height - 56, fill=False, stroke=True)

    # Header Surat
    c.setFont('Helvetica-Bold', 13)
    c.setFillColor(colors.HexColor('#0f172a'))
    c.drawCentredString(width / 2.0, height - 55, "LEMBAR AUDIT FORENSIK SWITCHER QRIS NASIONAL")
    
    c.setFont('Helvetica-Oblique', 9)
    c.setFillColor(colors.HexColor('#475569'))
    c.drawCentredString(width / 2.0, height - 70, "Nomor Berkas: BERKAS-SCAN/QRIS-SETTLE/2026-X1 &bull; Klasifikasi: DOKUMEN AUDIT FISIK")

    # Garis pemisah
    c.setStrokeColor(colors.HexColor('#94a3b8'))
    c.setLineWidth(1)
    c.line(40, height - 80, width - 40, height - 80)

    # Isi Teks OCR Layer
    y = height - 105
    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(colors.HexColor('#1e293b'))
    c.drawString(45, y, "1. LAPORAN VERIFIKASI FISIK SELISIH REKONSILIASI QRIS & SWITCHING")
    
    y -= 16
    c.setFont('Helvetica', 8.5)
    c.setFillColor(colors.HexColor('#334155'))
    lines1 = [
        "Tanggal Audit Lapangan: 28 September 2026 &bull; Tim Auditor: IT Security & Financial Governance Forensics",
        "Objek Audit: Jalur integrasi Settlement QRIS Merchant Aggregator dan Terminal POS Nasional.",
        "Temuan Lapangan: Ditemukan rekonsiliasi gantung sebanyak 4.312 transaksi QRIS pada periode peak hour 19:00 - 21:00 WIB.",
        "Akar Masalah (RCA): Lonjakan waktu tanggap (response time) dari switching partner melampaui 12.000 ms,",
        "menyebabkan timeout di sisi POS kasir meskipun saldo nasabah telah sukses terdebet (Status: DEBET_OK_PENDING_MERCHANT)."
    ]
    for line in lines1:
        c.drawString(45, y, line)
        y -= 13

    y -= 10
    c.setFont('Helvetica-Bold', 10)
    c.drawString(45, y, "2. KETENTUAN PENYELESAIAN DISPUTE & GANTI RUGI MERCHANT")
    y -= 16
    c.setFont('Helvetica', 8.5)
    lines2 = [
        "a. Rekonsiliasi Otomatis H+1: Semua transaksi gantung QRIS wajib diselesaikan melalui batch auto-settlement pada pukul 03:00 WIB.",
        "b. Tindakan Korektif: Merchant yang mengalami double-debit harus menerima pengembalian dana (refund) maksimal dalam 1x24 jam kerja.",
        "c. SLA Denda Keterlambatan: Mitra switching yang melebihi SLA rekonsiliasi dikenakan penalti kompensasi 0.15% per transaksi gantung.",
        "d. Kontak Darurat Hotline: Eskalasi L3 wajib menghubungi National Switcher Operations Desk pada IP VPN dedicated."
    ]
    for line in lines2:
        c.drawString(45, y, line)
        y -= 13

    y -= 10
    c.setFont('Helvetica-Bold', 10)
    c.drawString(45, y, "3. PENGESAHAN DOKUMEN & VERIFIKASI TANDA TANGAN DIGITAL AUDITOR")
    y -= 16
    c.setFont('Helvetica', 8.5)
    lines3 = [
        "Dokumen ini sah dan telah melalui proses verifikasi stempel basah serta pemindaian resolusi tinggi 300 DPI.",
        "Hash Integritas Berkas (SHA-256): 9f8a3c2e1b4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f",
        "Status Validasi Auditor Utama: APPROVED & CLOSED DENGAN REKOMENDASI PERBAIKAN INFRASTRUKTUR."
    ]
    for line in lines3:
        c.drawString(45, y, line)
        y -= 13

    # Stempel Kotak Verifikasi di Bawah
    c.setStrokeColor(colors.HexColor('#059669')) # Emerald green
    c.setFillColor(colors.HexColor('#ecfdf5'))
    c.rect(width - 210, 45, 165, 45, fill=True, stroke=True)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#065f46'))
    c.drawString(width - 200, 75, "VERIFIKASI AUDIT FORENSIK")
    c.setFont('Helvetica', 7)
    c.drawString(width - 200, 62, "STATUS: VALID / SESUAI SOP")
    c.drawString(width - 200, 52, "TANGGAL: 30 SEP 2026 - TIM L3")

    c.save()
    print(f"[+] Berhasil membuat Scanned-Style PDF: {output_path}")

if __name__ == "__main__":
    vault_sop = "vault/01_SOP_and_Policies/SOP_Keamanan_Siber_Failover_Gateway_v4.pdf"
    vault_scan = "vault/02_Incident_History/Audit_Forensik_QRIS_Switcher_Scan.pdf"
    create_non_scan_digital_pdf(vault_sop)
    create_scanned_style_pdf(vault_scan)
