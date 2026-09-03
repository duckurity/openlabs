#!/usr/bin/env bash
# Integration test for the openlabs brand pipeline.
#
# Runs scripts/make_badges.py and scripts/sync_wiki.py against a fresh
# copy of the repository in a temporary directory, exercising the same
# operations the CI workflow performs. Fails loudly on any deviation.
#
# Exits non-zero if any check fails. Safe to run repeatedly.

set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"

# --- Preflight -------------------------------------------------------------

command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
command -v git     >/dev/null || { echo "git not found";     exit 1; }
python3 -c "import fontTools" 2>/dev/null \
    || { echo "fonttools not installed (pip install fonttools==4.63.0)"; exit 1; }

# --- Fixture ---------------------------------------------------------------

WORK="$(mktemp -d -t openlabs-brand-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

cp -R "$REPO" "$WORK/repo"
cd "$WORK/repo"
rm -rf .git
git init -q -b main
git add -A
git -c user.name=test -c user.email=test@x commit -q -m "fixture"

# --- make_badges -----------------------------------------------------------

echo "== make_badges =="
# We use --no-manifest so byte-identity between runs is preserved
# (MANIFEST.json includes a wall-clock timestamp).
out="$(python3 scripts/make_badges.py --out "$WORK/badges" --no-manifest)"
echo "$out"
echo "$out" | grep -q "1 lab; wrote 18 svgs" \
    || { echo "expected '1 lab; wrote 18 svgs' in: $out"; exit 1; }

# Determinism: a second run must produce byte-identical output.
mkdir -p "$WORK/badges2"
python3 scripts/make_badges.py --out "$WORK/badges2" --no-manifest >/dev/null
diff -r "$WORK/badges" "$WORK/badges2" >/dev/null \
    || { echo "make_badges.py is not deterministic"; exit 1; }
echo "determinism: ok"

# MANIFEST sanity (separate run with manifest enabled)
python3 scripts/make_badges.py --out "$WORK/badges-manifest" >/dev/null
test -f "$WORK/badges-manifest/MANIFEST.json" \
    || { echo "MANIFEST.json not written"; exit 1; }
python3 -c "
import json
m = json.load(open('$WORK/badges-manifest/MANIFEST.json'))
assert m['lab_count'] == 1, m
assert len(m['files']) == 18, m
print('manifest: ok')
"

# --- sync_wiki bump --------------------------------------------------------

echo "== sync_wiki bump =="
# The fixture already carries committed ?v= hashes, so strip them first
# to exercise a genuine bump from an unversioned state.
find . -name "*.md" -exec sed -i 's/?v=[0-9a-f]\{8\}//g' {} +
grep -q 'src=".github/assets/banner.png"' README.md \
    || { echo "fixture strip failed: banner ref has no ?v="; exit 1; }

first="$(python3 scripts/sync_wiki.py bump)"
echo "$first"
echo "$first" | grep -q ".github/assets/banner.png -> ?v=" \
    || { echo "banner.png not bumped: $first"; exit 1; }

# Idempotency: a second run must print 'asset versions up to date'.
second="$(python3 scripts/sync_wiki.py bump)"
echo "$second"
echo "$second" | grep -q "asset versions up to date" \
    || { echo "bump is not idempotent: $second"; exit 1; }
echo "idempotency: ok"

# Heading count normalization
grep -q "## Labs <sub>1 live</sub>" README.md \
    || { echo "heading count not normalized to 1"; exit 1; }

# --- sync_wiki wiki (dry run) ---------------------------------------------

echo "== sync_wiki wiki (no-push) =="
out="$(python3 scripts/sync_wiki.py wiki --no-push 2>&1)"
echo "$out"
# The remote is the real wiki, which we do not push to. But the script
# clones, copies, commits locally in a temp clone, then exits without
# pushing. We assert that path was taken.
echo "$out" | grep -Eq "wiki up to date|prepared commit in" \
    || { echo "unexpected wiki output: $out"; exit 1; }

# --- Credential helper shape ----------------------------------------------

echo "== credential helper =="
cred="$(mktemp -d)/helper.sh"
# Re-create exactly as sync_wiki.py does, then verify output shape.
cat > "$cred" <<'HELPER'
#!/bin/sh
printf 'username=x-access-token\npassword=%s\n' "$OPENLABS_WIKI_TOKEN"
HELPER
chmod 700 "$cred"
out="$(OPENLABS_WIKI_TOKEN=gh_test_dummy "$cred" get)"
echo "$out" | grep -q "^username=x-access-token$" \
    || { echo "helper: bad username line: $out"; exit 1; }
echo "$out" | grep -q "^password=gh_test_dummy$" \
    || { echo "helper: bad password line: $out"; exit 1; }
echo "credential helper: ok"

# --- Output stability -----------------------------------------------------

# Each generated SVG must have a closing </svg>, a width attribute,
# exactly one background <rect>, and at least one text <path>.
fail=0
for f in "$WORK/badges"/*.svg; do
    grep -q "</svg>" "$f" || { echo "$f missing </svg>"; fail=1; }
    grep -q "width="     "$f" || { echo "$f missing width"; fail=1; }
    p=$(grep -c "<path" "$f" || true)
    r=$(grep -c "<rect" "$f" || true)
    if [ "$p" -lt 1 ]; then echo "$f: no text paths"; fail=1; fi
    if [ "$r" -ne 1 ]; then echo "$f: expected 1 rect, got $r"; fail=1; fi
done
exit "$fail"
