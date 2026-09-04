# Brand

The openlabs brand covers the color, type, and badge system. This page
explains the tokens and how the automated pipeline keeps them consistent
across the README, the wiki, and CI.

## Color tokens

Four colors carry the brand. Ember is the only saturated one.

| Token | Hex | Use |
| --- | --- | --- |
| Ink | `#1E1E1E` | text, icons on light surfaces |
| Warm | `#F4F2F1` | light surfaces, cards |
| Canvas | `#1C1916` | dark surfaces, badge backgrounds |
| Ember | `#FF3616` | accents, the live-lab count, active states |

Dark and light variants of every badge exist. They switch with the viewer
prefers-color-scheme using a `<picture>` element. Light variants use Ink
text on Warm fields. Dark variants use Warm text on Canvas fields. Ember
appears only on the lab-count badge.

## Type

Funnel Display is the brand typeface. It is vendored under
`.github/assets/fonts/` as `FunnelDisplay-Regular.otf` and
`FunnelDisplay-Bold.otf`, licensed under SIL OFL 1.1. The badge generator
renders labels with Funnel Display. The repo does not ship web fonts; the
badges are the only place the face is drawn.

## Badges and chips

`.github/assets/badges/` holds 18 SVGs. The generator draws flat-square,
sharp-cornered, shadowless badges with the brand colors and Funnel Display
labels. A badge carries an identity label, such as `docker` or `Apache-2.0`.
A chip carries a difficulty: `easy`, `medium`, `hard`, `insane`.

Never edit these SVGs by hand. Change `scripts/make_badges.py` and
regenerate so output stays byte-identical between runs. CI fails the brand
workflow if regeneration is not deterministic.

## Asset versioning

GitHub's camo proxy caches remote images aggressively. A stale cache can
show old badges. To force a refresh, every asset reference carries a
content-hash version parameter:

```text
src=".github/assets/badge.svg?v=6052eb0b"
```

The hash is the first 8 characters of the file's SHA-256. A change to the
asset changes the hash, which changes the URL, which bypasses the cache.

Never hand-edit `?v=` values. Run `scripts/sync_wiki.py bump`. It rewrites
the parameter in the README and every `wiki/*.md` that references an asset,
and it normalizes the live-lab count in the README heading. The command is
idempotent. A second run with nothing to change prints
`asset versions up to date`.

## Challenge sheet

Every lab ships a print challenge sheet, generated from `lab.yml` and the
lab `README.md` by `scripts/make_lab_pdf.py` and styled by
`templates/labsheet.cls`. It is a template engine, not a prose writer: the
class owns the layout, the generator fills fixed slots, and all wording and
structure come from the lab author.

The sheet is a print translation of the same brand. Funnel Display carries
the display hierarchy, Geist the body, Geist Mono the labels and code. One
warm-neutral ramp runs from Ink down through Soft and Dim to a hairline rule
colour; Ember appears exactly twice, once on the difficulty value and once
on the active meter segment.

Typography is set by size plus explicit leading and size-specific tracking
(`fontsize{}{}` + `LetterSpace`), never a blunt scale factor. Vertical
spacing is pitched on a shared 3mm beat so every gap is proportional.

Two invariants the pipeline enforces:

- The sheet is generated, never hand-edited. Change `templates/labsheet.cls`
  or the generator and re-run `make_lab_pdf.py`.
- Labels that overflow their measure fail CI. The labs workflow rebuilds
  every sheet with `--all --strict`, which exits nonzero on any
  overfull/underfull box.

Requires `xelatex` and `rsvg-convert`. The rendered sheet sits next to its
lab as `labs/<track>/<lab>/<name>.pdf`.

## Pipeline

Scripts automate the brand:

```bash
python3 scripts/make_badges.py           # regenerate badges and chips
python3 scripts/make_lab_pdf.py --all --strict   # rebuild every lab sheet
python3 scripts/sync_wiki.py bump        # hash-stamp asset refs (?v=)
python3 scripts/sync_wiki.py wiki        # publish wiki/ to the wiki repo
```

`make_badges.py` needs `fonttools`. It installs from
`requirements-dev.txt`. `sync_wiki.py` is pure standard library plus git. It
writes `MANIFEST.json` into the badges directory as a build artifact; the
file is gitignored and never committed.

`sync_wiki.py wiki` clones `Duckurity/openlabs.wiki`, copies `wiki/*.md` in,
commits as `github-actions[bot]` in CI, and pushes. The push token is read
from `WIKI_PUSH_TOKEN`. The script hands the token to git through a
temporary credential helper, so it never appears in a URL, in `argv`, or in
commit metadata. When no token is set, the script falls back to the local
git credentials, which is how a contributor pushes from a workstation.
Use `--no-push` to dry-run the sync without touching the remote.
