/* Shared core for kerosakan.html and ringkasan.html: Firebase, login, layouts, photos, defect records. */
function toggleNavDd(ev) { ev.stopPropagation(); document.getElementById('navDdMenu').classList.toggle('open'); }
document.addEventListener('click', () => { const m = document.getElementById('navDdMenu'); if (m) m.classList.remove('open'); });
const MAIN_URL = 'index.html';
document.querySelectorAll('a[data-main]').forEach(a => { a.href = MAIN_URL + a.getAttribute('data-main'); });
    const firebaseConfig = {
      apiKey: "AIzaSyCmc1cccrzh29H6SzWPt84a8rK1x747jU8",
      authDomain: "estate-perumahan.firebaseapp.com",
      databaseURL: "https://estate-perumahan-default-rtdb.asia-southeast1.firebasedatabase.app",
      projectId: "estate-perumahan",
      messagingSenderId: "821767387974",
      appId: "1:821767387974:web:e933ff358659c498994347"
    };

let elements = [];
let db = null;
let dbReady = false;
let lastSaved = {};
let photoCache = {};
let layouts = {};
let currentLayoutId = localStorage.getItem('currentLayoutId_v1') || '';
let listeningLayoutId = null;
let searchQuery = '';
let cameraStream = null;
let activeCamTarget = { houseId: null, doorIndex: null, listKey: null, key: null };

    const ITEMS_CHECKLIST = [
      { key: 'katilSingle', label: 'Katil Single' },
      { key: 'tilamSingle', label: 'Tilam Single' },
      { key: 'katilQueen', label: 'Katil Queen' },
      { key: 'tilamQueen', label: 'Tilam Queen' },
      { key: 'dapurGas', label: 'Dapur Gas' },
      { key: 'almari', label: 'Almari' },
      { key: 'meatSafe', label: 'Meat Safe' }
    ];

    const DEFECT_CHECKLIST = [
      { key: 'bumbungBocor', label: 'Bumbung Bocor' },
      { key: 'paipRosak', label: 'Paip Bocor / Rosak' },
      { key: 'wayarTerdedah', label: 'Wayar Elektrik Terdedah' },
      { key: 'tingkapRosak', label: 'Tingkap Pecah / Rosak' },
      { key: 'pintuRosak', label: 'Pintu / Kunci Rosak' },
      { key: 'lantaiRosak', label: 'Lantai Retak / Rosak' },
      { key: 'dindingRetak', label: 'Dinding Retak' },
      { key: 'longkangTersumbat', label: 'Longkang Tersumbat' }
    ];

    const CATEGORY_CONFIG = {
      pekerja: { label: 'Rumah Pekerja', icon: '🏠', colorClass: 'type-pekerja', defaultW: 140, defaultH: 80 },
      office:  { label: 'Pejabat (Office)', icon: '🏢', colorClass: 'type-office', defaultW: 160, defaultH: 100 },
      kedai:   { label: 'Kedai / Mart', icon: '🏪', colorClass: 'type-kedai', defaultW: 140, defaultH: 80 },
      dewan:   { label: 'Dewan Serbaguna', icon: '🏛️', colorClass: 'type-dewan', defaultW: 200, defaultH: 120 },
      store:   { label: 'Store / Depo', icon: '📦', colorClass: 'type-store', defaultW: 160, defaultH: 100 },
      surau:   { label: 'Surau', icon: '🕌', colorClass: 'type-surau', defaultW: 160, defaultH: 100 },
      jalan:   { label: 'Jalan Utama', icon: '🛣️', colorClass: 'type-road', defaultW: 300, defaultH: 40 }
    };

    function escapeHTML(str) {
      return String(str).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

function createDefaultDoor() {
  return { label: '', nama: '', jumlah: '1', checklist: {}, defects: {} };
}

    /* ===================== DEFECT RECORDS (permanent log) =====================
       Every defect report is mirrored into layouts/<layout>/defectLog/<id>. Records are never removed
       automatically (unticking, deleting a door/building, completing or repeating a defect all keep them);
       they are deleted only with the Padam rekod button on the Kerosakan page. */
    let defectLog = {};
    let lastLogJson = {};
    let logLoaded = false;
    let listeningLogLayoutId = null;

    function stableJson(o) { return JSON.stringify(Object.keys(o).sort().reduce((a, k) => { a[k] = o[k]; return a; }, {})); }
    function recordCore(r) { const c = Object.assign({}, r); delete c.dicipta; delete c.dikemaskini; return c; }
    function legacyLogId(item, di, key) { return 'L' + item.id + '_' + (di + 1) + '_' + key; }
    function entryLogId(item, di, key, e) { return e.logId || legacyLogId(item, di, key); }

    function defectSnapshot(d) {
      const { item, door, di, chk, e } = d;
      const photo = g => (g && !String(g).startsWith('data:')) ? g : '';
      return {
        id: entryLogId(item, di, chk.key, e), itemId: item.id, di: di, key: chk.key, label: chk.label,
        building: item.name || (CATEGORY_CONFIG[item.category] || {}).label || 'Elemen',
        category: item.category || '',
        door: door ? (door.label && door.label.trim() ? door.label.trim() : 'Pintu ' + (di + 1)) : '',
        penghuni: door && door.nama ? String(door.nama).trim() : '',
        tarikh: e.tarikh || '', tindakan: defStatus(e),
        catatan: e.catatan || '', pihak: e.pihak || '', catatanTindakan: e.catatanTindakan || '',
        tarikhTindakan: e.tarikhTindakan || '', tarikhSelesai: e.tarikhSelesai || '',
        gambar: photo(e.gambar), gambarTindakan: photo(e.gambarTindakan)
      };
    }

    function ensureLogIds() {
      allDefects().forEach(d => {
        if (d.e.logId) return;
        const legacy = legacyLogId(d.item, d.di, d.chk.key);
        d.e.logId = defectLog[legacy] ? 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6) : legacy;
      });
    }

    function defectLogUpdates() {
      const out = {};
      const base = 'layouts/' + currentLayoutId + '/defectLog/';
      const now = new Date().toISOString();
      allDefects().forEach(d => {
        const snap = defectSnapshot(d);
        const json = stableJson(snap);
        if (lastLogJson[snap.id] === json) return;
        const old = defectLog[snap.id];
        out[base + snap.id] = Object.assign({}, snap, { dicipta: (old && old.dicipta) || now, dikemaskini: now });
        lastLogJson[snap.id] = json;
      });
      return out;
    }

    function backfillLog() {
      if (logLoaded && allDefects().some(d => !d.e.logId)) saveToStorage();
    }

    function attachLogListener() {
      if (listeningLogLayoutId && db) db.ref('layouts/' + listeningLogLayoutId + '/defectLog').off();
      listeningLogLayoutId = currentLayoutId;
      defectLog = {}; lastLogJson = {}; logLoaded = false;
      const layoutAtStart = currentLayoutId;
      db.ref('layouts/' + currentLayoutId + '/defectLog').on('value', snap => {
        if (layoutAtStart !== currentLayoutId) return;
        defectLog = snap.val() || {};
        lastLogJson = {};
        Object.keys(defectLog).forEach(id => { lastLogJson[id] = stableJson(recordCore(defectLog[id])); });
        logLoaded = true;
        backfillLog();
        if (typeof onLogChanged === 'function') onLogChanged();
      }, err => console.error('defectLog: ' + err.message));
    }

    function detachLogListener() {
      if (db && listeningLogLayoutId) db.ref('layouts/' + listeningLogLayoutId + '/defectLog').off();
      listeningLogLayoutId = null; defectLog = {}; lastLogJson = {}; logLoaded = false;
    }

    function saveToStorage() {
      if (!dbReady || !currentLayoutId) return;
      if (logLoaded) ensureLogIds();
      const updates = {};
      const currentIds = new Set();
      elements.forEach(el => {
        currentIds.add(el.id);
        const json = JSON.stringify(el);
        if (lastSaved[el.id] !== json) {
          updates['layouts/' + currentLayoutId + '/elements/' + el.id] = JSON.parse(json);
          lastSaved[el.id] = json;
        }
      });
      Object.keys(lastSaved).forEach(id => {
        if (!currentIds.has(id)) {
          updates['layouts/' + currentLayoutId + '/elements/' + id] = null;
          delete lastSaved[id];
        }
      });
      if (logLoaded) Object.assign(updates, defectLogUpdates());
      if (Object.keys(updates).length) {
        db.ref().update(updates).catch(err => alert('Gagal simpan ke Firebase: ' + err.message));
      }
    }

    function idTime(id) { return parseInt(String(id).split('_').pop(), 10) || 0; }

    function normalizeElement(raw) {
      const el = JSON.parse(JSON.stringify(raw));
      if (el.type === 'building' && el.category === 'pekerja') {
        let doors = el.doors || [];
        if (!Array.isArray(doors)) doors = Object.keys(doors).sort((a, b) => a - b).map(k => doors[k]);
        el.doors = doors.map(d => {
          d = d || {};
          return Object.assign({ label: '', nama: '', jumlah: '1' }, d, { checklist: d.checklist || {}, defects: d.defects || {} });
        });
        if (el.doors.length === 0) el.doors = [createDefaultDoor()];
        el.doorCount = el.doors.length;
      } else {
        el.doors = [];
      }
      return el;
    }

    /* ===================== PHOTOS ===================== */
    function photoSrc(g) {
      if (!g) return '';
      return g.startsWith('data:') ? g : (photoCache[g] || '');
    }
    function compressImage(dataUri, maxDim = 1024, quality = 0.6) {
      return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
          const w = Math.round(img.width * scale), h = Math.round(img.height * scale);
          const c = document.createElement('canvas');
          c.width = w; c.height = h;
          c.getContext('2d').drawImage(img, 0, 0, w, h);
          let out = c.toDataURL('image/jpeg', quality);
          if (out.length > 300000) out = c.toDataURL('image/jpeg', 0.45);
          resolve(out);
        };
        img.onerror = () => reject(new Error('Gambar tidak sah'));
        img.src = dataUri;
      });
    }
    async function storeNewPhoto(dataUri) {
      const compressed = await compressImage(dataUri);
      const id = 'p' + Date.now() + Math.random().toString(36).slice(2, 7);
      await db.ref('photos/' + id).set(compressed);
      photoCache[id] = compressed;
      return id;
    }
    function deletePhoto(g) {
      if (g && !g.startsWith('data:') && db) {
        db.ref('photos/' + g).remove().catch(() => {});
        delete photoCache[g];
      }
    }
    function collectPhotoIds(doors) {
      const ids = [];
      (doors || []).forEach(d => ['checklist', 'defects'].forEach(k => {
        Object.values(d[k] || {}).forEach(e => { if (e && e.gambar) ids.push(e.gambar); if (e && e.gambarTindakan) ids.push(e.gambarTindakan); });
      }));
      return ids;
    }
    function loadMissingPhotos() {
      document.querySelectorAll('img[data-photo]').forEach(img => {
        const id = img.dataset.photo;
        if (photoCache[id]) { img.src = photoCache[id]; return; }
        db.ref('photos/' + id).once('value').then(snap => {
          const v = snap.val();
          if (v) { photoCache[id] = v; img.src = v; }
        });
      });
    }

    function setSyncStatus(ok) {
      const el = document.getElementById('syncStatus');
      el.textContent = ok ? '☁️ Tersambung' : '⚠️ Luar talian';
      el.textContent = ok ? '● Tersambung' : '● Luar talian'; el.style.color = ok ? '#4ADE80' : '#FBBF24';
    }
    function doLogin() {
      const email = document.getElementById('loginEmail').value.trim();
      const pw = document.getElementById('loginPassword').value;
      const err = document.getElementById('loginError');
      err.textContent = '';
      if (!email || !pw) { err.textContent = 'Sila isi emel dan kata laluan.'; return; }
      firebase.auth().signInWithEmailAndPassword(email, pw).catch(e => {
        err.textContent = 'Log masuk gagal: emel atau kata laluan salah.';
        console.error(e);
      });
    }
    function doLogout() { firebase.auth().signOut(); }


