import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from scripts.backup_db import BACKUP_DIR, parse_db_url


def run_restore(backup_file_path: Path):
    if not backup_file_path.exists():
        print(f"❌ Backup file not found: {backup_file_path}")
        return False

    print(f"♻️ Starting Database Restore from {backup_file_path.name}...")
    user, password, host, port, dbname = parse_db_url(settings.DATABASE_URL)

    env = os.environ.copy()
    env["PGPASSWORD"] = password

    psql_bin = shutil.which("psql")
    if not psql_bin:
        print("⚠️ psql CLI not found in PATH; cannot execute binary restore directly.")
        return False

    cmd = [psql_bin, "-h", host, "-p", port, "-U", user, "-d", dbname]

    try:
        if str(backup_file_path).endswith(".gz"):
            with gzip.open(backup_file_path, "rb") as gz_in:
                sql_content = gz_in.read()
        else:
            sql_content = backup_file_path.read_bytes()

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout, stderr = proc.communicate(input=sql_content)
        if proc.returncode != 0:
            print(f"❌ Restore failed: {stderr.decode()}")
            return False

        print("✅ Database restore completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Restore error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        backups = sorted(BACKUP_DIR.glob("devhire_backup_*.sql.gz"))
        if not backups:
            print("No backups found in backend/backups/")
            sys.exit(1)
        target = backups[-1]
        print(f"No file specified. Using latest backup: {target.name}")
    else:
        target = Path(sys.argv[1])

    success = run_restore(target)
    sys.exit(0 if success else 1)

