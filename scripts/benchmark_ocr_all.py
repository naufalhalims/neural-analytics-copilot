#!/usr/bin/env python3
"""Benchmark seluruh PDF di vault: klasifikasi otentikasi scan + statistik OCR."""
import json
import os
import re
import sys
from collections import defaultdict

import pymupdf

VAULT = "/home/ubuntu/apps/neural-analytics-chatbot/vault"


def classify(path):
    doc = pymupdf.open(path)
    page = doc[0]

    images = page.get_images(full=True)
    n_images = len(images)
    full_area = page.rect.width * page.rect.height
    img_area = 0.0
    for img in images:
        for r in page.get_image_rects(img[0]):
            img_area += r.width * r.height
    coverage = (img_area / full_area * 100) if full_area else 0.0

    text = page.get_text()
    n_chars = len(text.strip())

    stream = page.read_contents().decode("latin-1", errors="ignore")
    tr_modes = set(re.findall(r"(\d+)\s+Tr", stream))

    pages = doc.page_count
    doc.close()

    has_full_raster = n_images >= 1 and coverage > 80
    has_ocr = n_chars > 0
    is_invisible = "3" in tr_modes

    if has_full_raster and has_ocr and is_invisible:
        cat = "AUTHENTIC_SCANNED"
    elif has_full_raster and has_ocr:
        cat = "SCANNED_VISIBLE_TEXT"
    elif has_full_raster:
        cat = "PURE_IMAGE"
    else:
        cat = "DIGITAL_NATIVE"

    return dict(
        category=cat,
        n_images=n_images,
        coverage=round(coverage, 1),
        n_chars=n_chars,
        pages=pages,
    )


def main():
    results = {}
    # Berkas benchmark itu sendiri bukan dokumen vault — exclude dari scan
    EXCLUDE = {"OCR_Benchmark_Report.pdf"}
    for root, _, files in os.walk(VAULT):
        for f in files:
            if not f.lower().endswith(".pdf"):
                continue
            if f in EXCLUDE:
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, VAULT)
            try:
                results[rel] = classify(p)
            except Exception as e:
                results[rel] = dict(category="ERROR", error=str(e))

    # Agregasi
    by_cat = defaultdict(list)
    for rel, r in results.items():
        by_cat[r.get("category", "ERROR")].append(rel)

    total = len(results)
    summary = {
        "total_pdfs": total,
        "categories": {k: len(v) for k, v in sorted(by_cat.items())},
        "files": results,
    }

    out = "/home/ubuntu/apps/neural-analytics-chatbot/vault/ocr_benchmark_results.json"
    with open(out, "w") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"Total PDF: {total}")
    print("Kategori:")
    for k in sorted(by_cat):
        print(f"  {k}: {len(by_cat[k])}")
    print(f"\nDisimpan ke: {out}")

    # Tampilkan yang bukan AUTHENTIC_SCANNED (perlu perhatian)
    non = {rel: r for rel, r in results.items() if r.get("category") != "AUTHENTIC_SCANNED"}
    if non:
        print("\nBukan AUTHENTIC_SCANNED:")
        for rel, r in sorted(non.items()):
            print(f"  [{r.get('category')}] {rel}")


if __name__ == "__main__":
    main()