/* ===================== CLOUD SYNC ===================== */
function startCloudSync() {
  dbReady = true;
  db.ref('.info/connected').on('value', s => setSyncStatus(s.val() === true));
  db.ref('layoutNames').on('value', snap => {
    layouts = snap.val() || {};
    const ids = Object.keys(layouts);
    if (!ids.length) { renderPage(); return; }
    if (!currentLayoutId || !layouts[currentLayoutId]) {
      currentLayoutId = ids[0];
      localStorage.setItem('currentLayoutId_v1', currentLayoutId);
    }
    renderLayoutSelect();
    if (listeningLayoutId !== currentLayoutId) attachElementsListener();
  }, err => alert('Tiada kebenaran membaca data: ' + err.message));
}

function attachElementsListener() {
  if (listeningLayoutId) db.ref('layouts/' + listeningLayoutId + '/elements').off();
  listeningLayoutId = currentLayoutId;
  attachLogListener();
  elements = []; lastSaved = {};
  renderPage();
  db.ref('layouts/' + currentLayoutId + '/elements').on('value', snap => {
    const val = snap.val() || {};
    elements = Object.keys(val).map(k => normalizeElement(val[k])).sort((a, b) => idTime(a.id) - idTime(b.id));
    lastSaved = {};
    elements.forEach(e => { lastSaved[e.id] = JSON.stringify(e); });
    backfillLog();
    renderPage();
  }, err => alert('Tiada kebenaran membaca data: ' + err.message));
}

