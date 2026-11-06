#!/usr/bin/env python3
"""
scripts/generate_scanned_bitmap_pdf.py
Engine pembuat PDF Scanned Asli (Photorealistic Bitmap Scan):
1. Menggambar dokumen ke High-Resolution Image Canvas (300 DPI) via Pillow (PIL).
2. Menerapkan efek fisik scanner otentik:
   - Noise bintik kertas (Gaussian Paper Grain / Dust speckles).
   - Sedikit kemiringan sudut rotasi pemindaian (Micro-rotation 0.5 - 1.2 derajat).
   - Efek degradasi kontras & bayangan tepi lipatan kertas (Vignette & Scan margin blur).
   - Stempel basah fisik warna merah/biru miring.
3. Membungkus citra bitmap ke PDF dengan invisible/searchable OCR text layer (PyMuPDF)
   sehingga dokumen 100% terlihat sebagai kertas scan fisik saat dibuka manusia,
   sekaligus 100% terbaca sempurna oleh mesin RAG / Qdrant.
"""

import os
import random
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pymupdf

def create_photorealistic_scanned_pdf(
    output_pdf_path: str,
    title: str,
    doc_number: str,
    audit_date: str,
    sections: list,
    stamp_text: str = "TERVERIFIKASI AUDIT L3",
    stamp_color: tuple = (185, 28, 28, 200) # Deep crimson red
):
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    # 1. Canvas Dimensions (A4 at 150 DPI = 1240 x 1754 px for crystal clear display without huge file size)
    dpi = 150
    w = int(8.27 * dpi)
    h = int(11.69 * dpi)
    
    # Base paper color: Warm yellowish-white off-white (#fbfaf5)
    img = Image.new("RGB", (w, h), (251, 250, 246))
    
    # Add scanner paper grain / sensor noise
    grain = np.random.normal(0, 3.5, (h, w, 3)).astype(np.int16)
    img_np = np.clip(np.array(img, dtype=np.int16) + grain, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)
    
    draw = ImageDraw.Draw(img)
    
    # Load default or clean bitmap fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_meta = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", 14)
        font_h2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        font_stamp = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        font_title = font_h2 = font_stamp = ImageFont.load_default()
        font_meta = font_body = ImageFont.load_default()

    # Border frame dokumen resmi (agak pudar khas hasil fotokopi/scanner)
    border_col = (100, 116, 139)
    draw.rectangle([45, 45, w - 45, h - 45], outline=border_col, width=2)
    draw.rectangle([50, 50, w - 50, h - 50], outline=border_col, width=1)
    
    # Header Dokumen
    y = 75
    draw.text((w // 2, y), title, fill=(15, 23, 42), font=font_title, anchor="mt")
    y += 32
    draw.text((w // 2, y), f"Nomor Berkas: {doc_number}  |  Tanggal Audit: {audit_date}", fill=(71, 85, 105), font=font_meta, anchor="mt")
    y += 26
    
    # Garis pembatas tebal tipis
    draw.line([60, y, w - 60, y], fill=(148, 163, 184), width=2)
    y += 20
    
    # Text Chunks for Searchable OCR
    ocr_text_blocks = []
    ocr_text_blocks.append(f"{title}\nNomor Berkas: {doc_number}\nTanggal Audit: {audit_date}")

    for sec in sections:
        h2_title = sec.get("title", "")
        body_lines = sec.get("lines", [])
        
        draw.text((65, y), h2_title, fill=(30, 41, 59), font=font_h2)
        y += 24
        
        sec_text_block = [h2_title]
        for line in body_lines:
            # Wrap text to fit margins (~80 chars per line at this font size)
            words = line.split()
            current_line = []
            for word in words:
                current_line.append(word)
                test_str = " ".join(current_line)
                bbox = draw.textbbox((0, 0), test_str, font=font_body)
                if (bbox[2] - bbox[0]) > (w - 140):
                    current_line.pop()
                    draw.text((70, y), " ".join(current_line), fill=(51, 65, 85), font=font_body)
                    sec_text_block.append(" ".join(current_line))
                    y += 19
                    current_line = [word]
            if current_line:
                draw.text((70, y), " ".join(current_line), fill=(51, 65, 85), font=font_body)
                sec_text_block.append(" ".join(current_line))
                y += 19
        y += 14
        ocr_text_blocks.append("\n".join(sec_text_block))

    # Stempel Basah Otentik (Rubber Stamp) dengan rotasi & tekstur pudar
    stamp_w, stamp_h = 320, 100
    stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stamp_img)
    # Double ring oval/rectangle stamp
    s_draw.rectangle([6, 6, stamp_w - 6, stamp_h - 6], outline=stamp_color, width=3)
    s_draw.rectangle([11, 11, stamp_w - 11, stamp_h - 11], outline=stamp_color, width=1)
    s_draw.text((stamp_w // 2, 22), stamp_text, fill=stamp_color, font=font_stamp, anchor="mt")
    s_draw.text((stamp_w // 2, 50), "STATUS: SAH / CLOSED", fill=stamp_color, font=font_body, anchor="mt")
    s_draw.text((stamp_w // 2, 68), audit_date, fill=stamp_color, font=font_body, anchor="mt")

    # Miringkan stempel -14 derajat
    stamp_rotated = stamp_img.rotate(-14, expand=True, resample=Image.BICUBIC)
    
    # Tempel stempel di pojok kanan bawah
    stamp_x = w - stamp_rotated.width - 70
    stamp_y = h - stamp_rotated.height - 90
    img.paste(stamp_rotated, (stamp_x, stamp_y), stamp_rotated)

    # 4. Realistic Scanner Distortion (Sedikit miring 0.7 derajat & bayangan tepi scanner)
    img_scanned = img.rotate(0.65, expand=False, fillcolor=(245, 244, 239), resample=Image.BICUBIC)
    # Tambahkan sedikit blur lensa optik scanner (radius 0.3)
    img_scanned = img_scanned.filter(ImageFilter.GaussianBlur(radius=0.35))
    
    # Simpan sebagai JPG sementara resolusi tinggi
    temp_jpg = output_pdf_path.replace(".pdf", "_page.jpg")
    img_scanned.save(temp_jpg, "JPEG", quality=92)
    
    # 5. Bungkus ke PDF menggunakan PyMuPDF dengan Invisible OCR Text Layer tersemat
    # Ini adalah standar internasional "Searchable Scanned PDF"
    doc = pymupdf.open()
    rect = pymupdf.Rect(0, 0, 595.3, 841.9) # A4 points
    page = doc.new_page(width=rect.width, height=rect.height)
    
    # Masukkan gambar scan menutupi seluruh halaman background
    page.insert_image(rect, filename=temp_jpg)
    
    # Masukkan teks transparan (invisible OCR text layer) di posisi yang tepat
    # Teks transparan ini yang dibaca oleh modul RAG Qdrant & PyMuPDF
    full_ocr_text = "\n\n".join(ocr_text_blocks)
    page.insert_textbox(
        pymupdf.Rect(30, 30, rect.width - 30, rect.height - 30),
        full_ocr_text,
        fontsize=8,
        color=(0, 0, 0),
        render_mode=3 # render_mode=3 artinya text is invisible (OCR layer mode)
    )
    
    doc.save(output_pdf_path)
    doc.close()
    
    # Cleanup temp jpg
    if os.path.exists(temp_jpg):
        os.remove(temp_jpg)
        
    print(f"[+] Berhasil membuat Authentic Searchable Scanned PDF: {output_pdf_path}")
    return output_pdf_path

if __name__ == "__main__":
    smoke_output = "/home/ubuntu/apps/neural-analytics-chatbot/vault/02_Incident_History/Smoke_Test_Audit_Insiden_Fisik_Scan.pdf"
    sections = [
        {
            "title": "1. LAPORAN PEMERIKSAAN FISIK & INVESTIGASI SWITCHER",
            "lines": [
                "Berdasarkan instruksi Direktur Kepatuhan & Operasional, telah dilakukan audit forensik terhadap sistem Payment Gateway switching.",
                "Ditemukan selisih saldo tertahan sebanyak 1.428 transaksi pada jendela pemeliharaan switch sentral.",
                "Penyebab utama: Terputusnya session TLS port 8443 antara server Switcher dan Core Banking Mandiri/BCA."
            ]
        },
        {
            "title": "2. TINDAKAN PENYELESAIAN & PROSEDUR KOREKTIF (SLA 15 MENIT)",
            "lines": [
                "a. Tim L3 Network Security telah melakukan flush routing table dan failover ke dedicated fiber optics jalur sekunder.",
                "b. Seluruh transaksi tertahan (pending) otomatis diselesaikan melalui mekanisme dual-query inquiry sebelum batas akhir cut-off.",
                "c. Rekonsiliasi manual disetujui dengan pengembalian dana (refund) instan 100% tanpa potongan biaya switching."
            ]
        },
        {
            "title": "3. KESIMPULAN & PENETAPAN AUDITOR",
            "lines": [
                "Dokumen ini diterbitkan sebagai bukti fisik sah pemeriksaan berkas insiden Q3 2026.",
                "Seluruh metrik dan log telah diverifikasi memenuhi standar ISO 27001 dan regulasi transaksi Bank Indonesia."
            ]
        }
    ]
    
    create_photorealistic_scanned_pdf(
        output_pdf_path=smoke_output,
        title="BERITA ACARA AUDIT FISIK INSIDEN GATEWAY & SETTLEMENT",
        doc_number="BA-AUDIT/PHYSICAL-SCAN/2026-Q3/001",
        audit_date="05 November 2026",
        sections=sections,
        stamp_text="AUDIT FISIK L3 - TERVERIFIKASI"
    )
