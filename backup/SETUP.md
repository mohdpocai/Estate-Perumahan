# Laporan bulanan automatik (Excel + PDF ke Google Drive)

Pada **1hb setiap bulan, 00:10 waktu Malaysia**, GitHub menjana laporan bulan lepas (Excel + PDF), menyimpannya dalam folder Google Drive anda, dan (jika dihidupkan) **mengosongkan senarai semak** untuk bulan baharu.

**Dikosongkan:** semua tanda Rekod Kelengkapan, dan tanda kerosakan yang sudah *Selesai*.
**Kekal:** bangunan, pintu, nama penghuni, pelan, kerosakan yang *belum Selesai*, dan semua rekod di halaman Kerosakan.
**Keselamatan:** tiada apa dikosongkan kecuali fail sudah dimuat naik ke Drive dan saiznya disahkan. Sandaran bulan yang sama tidak boleh dikosongkan dua kali. Salinan laporan turut disimpan 90 hari dalam GitHub (Actions → artifak, peribadi).

## Persediaan sekali sahaja

### 1. Akaun sandaran dalam Firebase
Firebase console → **Authentication → Users → Add user**. Emel contoh `sandaran@estate.local` dan kata laluan yang kuat. (Jangan guna akaun staf harian.)

### 2. Penerima Google Drive (Apps Script)
1. Dalam Google Drive, buat folder, contohnya **Laporan Bulanan LP2**. Salin **ID folder** (bahagian akhir URL folder).
2. Buka <https://script.google.com> → **New project**. Padam semua kod, tampal isi `backup/apps_script.gs`.
3. Tukar `TOKEN` kepada kata rahsia panjang (rekaan sendiri) dan `FOLDER_ID` kepada ID folder.
4. **Deploy → New deployment → Web app**. *Execute as:* **Me**, *Who has access:* **Anyone**. Deploy, benarkan akses Drive apabila diminta, kemudian salin **Web app URL**.

### 3. Rahsia dalam GitHub
Repo → **Settings → Secrets and variables → Actions → New repository secret**. Tambah empat:

| Nama | Nilai |
|---|---|
| `BACKUP_EMAIL` | emel akaun sandaran (langkah 1) |
| `BACKUP_PASSWORD` | kata laluan akaun itu |
| `APPS_SCRIPT_URL` | Web app URL (langkah 2) |
| `APPS_SCRIPT_TOKEN` | kata rahsia yang sama dengan `TOKEN` dalam skrip |

### 4. Uji dahulu (data tidak diubah)
Repo → **Actions → Laporan bulanan → Run workflow**. Isi *month* contohnya `2026-10`, biarkan **clear** tidak ditanda, tekan Run. Selepas ~1 minit semak folder Drive: patut ada `Laporan-2026-10.xlsx` dan `.pdf`. Semak isinya.

### 5. Hidupkan pengosongan automatik
Hanya selepas laporan ujian betul: **Settings → Secrets and variables → Actions → Variables → New repository variable**: nama `CLEAR_AFTER_BACKUP`, nilai `true`.
Untuk mematikan semula, padam pembolehubah itu atau tukar kepada `false`.

## Perkara yang perlu diketahui
- Jika sesuatu gagal, GitHub menghantar emel "workflow failed" kepada pemilik repo dan **data tidak dikosongkan**. Jalankan semula dari tab Actions (*force* jika perlu).
- **PDF** mengandungi semua data dan gambar: ringkasan, senarai semua penghuni, rekod setiap bilik (kelengkapan dan kerosakan) dan rekod kerosakan kekal, dengan gambar bukti dimampatkan. **Excel** mengandungi data dalam bentuk jadual (tanpa gambar).
- Gambar sentiasa kekal dalam Firebase juga. Jika PDF terlalu besar (banyak gambar), ia masih boleh disimpan dalam Drive; had muat naik Apps Script lebih kurang 50 MB.
- GitHub memberhentikan jadual automatik jika repo tiada aktiviti 60 hari. Jika itu berlaku, hidupkan semula di tab Actions.
- Jika ada gambar yang tidak dapat dimasukkan dalam PDF, laporan tetap disimpan tetapi **pengosongan dihentikan** dan anda diemail. Untuk mengosongkan juga, tambah pembolehubah `ALLOW_MISSING_PHOTOS` = `true`.
- Uji tempatan: `python backup/test_backup.py`.
