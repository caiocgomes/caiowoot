#!/bin/bash
set -e
BACKUP_DIR="data"
DB_PATH="data/caiowoot.db"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
sqlite3 "$DB_PATH" ".backup ${BACKUP_DIR}/backup-${TIMESTAMP}.db"
find "$BACKUP_DIR" -name "backup-*.db" -mtime +7 -delete
echo "Backup complete: ${BACKUP_DIR}/backup-${TIMESTAMP}.db"
