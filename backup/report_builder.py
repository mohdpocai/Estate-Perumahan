"""Build the monthly Excel + PDF report from the Firebase data (layoutNames + layouts)."""
import io
from datetime import datetime

ITEMS = [('katilSingle', 'Katil Single'), ('tilamSingle', 'Tilam Single'), ('katilQueen', 'Katil Queen'),
         ('tilamQueen', 'Tilam Queen'), ('dapurGas', 'Dapur Gas'), ('almari', 'Almari'), ('meatSafe', 'Meat Safe')]
DEFECTS = [('bumbungBocor', 'Bumbung Bocor'), ('paipRosak', 'Paip Bocor / Rosak'), ('wayarTerdedah', 'Wayar Elektrik Terdedah'),
           ('tingkapRosak', 'Tingkap Pecah / Rosak'), ('pintuRosak', 'Pintu / Kunci Rosak'), ('lantaiRosak', 'Lantai Retak / Rosak'),
           ('dindingRetak', 'Dinding Retak'), ('longkangTersumbat', 'Longkang Tersumbat')]
ROAD = [('lubangJalan', 'Lubang / Jalan Berlubang'), ('lampuJalan', 'Lampu Jalan Rosak'), ('paritTersumbat', 'Parit Tersumbat'),
        ('jalanRetak', 'Permukaan Jalan Retak / Runtuh'), ('papanTanda', 'Papan Tanda Rosak'), ('bahuJalan', 'Bahu Jalan Terhakis')]
CATEGORY = {'pekerja': 'Rumah Pekerja', 'office': 'Pejabat (Office)', 'kedai': 'Kedai / Mart', 'dewan': 'Dewan Serbaguna',
            'store': 'Store / Depo', 'surau': 'Surau', 'jalan': 'Jalan Utama'}
KEADAAN = {'baik': 'Bagus', 'ganti': 'Perlu Diganti / Rosak', 'rosak': 'Rosak'}
STATUS = {'baru': 'Baharu', 'proses': 'Dalam Tindakan', 'selesai': 'Selesai'}
BULAN = ['Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun', 'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember']


def month_label(month):            # '2026-10' -> 'Oktober 2026'
    y, m = month.split('-')
    return f'{BULAN[int(m) - 1]} {y}'


def as_list(v):
    """Firebase returns arrays as list or as {index: value}."""
    if v is None: return []
    if isinstance(v, list): return [x or {} for x in v]
    if isinstance(v, dict): return [v[k] or {} for k in sorted(v, key=lambda k: int(k) if str(k).isdigit() else 0)]
    return []


def def_status(e):
    t = (e or {}).get('tindakan')
    return t if t in STATUS else 'baru'


def is_open(e):
    return bool(e and e.get('status') and def_status(e) != 'selesai')


def elements_of(layout):
    els = (layout or {}).get('elements') or {}
    return sorted(els.values(), key=lambda e: (str(e.get('name') or '').lower(), str(e.get('id') or '')))


def natural(s):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(s))]


