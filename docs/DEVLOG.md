ScoutAlina Dev Log
==================

2025-10-14
----------
- Add dynamic APK listing on `/downloads`:
  - Enumerates files in `server/static/apk/`, shows name, size, last updated, SHA256.
  - Generates absolute tracked URLs for QR codes and links.
- Add client-side QR generation on downloads page using `qrcode` JS.
- Add tracked APK endpoint `GET /downloads/apk/<filename>`:
  - Logs downloads to `logs/scoutalina.log` and appends CSV entries to `logs/apk_downloads.csv`.
  - Serves files from `server/static/apk/` via `send_from_directory`.
- Update `android/buildozer.spec`:
  - Add `plyer` and `requests` to requirements.
  - Add Android permissions: fine/coarse location, internet/network state, external storage.
- Improve local bootstrap in `app.py` (previous):
  - Ensures virtualenv and installs requirements automatically.
  - Ensures `static/apk/` exists so `/downloads` works out-of-the-box.

Notes
-----
- Removed any references to non-existent `ahoyapp` paths; none found in this repo.
- To publish an APK on Render, commit the file under `server/static/apk/` and redeploy.


