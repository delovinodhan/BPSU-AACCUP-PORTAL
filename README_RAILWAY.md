# BPSU CBA AACCUP Level IV Evidence Portal

This repository now contains the public Evidence Portal and its secure upload,
review, direct-publication, and accreditor workspace in one Flask application.

## Live workflow

1. Faculty sign in and upload the exact final document.
2. A reviewer approves it or requests revision.
3. A reviewer completes the privacy/publication clearance.
4. The College Dean or Accreditation Chair selects **Publish Directly to Evidence Library**.
5. The record and file become visible immediately to public visitors and accreditor accounts.

No GitHub token, transfer ZIP, metadata merge, or external staging portal is required.

## Railway configuration

- Build: Dockerfile
- Health check: `/health`
- Persistent volume mount path: `/data`
- Required variables:
  - `BPSU_PORTAL_SECRET` — long random session secret
  - `BPSU_SETUP_TOKEN` — private one-time administrator setup token
  - `BPSU_PORTAL_DATA_DIR=/data`
  - `BPSU_SECURE_COOKIE=1`
  - `BPSU_PUBLIC_PORTAL_ORIGIN=https://delovinodhan.github.io`

After the service is live, open `/setup`, enter the setup token, and create the
first College Dean account. The setup page disables itself after that account
is created.

## Storage and backups

The SQLite database and uploaded evidence are stored under `/data`. Keep the
Railway volume attached and create periodic volume backups. `backup.py` can also
create a portable ZIP backup of the database and uploads.

## Local test

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export BPSU_SETUP_TOKEN='choose-a-private-token'
python app.py
```

Open `http://127.0.0.1:5000/`.
