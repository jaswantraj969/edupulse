# Privacy scan of the git history

Tool: [`scripts/privacy_scan.py`](../../scripts/privacy_scan.py). It walks **every commit on all
refs** and **every version of every file ever committed** and checks:

| Check | Rule |
|---|---|
| Commit identities | author and committer e-mail must be the GitHub noreply address (or a demo domain) |
| Commit messages | no `Co-Authored-By` trailers |
| E-mail addresses in files | only reserved/demo domains (`edupulse.example`, `example.com/.org`, test fixtures) |
| Local absolute paths | Windows user-profile paths (drive letter + `Users` folder + name), the Git-Bash form of the same, and Linux/macOS home directories |
| Secret patterns | private keys, AWS keys, GitHub/Slack tokens, `api_key`/`secret_key` assignments |
| Forbidden files | `.env*` (except `.env.example`), `id_rsa`, `*.pem`, `*.p12`, `*.key` |
| File size | any file version larger than 1 MB |
| Runtime terms | strings supplied on the command line (`--term`) — used for the local username, the owner's personal e-mail, the local folder name and the actual local secret values; they are searched for but never printed |

The scanner was first run against a throw-away repository seeded with one planted example of
each problem (local path, personal e-mail, `.env`, 2 MB file, `Co-Authored-By`, foreign commit
identity, runtime term). It reported all of them, which also exposed and fixed a parser bug
(trailing log separator) before the real scan.

## Results

| Scan | Commits | File versions | Runtime terms | Result |
|---|---|---|---|---|
| Identity, paths, e-mails, secrets, files + username / personal e-mail / folder name | 9 | 292 | 5 | no findings |
| Same + the three secret values from the local `.env` | 9 | 292 | 3 | no findings |

Additional checks: `git ls-files` contains no `.env`; the committer e-mail is set in the
repository-local git config only; raw UCI data (`ml/data/raw/`) is git-ignored. The scan is
repeated after the last commit before publishing; its output is in
`docs/process/REVIEW_PACKET.md` (M9).
