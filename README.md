# BPSU CBA AACCUP Level IV — Static Read-Only Accreditation Portal

A static, database-free accreditation evidence portal designed as the visitor-facing companion to the internal BPSU CBA Document Management System.

## What this portal does

- Presents Areas I–X in an accreditor-friendly interface
- Searches and filters published evidence metadata
- Shows controlled document code, version, criterion/indicator, type, academic year, publication date, and tags
- Opens linked approved evidence files in read-only visitor mode
- Provides a printable evidence register
- Works on GitHub Pages or any standard static host
- Uses no database, login system, upload form, approval workflow, or server-side code

## Important publishing rule

Treat every file inside this static site as potentially accessible to external visitors. Publish only evidence formally cleared for accreditor/external viewing. Keep drafts, review notes, account information, personal data, and confidential records in the internal DMS.

## Add official Area titles

Edit `assets/data/portal-data.js` and replace each `Official area title to be configured` value under `areaTitles` with the exact official titles for the accreditation instrument being used.

## Add published evidence

1. Copy an approved file into `documents/`.
2. Add a record to `window.EVIDENCE_DATA` in `assets/data/portal-data.js`.
3. Set `fileUrl`, for example:

```js
fileUrl: "documents/BPSU-CBA-L4-AI-0001-v1.pdf"
```

A commented example record is included in `portal-data.js`.

## Import approved metadata from the internal DMS

The internal DMS can export a CSV document register. This package includes a helper that filters the export to `Approved` records:

```bash
python tools/import_dms_csv.py BPSU_AACCUP_DMS_Document_Register.csv
```

It creates `assets/data/portal-data.generated.js`. Review the generated records before publication. Document files are intentionally not copied automatically.

## Preview locally

The site works best through a tiny local web server:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080/`.

## GitHub Pages deployment

1. Create a separate repository such as `BPSU-AACCUP-PORTAL`.
2. Upload the contents of this folder to the repository root.
3. In GitHub, open **Settings → Pages**.
4. Choose **Deploy from a branch**.
5. Select `main` and `/ (root)`.
6. Save and wait for the GitHub Pages URL to appear.

Keeping the static portal in a separate repository from the dynamic DMS is recommended because it creates a clear boundary between internal workflow files and visitor-facing evidence.

## Branding assets

The portal uses the BPSU seal and Balanga Campus photograph supplied for this project.
