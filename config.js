/* Shared settings and the room report (used by index.html and bilik.html). */

/* Nombor WhatsApp penyelia (dengan kod negara, cth '60123456789' atau '0123456789').
   Kosongkan ('') = pekerja pilih sendiri penerima/kumpulan setiap kali. */
const WA_NUMBER = '';

function waNumber() {
  let n = String(WA_NUMBER || '').replace(/\D/g, '');
  if (n.startsWith('0')) n = '60' + n.slice(1);
  return n;
}

/* One report for one room: Rekod Kelengkapan + Senarai Semak Kerosakan (ticked items only), with picture links. */
function buildRoomReport(item, door, di, layoutName) {
  const label = door.label && door.label.trim() ? door.label.trim() : 'Pintu ' + (di + 1);
  const who = door.nama && door.nama.trim() ? ' (' + door.nama.trim() + (door.jumlah ? ', ' + door.jumlah + ' orang' : '') + ')' : '';
  const KEADAAN = { baik: 'Baik', ganti: 'Perlu Diganti', rosak: 'Rosak' };
  const checklist = door.checklist || {}, defects = door.defects || {};
  const photoIds = [];
  const pics = e => [e.gambar, e.gambarTindakan].filter(g => g && !String(g).startsWith('data:')).map(g => {
    photoIds.push(g);
    return '\n   📷 ' + new URL('gambar.html?p=' + encodeURIComponent(g), location.href).href;
  }).join('');
  const kel = ITEMS_CHECKLIST.filter(k => checklist[k.key] && checklist[k.key].status).map(k => {
    const e = checklist[k.key];
    return '• ' + k.label + ' - ' + (KEADAAN[e.keadaan || 'baik'] || 'Baik') + (e.tarikh ? ' (' + e.tarikh + ')' : '') + pics(e);
  });
  const ker = DEFECT_CHECKLIST.filter(k => defects[k.key] && defects[k.key].status).map(k => {
    const e = defects[k.key];
    return '• ' + k.label + ' - ' + DEF_STATUS[defStatus(e)].l + (e.tarikh ? ' (' + e.tarikh + ')' : '') +
      (e.catatan ? '\n   Catatan: ' + e.catatan : '') + (e.pihak ? '\n   Pihak bertindak: ' + e.pihak : '') + pics(e);
  });
  const text = ['*LAPORAN BILIK* - ' + (layoutName || ''),
    '📍 *' + (item.name || 'Bangunan') + ' • ' + label + '*' + who,
    '📅 ' + todayStr(), '',
    '🛏️ *Rekod Kelengkapan*', kel.length ? kel.join('\n') : 'Tiada barang direkod', '',
    '⚠️ *Senarai Semak Kerosakan*', ker.length ? ker.join('\n') : 'Tiada kerosakan'].join('\n');
  return { text, count: kel.length + ker.length, photoIds };
}

function openWhatsApp(text) {
  window.open('https://wa.me/' + waNumber() + '?text=' + encodeURIComponent(text.slice(0, 3500)), '_blank');
}
