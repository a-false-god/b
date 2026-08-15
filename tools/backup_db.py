#!/usr/bin/env python3
"""
Database Backup & Restore Tool for Prawko B MVP.

Features:
- Online SQLite backup via sqlite3.Connection.backup API.
- Timestamped snapshot naming: data/backups/prawko_YYYYMMDD_HHMMSS.sqlite
- Retention policy: keeps 14 daily + 4 weekly snapshots, pruning older files.
- Integrity verification: runs PRAGMA integrity_check before restore.
"""

import argparse
import datetime
import logging
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "prawko.sqlite"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

logger = logging.getLogger("backup_db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SNAPSHOT_PATTERN = re.compile(r"^prawko_(\d{8})_(\d{6})\.sqlite$")


def verify_sqlite_integrity(db_file: Path) -> Tuple[bool, str]:
    """Run PRAGMA integrity_check on the specified database file."""
    if not db_file.exists():
        return False, f"File {db_file} does not exist"

    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        rows = cursor.fetchall()
        conn.close()

        if rows and len(rows) == 1 and rows[0][0] == "ok":
            return True, "ok"
        errors = "; ".join(row[0] for row in rows)
        return False, f"Integrity check failed: {errors}"
    except Exception as e:
        return False, f"Integrity check exception: {e}"


def get_snapshot_datetime(file_path: Path) -> datetime.datetime | None:
    """Parse datetime from snapshot filename prawko_YYYYMMDD_HHMMSS.sqlite."""
    match = SNAPSHOT_PATTERN.match(file_path.name)
    if not match:
        return None
    date_str, time_str = match.groups()
    try:
        return datetime.datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def calculate_retention(snapshot_files: List[Path]) -> Tuple[Set[Path], Set[Path]]:
    """
    Apply retention policy:
    - 14 Daily: Most recent snapshot for each of the last 14 unique calendar days.
    - 4 Weekly: Most recent snapshot for each of the 4 preceding unique calendar weeks (ISO year-week).
    Returns (keep_set, prune_set).
    """
    valid_snapshots: List[Tuple[Path, datetime.datetime]] = []
    for file_path in snapshot_files:
        dt = get_snapshot_datetime(file_path)
        if dt:
            valid_snapshots.append((file_path, dt))

    # Sort descending by datetime (newest first)
    valid_snapshots.sort(key=lambda x: x[1], reverse=True)

    keep_set: Set[Path] = set()

    # Group by calendar day (YYYY-MM-DD)
    by_day: Dict[str, List[Tuple[Path, datetime.datetime]]] = {}
    for path, dt in valid_snapshots:
        day_key = dt.strftime("%Y-%m-%d")
        by_day.setdefault(day_key, []).append((path, dt))

    # Keep newest for up to 14 distinct days
    sorted_days = sorted(by_day.keys(), reverse=True)
    daily_days = sorted_days[:14]
    for day in daily_days:
        # Keep the latest snapshot of that day
        keep_set.add(by_day[day][0][0])

    # For weekly retention: consider remaining days / snapshots
    # Group remaining by ISO year and week (YYYY-Www)
    by_week: Dict[str, List[Tuple[Path, datetime.datetime]]] = {}
    for path, dt in valid_snapshots:
        day_key = dt.strftime("%Y-%m-%d")
        if day_key not in daily_days:
            week_key = dt.strftime("%G-W%V")
            by_week.setdefault(week_key, []).append((path, dt))

    sorted_weeks = sorted(by_week.keys(), reverse=True)
    weekly_weeks = sorted_weeks[:4]
    for week in weekly_weeks:
        keep_set.add(by_week[week][0][0])

    prune_set = {path for path, _ in valid_snapshots if path not in keep_set}
    return keep_set, prune_set


def prune_old_backups(backup_dir: Path = BACKUP_DIR) -> List[Path]:
    """Prune backups exceeding the retention policy."""
    if not backup_dir.exists():
        return []

    snapshot_files = [p for p in backup_dir.glob("prawko_*.sqlite") if p.is_file()]
    _, prune_set = calculate_retention(snapshot_files)

    pruned = []
    for path in prune_set:
        try:
            path.unlink()
            pruned.append(path)
            logger.info(f"Pruned old backup: {path.name}")
        except Exception as e:
            logger.warning(f"Failed to prune {path}: {e}")

    return pruned


def create_backup(db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR) -> Path:
    """
    Create a timestamped SQLite snapshot using the online backup API.
    Runs integrity check on the newly created snapshot and prunes old backups.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Source database not found at {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = backup_dir / f"prawko_{timestamp}.sqlite"

    logger.info(f"Creating online backup from {db_path} to {target_path}...")
    
    # Use SQLite online backup API
    src_conn = sqlite3.connect(db_path, timeout=30.0)
    dst_conn = sqlite3.connect(target_path, timeout=30.0)
    try:
        src_conn.backup(dst_conn, pages=100)
    finally:
        dst_conn.close()
        src_conn.close()

    # Verify backup integrity
    ok, msg = verify_sqlite_integrity(target_path)
    if not ok:
        target_path.unlink(missing_ok=True)
        raise RuntimeError(f"Backup verification failed: {msg}")

    logger.info(f"Backup successfully created and verified: {target_path.name}")
    prune_old_backups(backup_dir)
    return target_path


def restore_backup(backup_file: Path, target_db: Path = DB_PATH) -> bool:
    """
    Restore a backup to target_db after verifying PRAGMA integrity_check.
    Performs safe atomic swap.
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    logger.info(f"Verifying integrity of backup {backup_file} before restore...")
    ok, msg = verify_sqlite_integrity(backup_file)
    if not ok:
        logger.error(f"Cannot restore corrupted backup! {msg}")
        raise ValueError(f"Integrity check failed: {msg}")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_db.with_suffix(".restoring.tmp")

    try:
        shutil.copy2(backup_file, temp_target)
        # Verify temporary copy as well
        ok_temp, msg_temp = verify_sqlite_integrity(temp_target)
        if not ok_temp:
            raise RuntimeError(f"Integrity check on copied file failed: {msg_temp}")

        # Atomic replacement
        if target_db.exists():
            # Remove associated WAL and SHM files if any
            for suffix in ["-wal", "-shm"]:
                wal_file = target_db.parent / (target_db.name + suffix)
                if wal_file.exists():
                    wal_file.unlink(missing_ok=True)

        temp_target.replace(target_db)
        logger.info(f"Successfully restored database to {target_db} from {backup_file}")
        return True
    except Exception as e:
        if temp_target.exists():
            temp_target.unlink(missing_ok=True)
        logger.error(f"Restore failed: {e}")
        raise


def get_latest_snapshot(backup_dir: Path = BACKUP_DIR) -> Path | None:
    """Return the path to the newest snapshot if any exists."""
    if not backup_dir.exists():
        return None
    snapshots = [p for p in backup_dir.glob("prawko_*.sqlite") if p.is_file() and get_snapshot_datetime(p)]
    if not snapshots:
        return None
    snapshots.sort(key=lambda p: get_snapshot_datetime(p) or datetime.datetime.min, reverse=True)
    return snapshots[0]


def check_and_auto_backup(db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR) -> Path | None:
    """
    Called on app startup: if newest snapshot is older than 24h or none exists,
    creates a new snapshot safely. Non-blocking/safe: catches exceptions and logs.
    """
    try:
        if not db_path.exists():
            logger.info("Database file does not exist yet; skipping startup backup.")
            return None

        latest = get_latest_snapshot(backup_dir)
        now = datetime.datetime.now()

        if latest:
            latest_dt = get_snapshot_datetime(latest)
            if latest_dt and (now - latest_dt) < datetime.timedelta(hours=24):
                logger.info(f"Recent snapshot exists ({latest.name}); no startup backup needed.")
                return None

        logger.info("No recent snapshot within 24 hours found. Running startup backup...")
        return create_backup(db_path, backup_dir)
    except Exception as e:
        logger.error(f"Startup backup failed (non-blocking): {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Prawko B Database Backup & Restore Tool")
    parser.add_argument("--restore", type=str, help="Restore database from given backup file")
    parser.add_argument("--prune-only", action="store_true", help="Run retention pruning without creating a backup")
    args = parser.parse_args()

    if args.restore:
        restore_path = Path(args.restore)
        try:
            restore_backup(restore_path)
            print(f"Restore completed successfully from {restore_path}")
        except Exception as e:
            print(f"Restore failed: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.prune_only:
        pruned = prune_old_backups()
        print(f"Pruned {len(pruned)} snapshots.")
    else:
        try:
            backup_file = create_backup()
            print(f"Backup created: {backup_file}")
        except Exception as e:
            print(f"Backup failed: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
