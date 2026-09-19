# BPSU CBA AACCUP Level IV — Read-Only Accreditation Evidence Portal

Public/static presentation portal for approved accreditation evidence of the College of Business and Accountancy, Bataan Peninsula State University – Balanga Campus.

## Program workspaces

The public portal separates evidence for:

- **BSA** — Bachelor of Science in Accountancy
- **BSBA** — Bachelor of Science in Business Administration

Each program uses the following Area I–V structure supplied for this project:

1. Area I — RESEARCH
2. Area II — PERFORMANCE OF GRADUATES
3. Area III — EXTENSION
4. Area IV — INTERNATIONALIZATION
5. Area V — PLANNING PROCESS

## Published evidence data

The portal loads published evidence records from:

`assets/data/evidence.json`

Each record contains program, Area, criterion/indicator, controlled document code, version, title, document type, academic year, tags, owner/source, publication date, and the linked file path.

Published documents are stored under program/Area-specific folders, for example:

```text
documents/
  bsa/
    area-i-research/
      BPSU-CBA-BSA-L4-AI-0001-v1.pdf
  bsba/
    area-v-planning-process/
      BPSU-CBA-BSBA-L4-AV-0001-v1.pdf
```

## Integration with the Staging & Publication Portal

The separate **BPSU CBA Accreditation Staging & Publication Portal** can:

1. accept local browser uploads,
2. separate evidence by BSA / BSBA and Area I–V,
3. move records through Draft → For Review → Ready to Publish,
4. export a portal transfer ZIP, or
5. optionally publish selected Ready-to-Publish items directly to this GitHub repository using a fine-grained GitHub token restricted to this repository.

Direct publication uploads the evidence file to the correct `documents/` path and merges its metadata into `assets/data/evidence.json`.

## Publication rule

Treat every file in this repository as potentially public. Publish only evidence formally cleared for accreditor/external viewing. Do not place drafts, review comments, personal information, confidential records, credentials, or internal-only files here.

## GitHub Pages

This repository is intended to be served with GitHub Pages from the `main` branch and repository root.
