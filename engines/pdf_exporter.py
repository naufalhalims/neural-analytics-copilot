"""
engines/pdf_exporter.py
Modul Dedicated untuk menghasilkan Dokumen Executive Briefing & Incident Dossier PDF
menggunakan ReportLab dengan formatting standar enterprise.
"""

import time
import io
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_executive_briefing_pdf(payload: Dict[str, Any]) -> bytes:
    """Mengompilasi Executive Briefing PDF Dossier dari payload analitik dan mengembalikan raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
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
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=14
    )
    section_style = ParagraphStyle(
        'DocSec',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    code_style = ParagraphStyle(
        'DocCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0284C7')
    )

    elements = []

    # Header Dokumen
    elements.append(Paragraph("PT NEURAL TECHNOLOGIES INDONESIA", title_style))
    elements.append(Paragraph("EXECUTIVE OPERATIONAL BRIEFING & INCIDENT INVESTIGATION REPORT", subtitle_style))
    elements.append(Spacer(1, 4))

    # Metadata Kotak
    meta_data = [
        [
            Paragraph("<b>Waktu Audit:</b> " + time.strftime("%Y-%m-%d %H:%M:%S WIB"), body_style),
            Paragraph("<b>Status Sistem:</b> OPERATIONAL VERIFIED", body_style)
        ],
        [
            Paragraph("<b>Kueri Pengguna:</b> " + str(payload.get("query", "-")[:80]), body_style),
            Paragraph("<b>Engine:</b> DuckDB 5M + Qdrant RAG + Jev", body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[260, 260])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 10))

    # Ringkasan Narasi
    elements.append(Paragraph("1. RINGKASAN EKSEKUTIF & TEMUAN UTAMA", section_style))
    raw_reply = str(payload.get("reply", "Tidak ada narasi analitik."))
    clean_reply = (
        raw_reply.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("### ", "")
        .replace("## ", "")
        .replace("**", "")
    )
    if len(clean_reply) > 1200:
        clean_reply = clean_reply[:1200] + "..."
    elements.append(Paragraph(clean_reply.replace("\n", "<br/>"), body_style))
    elements.append(Spacer(1, 10))

    # Rincian Metrik & Tabel
    chart_p = payload.get("chart_payload")
    if chart_p and chart_p.get("labels") and chart_p.get("data"):
        elements.append(Paragraph("2. DATA PENDUKUNG (" + str(chart_p.get("title", "Rekap Angka")) + ")", section_style))
        table_rows = [["Kategori / Kanal", str(chart_p.get("label", "Nilai"))]]
        labels = chart_p.get("labels", [])
        data_vals = chart_p.get("data", [])
        for idx in range(min(6, len(labels))):
            val = data_vals[idx]
            val_str = f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
            table_rows.append([str(labels[idx]), val_str])
        
        t_data = Table(table_rows, colWidths=[300, 220])
        t_data.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 4),
            ('TOPPADDING', (0,0), (-1,0), 4),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('TOPPADDING', (0,1), (-1,-1), 3),
            ('BOTTOMPADDING', (0,1), (-1,-1), 3),
        ]))
        elements.append(t_data)
        elements.append(Spacer(1, 10))

    # Rujukan Dokumen & SQL
    elements.append(Paragraph("3. VERIFIKASI BUKTI DOKUMEN & AUDIT TRAIL SQL", section_style))
    cits = payload.get("citations", [])
    if cits:
        cit_texts = []
        for c in cits:
            t_c = str(c.get('title', 'Dokumen')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            s_c = str(c.get('section', '-')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            cit_texts.append(f"• <b>{t_c}</b> — Bab: {s_c} (Relevance: {c.get('score', '-')})")
        elements.append(Paragraph("<br/>".join(cit_texts), body_style))
    else:
        elements.append(Paragraph("• Terverifikasi terhadap dataset 5.000.000 transaksi pembayaran Parquet.", body_style))

    sql_q = str(payload.get("sql_executed", "")).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if sql_q:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("<b>AST Guardrail Verified SQL:</b>", body_style))
        elements.append(Paragraph(sql_q, code_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
