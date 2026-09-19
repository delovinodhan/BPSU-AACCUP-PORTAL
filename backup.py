import os, zipfile
from datetime import datetime
from pathlib import Path

base = Path(os.environ.get('BPSU_PORTAL_DATA_DIR', Path(__file__).resolve().parent / 'data')).resolve()
out_dir = Path(os.environ.get('BPSU_BACKUP_DIR', Path(__file__).resolve().parent / 'backups')).resolve()
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"bpsu-evidence-portal-backup-{datetime.now():%Y%m%d-%H%M%S}.zip"
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    if base.exists():
        for p in base.rglob('*'):
            if p.is_file(): z.write(p, p.relative_to(base))
print(out)
