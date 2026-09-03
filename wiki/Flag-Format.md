## The format

Every flag carries the mark:

```
duck{...}
```

- Lowercase letters, digits, and underscores between the braces
- 16 to 40 characters inside the braces
- Matches `^duck\{[a-z0-9_]{16,40}\}$`

## The hash

The repository never stores the plaintext flag. It stores the SHA-256 of the
full flag string, braces included, in `lab.yml` as `flag_hash`.

```bash
printf '%s' 'duck{your_flag_here}' | sha256sum
```

Copy the 64-hex output into `flag_hash`.

## The checker

Players verify a solve through `scripts/check.py`.

```bash
python3 scripts/check.py labs/web/duck-cross
```

The player types the flag. The script hashes it, compares it to `flag_hash`,
and prints `solved` or `not solved`.

## Rules for authoring

- Generate the flag body randomly.
- One flag per lab, never reused across labs.
- The plaintext appears only inside lab internals, the service files under
  the lab directory.
- `flag_hash` is the only flag artifact the validator trusts.

## Honesty by design

Reading the lab source to find the flag is a legitimate solve. Open labs
work that way. The plaintext sits inside the service precisely so players
can find it there. The hash prevents the repository itself from leaking it
into search indexes and feeds.