function stopCloudSync() {
  if (db) {
    db.ref('.info/connected').off();
    db.ref('layoutNames').off();
    if (listeningLayoutId) db.ref('layouts/' + listeningLayoutId + '/elements').off();
  }
  detachLogListener();
  dbReady = false;
  listeningLayoutId = null;
  layouts = {};
  elements = []; lastSaved = {};
  renderPage();
}

function renderLayoutSelect() {
  const sel = document.getElementById('layoutSelect');
  sel.innerHTML = Object.keys(layouts)
    .sort((a, b) => (layouts[a] || '').localeCompare(layouts[b] || ''))
    .map(id => `<option value="${id}" ${id === currentLayoutId ? 'selected' : ''}>${escapeHTML(layouts[id])}</option>`)
    .join('');
  sel.value = currentLayoutId;
}

function changeLayout(id) {
  if (!layouts[id] || id === currentLayoutId) return;
  currentLayoutId = id;
  localStorage.setItem('currentLayoutId_v1', id);
  attachElementsListener();
}

function initFirebase() {
  firebase.initializeApp(firebaseConfig);
  db = firebase.database();
  firebase.auth().onAuthStateChanged(user => {
    if (user) {
      document.getElementById('login-overlay').style.display = 'none';
      startCloudSync();
    } else {
      stopCloudSync();
      document.getElementById('login-overlay').style.display = 'flex';
    }
  });
}

