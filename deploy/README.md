# Deploying EduPulse on a VPS

This folder runs EduPulse on one Linux server with Docker Compose:

| Service | Role | Reachable from the internet |
|---|---|---|
| `caddy` | The only entry point: HTTPS (automatic Let's Encrypt certificate), redirect from HTTP, HSTS. Sends `/api/*` to `api` and everything else to `web` | **yes — ports 80 and 443 only** |
| `web` | nginx serving the single-page app | no |
| `api` | FastAPI; applies database migrations at start; trusts `X-Forwarded-For` from Caddy's fixed address only | no |
| `db` | PostgreSQL 16 | no |
| `backup` | Daily compressed `pg_dump` into the `db-backups` volume (kept 14 days) | no |
| `demo-reset` | Public demo only: seeds an empty database, then resets it to the synthetic seed every 6 hours | no |

Every service restarts automatically and has CPU and memory limits. Logs are rotated (5 × 10 MB per service).

**Public demo mode** (`EDUPULSE_PUBLIC_DEMO=true`, the default in `.env.example`) is meant for an installation that anyone may use:
- Deleting records, CSV import, approving or rejecting accounts, and creating administrators are refused for everyone (HTTP 403 `disabled_in_public_demo`); the buttons are disabled in the app.
- Every page shows "Public demo — synthetic data, reset every 6 hours".
- The demo accounts and their password are shown on the login page.

**Never put real student data in a public demo.** For a private installation with real data, set `EDUPULSE_PUBLIC_DEMO=false`, `EDUPULSE_DEMO_MODE=false` and leave `EDUPULSE_DEMO_PASSWORD` empty.

## 1. Get a server

Any VPS with **Ubuntu 24.04 LTS**, **2 vCPU and 2 GB RAM or more** (4 GB is comfortable while images build) and 20 GB of disk will do. Examples: Hetzner Cloud CX22 or CPX11, DigitalOcean Basic 2 GB, or Vultr / Linode 2 GB. Add your SSH key when you create it. Note the server's public IPv4 address.

## 2. Give it a name

HTTPS needs a DNS name that points at the server's IP address. Either:

- **Your own domain:** at your DNS provider, create an `A` record such as `edupulse.example.com` → the server IP.
- **A free name:** create a subdomain at <https://www.duckdns.org> (for example `my-edupulse.duckdns.org`) and set it to the server IP. Alternatively, `<ip-with-dashes>.sslip.io` (for example `203-0-113-5.sslip.io`) resolves to that IP with no sign-up.

Check that it resolves before going on: `dig +short <your-name>` must print the server IP.

## 3. Prepare the server (once)

Log in as root (`ssh root@<server-ip>`), then:

```bash
# Updates and a non-root user with sudo
apt update && apt -y upgrade
adduser --gecos "" edupulse                 # choose a password
usermod -aG sudo edupulse
rsync --archive --chown=edupulse:edupulse ~/.ssh ~edupulse/

# Firewall: only SSH, HTTP and HTTPS (443/udp is HTTP/3)
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

# Optional: disable root and password logins over SSH
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

Docker publishes ports past `ufw`. That is why only Caddy publishes any: the database and the API have no published ports.

Log in again as the new user (`ssh edupulse@<server-ip>`) and install Docker from Docker's official repository:

```bash
sudo apt -y install ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
exit   # log in again so the docker group applies
```

## 4. Install EduPulse

```bash
git clone https://github.com/jaswantraj969/edupulse.git
cd edupulse/deploy
./make_env.sh <your-name> <your-email>     # e.g. ./make_env.sh my-edupulse.duckdns.org me@example.org
```

`make_env.sh` writes `deploy/.env` with random secrets: the database password, the JWT secret and the demo password. The file is readable only by you and is git-ignored. Review it (`nano .env`):

- `EDUPULSE_PUBLIC_DEMO=true` for a public demo; `false` for a private installation.
- `EDUPULSE_DEMO_RESET_HOURS` (default 6).

Then build and start:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps        # all services "Up"; api "healthy"
```

The first build takes a few minutes. In a public demo the `demo-reset` service loads the synthetic data within a minute of the API becoming healthy. For a private installation with demo data, run:

```bash
docker compose -f docker-compose.prod.yml exec api python -m app.seed
```

## 5. Verify

```bash
./smoke_test.sh https://<your-name>
```

It checks health and readiness, the login page, the HTTP → HTTPS redirect, the security headers and, in a public demo, that every blocked action returns 403. It changes no data. The last line must be `RESULT: all checks passed`.

Then open `https://<your-name>` and sign in with a demo account from the login page.

## Everyday operations

All commands run in `edupulse/deploy`.

| Task | Command |
|---|---|
| Status | `docker compose -f docker-compose.prod.yml ps` |
| Logs (all / one service) | `docker compose -f docker-compose.prod.yml logs -f --tail=200` / `... logs -f api` |
| Update to the latest version | `git pull && docker compose -f docker-compose.prod.yml up -d --build` (migrations run automatically) |
| Restart | `docker compose -f docker-compose.prod.yml restart` |
| Reset the public demo now | `docker compose -f docker-compose.prod.yml exec demo-reset python -m app.demo_reset` |
| Stop (data kept) | `docker compose -f docker-compose.prod.yml down` |

### Backups

The `backup` service writes `edupulse-<UTC time>.sql.gz` to the `db-backups` volume once a day and deletes files older than `BACKUP_KEEP_DAYS`.

List the backups, or copy one off the server (recommended: keep copies elsewhere):

```bash
docker compose -f docker-compose.prod.yml exec backup ls -lh /backups
docker compose -f docker-compose.prod.yml cp backup:/backups/<file>.sql.gz .
```

To restore a backup (this replaces the current data):

```bash
docker compose -f docker-compose.prod.yml stop api demo-reset web
docker compose -f docker-compose.prod.yml exec db dropdb -U edupulse edupulse
docker compose -f docker-compose.prod.yml exec db createdb -U edupulse edupulse
docker compose -f docker-compose.prod.yml exec -T backup sh -c 'gunzip -c /backups/<file>.sql.gz | psql -q'
docker compose -f docker-compose.prod.yml start api web demo-reset
```

In a public demo the next scheduled reset replaces restored data anyway.

## Limits of this setup

- **One server, one API process.** The login and sign-up rate limits are in memory and reset when the API restarts.
- **Backups stay on the same server** until you copy them elsewhere.
- **Public demo reset is time-based** (counted from when `demo-reset` started), not at fixed clock times.
- Changing the internal subnet (`172.31.58.0/24`) means changing Caddy's address in both `docker-compose.prod.yml` entries (`ipv4_address` and `EDUPULSE_TRUSTED_PROXY`).
