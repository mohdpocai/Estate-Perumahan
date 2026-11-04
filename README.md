# Estate Perumahan (LP2)

Worker-housing management. Plain HTML + Firebase (Realtime Database + email login). No build step.
Host it with GitHub Pages: Settings → Pages → `main` / root.

## Pages

| File | What it is |
|---|---|
| `index.html` | Main app: **Senarai** (list) and **Pelan** (map). Building details, doors, checklists, defect ticking, WhatsApp/Emel/Kongsi report buttons. |
| `kerosakan.html` | **Kerosakan**: all defect records, status actions (Mula Tindakan / Selesai), contractor, notes, evidence photos, **Padam rekod**. |
| `ringkasan.html` | **Ringkasan**: only items that are rosak or need replacing. |
| `bilik.html` | **Rekod Bilik**: the page a room's QR code opens. Shows one room and its two forms: Rekod Kelengkapan and Senarai Semak Kerosakan. |
| `qrcode.js` | QR generator (MIT, Kazuhiko Arase). Runs in the browser, no internet needed. |
| `shared.js` / `shared.css` | Code and styles used by `kerosakan.html`, `ringkasan.html` and `bilik.html` (Firebase, login, layouts, photos, defect records). |

In the building detail window, a bar of door chips at the top (Ringkasan, then each door) lets you jump to any door; Sebelum / Seterusnya at the bottom move one door at a time.

`index.html` keeps its own copy of the Firebase/login/defect-record code, so a change to that part must be made in both `index.html` and `shared.js`.

## QR code for every room

Open a building (Senarai or Pelan) → go to a door → **📱 Kod QR bilik ini** to show, **Cetak**, **Simpan gambar** or **Salin pautan**. On the first page of the building window, **Cetak QR semua bilik** prints one A4 sheet of labels (door name + QR) to stick on each door.

- Link format: `bilik.html?l=<layoutId>&b=<buildingId>&d=<door number, from 0>`. It uses the address the main app was opened on, so open the app from the GitHub Pages address before printing.
- Scanning needs the normal staff login (same Firebase account). After login the room page opens directly.
- The room page saves **only that room** (`layouts/<l>/elements/<b>/doors/<d>`), so people filling different rooms of one building never overwrite each other. Defect records (`defectLog`), photos, Selesai dates and the Padam/Buka Semula rules behave exactly as in the main app.
- The door is identified by its position. If the last door of a building is removed and a new one added, the old sticker opens the new door. Removed rooms/buildings/layouts show a clear message instead.
- `bilik.html` sets `FIXED_LAYOUT` before `shared.js`, so scanning never changes the layout remembered by the main app.

## Data flow (Firebase)

```
layoutNames/<layoutId>                      layout names (LP2, LP3, ...)
layouts/<layoutId>/elements/<id>            buildings and roads (doors, checklists, defects live inside)
layouts/<layoutId>/defectLog/<recordId>     permanent defect records (one per report)
photos/<photoId>                            compressed photos (referenced by id)
```

- Tick a defect in a building (`index.html`) → saved on the building **and** copied to `defectLog`.
- `kerosakan.html` reads `defectLog` + the live buildings. Status changes update both.
- Records are never removed automatically: unticking, completing, repeating a defect, or deleting a door/building keeps the record and its photos. Only **Padam rekod** (or deleting a whole layout) removes them.
- When a defect is marked **Selesai** (Kerosakan page or the Status Tindakan dropdown in the building window) you pick the **completion date** (default today; not before the report date, not in the future) and it is automatically **unticked** in the building, ready for the next inspection. Its record stays as a finished repair, with **Buka Semula** if it needs to be reopened.
- A completed defect that happens again (ticked at the next inspection) becomes a **new** record; the old one stays.

## Navigation

The dropdown at the top-left switches between Senarai, Pelan, Kerosakan and Ringkasan. All pages share one login and one database, so a change in one shows in the others.
