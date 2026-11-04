#!/usr/bin/env python3
"""Monthly backup: read Firebase -> Excel + PDF -> save to Google Drive -> (optionally) clear the senarai semak.

Runs from GitHub Actions on the 1st of every month (Malaysia time) and reports the PREVIOUS month.
Nothing is cleared unless the files were uploaded to Drive and verified, and CLEAR is switched on.
"""
import argparse, base64, json, os, sys
from datetime import datetime, timedelta, timezone

import requests

from report_builder import make_xlsx, make_pdf, month_label, photo_ids
from clear_plan import plan_clear

API_KEY = os.environ.get('FIREBASE_API_KEY', 'AIzaSyCmc1cccrzh29H6SzWPt84a8rK1x747jU8')
DB_URL = os.environ.get('FIREBASE_DB_URL', 'https://estate-perumahan-default-rtdb.asia-southeast1.firebasedatabase.app').rstrip('/')
MYT = timezone(timedelta(hours=8))


def previous_month(now):
    first = now.replace(day=1)
    last = first - timedelta(days=1)
    return f'{last.year}-{last.month:02d}'


def login():
    r = requests.post(os.environ.get('FIREBASE_AUTH_URL', 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword'), params={'key': API_KEY},
                      json={'email': os.environ['BACKUP_EMAIL'], 'password': os.environ['BACKUP_PASSWORD'], 'returnSecureToken': True}, timeout=30)
    if r.status_code != 200:
        sys.exit('Login Firebase gagal: ' + r.text[:200])
    return r.json()['idToken']


def fb(method, path, token, body=None):
    r = requests.request(method, f'{DB_URL}/{path}.json', params={'auth': token}, json=body, timeout=120)
    if r.status_code != 200:
        sys.exit(f'Firebase {method} {path} gagal: {r.status_code} {r.text[:200]}')
    return r.json()


def upload_to_drive(files):
    r = requests.post(os.environ['APPS_SCRIPT_URL'], timeout=180, json={
        'token': os.environ['APPS_SCRIPT_TOKEN'],
        'files': [{'name': n, 'mime': m, 'b64': base64.b64encode(b).decode()} for n, m, b in files]})
    try:
        res = r.json()
    except Exception:
        sys.exit('Google Drive: jawapan tidak sah (' + r.text[:200] + ')')
    if not res.get('ok'):
        sys.exit('Google Drive gagal: ' + str(res.get('error')))
    sizes = {f['name']: f.get('size') for f in res.get('files', [])}
    for n, _, b in files:                                   # verify every file arrived complete
        if int(sizes.get(n) or -1) != len(b):
            sys.exit(f'Google Drive: saiz fail {n} tidak sepadan ({sizes.get(n)} vs {len(b)})')
    return res['files']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--month', help='YYYY-MM (default: previous month)')
    ap.add_argument('--force', action='store_true', help='run even if it is not the 1st / already done')
    ap.add_argument('--clear', action='store_true', help='clear the senarai semak after a verified backup')
    ap.add_argument('--allow-missing-photos', action='store_true', help='clear even if some pictures could not be put in the PDF')
    ap.add_argument('--out', default='backup/out', help='folder for the generated files')
    ap.add_argument('--data-file', help='test only: read this JSON instead of Firebase (never uploads or clears)')
    a = ap.parse_args()

    now = datetime.now(MYT)
    if not a.month and not a.force and not a.data_file and now.day != 1:
        print(f'Hari ini {now:%d/%m/%Y} bukan 1hb (waktu Malaysia). Tiada tindakan.'); return
    month = a.month or previous_month(now)
    print('Bulan laporan:', month, '-', month_label(month))

    token = None
    if a.data_file:
        data = json.load(open(a.data_file))
    else:
        token = login()
        if fb('GET', f'backups/{month}', token) and not a.force:
            print(f'Sandaran {month} sudah dibuat dan dikosongkan sebelum ini. Tiada tindakan.'); return
        data = {'layoutNames': fb('GET', 'layoutNames', token) or {}, 'layouts': fb('GET', 'layouts', token) or {}}

    xlsx, rows = make_xlsx(data, month)
    photos = {}
    if a.data_file:
        photos = data.get('photos') or {}
    else:
        for pid in sorted(photo_ids(data)):                  # pictures referenced by the data (rooms + defect records)
            try:
                v = fb('GET', f'photos/{pid}', token)
                if v: photos[pid] = v
            except SystemExit:
                print('  gambar tidak dapat dibaca:', pid)
    pdf = make_pdf(data, month, rows, photos)
    print(f'Gambar dalam PDF: {make_pdf.stats["shown"]} (tiada/rosak: {make_pdf.stats["missing"]}). Saiz PDF: {len(pdf) // 1024} KB.')
    os.makedirs(a.out, exist_ok=True)
    files = [(f'Laporan-{month}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', xlsx),
             (f'Laporan-{month}.pdf', 'application/pdf', pdf)]
    for n, _, b in files:
        open(os.path.join(a.out, n), 'wb').write(b)
    print(f'Dijana: {len(rows["kel"])} barang, {len(rows["ker"])} kerosakan semasa, {len(rows["rec"])} rekod kerosakan.')
    if a.data_file:
        print('Mod ujian: tiada muat naik atau pengosongan.'); return

    saved = upload_to_drive(files)
    print('Disimpan ke Google Drive:', ', '.join(f['name'] for f in saved))

    if not a.clear:
        print('Pengosongan TIDAK dihidupkan: data tidak diubah.'); return
    if make_pdf.stats['missing'] and not a.allow_missing_photos:
        sys.exit(f'{make_pdf.stats["missing"]} gambar tidak dapat dimasukkan dalam PDF. Laporan sudah disimpan tetapi data TIDAK dikosongkan. '
                 'Semak gambar atau jalankan semula dengan ALLOW_MISSING_PHOTOS=true.')
    plan = plan_clear(data['layouts'])
    print(f'Mengosongkan senarai semak: {len(plan)} entri.')
    if plan:
        fb('PATCH', '', token, plan)
    fb('PUT', f'backups/{month}', token, {'at': datetime.now(MYT).isoformat(timespec='seconds'), 'cleared': len(plan), 'files': [f['name'] for f in saved]})
    print('Selesai. Bulan baharu bermula dengan senarai semak kosong.')


if __name__ == '__main__':
    main()
