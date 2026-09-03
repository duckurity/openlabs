Review checks whether a lab is honest, reproducible, and written in the
house voice. The validator checks the mechanics; you check the craft.

## Structure

- The lab lives under `labs/<track>/<lab>/` in its own directory.
- `lab.yml` is flat YAML with all five fields present and valid.
- `name` matches the directory name.
- The lab has a player `README.md` brief.
- `labs/_template/` is untouched.

## Mechanics

- `python3 scripts/validate.py` passes.
- `python3 scripts/validate.py --compose` passes.
- The lab runs from a clean clone.
- One documented host port. The brief and `docker-compose.yml` agree.

## Flags

- `duck{...}`, lowercase and digits and underscores, 16 to 40 characters.
- `flag_hash` is the SHA-256 of the full flag string, 64 lowercase hex.
- The plaintext flag appears only inside lab internals, never in the brief,
  `lab.yml`, or anywhere outside `labs/`.
- Verify the hash yourself: `printf '%s' 'duck{...}' | sha256sum`.
- One flag, never reused.

## Difficulty

- The grade matches the action, not the clock.
- The tier is chosen from `easy`, `medium`, `hard`, `insane`.
- A lab between tiers grades down.

## Service and supply chain

- The lab is self-contained and offline after pull.
- No runtime calls out, no license servers, no phone-home.
- Base images pinned to full version tags.

## Voice

- Short declarative sentences, one idea each.
- Sentence-case headings.
- No exclamation marks, no em-dashes, no superlatives, no adverbs.
- No larp phrasing.
- Values sit in code spans: ports, commands, formats.
- The brief points at the surface without handing over the solve.

## Craft

- The goal is stated as an instruction, not a hint.
- The description in `lab.yml` is one honest line.
- The story sets up stakes in two or three sentences.
- A clean clone + the brief + the goal is enough to start.

If any item fails, the pull request goes back for changes. A review that
merges a weak lab costs every player who reads it. Keep the bar.
