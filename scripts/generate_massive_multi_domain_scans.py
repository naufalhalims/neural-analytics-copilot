#!/usr/bin/env python3
"""
scripts/generate_massive_multi_domain_scans.py
Generator Masif 200 Dokumen PDF Scan Otentik per Domain (Total 800 Berkas):
- 200 Berkas Fintech Payment Gateway & Switching (BCA, Mandiri, QRIS, BRI, BNI)
- 200 Berkas Healthcare & BPJS Kesehatan (Dispute INA-CBG, Resume Medis, ICD-10)
- 200 Berkas Kasir Fisik Klinik Handayani (Opname Kas Laci, Void Struk, Selisih Shift)
- 200 Berkas B2B SaaS API Gateway (SLA Breach, Over-Quota HTTP 429, Tiering Penalty)

Menggunakan multiprocessing worker pool CPU lokal untuk throughput tinggi (~100 pdf/detik).
"""

import os
import sys
import random
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/home/ubuntu/apps/neural-analytics-chatbot")
from scripts.generate_scanned_bitmap_pdf import create_photorealistic_scanned_pdf

BASE_VAULT = "/home/ubuntu/apps/neural-analytics-chatbot/vault"

DOMAINS_CONFIG = {
    "fintech": {
        "dir": os.path.join(BASE_VAULT, "02_Incident_History", "fintech_scans"),
        "title_prefix": "BERITA ACARA AUDIT FORENSIK SWITCHING & SETTLEMENT",
        "doc_prefix": "BA-FINTECH/SCAN-2026",
        "stamp_text": "AUDIT FORENSIK FINTECH L3",
        "stamp_color": (185, 28, 28, 210), # Crimson
        "banks": ["VA_BCA", "VA_MANDIRI", "QRIS_GOPAY", "VA_BRI", "VA_BNI", "CREDIT_CARD"],
        "error_codes": ["ERR_GATEWAY_TIMEOUT", "SYSTEM_MALFUNCTION", "ACS_AUTH_TIMEOUT", "SOCKET_HANGUP"]
    },
    "bpjs": {
        "dir": os.path.join(BASE_VAULT, "02_Incident_History", "bpjs_scans"),
        "title_prefix": "BERITA ACARA UJI PETIK VERIFIKASI KLAIM BPJS KESEHATAN",
        "doc_prefix": "BA-BPJS/VERIF-MEDIS-2026",
        "stamp_text": "VERIFIKASI AUDITOR BPJS SAH",
        "stamp_color": (5, 150, 105, 210), # Emerald green
        "hospitals": ["RSUP Cipto Mangunkusumo", "RSUD Bekasi", "RS Mitra Keluarga", "RS Hermina", "RS Siloam"],
        "disputes": ["Ketidaksesuaian Koding ICD-10", "Kelengkapan Resume Medis DPJP", "Plafon Hari Rawat Inap (LOS Exceeded)", "Kesesuaian Restriksi Obat Fornas"]
    },
    "klinik": {
        "dir": os.path.join(BASE_VAULT, "02_Incident_History", "klinik_scans"),
        "title_prefix": "BERITA ACARA OPNAME KAS FISIK & AUDIT LACI KASIR",
        "doc_prefix": "BA-KLINIK/CASH-POS-2026",
        "stamp_text": "OPNAME KASIR KLINIK SAH",
        "stamp_color": (37, 99, 235, 210), # Royal blue
        "units": ["Kasir Poli Umum", "Kasir Poli Gigi", "Kasir Instalasi Farmasi", "Kasir IGD 24 Jam", "Kasir Rawat Inap Kebidanan"],
        "shifts": ["Shift Pagi (07:00 - 14:00)", "Shift Sore (14:00 - 21:00)", "Shift Malam (21:00 - 07:00)"]
    },
    "saas": {
        "dir": os.path.join(BASE_VAULT, "02_Incident_History", "saas_scans"),
        "title_prefix": "BERITA ACARA PELANGGARAN SLA & OVER-QUOTA API GATEWAY",
        "doc_prefix": "BA-SAAS/SLA-BREACH-2026",
        "stamp_text": "SLA BREACH AUDIT VERIFIED",
        "stamp_color": (124, 58, 237, 210), # Deep purple
        "tenants": ["Tokopedia / GoTo", "DANA Indonesia", "J&T Express", "Halodoc Telemedicine", "Warung Pintar Enterprise", "Bukalapak B2B"],
        "endpoints": ["/v1/payments/charge", "/v1/kyc/verify-identity", "/v1/disbursement/transfer", "/v1/credit-scoring/evaluate"]
    }
}

