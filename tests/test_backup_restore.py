"""
Tests for SQLite backup, retention pruning, and restore drill (Task S1).
"""

import datetime
import sqlite3
import shutil
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.backup_db import (
    create_backup,
    restore_backup,
    verify_sqlite_integrity,
    calculate_retention,
    prune_old_backups,
    check_and_auto_backup,
    get_latest_snapshot,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary populated SQLite database."""
    db_file = tmp_path / "test_prawko.sqlite"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, login TEXT UNIQUE, password_hash TEXT);")
    cursor.execute("INSERT INTO users (login, password_hash) VALUES ('testuser', 'hash123');")
    cursor.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, val TEXT);")
    cursor.execute("INSERT INTO test_data (val) VALUES ('original_data');")
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Create a temporary directory for backups."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def test_backup_creation_and_integrity(temp_db, temp_backup_dir):
    """Verify create_backup creates a valid snapshot that passes integrity check."""
    backup_path = create_backup(db_path=temp_db, backup_dir=temp_backup_dir)
    assert backup_path.exists()
    assert backup_path.name.startswith("prawko_")

    ok, msg = verify_sqlite_integrity(backup_path)
    assert ok is True
    assert msg == "ok"

    # Verify data in backup
    conn = sqlite3.connect(backup_path)
    cursor = conn.cursor()
    cursor.execute("SELECT val FROM test_data WHERE id = 1;")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "original_data"


def test_restore_drill_tamper_and_recover(temp_db, temp_backup_dir):
    """
    Restore drill:
    1. Create snapshot of original database.
    2. Tamper / modify original database.
    3. Restore from snapshot.
    4. Verify integrity and restored state.
    """
    # Step 1: Create backup
    backup_path = create_backup(db_path=temp_db, backup_dir=temp_backup_dir)

    # Step 2: Tamper / modify original db
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("UPDATE test_data SET val = 'tampered_data' WHERE id = 1;")
    cursor.execute("INSERT INTO test_data (val) VALUES ('unwanted_row');")
    conn.commit()
    conn.close()

    # Verify tampering happened
    conn = sqlite3.connect(temp_db)
    row = conn.execute("SELECT val FROM test_data WHERE id = 1;").fetchone()
    conn.close()
    assert row[0] == "tampered_data"

    # Step 3: Restore from backup
    restore_success = restore_backup(backup_file=backup_path, target_db=temp_db)
    assert restore_success is True

    # Step 4: Verify restored state and integrity
    ok, msg = verify_sqlite_integrity(temp_db)
    assert ok is True
    assert msg == "ok"

    conn = sqlite3.connect(temp_db)
    row = conn.execute("SELECT val FROM test_data WHERE id = 1;").fetchone()
    all_rows = conn.execute("SELECT val FROM test_data;").fetchall()
    conn.close()

    assert row[0] == "original_data"
    assert len(all_rows) == 1


def test_restore_rejects_corrupted_file(temp_db, temp_backup_dir):
    """Verify restore_backup rejects a corrupted/invalid backup file before modifying target."""
    corrupted_file = temp_backup_dir / "prawko_20260101_000000.sqlite"
    corrupted_file.write_bytes(b"THIS IS NOT A VALID SQLITE DATABASE FILE GARBAGE BYTES")

    with pytest.raises((ValueError, RuntimeError)):
        restore_backup(corrupted_file, target_db=temp_db)

    # Verify original db remains unchanged
    conn = sqlite3.connect(temp_db)
    row = conn.execute("SELECT val FROM test_data WHERE id = 1;").fetchone()
    conn.close()
    assert row[0] == "original_data"


def test_retention_policy_calculation(temp_backup_dir):
    """
    Test retention logic: 14 daily + 4 weekly snapshots, pruning older.
    """
    base_date = datetime.datetime(2026, 8, 14, 12, 0, 0)
    created_files = []

    # Generate snapshots spanning 40 days
    # Days 0..13 (14 days): 2 snapshots per day
    # Days 14..35 (3 weeks): 1 snapshot every 2 days
    # Days 36..45 (older): 1 snapshot every 3 days
    for days_ago in range(45, -1, -1):
        snapshot_dt = base_date - datetime.timedelta(days=days_ago)
        filename = f"prawko_{snapshot_dt.strftime('%Y%m%d_%H%M%S')}.sqlite"
        fpath = temp_backup_dir / filename
        fpath.write_text("stub", encoding="utf-8")
        created_files.append(fpath)

        # For recent 5 days, add a second snapshot on the same day
        if days_ago < 5:
            snapshot_dt2 = snapshot_dt + datetime.timedelta(hours=2)
            filename2 = f"prawko_{snapshot_dt2.strftime('%Y%m%d_%H%M%S')}.sqlite"
            fpath2 = temp_backup_dir / filename2
            fpath2.write_text("stub2", encoding="utf-8")
            created_files.append(fpath2)

    keep_set, prune_set = calculate_retention(created_files)

    # Total kept should be at most 14 daily + 4 weekly = 18 snapshots
    assert len(keep_set) <= 18
    assert len(keep_set) >= 14
    assert len(prune_set) > 0
    assert keep_set.isdisjoint(prune_set)
    assert keep_set | prune_set == set(created_files)


def test_check_and_auto_backup(temp_db, temp_backup_dir):
    """Test automated startup backup trigger logic."""
    # First run when backup dir is empty -> creates backup
    b1 = check_and_auto_backup(db_path=temp_db, backup_dir=temp_backup_dir)
    assert b1 is not None
    assert b1.exists()

    # Second run immediately -> recent snapshot exists within 24h -> returns None
    b2 = check_and_auto_backup(db_path=temp_db, backup_dir=temp_backup_dir)
    assert b2 is None
