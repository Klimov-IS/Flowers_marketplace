#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/flower-market"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="flower_market_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump via docker, compress with gzip
sudo docker exec flower_postgres pg_dump -U flower_user flower_market | gzip > "$BACKUP_DIR/$FILENAME"

# Verify backup is not empty (minimum 1KB)
FILE_SIZE=$(stat -f%z "$BACKUP_DIR/$FILENAME" 2>/dev/null || stat -c%s "$BACKUP_DIR/$FILENAME" 2>/dev/null)
if [ "$FILE_SIZE" -lt 1024 ]; then
    echo "ERROR: Backup file too small (${FILE_SIZE} bytes), possibly failed"
    rm -f "$BACKUP_DIR/$FILENAME"
    exit 1
fi

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

SIZE=$(du -h "$BACKUP_DIR/$FILENAME" | cut -f1)
echo "$(date): Backup OK: $FILENAME ($SIZE)"
