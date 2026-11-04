# Estate Perumahan (LP2)

Worker-housing management. Plain HTML + Firebase (Realtime Database + email login). No build step.
Host it with GitHub Pages: Settings → Pages → `main` / root.

## Pages

| File | What it is |
|---|---|
| `index.html` | Main app: **Senarai** (list) and **Pelan** (map). Building details, doors, checklists, defect ticking, one **Hantar rekod bilik ini ke WhatsApp** button per room (no buttons on individual checklist rows), and a building-level defect report. |
| `kerosakan.html` | **Kerosakan**: all defect records, status actions (Mula Tindakan / Selesai), contractor, notes, evidence photos, **Padam rekod**. |
| `ringkasan.html` | **Ringkasan**: only items that are rosak or need replacing. |
| `bilik.html` | **Rekod Bilik**: the page a room's QR code opens. Shows one room and its two forms: Rekod Kelengkapan and Senarai Semak Kerosakan. |
| `gambar.html` | Read-only photo viewer opened from the picture links in the WhatsApp report. |
| `config.js` | `WA_NUMBER` and the room report text (shared by `index.html` and `bilik.html`). |
| `qrcode.js` | QR generator (MIT, Kazuhiko Arase). Runs in the browser, no internet needed. |
| `shared.js` / `shared.css` | Code and styles used by `kerosakan.html`, `ringkasan.html` and `bilik.html` (Firebase, login, layouts, photos, defect records). |

In the building detail window, a bar of door chips at the top (Ringkasan, then each door) lets you jump to any door; Sebelum / Seterusnya at the bottom move one door at a time.

`index.html` keeps its own copy of the Firebase/login/defect-record code, so a change to that part must be made in both `index.html` and `shared.js`.

## QR code for every room

Open a building (Senarai or Pelan) → go to a door → **📱 Kod QR bilik ini** to show, **Cetak**, **Simpan gambar** or **Salin pautan**. On the first page of the building window, **Cetak QR semua bilik** prints one A4 sheet of labels (door name + QR) to stick on each door.

- Link format: `bilik.html?l=<layoutId>&b=<buildingId>&d=<door number, from 0>`. It uses the address the main app was opened on, so open the app from the GitHub Pages address before printing.
- **No login on the QR page.** It signs in anonymously (Firebase Anonymous sign-in) and shows only that one room: Rekod Kelengkapan and Senarai Semak Kerosakan, plus **Hantar rekod ke WhatsApp**. There are no links, no menu and no logout, so there is nowhere else to go.
- Anonymous sessions are refused by `index.html`, `kerosakan.html` and `ringkasan.html` (they sign it out and show the login window), so a QR session can never open the main app.
- **WhatsApp number**: set `WA_NUMBER` once in `config.js` (used by both the QR page and the main app) (e.g. `'0123456789'` or `'60123456789'`). Empty = the person chooses the recipient. WhatsApp links cannot attach pictures, so the message carries a link per photo (`gambar.html?p=<photoId>`, a read-only page that opens without login), and a **Kongsi dengan gambar** button (phones) attaches the real pictures through the share sheet (the person then picks WhatsApp and the recipient). Anonymous access to `photos/<id>` is already covered by `firebase-rules.json`.
- The room page saves **only that room** (`layouts/<l>/elements/<b>/doors/<d>`) and its defect records, so people filling different rooms of one building never overwrite each other. Selesai dates, photos and the Padam/Buka Semula rules behave exactly as in the main app.
- The door is identified by its position. If the last door of a building is removed and a new one added, the old sticker opens the new door. Removed rooms/buildings/layouts show a clear message.

### One-time Firebase setup for the QR pages

1. Firebase console → **Authentication → Sign-in method** → enable **Anonymous**.
2. **Realtime Database → Rules** → paste `firebase-rules.json` → **Publish**. Anonymous users can then read/write only layout names, building id/name, **doors** and **defect records/photos** (by exact id). They cannot list or read buildings, other layouts, or the layout list. Logged-in staff keep full access.

Limit to know: the QR links and page code are public, so anyone who learns a building id and door number can edit that door's records. Keep stickers on doors only, and use **Authentication → Users** / Rules if you need to tighten it later.

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
