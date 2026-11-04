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
KEADAAN = {'baik': 'Baik', 'ganti': 'Perlu Diganti', 'rosak': 'Rosak'}
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
                            out['kel'].append([lname, bname, dname, nama, label, KEADAAN.get(k, 'Baik'), e.get('tarikh') or ''])
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


H_SUM = ['Layout', 'Bangunan', 'Bilik', 'Bilik berpenghuni', 'Barang direkod', 'Rosak', 'Perlu diganti',
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
    sheets = [('Ringkasan', H_SUM, summary_rows(c['summary'])), ('Kelengkapan', H_KEL, c['kel']),
              ('Kerosakan semasa', H_KER, c['ker']), ('Rekod kerosakan', H_KER, c['rec'])]
    for title, head, rows in sheets:
        ws = wb.create_sheet(title)
        ws.append([f'Laporan bulanan {month_label(month)} - {title}']); ws['A1'].font = Font(bold=True, size=13)
        ws.append(head)
        for cell in ws[2]:
            cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='0B2447')
            cell.alignment = Alignment(wrap_text=True, vertical='center')
        for r in rows: ws.append(r)
        if not rows: ws.append(['Tiada rekod'])
        ws.freeze_panes = 'A3'
        for i in range(1, len(head) + 1):
            width = max(len(str(head[i - 1])), *[len(str(r[i - 1])) for r in rows if len(r) >= i]) if rows else len(head[i - 1])
            ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 45)
        if rows: ws.auto_filter.ref = f'A2:{get_column_letter(len(head))}{len(rows) + 2}'
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue(), c


def make_pdf(data, month, c=None):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    c = c or collect(data, month)
    import os
    base = '/usr/share/fonts/truetype/dejavu/'
    if os.path.exists(base + 'DejaVuSans.ttf'):
        pdfmetrics.registerFont(TTFont('F', base + 'DejaVuSans.ttf')); pdfmetrics.registerFont(TTFont('FB', base + 'DejaVuSans-Bold.ttf'))
        f, fb = 'F', 'FB'
    else:
        f, fb = 'Helvetica', 'Helvetica-Bold'
    st = ParagraphStyle('s', fontName=f, fontSize=8, leading=10)
    sh = ParagraphStyle('h', fontName=fb, fontSize=8, leading=10, textColor=colors.white)
    h1 = ParagraphStyle('t', fontName=fb, fontSize=16, leading=20, spaceAfter=6)
    h2 = ParagraphStyle('t2', fontName=fb, fontSize=11, spaceBefore=10, spaceAfter=4)
    note = ParagraphStyle('n', fontName=f, fontSize=8, textColor=colors.grey)

    def table(head, rows, widths=None):
        if not rows: return Paragraph('Tiada rekod.', st)
        data_ = [[Paragraph(str(x), sh) for x in head]] + [[Paragraph(str(x).replace('&', '&amp;').replace('<', '&lt;'), st) for x in r] for r in rows]
        t = Table(data_, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B2447')), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#C7D2E0')),
                               ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F6FA')]), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        return t

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f'Laporan Bulanan {month_label(month)}')
    W = landscape(A4)[0] - 24 * mm
    el = [Paragraph(f'Laporan Bulanan - {month_label(month)}', h1),
          Paragraph('Pengurusan Rumah Pekerja. Dijana ' + datetime.now().strftime('%d/%m/%Y %H:%M') + '. Fail Excel mengandungi data penuh.', note),
          Paragraph('Ringkasan', h2), table(H_SUM, summary_rows(c['summary']))]
    bad = [r for r in c['kel'] if r[5] != 'Baik']
    ok_n = len(c['kel']) - len(bad)
    el += [Paragraph('Kelengkapan rosak / perlu diganti', h2), Paragraph(f'{ok_n} barang direkod dalam keadaan baik.', note),
           table(H_KEL, bad, [W * x for x in (.1, .16, .14, .18, .16, .14, .12)])]
    el += [Paragraph('Senarai semak kerosakan semasa', h2),
           table(H_KER, c['ker'], [W * x for x in (.06, .1, .09, .1, .13, .08, .08, .18, .1, .08)])]
    el += [Paragraph(f'Rekod kerosakan ({month_label(month)} dan yang belum selesai)', h2),
           table(H_KER, c['rec'], [W * x for x in (.06, .1, .09, .1, .13, .08, .08, .18, .1, .08)])]
    doc.build(el)
    return buf.getvalue()
