#!/usr/bin/env python3
"""Convert the DMS CSV export into static portal evidence metadata.

Usage:
  python tools/import_dms_csv.py BPSU_AACCUP_DMS_Document_Register.csv

Only rows with status == Approved are published.
The script does NOT copy document files. Add files to documents/ and fill fileUrl values
manually after reviewing what may be shared externally.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

if len(sys.argv) < 2:
    raise SystemExit("Usage: python tools/import_dms_csv.py <document-register.csv>")

source = Path(sys.argv[1])
out = Path(__file__).resolve().parents[1] / "assets" / "data" / "portal-data.generated.js"

records = []
with source.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if (row.get("status") or "").strip().lower() != "approved":
            continue
        tags = [x.strip() for x in (row.get("tags") or "").split(",") if x.strip()]
        doc_code = (row.get("doc_code") or "").strip()
        version = int((row.get("version") or "1").strip() or 1)
        records.append({
            "id": f"{doc_code}-v{version}",
            "docCode": doc_code,
            "version": version,
            "title": (row.get("title") or "").strip(),
            "description": "",
            "area": (row.get("area") or "").strip(),
            "criterion": (row.get("criterion") or "").strip(),
            "docType": (row.get("doc_type") or "").strip(),
            "academicYear": (row.get("academic_year") or "").strip(),
            "tags": tags,
            "publishedDate": (row.get("updated_at") or "")[:10],
            "owner": (row.get("owner") or "").strip(),
            "fileUrl": ""
        })

payload = "window.EVIDENCE_DATA = " + json.dumps(records, ensure_ascii=False, indent=2) + ";\n"
out.write_text(payload, encoding="utf-8")
print(f"Wrote {len(records)} approved records to {out}")
print("Review every record and add fileUrl values only for documents cleared for external viewing.")
