/* Google Apps Script: terima laporan bulanan daripada GitHub dan simpan dalam folder Google Drive anda.
   Tampal di script.google.com, tukar dua nilai di bawah, kemudian Deploy > New deployment > Web app
   (Execute as: Me, Who has access: Anyone). Salin URL Web app ke GitHub secret APPS_SCRIPT_URL. */
const TOKEN = 'GANTI-DENGAN-KATA-RAHSIA-PANJANG';      // sama dengan GitHub secret APPS_SCRIPT_TOKEN
const FOLDER_ID = 'GANTI-DENGAN-ID-FOLDER-DRIVE';      // bahagian akhir URL folder Drive anda

function doPost(e) {
  try {
    const p = JSON.parse(e.postData.contents);
    if (p.token !== TOKEN) return out({ ok: false, error: 'token salah' });
    const folder = DriveApp.getFolderById(FOLDER_ID);
    const files = p.files.map(function (f) {
      const blob = Utilities.newBlob(Utilities.base64Decode(f.b64), f.mime, f.name);
      const file = folder.createFile(blob);
      return { name: f.name, id: file.getId(), size: file.getSize() };
    });
    return out({ ok: true, files: files });
  } catch (err) {
    return out({ ok: false, error: String(err) });
  }
}
function out(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
