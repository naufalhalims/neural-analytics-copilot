# PROSEDUR OPERASIONAL STANDAR (SOP)
## Penanganan Transaksi Gagal, Rekonsiliasi, dan Batas Waktu Pelayanan (SLA)
**Nomor Dokumen**: SOP-OPS-FIN-2026-V2.1  
**Tanggal Berlaku**: 1 Juli 2026  
**Klasifikasi**: Internal Korporat  
**Otoritas Penerbit**: Departemen Operasional Pembayaran & Manajemen Risiko  

---

### 1. TUJUAN & RUANG LINGKUP
Dokumen ini menetapkan panduan baku bagi seluruh tim operasional, *customer support*, dan *engineering* dalam mengidentifikasi, merespons, dan menyelesaikan kegagalan transaksi pada ekosistem kanal pembayaran korporat, mencakup: Virtual Account (BCA, Mandiri), QRIS, Kartu Kredit (Credit Card), dan Dompet Digital (E-Wallet).

---

### 2. KATEGORI KEGAGALAN & MATRIKS RESPON (ERROR TAXONOMY)

| Kode Kegagalan | Kategori Insiden | Deskripsi Teknis | Tindakan Operasional Wajib | Batas SLA Penyelesaian |
| :--- | :--- | :--- | :--- | :--- |
| **`ERR_GATEWAY_TIMEOUT`** | Infrastruktur / Jaringan Vendor | Koneksi API ke *host* perbankan/acquirer terputus (*socket timeout* > 30 detik) saat *in-flight request*. | Cek status jaringan mitra via *heartbeat monitor*. Jika status menggantung (*in-doubt*), lakukan *inquiry callback* otomatis. Jangan debit ganda. | Maksimal 15 Menit |
| **`SYSTEM_MALFUNCTION`** | Database / Server Internal | Galat internal pada payment switch korporat (*HTTP 500/502/503*), *database connection pool exhaustion*, atau *memory spike*. | Eskalasi darurat ke Tim SRE/DevOps Level 3. Alihkan lalu lintas pembayaran (*traffic failover*) ke gateway cadangan. | Maksimal 10 Menit |
| **`INSUFFICIENT_FUNDS`** | Pengguna / Saldo Nasabah | Saldo rekening atau limit kartu nasabah tidak mencukupi saat proses otorisasi. | Tampilkan pesan informatif kepada nasabah untuk mengisi saldo atau mengganti metode pembayaran. Tidak ada eskalasi teknis. | Real-time (Otomatis) |
| **`INVALID_PIN`** | Pengguna / Kesalahan Input | Kesalahan otentikasi PIN/OTP oleh pengguna lebih dari 3 kali. | Kunci transaksi sementara demi keamanan akun. Berikan notifikasi reset PIN atau panduan keamanan. | Real-time (Otomatis) |
| **`SUSPECTED_FRAUD`** | Risiko Keamanan & Kepatuhan | Transaksi terdeteksi oleh sistem *Fraud Detection System* (FDS) karena anomali velocity atau lokasi. | Tahan dana transaksi (*freeze*), masukkan kartu/ID ke *blacklist temporary*, dan eskalasi ke Tim Analis Fraud. | Maksimal 60 Menit |

---

### 3. PROSEDUR ESKALASI & LEVEL DUKUNGAN (ESCALATION MATRIX)

#### Level 1: Tim Customer Care & Monitoring L1
- Memantau dasbor *real-time telemetri*. Jika tingkat kegagalan (*failure rate*) pada satu kanal melebihi ambang batas **5% dalam rentang 10 menit**, L1 wajib memicu notifikasi peringatan di saluran komunikasi operasional.
- Melakukan verifikasi nomor transaksi (*reference ID*) dan memastikan status dana nasabah.

#### Level 2: Tim Operasional Pembayaran & Settlement L2
- Bertanggung jawab melakukan rekonsiliasi selisih dana (*dispute & settlement discrepancy*).
- Jika kegagalan disebabkan oleh gangguan mitra perbankan terkonfirmasi, L2 berwenang mengaktifkan pesan pemeliharaan pada aplikasi (*banner notification*) untuk kanal terkait.
- **Kanal Kontak Darurat Vendor**:
  - Helpdesk Bank BCA: `helpdesk.api@bca.co.id` / Hotline: `021-23588000` (Ext 4).
  - Helpdesk Bank Mandiri: `api.support@bankmandiri.co.id` / Hotline: `021-52997777`.
  - Switching Gateway Network: `noc@artajasa.co.id`.

#### Level 3: Tim SRE, Network & Software Engineering L3
- Dilibatkan apabila insiden berdampak pada lebih dari 2 kanal secara simultan atau kegagalan berstatus `SYSTEM_MALFUNCTION` dan `ERR_GATEWAY_TIMEOUT` yang berlangsung > 15 menit.
- Mengeksekusi *circuit breaker*, *traffic rerouting*, atau pemulihan *failover switch* ke *secondary data center*.

---

### 4. KEBIJAKAN PENGEMBALIAN DANA (AUTO-REFUND & REVERSAL POLICY)
1. **Transaksi Menggantung (*In-Doubt Transaction*)**:
   - Jika nasabah telah terdebit namun status di *merchant* masih `FAILED` atau `PENDING` akibat `ERR_GATEWAY_TIMEOUT`, sistem rekonsiliasi otomatis (*auto-recon*) akan menjalankan sinkronisasi pada pukul 23:59 WIB setiap hari.
2. **Auto-Refund Instan**:
   - Khusus transaksi kanal QRIS dan E-Wallet, jika notifikasi sukses dari mitra tidak diterima dalam kurun waktu **30 menit**, dana wajib dikembalikan secara otomatis (*auto-reversal*) ke dompet asal nasabah.
3. **Manual Refund (Virtual Account & Kartu Kredit)**:
   - Pengembalian dana untuk Virtual Account membutuhkan waktu 1x24 jam kerja setelah formulir klaim nasabah dan mutasi rekening terverifikasi oleh tim L2.

---

### 5. DOKUMENTASI DAN POST-MORTEM
Setiap insiden dengan tingkat keparahan **P1 (Kritis)** di mana volume kegagalan transaksi mencapai >1.000 transaksi atau kerugian potensial > Rp 500.000.000 wajib dibuatkan dokumen *Postmortem Incident Log* paling lambat **2x24 jam** setelah status insiden dinyatakan `RESOLVED`.
