#!/usr/bin/env bash
# Create deploy/.env with freshly generated secrets.
#   ./make_env.sh <domain> <email-for-lets-encrypt>
# Refuses to overwrite an existing .env.
set -euo pipefail

cd "$(dirname "$0")"
if [ $# -ne 2 ]; then
  echo "usage: $0 <domain> <email-for-lets-encrypt>" >&2
  exit 2
fi
if [ -e .env ]; then
  echo "deploy/.env already exists; not overwriting it." >&2
  exit 1
fi
command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 1; }

domain="$1"
email="$2"
postgres_password="$(openssl rand -hex 24)"
jwt_secret="$(openssl rand -hex 48)"
# Policy: 12+ characters with upper-case, lower-case and a digit.
demo_password="Demo-$(openssl rand -hex 6)-Q7"

umask 077
sed \
  -e "s|^EDUPULSE_DOMAIN=.*|EDUPULSE_DOMAIN=${domain}|" \
  -e "s|^ACME_EMAIL=.*|ACME_EMAIL=${email}|" \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${postgres_password}|" \
  -e "s|^EDUPULSE_JWT_SECRET=.*|EDUPULSE_JWT_SECRET=${jwt_secret}|" \
  -e "s|^EDUPULSE_DEMO_PASSWORD=.*|EDUPULSE_DEMO_PASSWORD=${demo_password}|" \
  .env.example > .env

echo "Wrote deploy/.env (readable only by you). Demo password: ${demo_password}"