def collect(data, month):
    """Flatten everything into row lists. Returns dict of lists."""
    names = data.get('layoutNames') or {}
    layouts = data.get('layouts') or {}
    out = {'summary': [], 'kel': [], 'ker': [], 'rec': []}
    for lid in sorted(layouts, key=lambda k: natural(names.get(k, k))):
        lname = names.get(lid, lid)
        layout = layouts[lid] or {}
        s = dict(layout=lname, bangunan=0, bilik=0, berpenghuni=0, ditanda=0, rosak=0, ganti=0, terbuka=0, selesai=0)
        for el in sorted(elements_of(layout), key=lambda e: natural(e.get('name') or '')):
            bname = el.get('name') or CATEGORY.get(el.get('category'), 'Elemen')
            s['bangunan'] += 1
            if el.get('category') == 'pekerja':
                for i, door in enumerate(as_list(el.get('doors'))):
                    dname = (door.get('label') or '').strip() or f'Pintu {i + 1}'
                    nama = (door.get('nama') or '').strip()
                    s['bilik'] += 1
                    s['berpenghuni'] += 1 if nama else 0
                    for key, label in ITEMS:
                        e = (door.get('checklist') or {}).get(key)
                        if e and e.get('status'):
                            k = e.get('keadaan') or 'baik'
                            s['ditanda'] += 1; s['rosak'] += k == 'rosak'; s['ganti'] += k == 'ganti'
                            out['kel'].append([lname, bname, dname, nama, label, KEADAAN.get(k, 'Bagus'), e.get('tarikh') or ''])
                    for key, label in DEFECTS:
                        e = (door.get('defects') or {}).get(key)
                        if e and e.get('status'):
                            s['terbuka'] += is_open(e)
                            out['ker'].append([lname, bname, dname, nama, label, STATUS[def_status(e)], e.get('tarikh') or '',
                                               e.get('catatan') or '', e.get('pihak') or '', e.get('tarikhSelesai') or ''])
            else:
                for key, label in (ROAD if el.get('category') == 'jalan' else DEFECTS):
                    e = (el.get('defects') or {}).get(key)
                    if e and e.get('status'):
                        s['terbuka'] += is_open(e)
                        out['ker'].append([lname, bname, '', '', label, STATUS[def_status(e)], e.get('tarikh') or '',
                                           e.get('catatan') or '', e.get('pihak') or '', e.get('tarikhSelesai') or ''])
        for rid, r in sorted((layout.get('defectLog') or {}).items(), key=lambda kv: (kv[1] or {}).get('tarikh') or ''):
            r = r or {}
            stat = def_status(r)
            dates = [r.get('tarikh'), r.get('tarikhTindakan'), r.get('tarikhSelesai'), (r.get('dikemaskini') or '')[:10]]
            if stat != 'selesai' or any((d or '').startswith(month) for d in dates):
                s['selesai'] += (stat == 'selesai' and (r.get('tarikhSelesai') or '').startswith(month))
                out['rec'].append([lname, r.get('building') or '', r.get('door') or '', r.get('penghuni') or '', r.get('label') or '',
                                   STATUS[stat], r.get('tarikh') or '', r.get('catatan') or '', r.get('pihak') or '',
                                   r.get('tarikhSelesai') or ''])
        out['summary'].append(s)
    return out


H_SUM = ['Layout', 'Bangunan', 'Bilik', 'Bilik berpenghuni', 'Barang direkod', 'Rosak', 'Perlu diganti / rosak',
         'Kerosakan belum selesai', 'Kerosakan selesai bulan ini']
H_KEL = ['Layout', 'Bangunan', 'Pintu / Bilik', 'Penghuni', 'Barang', 'Keadaan', 'Tarikh']
H_KER = ['Layout', 'Bangunan', 'Pintu / Bilik', 'Penghuni', 'Kerosakan', 'Status', 'Tarikh dilaporkan', 'Catatan', 'Pihak bertindak', 'Tarikh selesai']


def summary_rows(rows):
    return [[s['layout'], s['bangunan'], s['bilik'], s['berpenghuni'], s['ditanda'], s['rosak'], s['ganti'], s['terbuka'], s['selesai']] for s in rows]