function onSearchInput() {
  searchQuery = document.getElementById('headerSearch').value.toLowerCase().trim();
  renderPage();
}

/* ===================== DEFECT HELPERS (shared) ===================== */
    const DEF_STATUS = {
      baru:    { l: 'Baharu', c: 'st-new' },
      proses:  { l: 'Dalam Tindakan', c: 'st-prog' },
      selesai: { l: 'Selesai', c: 'st-done' }
    };
    const AUTO_NOTE = { baru: 'Tiada Tindakan', proses: 'Sedang dibaiki', selesai: 'Selesai' };
    let defFilter = 'aktif';
    const todayStr = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };

    function defStatus(e) { return DEF_STATUS[e && e.tindakan] ? e.tindakan : 'baru'; }
    function isOpenDefect(e) { return !!(e && e.status && defStatus(e) !== 'selesai'); }

    const ROAD_DEFECT_CHECKLIST = [
      { key: 'lubangJalan', label: 'Lubang / Jalan Berlubang' },
      { key: 'lampuJalan', label: 'Lampu Jalan Rosak' },
      { key: 'paritTersumbat', label: 'Parit Tersumbat' },
      { key: 'jalanRetak', label: 'Permukaan Jalan Retak / Runtuh' },
      { key: 'papanTanda', label: 'Papan Tanda Rosak' },
      { key: 'bahuJalan', label: 'Bahu Jalan Terhakis' }
    ];
    function checklistFor(item) { return item.category === 'jalan' ? ROAD_DEFECT_CHECKLIST : DEFECT_CHECKLIST; }

    function allDefects() {
      const out = [];
      elements.forEach(item => {
        if (item.category === 'pekerja') return;
        checklistFor(item).forEach(chk => {
          const e = item.defects && item.defects[chk.key];
          if (e && e.status) out.push({ item, door: null, di: -1, chk, e });
        });
      });
      elements.forEach(item => (item.doors || []).forEach((door, di) => {
        DEFECT_CHECKLIST.forEach(chk => {
          const e = door.defects && door.defects[chk.key];
          if (e && e.status) out.push({ item, door, di, chk, e });
        });
      }));
      return out;
    }

