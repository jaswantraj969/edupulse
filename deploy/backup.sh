#!/bin/sh
# Daily compressed pg_dump of the EduPulse database into /backups (the db-backups volume).
# Runs inside the backup container (postgres:16-alpine); PG* variables come from compose.
set -eu

keep_days="${BACKUP_KEEP_DAYS:-14}"

backup() {
  file="/backups/edupulse-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
  if pg_dump --no-owner --no-privileges | gzip > "$file.partial"; then
    mv "$file.partial" "$file"
    echo "backup written: $file ($(wc -c < "$file") bytes)"
  else
    rm -f "$file.partial"
    echo "backup FAILED" >&2
  fi
  find /backups -name 'edupulse-*.sql.gz' -mtime "+$keep_days" -delete
}

backup
while true; do
  sleep 86400
  backup
done
