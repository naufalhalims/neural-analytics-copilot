# POST-MORTEM & HISTORICAL INCIDENT LOG
## Rekam Jejak Insiden Operasional Sistem Pembayaran — Kuartal 3 (Q3) 2026
**Periode Pencatatan**: 1 Juli 2026 – 30 September 2026  
**Otoritas Dokumentasi**: Tim Engineering SRE & Operasional Pembayaran  
**Status Audit**: Terverifikasi Resmi  

---

### TIKET INSIDEN #1: #INC-20260912-BCA (SEVERITY LEVEL: P1 - CRITICAL)
- **Judul Insiden**: Gangguan Masif Koneksi API Virtual Account BCA akibat Migrasi Switch Data Center
- **Waktu Mulai**: **12 September 2026, Pukul 14:15 WIB**
- **Waktu Selesai**: **15 September 2026, Pukul 09:45 WIB**
- **Durasi Total**: 67 Jam 30 Menit
- **Kanal Terdampak Utama**: **`VA_BCA`** (Virtual Account BCA)
- **Kode Kegagalan Dominan**: **`ERR_GATEWAY_TIMEOUT`** (92,4% dari total transaksi gagal)
- **Dampak Kuantitatif**:
  - Tingkat kegagalan (*failure rate*) pada kanal VA_BCA melonjak drastis dari baseline normal **3,4%** menjadi **28,4%**.
  - Total transaksi gagal selama jendela insiden: **±14.820 transaksi**.
  - Estimasi volume nilai tertunda: **Rp 18,4 Miliar**.

#### Kronologi & Akar Masalah (Root Cause Analysis):
1. **Pemicu Utama**: Tim infrastruktur jaringan eksternal Bank BCA melakukan migrasi terjadwal perangkat *core switch* pada Data Center Sekunder (DC Sentul).
2. **Kegagalan Teknis**: Terjadi kesalahan konfigurasi tabel *Border Gateway Protocol* (BGP) pada router *edge* perbankan yang memicu *routing loop* dan *intermittent packet loss* sebesar 34% ke IP gateway korporat kami.
3. **Dampak Sistemik**: Permintaan pembuatan nomor VA dan notifikasi pelunasan mengalami *socket hang* lebih dari 30 detik (*ERR_GATEWAY_TIMEOUT*).
4. **Tindakan Mitigasi**:
   - Tim L2 mengaktifkan *maintenance banner* pada antarmuka kasir/checkout untuk merekomendasikan nasabah beralih ke `VA_MANDIRI` atau `QRIS_GOPAY`.
   - Tim L3 mengaktifkan *rate-limiting queue* dan memperpanjang batas waktu *retry* menjadi 45 detik.
   - Pihak Bank BCA berhasil melakukan *rollback* konfigurasi BGP parsial pada 14 September malam, dan stabilisasi penuh tercapai pada 15 September pukul 09:45 WIB.

---

### TIKET INSIDEN #2: #INC-20260804-TELKOM (SEVERITY LEVEL: P2 - HIGH)
- **Judul Insiden**: Putusnya Kabel Laut Internasional (Submarine Cable) Berdampak pada Otentikasi 3D-Secure Kartu Kredit Internasional
- **Waktu Mulai**: **4 Agustus 2026, Pukul 08:30 WIB**
- **Waktu Selesai**: **4 Agustus 2026, Pukul 18:20 WIB**
- **Durasi Total**: 9 Jam 50 Menit
- **Kanal Terdampak Utama**: **`CREDIT_CARD`** (Khusus Kartu Visa/Mastercard Penerbit Luar Negeri)
- **Kode Kegagalan Dominan**: **`ERR_GATEWAY_TIMEOUT`**
- **Dampak Kuantitatif**:
  - Failure rate kanal kartu kredit naik sementara dari 4,8% ke 16,2%.
  - Transaksi domestik tetap berjalan normal 100%.

#### Kronologi & Tindakan Mitigasi:
- Terjadi gangguan kabel optik bawah laut segmen Batam-Singapura. Otentikasi ACS (*Access Control Server*) untuk kartu kredit internasional mengalami kegagalan.
- Tim L3 mengalihkan rute jaringan (*traffic rerouting*) melalui rute satelit/backhaul alternatif hingga perbaikan kabel selesai.

---

### TIKET INSIDEN #3: #INC-20260718-INTERNAL (SEVERITY LEVEL: P3 - MEDIUM)
- **Judul Insiden**: Lonjakan Antrean Message Broker Kafka Memperlambat Pembuatan Dynamic QRIS
- **Waktu Mulai**: **18 Juli 2026, Pukul 19:00 WIB**
- **Waktu Selesai**: **18 Juli 2026, Pukul 20:30 WIB**
- **Durasi Total**: 1 Jam 30 Menit
- **Kanal Terdampak Utama**: **`QRIS_GOPAY`**
- **Kode Kegagalan Dominan**: **`SYSTEM_MALFUNCTION`**
- **Dampak Kuantitatif**:
  - Failure rate sesaat menyentuh 12% selama flash-sale kategori *Retail*.
  - Penyebab: *Consumer group lag* pada cluster Kafka internal karena lonjakan permintaan simultan (5.000 RPS).
  - Resolusi: *Autoscaling* worker consumer dan penambahan partisi antrean.