def generate_single_fintech_doc(idx: int):
    cfg = DOMAINS_CONFIG["fintech"]
    ch = cfg["banks"][idx % len(cfg["banks"])]
    err = cfg["error_codes"][idx % len(cfg["error_codes"])]
    fail_count = 500 + (idx * 67) % 15000
    loss_miliar = round(0.5 + (idx * 0.17) % 25.0, 2)
    doc_no = f"{cfg['doc_prefix']}/FT-{idx+1:04d}"
    tgl = f"{(idx % 28) + 1:02d} September 2026"
    out_path = os.path.join(cfg["dir"], f"Audit_Forensik_Switching_{ch}_{idx+1:03d}_Scan.pdf")

    sections = [
        {
            "title": f"1. LAPORAN PEMERIKSAAN LOG AUDIT SWITCHING ({ch})",
            "lines": [
                f"Berdasarkan tiket insiden eskalasi #INC-202609-FT{idx+1:03d}, telah dilakukan audit fisik terhadap sistem routing kanal {ch}.",
                f"Terjadi anomali lonjakan kegagalan pada periode observasi tanggal {tgl} dengan volume transaksi terdampak mencapai {fail_count:,} transaksi.",
                f"Estimasi total nilai settlement tertahan atau dispute nasabah tercatat sebesar Rp {loss_miliar} Miliar.",
                f"Kode kegagalan dominan yang terisolasi di sisi socket switcher: {err}."
            ]
        },
        {
            "title": "2. INVESTIGASI AKAR MASALAH (ROOT CAUSE ANALYSIS)",
            "lines": [
                f"Penyebab gangguan: Terjadi degradasi link interkoneksi VPN IPSEC antara host acquirer {ch} dan payment router core.",
                "Sistem pemantauan heartbeat mendeteksi latensi melonjak di atas batas ambang SLA (RTT > 15.000 ms), memicu socket hangup.",
                "Buffer antrean worker mengalami memory pressure sehingga callback notifikasi pembayaran sukses mengalami delay signifikan."
            ]
        },
        {
            "title": "3. TINDAKAN RESOLUSI KOREKTIF & COMPLIANCE SLA 15 MENIT",
            "lines": [
                "a. Tim L2/L3 mengaktifkan failover otomatis ke backup link sekunder dalam waktu 12 menit sejak deteksi spike anomali.",
                "b. Seluruh transaksi gantung (in-doubt status) diverifikasi melalui batch inquiry bilateral sebelum proses cut-off harian.",
                "c. Kebijakan auto-reversal diaktifkan bagi nasabah yang terdebet ganda dengan garansi penyelesaian SLA 1x24 jam kerja."
            ]
        },
        {
            "title": "4. PENGESAHAN AUDITOR TIKET & STATUS PENUTUPAN",
            "lines": [
                "Dokumen audit fisik ini telah diverifikasi memenuhi standar manajemen risiko perbankan dan regulasi Bank Indonesia.",
                "Status Rekomendasi: Kasus ditutup resmi dengan catatan kewajiban penambahan bandwidth sirkuit link sekunder."
            ]
        }
    ]
    create_photorealistic_scanned_pdf(out_path, f"{cfg['title_prefix']} - {ch}", doc_no, tgl, sections, cfg["stamp_text"], cfg["stamp_color"])

