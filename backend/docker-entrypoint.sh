#!/bin/sh
# Apply migrations, then start the API.
set -e
alembic upgrade head
# Trust X-Forwarded-For only from the reverse proxy (the web container in docker compose).
# Any other peer, including a client reaching the published API port directly, is identified by
# its own address, so it cannot pick a new per-client rate-limit key by forging the header.
TRUSTED_PROXY="${EDUPULSE_TRUSTED_PROXY:-127.0.0.1}"
case "$TRUSTED_PROXY" in
  *'*'*)
    echo "EDUPULSE_TRUSTED_PROXY must list the proxy's address, never '*'" >&2
    exit 1
    ;;
esac
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="$TRUSTED_PROXY"
