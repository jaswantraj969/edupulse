#!/usr/bin/env bash
# Smoke test for a deployed EduPulse.
#   ./smoke_test.sh https://demo.example.org [--insecure]
# Checks: health and readiness, login page, HTTP -> HTTPS redirect, security headers, and (in a
# public demo) that blocked actions return 403. It never changes data: the blocked actions are
# sent with ids that do not exist, so even a missing guard would only produce a 404 (which this
# script reports as a failure).
# --insecure accepts a self-signed certificate (for a local test with EDUPULSE_DOMAIN=localhost).
set -uo pipefail

url="${1:-}"
if [[ ! "$url" =~ ^https:// ]]; then
  echo "usage: $0 https://<domain>[:port] [--insecure]" >&2
  exit 2
fi
url="${url%/}"
curl_opts=(--silent --show-error --max-time 20)
[ "${2:-}" = "--insecure" ] && curl_opts+=(--insecure)
python="${PYTHON:-python3}"  # override with PYTHON=... where python3 is not the interpreter
"$python" -c "import json" 2>/dev/null || { echo "$python is required (set PYTHON=...)" >&2; exit 2; }

failures=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }
status() { curl "${curl_opts[@]}" -o /dev/null -w '%{http_code}' "$@"; }
json() { "$python" -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

# 1. Health and readiness
code=$(status "$url/api/v1/health")
if [ "$code" = 200 ]; then pass "health endpoint (200)"; else fail "health endpoint returned $code"; fi
ready=$(curl "${curl_opts[@]}" "$url/api/v1/ready")
if [ "$(printf '%s' "$ready" | json "d.get('status')" 2>/dev/null)" = ready ]; then
  pass "readiness: $ready"
else
  fail "readiness: $ready"
fi

# 2. Login page (the single-page app)
page=$(curl "${curl_opts[@]}" -w '\n%{http_code}' "$url/login")
if [ "${page##*$'\n'}" = 200 ] && printf '%s' "$page" | grep -q '<div id="root">'; then
  pass "login page (200, app shell)"
else
  fail "login page"
fi

# 3. HTTP -> HTTPS redirect
host_port="${url#https://}"
host="${host_port%%:*}"
http_url="http://${host}${HTTP_PORT:+:$HTTP_PORT}/login"
redirect=$(curl "${curl_opts[@]}" -o /dev/null -w '%{http_code} %{redirect_url}' "$http_url")
if [[ "$redirect" =~ ^30[178]\ https:// ]]; then
  pass "HTTP redirects to HTTPS ($redirect)"
else
  fail "HTTP -> HTTPS redirect ($http_url gave: $redirect)"
fi

# 4. Security headers on the app and on the API
check_headers() {
  local target="$1"; shift
  local headers
  headers=$(curl "${curl_opts[@]}" -D - -o /dev/null "$target" | tr -d '\r' | tr '[:upper:]' '[:lower:]')
  for expected in "$@"; do
    if printf '%s\n' "$headers" | grep -q "^${expected}"; then
      pass "header on ${target#"$url"}: $expected"
    else
      fail "header missing on ${target#"$url"}: $expected"
    fi
  done
}
check_headers "$url/login" \
  "strict-transport-security: max-age=" \
  "content-security-policy: default-src 'self'" \
  "x-content-type-options: nosniff" \
  "x-frame-options: deny" \
  "referrer-policy:"
check_headers "$url/api/v1/health" \
  "strict-transport-security: max-age=" \
  "content-security-policy: default-src 'none'" \
  "x-content-type-options: nosniff" \
  "x-frame-options: deny" \
  "x-request-id:"

# 5. Public demo: blocked actions return 403 disabled_in_public_demo
meta=$(curl "${curl_opts[@]}" "$url/api/v1/meta")
if [ "$(printf '%s' "$meta" | json "d.get('public_demo')" 2>/dev/null)" != True ]; then
  echo "SKIP  blocked actions (public demo is off on this server)"
else
  email=$(printf '%s' "$meta" | json "[a for a in d['demo_accounts'] if a['role']=='admin'][0]['email']")
  password=$(printf '%s' "$meta" | json "[a for a in d['demo_accounts'] if a['role']=='admin'][0]['password']")
  token=$(curl "${curl_opts[@]}" --data-urlencode "username=$email" --data-urlencode "password=$password" \
    "$url/api/v1/auth/login" | json "d.get('access_token','')" 2>/dev/null)
  if [ -z "$token" ]; then
    fail "could not sign in as the demo administrator"
  else
    auth=(-H "Authorization: Bearer $token")
    blocked() {
      local label="$1"; shift
      local body
      body=$(curl "${curl_opts[@]}" "${auth[@]}" -w '\n%{http_code}' "$@")
      if [ "${body##*$'\n'}" = 403 ] && printf '%s' "$body" | grep -q '"disabled_in_public_demo"'; then
        pass "blocked in public demo: $label"
      else
        fail "not blocked: $label (got ${body##*$'\n'})"
      fi
    }
    for resource in students teachers staff classes; do
      blocked "delete $resource" -X DELETE "$url/api/v1/$resource/999999999"
    done
    for resource in students teachers staff; do
      blocked "import $resource" -X POST -F "file=id;filename=empty.csv;type=text/csv" \
        "$url/api/v1/$resource/import"
    done
    blocked "approve account" -X POST -H 'Content-Type: application/json' -d '{"role":"admin"}' \
      "$url/api/v1/account-requests/999999999/approve"
    blocked "reject account" -X POST -H 'Content-Type: application/json' -d '{}' \
      "$url/api/v1/account-requests/999999999/reject"
    # The demo admin's own e-mail: even without the guard this would be a 409, never a new user.
    blocked "create admin user" -X POST -H 'Content-Type: application/json' \
      -d "{\"email\":\"$email\",\"full_name\":\"x\",\"password\":\"Smoke-Test-Pass-1\",\"role\":\"admin\"}" \
      "$url/api/v1/auth/register"
  fi
fi

echo
if [ "$failures" -eq 0 ]; then
  echo "RESULT: all checks passed"
else
  echo "RESULT: $failures check(s) failed"
  exit 1
fi
