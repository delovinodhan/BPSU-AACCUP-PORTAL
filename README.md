# BPSU CBA AACCUP Level IV Accreditation Evidence Portal

Integrated evidence portal for the College of Business and Accountancy,
Bataan Peninsula State University – Balanga Campus.

The same application now provides:

- the public, read-only Evidence Library;
- secure faculty uploads;
- reviewer validation and revision requests;
- privacy/publication clearance;
- direct publication for accreditors;
- BSA and BSBA workspaces;
- the five approved accreditation Areas;
- controlled document codes, versions, audit history, and user roles.

## Accreditation Areas

1. Area I — Research
2. Area II — Performance of Graduates
3. Area III — Extension
4. Area IV — Internationalization
5. Area V — Planning Process

Each program/Area starts with **Narrative Profile** and **Extent of Compliance**
requirement entries. Administrators can add the official detailed indicators.

## Publication workflow

1. Faculty upload the exact final document.
2. An Area Head, Accreditation Chair, or College Dean reviews it.
3. Approved evidence receives a separate privacy/publication review.
4. The College Dean or Accreditation Chair publishes it directly.
5. The record and file immediately appear in the Evidence Library.

Uploads never become public automatically. GitHub tokens, transfer ZIPs, and
manual JSON merging are no longer part of the normal workflow.

## Hosting

The application is configured for Railway with Docker and a `/health` endpoint.
Attach a persistent volume at `/data`; this is where the SQLite database and all
uploaded files are stored. See [README_RAILWAY.md](README_RAILWAY.md) for the
deployment variables and initial administrator setup.

The existing GitHub Pages address can remain as the public presentation URL.
Its secure-workspace and live-evidence settings are configured in
`assets/data/portal-data.js` after the Railway domain is generated.

## Security notes

- Use named user accounts and least-privilege roles.
- Publish only documents cleared for external/accreditor viewing.
- Do not upload drafts, credentials, or unnecessary personal data.
- Keep Railway volume backups and periodically test restoration.
- Before formal institutional use, complete the University's privacy, malware
  scanning, retention, and security review requirements.