def make_xlsx(data, month):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    c = collect(data, month)
    wb = Workbook(); wb.remove(wb.active)
    H_BRG = ['Layout', 'Barang', 'Direkod', 'Bagus', 'Rosak', 'Perlu diganti / rosak', 'Perlu tindakan']
    H_BLD = ['Layout', 'Bangunan', 'Barang', 'Direkod', 'Bagus', 'Rosak', 'Perlu diganti / rosak', 'Perlu tindakan']
    from collections import defaultdict
    by_item = defaultdict(lambda: [0, 0, 0, 0]); by_bld = defaultdict(lambda: [0, 0, 0, 0])
    inv = {v: k for k, v in KEADAAN.items()}
    for lay, bld, _d, _n, barang, keadaan, _t in c['kel']:
        i = {'baik': 1, 'rosak': 2, 'ganti': 3}[inv[keadaan]]
        for tbl, key in ((by_item, (lay, barang)), (by_bld, (lay, bld, barang))):
            tbl[key][0] += 1; tbl[key][i] += 1
    labels = [l for _, l in ITEMS]
    brg_rows, bld_rows = [], []
    for s_ in c['summary']:
        lay = s_['layout']; tot = [0, 0, 0, 0]
        for l in labels:
            v = by_item[(lay, l)]; tot = [a + b for a, b in zip(tot, v)]
            brg_rows.append([lay, l, v[0], v[1], v[2], v[3], v[2] + v[3]])
        brg_rows.append([lay, 'JUMLAH', tot[0], tot[1], tot[2], tot[3], tot[2] + tot[3]])
        blds = sorted({k[1] for k in by_bld if k[0] == lay}, key=natural)
        for b in blds:
            for l in labels:
                v = by_bld.get((lay, b, l))
                if v: bld_rows.append([lay, b, l, v[0], v[1], v[2], v[3], v[2] + v[3]])
    sheets = [('Ringkasan', H_SUM, summary_rows(c['summary'])), ('Ringkasan barang', H_BRG, brg_rows),
              ('Barang ikut bangunan', H_BLD, bld_rows), ('Kelengkapan', H_KEL, c['kel']),
              ('Kerosakan semasa', H_KER, c['ker']), ('Rekod kerosakan', H_KER, c['rec'])]
    for title, head, rows in sheets:
        ws = wb.create_sheet(title)
        ws.append([f'Laporan bulanan {month_label(month)} - {title}']); ws['A1'].font = Font(bold=True, size=13)
        ws.append(head)
        for cell in ws[2]:
            cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='0B2447')
            cell.alignment = Alignment(wrap_text=True, vertical='center')
        for r in rows:
            ws.append(r)
            if len(r) > 1 and r[1] == 'JUMLAH':
                for cell in ws[ws.max_row]: cell.font = Font(bold=True)
        if not rows: ws.append(['Tiada rekod'])
        ws.freeze_panes = 'A3'
        for i in range(1, len(head) + 1):
            width = max(len(str(head[i - 1])), *[len(str(r[i - 1])) for r in rows if len(r) >= i]) if rows else len(head[i - 1])
            ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 45)
        if rows: ws.auto_filter.ref = f'A2:{get_column_letter(len(head))}{len(rows) + 2}'
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue(), c


def photo_ids(data):
    """Every photo id referenced by the data (rooms and defect records)."""
    ids = set()
    def add(e):
        for k in ('gambar', 'gambarTindakan'):
            g = (e or {}).get(k)
            if g and not str(g).startswith('data:'): ids.add(g)
    for layout in (data.get('layouts') or {}).values():
        for el in ((layout or {}).get('elements') or {}).values():
            for d in as_list(el.get('doors')):
                for e in list((d.get('checklist') or {}).values()) + list((d.get('defects') or {}).values()): add(e)
            for e in (el.get('defects') or {}).values(): add(e)
        for r in ((layout or {}).get('defectLog') or {}).values(): add(r)
    return ids


def rooms(data, month, rec_ids):
    """Structured room records for the PDF: [(layout, building, door, nama, jumlah, kel[], ker[])]."""
    names = data.get('layoutNames') or {}
    out = []
    for lid in sorted(data.get('layouts') or {}, key=lambda k: natural(names.get(k, k))):
        lname = names.get(lid, lid)
        for el in sorted(elements_of(data['layouts'][lid]), key=lambda e: natural(e.get('name') or '')):
            bname = el.get('name') or CATEGORY.get(el.get('category'), 'Elemen')
            if el.get('category') == 'pekerja':
                for i, door in enumerate(as_list(el.get('doors'))):
                    dname = (door.get('label') or '').strip() or f'Pintu {i + 1}'
                    kel = [(label, door['checklist'][key]) for key, label in ITEMS if (door.get('checklist') or {}).get(key, {}).get('status')]
                    ker = [(label, door['defects'][key]) for key, label in DEFECTS if (door.get('defects') or {}).get(key, {}).get('status')]
                    out.append((lname, bname, dname, (door.get('nama') or '').strip(), door.get('jumlah') or '', kel, ker))
            else:
                lst = ROAD if el.get('category') == 'jalan' else DEFECTS
                ker = [(label, el['defects'][key]) for key, label in lst if (el.get('defects') or {}).get(key, {}).get('status')]
                if ker: out.append((lname, bname, '', '', '', [], ker))
    return out


