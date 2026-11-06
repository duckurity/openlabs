# VaultCorp — automated verification script

`verify_solve.py` replays the full intended 6-stage exploit chain against a
running instance of the lab, end to end, and prints the recovered flag. It
exists as evidence that the intended solve path actually works, and as a
regression check for future changes to the app.

## Requirements

- Python 3.8+
- `pip install requests`
- A running instance of the lab (`docker compose up --build` from `bin/`)

## Usage

```bash
python3 verify_solve.py --base-url http://localhost:5000
```

To also assert the flag matches a known value (useful in CI):

```bash
python3 verify_solve.py --base-url http://localhost:5000 \
    --expect-flag duck{...}
```

Exit code is `0` on a successful solve (and a matching `--expect-flag`, if
given), non-zero otherwise.

## What it does

1. Registers a fresh, lowest-privilege account.
2. Fetches `/js/user-utils.js` as that account and decodes the leaked
   `prod` fixture (XOR `0x42` + Base64) to recover the tenant Admin's
   `LocalId` and `ApiToken`.
3. Posts those to `/support_login` to escalate to an Admin session.
4. Abuses `/admin/import` (SSRF) to reach the unauthenticated Hangfire
   job-creation endpoint over loopback, bypassing the naive string-blacklist
   WAF with the alternate loopback literal `127.1`.
5. Creates a Hangfire job that runs `cat /app/flag.txt` via
   `CommandExecutorJob`, writing its output into `wwwroot`.
6. Fetches that output file and extracts the flag.
