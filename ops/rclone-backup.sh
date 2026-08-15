#!/usr/bin/env bash
# ==============================================================================
# Prawko B — Offsite SQLite Backup Synchronization via Rclone (Task P6)
# ==============================================================================
# Syncs local snapshots in data/backups/ to a cloud remote defined in BACKUP_REMOTE.
#
# Cron schedule (nightly at 04:00):
#   0 4 * * * /home/ubuntu/b/ops/rclone-backup.sh >> /var/log/rclone-backup.log 2>&1
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env if present
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

BACKUP_REMOTE="${BACKUP_REMOTE:-}"

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting automated SQLite backup & sync..."

if [[ -z "$BACKUP_REMOTE" ]]; then
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] WARNING: BACKUP_REMOTE is not set in environment or .env. Skipping offsite sync."
  exit 0
fi

# 1. Trigger local snapshot creation & retention cleanup
BACKUPS_DIR="$PROJECT_ROOT/data/backups"
mkdir -p "$BACKUPS_DIR"

if command -v python3 >/dev/null 2>&1; then
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Creating local backup snapshot..."
  python3 "$PROJECT_ROOT/tools/backup_db.py" || {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: Local backup snapshot creation failed."
    exit 1
  }
fi

# 2. Check if rclone is installed
if ! command -v rclone >/dev/null 2>&1; then
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: rclone is not installed on system."
  exit 1
fi

# 3. Synchronize data/backups to remote
REMOTE_TARGET="${BACKUP_REMOTE}"
if [[ "$REMOTE_TARGET" != *":"* ]]; then
  REMOTE_TARGET="${REMOTE_TARGET}:prawko-backups"
fi

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Syncing '$BACKUPS_DIR' to '$REMOTE_TARGET'..."
rclone sync "$BACKUPS_DIR" "$REMOTE_TARGET" --verbose

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Backup sync completed successfully."
