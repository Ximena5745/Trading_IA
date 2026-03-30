"""
Script: scripts/backup_db.py
Responsibility: pg_dump trader_ai → .sql.gz → upload to OneDrive via rclone
Retention: keeps last 30 days, deletes older backups from OneDrive
Schedule: Windows Task Scheduler daily at 03:00 AM

Setup (one-time):
  1. Install rclone: https://rclone.org/downloads/ (Windows binary)
  2. Configure OneDrive remote: rclone config  → name it "onedrive"
  3. Test: rclone ls onedrive:trader_ai_backups
  4. Schedule via Task Scheduler:
       Program: python
       Arguments: "C:\\path\\to\\scripts\\backup_db.py"
       Trigger: daily at 03:00

Usage:
  python scripts/backup_db.py
  python scripts/backup_db.py --dry-run   # show what would happen, no upload
"""
from __future__ import annotations

import gzip
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
DB_CONTAINER = "trader_db"  # name of the Docker container running PostgreSQL
DB_NAME = "trader_ai"
DB_USER = "trader"
RCLONE_REMOTE = "onedrive"  # rclone remote name (configure with: rclone config)
RCLONE_PATH = f"{RCLONE_REMOTE}:trader_ai_backups"
RETENTION_DAYS = 30
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"
# ─────────────────────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def dump_database(backup_path: Path) -> None:
    """pg_dump via docker exec, compressed with gzip."""
    _log(f"Dumping {DB_NAME} from container {DB_CONTAINER}...")
    result = _run(
        [
            "docker",
            "exec",
            DB_CONTAINER,
            "pg_dump",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "--no-password",
            "-F",
            "plain",
        ]
    )
    compressed = backup_path.with_suffix(".sql.gz")
    with gzip.open(compressed, "wt", encoding="utf-8") as f:
        f.write(result.stdout)
    size_kb = compressed.stat().st_size // 1024
    _log(f"Backup created: {compressed.name} ({size_kb} KB)")


def upload_to_onedrive(backup_path: Path, dry_run: bool) -> None:
    """Upload compressed backup to OneDrive via rclone."""
    compressed = backup_path.with_suffix(".sql.gz")
    if dry_run:
        _log(f"[DRY RUN] Would upload {compressed} to {RCLONE_PATH}/")
        return
    _log(f"Uploading to {RCLONE_PATH}/...")
    _run(["rclone", "copy", str(compressed), RCLONE_PATH + "/"])
    _log("Upload complete.")


def purge_old_backups(dry_run: bool) -> None:
    """Delete backups older than RETENTION_DAYS from OneDrive and local."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    # Local cleanup
    for f in BACKUP_DIR.glob("backup_*.sql.gz"):
        try:
            # filename: backup_YYYYMMDD_HHMMSS.sql.gz
            date_str = f.stem.replace("backup_", "").replace(".sql", "")
            file_dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S").replace(
                tzinfo=timezone.utc
            )
            if file_dt < cutoff:
                if dry_run:
                    _log(f"[DRY RUN] Would delete local: {f.name}")
                else:
                    f.unlink()
                    _log(f"Deleted local: {f.name}")
        except (ValueError, OSError):
            continue

    # OneDrive cleanup via rclone
    if dry_run:
        _log(f"[DRY RUN] Would purge OneDrive backups older than {RETENTION_DAYS} days")
        return
    try:
        result = _run(
            ["rclone", "lsf", RCLONE_PATH + "/", "--format", "np"], check=False
        )
        for line in result.stdout.splitlines():
            parts = line.strip().split(";")
            if len(parts) < 2:
                continue
            name, date_str = parts[0].strip(), parts[1].strip()
            if not name.startswith("backup_") or not name.endswith(".sql.gz"):
                continue
            try:
                file_dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
                if file_dt < cutoff:
                    _run(["rclone", "deletefile", f"{RCLONE_PATH}/{name}"])
                    _log(f"Deleted from OneDrive: {name}")
            except ValueError:
                continue
    except Exception as exc:
        _log(f"Warning: OneDrive purge failed — {exc}")


def main(dry_run: bool = False) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}.sql"

    try:
        dump_database(backup_path)
        upload_to_onedrive(backup_path, dry_run)
        purge_old_backups(dry_run)
        _log("Backup finished successfully.")
    except subprocess.CalledProcessError as exc:
        _log(f"ERROR: {exc.cmd} failed\n{exc.stderr}")
        sys.exit(1)
    finally:
        # Keep local compressed copy; remove uncompressed temp if it exists
        if backup_path.exists():
            backup_path.unlink()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
