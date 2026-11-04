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
- Gambar tidak dimasukkan dalam Excel/PDF (hanya data). Gambar kekal dalam Firebase.
- GitHub memberhentikan jadual automatik jika repo tiada aktiviti 60 hari. Jika itu berlaku, hidupkan semula di tab Actions.
- Uji tempatan: `python backup/test_backup.py`.
