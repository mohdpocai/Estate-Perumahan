#!/usr/bin/env python3
"""Self-test: runs monthly_backup.py against a fake Firebase + fake Google Drive receiver. Run: python backup/test_backup.py"""
import base64, json, os, subprocess, sys, threading, tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from clear_plan import plan_clear

DATA = {'layoutNames': {'lp2': 'LP2'}, 'layouts': {'lp2': {'elements': {
    'e_1': {'id': 'e_1', 'category': 'pekerja', 'name': 'Blok A', 'doors': [
        {'nama': 'Ali', 'checklist': {'almari': {'status': True, 'keadaan': 'rosak', 'tarikh': '2026-10-02'}},
         'defects': {'bumbungBocor': {'status': True, 'tindakan': 'proses', 'tarikh': '2026-10-05'},
                     'paipRosak': {'status': False, 'tindakan': 'selesai', 'tarikh': '2026-10-01', 'tarikhSelesai': '2026-10-09'}}},
        {'nama': '', 'checklist': {}, 'defects': {}}]}},
    'defectLog': {'Lx': {'label': 'Bumbung Bocor', 'building': 'Blok A', 'door': 'Pintu 1', 'tarikh': '2026-10-05', 'tindakan': 'proses', 'gambar': 'p2'}}}}}
import io as _io
from PIL import Image as _I
_b = _io.BytesIO(); _I.new('RGB', (800, 600), (200, 50, 50)).save(_b, 'JPEG')
PHOTOS = {'p1': 'data:image/jpeg;base64,' + base64.b64encode(_b.getvalue()).decode(), 'p2': 'data:image/jpeg;base64,' + base64.b64encode(_b.getvalue()).decode()}
DATA['layouts']['lp2']['elements']['e_1']['doors'][0]['checklist']['almari']['gambar'] = 'p1'
state = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(b)
    def body(self): return json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or 'null')
    def do_POST(self):
        b = self.body()
        if self.path.startswith('/auth'): return self.send({'idToken': 'T'})
        if self.path.startswith('/script'):
            state['script_calls'] = state.get('script_calls', 0) + 1
            if state.get('script_mode') == 'fail': return self.send({'ok': False, 'error': 'token salah'})
            files = [{'name': f['name'], 'id': 'x', 'size': len(base64.b64decode(f['b64'])) + (1 if state.get('script_mode') == 'short' else 0)} for f in b['files']]
            state['uploaded'] = {f['name']: base64.b64decode(f['b64']) for f in b['files']}
            return self.send({'ok': True, 'files': files})
    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/layoutNames.json': return self.send(DATA['layoutNames'])
        if p == '/layouts.json': return self.send(DATA['layouts'])
        if p.startswith('/photos/'): state.setdefault('photo_reads', []).append(p); return self.send(PHOTOS.get(p.split('/')[-1][:-5]))
        if p.startswith('/backups/'): return self.send(state.get('marker'))
        self.send(None, 404)
    def do_PATCH(self): state['patch'] = self.body(); self.send({})
    def do_PUT(self): state['marker'] = self.body(); self.send({})


srv = HTTPServer(('127.0.0.1', 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
ENV = dict(os.environ, FIREBASE_DB_URL=f'http://127.0.0.1:{port}', FIREBASE_AUTH_URL=f'http://127.0.0.1:{port}/auth', BACKUP_EMAIL='a@b.c', BACKUP_PASSWORD='x',
           APPS_SCRIPT_URL=f'http://127.0.0.1:{port}/script', APPS_SCRIPT_TOKEN='t')


def run(*args):
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, os.path.join(HERE, 'monthly_backup.py'), '--out', out, *args], env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, out


def ok(c, m):
    if not c: print('FAIL:', m); sys.exit(1)
    print('ok -', m)


# 1. not the 1st and no --month: does nothing
import datetime
code, out, _ = run()
if datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).day != 1:
    ok(code == 0 and 'bukan 1hb' in out and not state, 'not the 1st: nothing happens')

# 2. backup only (clear off): uploaded, nothing changed
state.clear(); code, out, _ = run('--month', '2026-10')
ok(code == 0 and set(state['uploaded']) == {'Laporan-2026-10.xlsx', 'Laporan-2026-10.pdf'}, 'report uploaded to Drive (xlsx + pdf)')
ok(state['uploaded']['Laporan-2026-10.pdf'][:4] == b'%PDF' and state['uploaded']['Laporan-2026-10.xlsx'][:2] == b'PK', 'files are a real PDF and a real xlsx')
ok('patch' not in state and 'marker' not in state and 'TIDAK dihidupkan' in out, 'clear off: database untouched, no marker')

import re
pdf = state['uploaded']['Laporan-2026-10.pdf']
ok(sorted(state['photo_reads']) == ['/photos/p1.json', '/photos/p2.json'], 'the script downloaded the pictures used by the data: ' + ','.join(state['photo_reads']))
try:
    from pypdf import PdfReader
    n = sum(len(pg.images) for pg in PdfReader(_io.BytesIO(pdf)).pages)
    ok(n == 2, f'the PDF contains the 2 pictures ({n} found)')
    txt = ' '.join(pg.extract_text() for pg in PdfReader(_io.BytesIO(pdf)).pages)
    ok('Senarai penghuni' in txt and 'Ali' in txt and 'Rekod kerosakan kekal' in txt, 'the PDF has the resident list, room records and permanent defect records')
except ImportError:
    ok(pdf.count(b'/Subtype /Image') >= 2, 'the PDF contains the pictures')

# 3. Drive fails: nothing cleared
for mode in ('fail', 'short'):
    state.clear(); state['script_mode'] = mode; code, out, _ = run('--month', '2026-10', '--clear')
    ok(code != 0 and 'patch' not in state and 'marker' not in state, f'Drive "{mode}": exit with error, NOTHING cleared')

# 3b. a picture that cannot be read: report saved, but nothing cleared
saved_photos = dict(PHOTOS); PHOTOS.pop('p1')
state.clear(); code, out, _ = run('--month', '2026-10', '--clear')
ok(code != 0 and 'patch' not in state and 'marker' not in state and 'uploaded' in state, 'missing picture: report uploaded, NOTHING cleared, exit with error')
state.clear(); code, out, _ = run('--month', '2026-10', '--clear', '--allow-missing-photos')
ok(code == 0 and 'patch' in state, '--allow-missing-photos overrides it')
PHOTOS.update(saved_photos)

# 4. normal run with clear
state.clear(); code, out, _ = run('--month', '2026-10', '--clear')
exp = plan_clear(DATA['layouts'])
ok(code == 0 and state['patch'] == exp, 'clear: PATCH equals the plan: ' + json.dumps(exp))
ok(exp == {'layouts/lp2/elements/e_1/doors/0/checklist': None, 'layouts/lp2/elements/e_1/doors/0/defects/paipRosak': None}, 'clears kelengkapan + Selesai defect; keeps the open defect, names, buildings')
ok(state['marker']['cleared'] == 2 and state['marker']['files'] == ['Laporan-2026-10.xlsx', 'Laporan-2026-10.pdf'], 'marker backups/2026-10 written')

# 5. re-run: already done -> skipped, no double clear
state.pop('patch'); state.pop('uploaded'); n = state.get('script_calls', 0)
code, out, _ = run('--month', '2026-10', '--clear')
ok(code == 0 and 'sudah dibuat' in out and 'patch' not in state and state.get('script_calls') == n, 're-run for the same month does nothing (protects new data)')
print('BACKUP TESTS PASSED')
