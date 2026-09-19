# BPSU CBA Accreditation Staging & Publication Portal

Static browser-based staging application for Level IV accreditation evidence of the College of Business and Accountancy.

## Program workspaces

- **BSA** — Bachelor of Science in Accountancy
- **BSBA** — Bachelor of Science in Business Administration

Each program uses the exact Area wording supplied for this project:

1. Area I — RESEARCH
2. Area II — PERFORMANCE OF GRADUATES
3. Area III — EXTENSION
4. Area IV — INTERNATIONALIZATION
5. Area V — PLANNING PROCESS

## Architecture

This is a **static application**. It has no server database. Uploaded files are stored in the browser's IndexedDB on the current device. They remain private/local until an authorized user exports or publishes them.

Workflow:

**Local Upload → For Review → Publication Clearance → Ready to Publish → Transfer → Public BPSU AACCUP Portal**

## Publication methods

### A. Transfer Package (recommended)

Select Ready-to-Publish items and choose **Export Transfer Package**. The ZIP contains the evidence files under their final `documents/` paths, `portal-records.json`, `portal-records.js`, a CSV manifest, and instructions.

### B. Direct GitHub Publish (optional)

The static browser app can call the GitHub REST API directly. For this method, use a **fine-grained GitHub token limited to the `BPSU-AACCUP-PORTAL` repository with Contents read/write permission**.

The token is not stored in IndexedDB or localStorage by the application and is cleared when the page is refreshed or closed.

For direct publishing, the public portal repository must contain:

`assets/data/evidence.json`

The staging portal uploads evidence to program/area-specific subfolders under `documents/`, merges records into `evidence.json`, then marks the local staging record as Published.

## Important limitations

- Browser data can be erased if site storage is cleared. Use **Download Full Workspace Backup** regularly.
- Direct GitHub publishing is limited to 20 MB per file in this build. Use the transfer ZIP for larger documents.
- A public GitHub Pages portal should contain only evidence approved for external/accreditor viewing.
- This static tool does not provide institutional authentication. Host it in an administratively controlled environment and restrict who has access to the device/browser profile.
- For university-wide production use with many simultaneous contributors, a server-backed system remains preferable.

## Run locally

You can double-click `index.html`. For the most consistent browser behavior, run:

```bash
python -m http.server 8080
```

and open `http://localhost:8080/`.

## GitHub Pages

The staging app can itself be hosted as a static site, but uploaded evidence still remains in each user's browser unless it is exported/published. Do not treat GitHub Pages hosting of this staging tool as centralized document storage.