def make_pdf(data, month, c=None, photos=None):
    """Full backup PDF: summary, every resident, every room record, permanent defect records, all with pictures."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image, PageBreak
    import base64, os
    from PIL import Image as PILImage
    photos = photos or {}
    c = c or collect(data, month)
    base = '/usr/share/fonts/truetype/dejavu/'
    if os.path.exists(base + 'DejaVuSans.ttf'):
        pdfmetrics.registerFont(TTFont('F', base + 'DejaVuSans.ttf')); pdfmetrics.registerFont(TTFont('FB', base + 'DejaVuSans-Bold.ttf'))
        f, fb = 'F', 'FB'
    else:
        f, fb = 'Helvetica', 'Helvetica-Bold'
    st = ParagraphStyle('s', fontName=f, fontSize=8, leading=10)
    sc = ParagraphStyle('c', fontName=f, fontSize=7, leading=9, textColor=colors.HexColor('#475569'))
    sh = ParagraphStyle('h', fontName=fb, fontSize=8, leading=10, textColor=colors.white)
    h1 = ParagraphStyle('t', fontName=fb, fontSize=16, leading=20, spaceAfter=6)
    h2 = ParagraphStyle('t2', fontName=fb, fontSize=11, leading=14, spaceBefore=12, spaceAfter=4)
    h3 = ParagraphStyle('t3', fontName=fb, fontSize=9.5, leading=12, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor('#0B2447'))
    note = ParagraphStyle('n', fontName=f, fontSize=8, textColor=colors.grey)
    esc = lambda x: str(x if x is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    W = landscape(A4)[0] - 24 * mm

    def table(head, rows, fr=None):
        if not rows: return Paragraph('Tiada rekod.', st)
        d = [[Paragraph(esc(x), sh) for x in head]] + [[Paragraph(esc(x), st) for x in r] for r in rows]
        t = Table(d, colWidths=[W * x for x in fr] if fr else None, repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B2447')), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#C7D2E0')),
                               ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F6FA')]), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        return t

    stats = {'shown': 0, 'missing': 0}
    cache = {}
    def img(pid):
        if pid in cache: return cache[pid]
        uri = photos.get(pid)
        if not uri:
            cache[pid] = None; stats['missing'] += 1; return None
        try:
            raw = base64.b64decode(uri.split(',', 1)[1] if uri.startswith('data:') else uri)
            im = PILImage.open(io.BytesIO(raw)).convert('RGB'); im.thumbnail((900, 900))
            b = io.BytesIO(); im.save(b, 'JPEG', quality=72); b.seek(0)
            w, h = im.size; k = min(62 * mm / w, 46 * mm / h)
            cache[pid] = Image(b, width=w * k, height=h * k); stats['shown'] += 1
        except Exception:
            cache[pid] = None; stats['missing'] += 1
        return cache[pid]

    def gallery(items):
        """items: [(caption, photo id)] -> table of pictures, 4 per row."""
        cells = []
        for cap, pid in items:
            im = img(pid)
            cells.append([im, Paragraph(esc(cap), sc)] if im else [Paragraph('(gambar tiada)', sc), Paragraph(esc(cap), sc)])
        if not cells: return None
        rows = []
        for i in range(0, len(cells), 4):
            chunk = cells[i:i + 4]
            rows.append([x for x in chunk] + [''] * (4 - len(chunk)))
        t = Table(rows, colWidths=[W / 4] * 4)
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        return t

    def pics_of(e, label):
        out = []
        if e.get('gambar'): out.append((label + ' - bukti', e['gambar']))
        if e.get('gambarTindakan'): out.append((label + ' - bukti tindakan', e['gambarTindakan']))
        return out

    rec_ids = {r for r in (data_log_ids(data, month))}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f'Laporan Bulanan {month_label(month)}')
    el = [Paragraph(f'Laporan Bulanan - {month_label(month)}', h1),
          Paragraph('Pengurusan Rumah Pekerja. Sandaran penuh data dan gambar. Dijana ' + datetime.now().strftime('%d/%m/%Y %H:%M') + '.', note),
          Paragraph('Ringkasan', h2), table(H_SUM, summary_rows(c['summary']))]

    R = rooms(data, month, rec_ids)
    res_rows = [[a, b, d, n or '-', j] for a, b, d, n, j, _, _ in R if d]
    el += [Paragraph('Senarai penghuni (semua bilik)', h2), table(['Layout', 'Bangunan', 'Pintu / Bilik', 'Penghuni', 'Jumlah'], res_rows, (.15, .25, .2, .3, .1))]

    el += [PageBreak(), Paragraph('Rekod bilik dan bangunan', h2)]
    any_room = False
    for lname, bname, dname, nama, jumlah, kel, ker in R:
        if not kel and not ker: continue
        any_room = True
        title = f'{lname} • {bname}' + (f' • {dname}' if dname else '') + (f'  ({nama}' + (f', {jumlah} orang' if jumlah else '') + ')' if nama else '')
        parts = [Paragraph(esc(title), h3)]
        if kel:
            parts.append(table(['Barang', 'Keadaan', 'Tarikh'], [[l, KEADAAN.get(e.get('keadaan') or 'baik', 'Bagus'), e.get('tarikh') or ''] for l, e in kel], (.4, .3, .3)))
            g = gallery([p for l, e in kel for p in pics_of(e, l)])
            if g: parts.append(g)
        if ker:
            parts.append(table(['Kerosakan', 'Status', 'Tarikh', 'Catatan', 'Pihak bertindak', 'Tarikh selesai'],
                               [[l, STATUS[def_status(e)], e.get('tarikh') or '', e.get('catatan') or '', e.get('pihak') or '', e.get('tarikhSelesai') or ''] for l, e in ker],
                               (.2, .12, .1, .3, .16, .12)))
            g = gallery([p for l, e in ker if (e.get('logId') or '') not in rec_ids for p in pics_of(e, l)])
            if g: parts.append(g)
            if any((e.get('logId') or '') in rec_ids and pics_of(e, l) for l, e in ker):
                parts.append(Paragraph('Gambar kerosakan di bilik ini ada dalam bahagian Rekod kerosakan kekal di bawah.', sc))
        el.append(KeepTogether(parts))
    if not any_room: el.append(Paragraph('Tiada rekod kelengkapan atau kerosakan pada bilik/bangunan.', st))

    el += [PageBreak(), Paragraph(f'Rekod kerosakan kekal ({month_label(month)} dan yang belum selesai)', h2)]
    names = data.get('layoutNames') or {}
    any_rec = False
    for lid in sorted(data.get('layouts') or {}, key=lambda k: natural(names.get(k, k))):
        for rid, r in sorted((((data['layouts'][lid] or {}).get('defectLog')) or {}).items(), key=lambda kv: ((kv[1] or {}).get('tarikh') or '', kv[0])):
            if rid not in rec_ids: continue
            r = r or {}; any_rec = True
            place = ' • '.join(x for x in (names.get(lid, lid), r.get('building'), r.get('door')) if x) + (f' ({r["penghuni"]})' if r.get('penghuni') else '')
            parts = [Paragraph(esc(place + ' - ' + (r.get('label') or '')), h3),
                     table(['Status', 'Tarikh dilaporkan', 'Catatan', 'Pihak bertindak', 'Catatan tindakan', 'Tarikh selesai'],
                           [[STATUS[def_status(r)], r.get('tarikh') or '', r.get('catatan') or '', r.get('pihak') or '', r.get('catatanTindakan') or '', r.get('tarikhSelesai') or '']],
                           (.12, .12, .28, .16, .2, .12))]
            g = gallery(pics_of(r, r.get('label') or 'Kerosakan'))
            if g: parts.append(g)
            el.append(KeepTogether(parts))
    if not any_rec: el.append(Paragraph('Tiada rekod.', st))
    doc.build(el)
    make_pdf.stats = stats
    return buf.getvalue()


def data_log_ids(data, month):
    """Ids of the defect-log records that belong in this month's report (same rule as the Excel sheet)."""
    ids = set()
    for layout in (data.get('layouts') or {}).values():
        for rid, r in (((layout or {}).get('defectLog')) or {}).items():
            r = r or {}
            dates = [r.get('tarikh'), r.get('tarikhTindakan'), r.get('tarikhSelesai'), (r.get('dikemaskini') or '')[:10]]
            if def_status(r) != 'selesai' or any((d or '').startswith(month) for d in dates): ids.add(rid)
    return ids