function updateDefectBadge() {
  const n = allDefects().filter(d => isOpenDefect(d.e)).length;
  const b = document.getElementById('defectCount');
  if (b) { b.textContent = n; b.style.display = n ? 'inline-block' : 'none'; }
}
function onLogChanged() { if (typeof renderPage === 'function') renderPage(); }
function afterDefectChange() {
  saveToStorage();
  renderPage();
}

    function getChecklistEntry(id, doorIndex, listKey, key, createIfMissing) {
      const item = elements.find(e => e.id === id);
      const door = doorIndex === -1 ? item : (item && item.doors && item.doors[doorIndex]);
      if (!door) return null;
      if (!door[listKey]) door[listKey] = {};
      if (!door[listKey][key] && createIfMissing) {
        door[listKey][key] = { status: false, tarikh: '', gambar: '', catatan: '' };
      }
      return door[listKey][key] || null;
    }

    function uploadItemImage(e, id, doorIndex, listKey, key, field) {
      field = field || 'gambar';
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async function (evt) {
        try {
          const photoId = await storeNewPhoto(evt.target.result);
          const entry = getChecklistEntry(id, doorIndex, listKey, key, false);
          if (!entry) return;
          deletePhoto(entry[field]);
          entry[field] = photoId;
          afterDefectChange(id);
        } catch (err) {
          alert('Gagal muat naik gambar: ' + err.message);
        }
      };
      reader.readAsDataURL(file);
    }
    function removeItemImage(id, doorIndex, listKey, key, field) {
      field = field || 'gambar';
      const entry = getChecklistEntry(id, doorIndex, listKey, key, false);
      if (!entry) return;
      deletePhoto(entry[field]);
      entry[field] = '';
      afterDefectChange(id);
    }

    /* ===================== CAMERA ===================== */
    function openCameraModal(id, doorIndex, listKey, key, field) {
      activeCamTarget = { houseId: id, doorIndex: doorIndex, listKey: listKey, key: key, field: field || 'gambar' };
      const modal = document.getElementById('camera-modal');
      const video = document.getElementById('camera-video');
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(stream => {
          cameraStream = stream;
          video.srcObject = stream;
          modal.style.display = 'flex';
        })
        .catch(err => { alert('Gagal mengakses kamera: ' + err.message); });
    }
    function closeCameraModal() {
      document.getElementById('camera-modal').style.display = 'none';
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
      }
    }
    function takePicture() {
      const video = document.getElementById('camera-video');
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUri = canvas.toDataURL('image/jpeg', 0.8);
      const { houseId, doorIndex, listKey, key, field } = activeCamTarget;
      closeCameraModal();
      storeNewPhoto(dataUri).then(photoId => {
        const entry = getChecklistEntry(houseId, doorIndex, listKey, key, false);
        if (!entry) return;
        deletePhoto(entry[field]);
        entry[field] = photoId;
        afterDefectChange(houseId);
      }).catch(err => alert('Gagal simpan gambar: ' + err.message));
    }
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && cameraStream) closeCameraModal();
    });