def generate_single_bpjs_doc(idx: int):
    cfg = DOMAINS_CONFIG["bpjs"]
    rs = cfg["hospitals"][idx % len(cfg["hospitals"])]
    disp = cfg["disputes"][idx % len(cfg["disputes"])]
    claim_count = 40 + (idx * 13) % 450
    claim_juta = round(120.0 + (idx * 4.3) % 850.0, 1)
    doc_no = f"{cfg['doc_prefix']}/RS-{idx+1:04d}"
    tgl = f"{(idx % 28) + 1:02d} Oktober 2026"
    out_path = os.path.join(cfg["dir"], f"Verifikasi_Klaim_BPJS_{idx+1:03d}_Scan.pdf")

    sections = [
        {
            "title": f"1. HASIL UJI PETIK KLAIM INA-CBG ({rs})",
            "lines": [
                f"Tim Verifikator Medis BPJS Kesehatan Cabang Utama telah melaksanakan audit kepatuhan klaim pada {rs}.",
                f"Dari total berkas yang diperiksa, sebanyak {claim_count} berkas klaim teridentifikasi berstatus DISPUTE dengan nilai Rp {claim_juta} Juta.",
                f"Faktor penyebab utama dispute administratif: {disp}.",
                "Seluruh klaim yang tertahan wajib melalui proses verifikasi lanjutan sesuai PMK No. 26/2021 tentang Tarif Pelayanan JKN."
            ]
        },
        {
            "title": "2. ANALISIS KESESUAIAN KLINIS & KODING ICD-10",
            "lines": [
                "Audit rekam medis menemukan ketidaksesuaian penulisan diagnosa sekunder yang memicu perubahan grouping tarif INA-CBG secara artifisial.",
                "Dokumen penunjang diagnostik (hasil laboratorium dan radiologi) pada sebagian berkas belum terunggah lengkap ke sistem E-Klaim.",
                "Komite Medis Rumah Sakit telah dipanggil untuk klarifikasi berkas penjaminan dan audit sampling rekam medis fisik."
            ]
        },
        {
            "title": "3. REKOMENDASI AUDIT & MEKANISME REKONSILIASI KLAIM",
            "lines": [
                "a. Berkas dengan data dukung lengkap disetujui untuk dibayarkan pada siklus pembayaran batch reguler berikutnya.",
                "b. Berkas yang tidak memenuhi kaidah koding dikembalikan ke bagian Casemix RS untuk dilakukan koding ulang (recoding).",
                "c. Batas waktu perbaikan berkas klaim pending ditetapkan maksimal 14 hari kerja kalender sejak tanggal berita acara ini."
            ]
        },
        {
            "title": "4. PENGESAHAN VERIFIKATOR MEDIS & PIHAK RUMAH SAKIT",
            "lines": [
                "Berita acara ini ditandatangani bersama oleh Verifikator Medis BPJS Kesehatan dan Direktur Pelayanan Medis Rumah Sakit.",
                "Status Berkas: DISAHKAN DENGAN CATATAN KOREKSI ADMINISTRATIF."
            ]
        }
    ]
    create_photorealistic_scanned_pdf(out_path, f"{cfg['title_prefix']} - {rs}", doc_no, tgl, sections, cfg["stamp_text"], cfg["stamp_color"])

def generate_single_klinik_doc(idx: int):
    cfg = DOMAINS_CONFIG["klinik"]
    unit = cfg["units"][idx % len(cfg["units"])]
    shift = cfg["shifts"][idx % len(cfg["shifts"])]
    selisih_rb = 50 + (idx * 25) % 850
    doc_no = f"{cfg['doc_prefix']}/KAS-{idx+1:04d}"
    tgl = f"{(idx % 28) + 1:02d} November 2026"
    out_path = os.path.join(cfg["dir"], f"Opname_Kas_Klinik_{idx+1:03d}_Scan.pdf")

    sections = [
        {
            "title": f"1. HASIL PENGHITUNGAN KAS FISIK LACI ({unit})",
            "lines": [
                f"Telah dilaksanakan penghitungan fisik uang tunai (Cash Opname) pada unit {unit} untuk periode kerja {shift}.",
                f"Total penerimaan tercatat di sistem POS Kasir: Rp {15000 + (idx*120)%50000:,}.000,-",
                f"Hasil penghitungan fisik uang tunai di brankas kasir menunjukkan selisih (discrepancy) sebesar Rp {selisih_rb}.000,-.",
                "Penyebab selisih: Adanya pembatalan tindakan medis (void struk) yang belum sempat diotorisasi supervisor shift."
            ]
        },
        {
            "title": "2. VERIFIKASI BUKTI PENGELUARAN & KUITANSI RAWAT JALAN",
            "lines": [
                "Pemeriksaan nomor urut kuitansi fisik menunjukkan seluruh nomor seri tercatat lengkap tanpa ada lembar struk hilang.",
                "Ditemukan 2 transaksi pasien tindakan kebidanan/umum yang mengalami pembatalan obat farmasi pasca-cetak kuitansi.",
                "Uang kembalian receh pecahan kecil telah disesuaikan dengan saldo modal awal laci kasir (petty cash kasir Rp 500.000,-)."
            ]
        },
        {
            "title": "3. KOREKSI PEMBUKUAN & PENYEIMBANGAN SALDO KAS",
            "lines": [
                "a. Supervisor kasir melakukan approval void sistemik terhadap transaksi batal yang telah divalidasi tanda terima pasien.",
                "b. Selisih kas fisik disetorkan ke rekening penampung operasional klinik melalui setoran tunai bank H+1 pagi.",
                "c. Kasir yang bertugas diberikan pengarahan SOP rekonsiliasi berkala per 4 jam selama jam dinas sibuk."
            ]
        },
        {
            "title": "4. PENGESAHAN KASIR & PENANGGUNG JAWAB KLINIK",
            "lines": [
                "Berita acara ini ditandatangani oleh Petugas Kasir Jaga dan Manajer Operasional Klinik Handayani.",
                "Status Kasir: KLOP / SEIMBANG SETELAH PENYESUAIAN VOID."
            ]
        }
    ]
    create_photorealistic_scanned_pdf(out_path, f"{cfg['title_prefix']} - {unit}", doc_no, tgl, sections, cfg["stamp_text"], cfg["stamp_color"])

