#!/usr/bin/env python3
"""Bukti verifikasi PDF scan via PyMuPDF.

Membuktikan 4 hal yang membedakan 'Authentic Searchable Scanned PDF'
dari PDF digital biasa:
  1. Full-page raster image  (halaman adalah foto scan, bukan teks vektor)
  2. OCR text layer tersemat  (teks bisa dicari/disalin)
  3. Teks digambar dgn render mode 3 (invisible) -> tak muncul di atas gambar
  4. Jadi: terlihat 100% kertas scan saat dibaca manusia, 100% terbaca mesin.
"""
import re
import sys
import pymupdf


def check(path):
    doc = pymupdf.open(path)
    page = doc[0]

    # 1) Gambar raster (hasil scan)
    images = page.get_images(full=True)
    n_images = len(images)
    full_area = page.rect.width * page.rect.height
    img_area = 0.0
    for img in images:
        for r in page.get_image_rects(img[0]):
            img_area += r.width * r.height
    coverage = (img_area / full_area * 100) if full_area else 0.0

    # 2) Teks (OCR layer)
    text = page.get_text()
    n_chars = len(text.strip())

    # 3) Render mode invisible (Tr = 3) di content stream
    stream = page.read_contents().decode("latin-1", errors="ignore")
    tr_modes = set(re.findall(r"(\d+)\s+Tr", stream))

    doc.close()
    return dict(
        n_images=n_images,
        coverage_pct=round(coverage, 1),
        n_chars=n_chars,
        tr_modes=tr_modes,
    )


def verdict(r):
    has_full_raster = r["n_images"] >= 1 and r["coverage_pct"] > 80
    has_ocr_text = r["n_chars"] > 0
    is_invisible = "3" in r["tr_modes"]
    if has_full_raster and has_ocr_text and is_invisible:
        return "AUTHENTIC SEARCHABLE SCANNED PDF"
    if has_full_raster and has_ocr_text:
        return "Scanned PDF (gambar + teks, tapi teks terlihat)"
    if has_full_raster:
        return "Pure image scan (TIDAK searchable)"
    return "DIGITAL NATIVE (bukan scan)"


if __name__ == "__main__":
    for path in sys.argv[1:]:
        r = check(path)
        print(f"File : {path}")
        print(f"  Gambar raster       : {r['n_images']} (coverage {r['coverage_pct']}%)")
        print(f"  Karakter teks OCR   : {r['n_chars']}")
        print(f"  Render mode Tr      : {sorted(r['tr_modes'])}  (3 = invisible OCR)")
        print(f"  => {verdict(r)}")
        print()
