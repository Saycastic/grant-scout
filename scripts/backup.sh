#!/bin/bash
# Grant Scout — SQLite backup script
# Cron: 0 3 * * * /root/grant-scout/scripts/backup.sh

REPO_DIR="${GRANT_SCOUT_DIR:-/root/grant-scout}"
DB="$REPO_DIR/data/grant_scout.db"
BACKUP_DIR="$REPO_DIR/data/backups"
DATE=$(date +%F)
WEEKDAY=$(date +%u)  # 1=Mon 7=Sun
DAY=$(date +%d)

mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/monthly"

# Daily backup (keep 14)
DAILY="$BACKUP_DIR/daily/grant_scout_$DATE.db"
python3 -c "import sqlite3, shutil, sys; src=sys.argv[1]; dst=sys.argv[2]; conn=sqlite3.connect(src); bk=sqlite3.connect(dst); conn.backup(bk); bk.close(); conn.close()" "$DB" "$DAILY"
echo "[backup] Daily: $DAILY"

# Weekly (every Monday)
if [ "$WEEKDAY" = "1" ]; then
    cp "$DAILY" "$BACKUP_DIR/weekly/grant_scout_week_$DATE.db"
    echo "[backup] Weekly saved"
fi

# Monthly (1st of month)
if [ "$DAY" = "01" ]; then
    cp "$DAILY" "$BACKUP_DIR/monthly/grant_scout_month_$DATE.db"
    echo "[backup] Monthly saved"
fi

# Cleanup: keep only 14 daily, 8 weekly, 6 monthly
ls -t "$BACKUP_DIR/daily/"*.db 2>/dev/null | tail -n +15 | xargs rm -f
ls -t "$BACKUP_DIR/weekly/"*.db 2>/dev/null | tail -n +9 | xargs rm -f
ls -t "$BACKUP_DIR/monthly/"*.db 2>/dev/null | tail -n +7 | xargs rm -f

echo "[backup] Done"
