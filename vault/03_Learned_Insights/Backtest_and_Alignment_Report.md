# Laporan Hasil Backtesting & In-Context Alignment

- **Waktu Eksekusi**: 2026-11-02 18:43:04 WIB
- **Dataset Diuji**: 5.000.000 Baris Transaksi (`transactions_5m.parquet`)
- **Akurasi Validasi Walk-Forward**: 100.0%
- **Rata-rata Waktu Eksekusi DuckDB**: 90.81 ms
- **Jumlah Skenario Tervalidasi**: 25/25

## Aturan Kueri Terbukti (Proven In-Context Rules):
1. **Pemisahan Waktu (Temporal Granularity)**:
   - Gunakan `strftime(timestamp, '%Y-%m-%d')` untuk linimasa harian.
   - Gunakan `EXTRACT(hour FROM timestamp)` untuk deteksi pola lonjakan per jam.
   - Gunakan `EXTRACT(dow FROM timestamp) IN (0, 6)` untuk analisis komparasi akhir pekan (weekend).
2. **Kalkulasi Metrik Nominal (GMV)**:
   - Bagi nominal dengan `1e12` untuk satuan Triliun Rupiah.
   - Bagi nominal dengan `1e9` untuk satuan Miliar Rupiah.
3. **Pencegahan Error Skema**:
   - Kolom status transaksi hanya memiliki nilai `SUCCESS` dan `FAILED`.
   - Kode kegagalan tersimpan di kolom `failure_code`.
