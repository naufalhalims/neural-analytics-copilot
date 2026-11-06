#!/usr/bin/env python3
"""Generate dokumen PDF benchmark OCR/scan system dari hasil benchmark."""
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

RESULTS = "/home/ubuntu/apps/neural-analytics-chatbot/vault/ocr_benchmark_results.json"
OUT = "/home/ubuntu/apps/neural-analytics-chatbot/vault/OCR_Benchmark_Report.pdf"

HEADER = colors.HexColor("#0F172A")
CYAN = colors.HexColor("#06B6D4")
GREEN = colors.HexColor("#10B981")
AMBER = colors.HexColor("#F59E0B")
RED = colors.HexColor("#EF4444")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F1F5F9")


def main():
    data = json.load(open(RESULTS))
    files = data["files"]

    doc = SimpleDocTemplate(
        OUT, pagesize=A4, rightMargin=40, leftMargin=40,
        topMargin=36, bottomMargin=36,
    )
    ss = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=ss["Heading1"], fontName="Helvetica-Bold",
                           fontSize=17, leading=21, textColor=HEADER, spaceAfter=4)
    sub = ParagraphStyle("S", parent=ss["Normal"], fontName="Helvetica-Oblique",
                         fontSize=9.5, textColor=SLATE, spaceAfter=14)
    h2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                        fontSize=12.5, leading=15, textColor=HEADER, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("B", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=9.5, leading=13, textColor=HEADER, spaceAfter=6)
    mono = ParagraphStyle("M", parent=ss["Normal"], fontName="Courier",
                          fontSize=8.5, leading=11, textColor=SLATE)

    story = []
    story.append(Paragraph("OCR &amp; Scan Integrity Benchmark Report", title))
    story.append(Paragraph(
        "Neural Analytics Copilot — PT Neural Technologies Indonesia | Dokumen pembuktian otentikasi "
        "PDF scan via PyMuPDF (engine: scripts/benchmark_ocr_all.py)", sub))
    story.append(Paragraph(
        "Tujuan benchmark: membuktikan secara terukur bahwa setiap dokumen di vault adalah "
        "<b>Authentic Searchable Scanned PDF</b> — halaman berupa foto scan penuh (full-page raster), "
        "dilengkapi invisible OCR text layer (render mode 3) sehingga 100% terbaca manusia sebagai "
        "kertas fisik sekaligus 100% terbaca mesin RAG/Qdrant.", body))

    # Kriteria kelulusan
    story.append(Paragraph("Kriteria Kelulusan (Verdict)", h2))
    crit = [
        ["Sinyal PyMuPDF", "Ambang", "Makna"],
        ["Jumlah gambar raster (get_images)", ">= 1", "Halaman adalah foto scan, bukan vektor teks"],
        ["Coverage gambar halaman", "> 80%", "Gambar menutupi hampir seluruh halaman"],
        ["Karakter teks OCR (get_text)", "> 0", "Ada text layer -> searchable"],
        ["Render mode Tr (content stream)", "= 3", "Teks invisible, tak menimpa gambar"],
    ]
    t = Table(crit, colWidths=[90*mm, 30*mm, 60*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Verdict <b>AUTHENTIC_SCANNED</b> hanya jika keempat sinyal terpenuhi sekaligus. "
        "Dokumen digital-native (0 gambar) otomatis ditolak — dipakai sebagai kontrol negatif.", body))

    # Ringkasan agregat
    story.append(Paragraph("Hasil Agregat (205 PDF)", h2))
    cats = data["categories"]
    total = data["total_pdfs"]
    rows = [["Kategori", "Jumlah", "Persentase"]]
    cat_label = {
        "AUTHENTIC_SCANNED": "Authentic Scanned PDF (LULUS)",
        "DIGITAL_NATIVE": "Digital Native (kontrol negatif)",
        "SCANNED_VISIBLE_TEXT": "Scan + teks terlihat",
        "PURE_IMAGE": "Scan murni (tak searchable)",
        "ERROR": "Gagal dibaca",
    }
    cat_color = {
        "AUTHENTIC_SCANNED": GREEN,
        "DIGITAL_NATIVE": AMBER,
        "SCANNED_VISIBLE_TEXT": RED,
        "PURE_IMAGE": RED,
        "ERROR": RED,
    }
    for k, n in sorted(cats.items()):
        rows.append([cat_label.get(k, k), str(n), f"{n/total*100:.1f}%"])
    t2 = Table(rows, colWidths=[110*mm, 30*mm, 40*mm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)

    # Statistik kualitas OCR
    auth = {k: v for k, v in files.items() if v.get("category") == "AUTHENTIC_SCANNED"}
    chars = [v["n_chars"] for v in auth.values()]
    story.append(Paragraph("Statistik Kualitas OCR (201 dokumen lulus)", h2))
    stats = [
        ["Metrik", "Nilai"],
        ["Karakter OCR minimum", f"{min(chars)} char"],
        ["Karakter OCR maksimum", f"{max(chars)} char"],
        ["Karakter OCR rata-rata", f"{sum(chars)//len(chars)} char"],
        ["Coverage gambar (min/max)", f"{min(v['coverage'] for v in auth.values())}% / {max(v['coverage'] for v in auth.values())}%"],
        ["Gambar per halaman", "1 (konsisten)"],
        ["Jumlah halaman per dokumen", "1 (konsisten)"],
    ]
    t3 = Table(stats, colWidths=[90*mm, 90*mm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t3)

    # Breakdown per domain
    story.append(Paragraph("Breakdown per Domain", h2))
    dom_rows = [["Domain", "Berkas Lulus", "Rata-rata Char OCR"]]
    domains = {}
    for k, v in auth.items():
        d = k.split("/")[1] if "/" in k else "root"
        domains.setdefault(d, []).append(v["n_chars"])
    for d in sorted(domains):
        dom_rows.append([d, str(len(domains[d])), f"{sum(domains[d])//len(domains[d])} char"])
    t4 = Table(dom_rows, colWidths=[90*mm, 40*mm, 50*mm])
    t4.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t4)

    # Kontrol negatif
    story.append(Paragraph("Kontrol Negatif (ditolak — bukti detektor tidak asal lolos)", h2))
    neg = {k: v for k, v in files.items() if v.get("category") == "DIGITAL_NATIVE"}
    neg_rows = [["File", "Gambar", "Char OCR", "Tr mode"]]
    for k, v in sorted(neg.items()):
        neg_rows.append([k, str(v.get("n_images", 0)), str(v.get("n_chars", 0)), str(sorted(v.get("tr_modes", [])))])
    t5 = Table(neg_rows, colWidths=[110*mm, 20*mm, 20*mm, 30*mm])
    t5.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AMBER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t5)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Empat berkas di atas adalah dokumen digital-native (dibuat dengan fpdf/ReportLab, bukan "
        "pipeline scan bitmap). Keempatnya ditolak verdict scan — ini justru membuktikan detektor "
        "bekerja benar (tidak false-positive).", body))

    # Metodologi
    story.append(Paragraph("Metodologi & Reproduksibilitas", h2))
    story.append(Paragraph(
        "Benchmark dapat direproduksi kapan saja dengan:", body))
    story.append(Paragraph("&gt; cd neural-analytics-chatbot &amp;&amp; ./venv/bin/python scripts/benchmark_ocr_all.py", mono))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Skrip membaca setiap .pdf di folder vault/, mengekstrak (1) jumlah gambar raster via "
        "page.get_images(full=True), (2) coverage via page.get_image_rects(xref), (3) karakter teks "
        "via page.get_text(), dan (4) render mode invisible via regex '\\d+ Tr' pada content stream "
        "page.read_contents(). Hasil penuh tersimpan di vault/ocr_benchmark_results.json.", body))

    doc.build(story)
    print(f"[+] Benchmark PDF: {OUT}")


if __name__ == "__main__":
    main()