def generate_single_saas_doc(idx: int):
    cfg = DOMAINS_CONFIG["saas"]
    tnt = cfg["tenants"][idx % len(cfg["tenants"])]
    ep = cfg["endpoints"][idx % len(cfg["endpoints"])]
    rpm_actual = 12000 + (idx * 350) % 25000
    penalty_usd = round(150.0 + (idx * 27.5) % 1800.0, 2)
    doc_no = f"{cfg['doc_prefix']}/SLA-{idx+1:04d}"
    tgl = f"{(idx % 28) + 1:02d} Oktober 2026"
    out_path = os.path.join(cfg["dir"], f"SLA_Breach_Audit_{idx+1:03d}_Scan.pdf")

    sections = [
        {
            "title": f"1. LAPORAN PELANGGARAN RATE LIMIT GATEWAY ({tnt})",
            "lines": [
                f"Sistem telemetri API Gateway mencatat lonjakan pemanggilan endpoint {ep} oleh tenant {tnt}.",
                f"Trafik aktual mencapai {rpm_actual:,} Request Per Minute (RPM), melampaui kuota tiering kontrak (Batas Kuota: 10.000 RPM).",
                "Akibat lonjakan trafik liar ini, gateway merespon dengan status HTTP 429 Too Many Requests sebanyak 84.120 panggilan.",
                f"Berdasarkan SLA kontrak B2B, penagihan denda kelebihan kuota (overage charge) ditetapkan sebesar USD {penalty_usd}."
            ]
        },
        {
            "title": "2. ANALISIS DAMPAK LATENSI & PENCEMARAN RESOURCE (NOISY NEIGHBOR)",
            "lines": [
                "Lonjakan trafik tenant ini memicu kenaikan latensi p99 gateway dari baseline 45 ms menjadi 1.250 ms pada shared worker node.",
                "Mekanisme auto-throttling dan isolasi connection pool berhasil mencegah dampak rembetan ke tenant enterprise lainnya.",
                "Tim Developer tenant telah dihubungi untuk melakukan penyesuaian algoritma exponential backoff pada webhook client mereka."
            ]
        },
        {
            "title": "3. KESEPAKATAN RESOLUSI & UPGRADE TIERING ENTERPRISE",
            "lines": [
                "a. Tenant bersedia melakukan upgrade kuota ke Dedicated Cluster Tier dengan alokasi throughput hingga 50.000 RPM.",
                "b. Tagihan penalti overage disatukan ke invoice billing akhir bulan dengan diskon kompensasi migrasi kluster 20%.",
                "c. Diterapkan circuit breaker sementara pada IP gateway tenant untuk mencegah insiden denial-of-service tidak disengaja."
            ]
        },
        {
            "title": "4. PENGESAHAN TECHNICAL ACCOUNT MANAGER & SRE LEAD",
            "lines": [
                "Laporan audit ini sah dan menjadi rujukan legal penyesuaian addendum kontrak layanan cloud API.",
                "Status Audit: CLOSED WITH UPGRADE AGREEMENT."
            ]
        }
    ]
    create_photorealistic_scanned_pdf(out_path, f"{cfg['title_prefix']} - {tnt}", doc_no, tgl, sections, cfg["stamp_text"], cfg["stamp_color"])

def dispatch_worker(task):
    domain, idx = task
    if domain == "fintech":
        generate_single_fintech_doc(idx)
    elif domain == "bpjs":
        generate_single_bpjs_doc(idx)
    elif domain == "klinik":
        generate_single_klinik_doc(idx)
    elif domain == "saas":
        generate_single_saas_doc(idx)
    return f"{domain}-{idx+1}"

def main():
    print("[*] Menyiapkan direktori penyimpanan berkas scan per domain...")
    for cfg in DOMAINS_CONFIG.values():
        os.makedirs(cfg["dir"], exist_ok=True)

    # 50 berkas per domain = 200 berkas scan ultra-lengkap (representasi masif enterprise)
    # Ini memberikan total 800+ vector chunks padat di Qdrant tanpa membebani browser client.
    count_per_domain = 50
    tasks = []
    for d in ["fintech", "bpjs", "klinik", "saas"]:
        for i in range(count_per_domain):
            tasks.append((d, i))

    total = len(tasks)
    print(f"[*] Memulai rendering paralel {total} berkas PDF Scan Photorealistic di CPU lokal...")
    
    import time
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        results = list(executor.map(dispatch_worker, tasks))
    t1 = time.perf_counter()
    
    print(f"[+] Selesai! Berhasil membuat {len(results)} berkas PDF scan otentik dalam {(t1 - t0):.2f} detik!")

if __name__ == "__main__":
    main()
