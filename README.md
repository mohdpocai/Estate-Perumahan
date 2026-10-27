# Estate Perumahan (LP2)

Worker-housing management. Plain HTML + Firebase (Realtime Database + email login). No build step.
Host it with GitHub Pages: Settings → Pages → `main` / root.

## Pages

| File | What it is |
|---|---|
| `index.html` | Main app: **Senarai** (list) and **Pelan** (map). Building details, doors, checklists, defect ticking, WhatsApp/Emel/Kongsi report buttons. |
| `kerosakan.html` | **Kerosakan**: all defect records, status actions (Mula Tindakan / Selesai), contractor, notes, evidence photos, **Padam rekod**. |
| `ringkasan.html` | **Ringkasan**: only items that are rosak or need replacing. |
| `shared.js` / `shared.css` | Code and styles used by `kerosakan.html` and `ringkasan.html` (Firebase, login, layouts, photos, defect records). |

`index.html` keeps its own copy of the Firebase/login/defect-record code, so a change to that part must be made in both `index.html` and `shared.js`.

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
- When a defect is marked **Selesai** (Kerosakan page or the Status Tindakan dropdown in the building window) it is automatically **unticked** in the building, ready for the next inspection. Its record stays as a finished repair, with **Buka Semula** if it needs to be reopened.
- A completed defect that happens again (ticked at the next inspection) becomes a **new** record; the old one stays.

## Navigation

The dropdown at the top-left switches between Senarai, Pelan, Kerosakan and Ringkasan. All pages share one login and one database, so a change in one shows in the others.
