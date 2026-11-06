# Build Instructions — v3

## What's new in v3

- `game.exe` and `checker.exe` are **completely independent files**. `checker.exe` does not take input from, or read anything produced by, `game.exe` at runtime.
- Each file has its **own independent secret/evidence** to recover through reverse engineering.
- `checker.exe` has **two gates** before it reveals the flag:
  1. The file password (= password 2, obtained by winning `game.exe`).
  2. A 16-byte hex value that **must be computed** — it is not stored anywhere in the binary. You have to read and understand the algorithm (`compute_check_value`) in the decompiled Pseudo-C in Ghidra and reimplement it yourself (typically with a small Python script, or a CyberChef recipe).
- Only if both are correct does the program compute the final AES key (combining the password and the hex value) and decrypt the flag.
- **The flag does not exist as plaintext in either binary** — not in `game.exe`, not in `checker.exe`. Even a `strings` scan of both files shows no trace of the flag format or either password.

---

## Build steps (MinGW / TDM-GCC on Windows)

Open a Command Prompt in the `src` folder:

```
gcc -o game.exe game.c base64.c -Wall
gcc -o checker.exe checker.c aes.c sha256.c -Wall
```

If you get a "gcc not recognized" error, make sure MinGW/TDM-GCC is added to PATH, or use its Start Menu shortcut (e.g. "TDM-GCC command prompt").

---

## Quick sanity test before shipping

### game.exe
Run it and follow this order:
1. Password: `r3v3rs3_m3_pl2`
2. Quiz answers: `4`, then `4B 33 79 21` (all 4 key bytes, with or without spaces), then `verify_sys_integrity`
3. Mini-game: `7`
4. It should print: `ch3ck3r_unl0ck_key` (this is password 2)

### checker.exe
Run it and follow this order:
1. Password: `ch3ck3r_unl0ck_key` (from `game.exe`)
2. Hex value: `2bb50ef99ea5dcea300e6efd3d8085e4`
3. It should print the flag: `duck{...}`

> Note: only `checker.c`'s embedded `FLAG_CIPHERTEXT` changed (to match the
> catalog's `^duck\{[a-z0-9_]{16,40}\}$` flag format — the previous flag
> had uppercase letters and symbols, which the catalog rejects). The
> password, the hex-value algorithm (`CHECK_SEED`/`CHECK_CONST`/
> `compute_check_value`), and `game.exe` are all byte-for-byte unchanged,
> so the documented solve path and every step of `Walkthrough.md` still
> apply exactly as written — only the final printed flag differs.
> `checker.exe` must be rebuilt from the updated `checker.c` (same build
> command above) before shipping; `game.exe` does not need rebuilding.

If these values don't match, there's a build problem — recheck the steps above.

---

## Negative tests (confirming correct rejection behavior)

- Wrong password in `checker.exe` → `"Incorrect password."`
- Correct password + wrong hex value → `"Incorrect value. Keep reversing."`
- In both cases: **the flag never appears in any error message.**

---

## Developer-only tools (DO NOT ship these to players)

- `gen_checker_v3.c` — computes every embedded constant in `checker.c` (password SHA-256, expected hex value, AES-encrypted flag). Only needed if you want to change the flag or any embedded constant.
- `sha256.c` / `test_sha256.c` — validates the SHA-256 implementation (already verified against official NIST test vectors — all PASS).

**When preparing the final deliverable for a player, ship only:**
- `game.exe`
- `checker.exe`

**Never ship:**
- Any `.c` or `.h` file
- Any `gen_*` or `test_*` tool or its compiled executable

Anyone who gets direct access to the source code would find every constant and algorithm already laid out, with no reverse engineering required.

---

## Design note

The hex value `checker.exe` needs is built from a **chained** algorithm (each byte's result depends on the previous byte's result, similar in spirit to AES-CBC but simplified) — meaning the player must compute it in order, from start to finish, not byte-by-byte independently. This raises the difficulty from "extract bytes and XOR-decode them" (the level in `game.exe`) to "understand and reimplement an algorithm" (the level required in `checker.exe`), so each file contributes a genuinely different kind of challenge instead of being a repeat of the other.
