# AGENTS.md

Entry point for coding agents working in this repository.

## What this repo is

openlabs is a library of self-contained, Docker-based cybersecurity labs.
Each lab is a directory under `labs/<track>/<lab>/` holding `lab.yml`
metadata, a player-facing `README.md`, a compose file, and the lab service.
`scripts/validate.py` checks structure and metadata; `scripts/check.py`
verifies a player's flag against the stored SHA-256 hash.

## Structure

| Path | What it is |
|---|---|
| `labs/<track>/<lab>/` | one lab; tracks: `web`, `binary`, `crypto`, `network`, `osint` |
| `labs/_template/` | skeleton for new labs, skipped by validation |
| `scripts/validate.py` | CI validator, zero dependencies |
| `scripts/check.py` | player flag checker, zero dependencies |
| `scripts/make_badges.py` | badge and chip generator, needs `fonttools` and vendored fonts |
| `scripts/make_lab_pdf.py` | branded challenge-sheet PDF, template-driven, needs `xelatex` + `rsvg-convert` |
| `templates/labsheet.cls` | layout and type system the PDF fills; never edited by hand past the generator |
| `scripts/test_brand.sh` | integration-test the brand pipeline in a temp clone |
| `BRAND.md` | color, type, badge, and pipeline reference |
| `scripts/sync_wiki.py` | asset version bumps and wiki repo sync, zero dependencies |
| `scripts/sync_site_content.py` | generates `content/labs/` from `labs/` at build time; zero dependencies |
| `scripts/score_lab.py` | scores each lab 0-100 (structure, secrets, Dockerfile, compose, docs); blocks CI below 70 |
| `.github/assets/fonts/` | vendored Funnel Display cuts, SIL OFL 1.1 |
| `wiki/` | GitHub wiki source: player, authoring, and review guides |
| `app/`, `components/`, `content/`, `lib/`, `hooks/` | Next.js library site at the repo root, deployed to GitHub Pages |
| `content/labs/` | generated from `labs/` by `prebuild`/`predev`; gitignored, never edited by hand |
| `app/styles/theming.css` | design tokens: palette, type, radius; edit here, never hardcode values in components |
| `.github/workflows/site.yml` | syncs content, builds the site, and deploys to Pages on `main` |
| `.github/workflows/labs.yml` | CI: validator, security scans + score gate (min 70), content contracts |
| `.github/workflows/brand.yml` | regenerates badges, bumps asset versions, syncs the wiki |

## Voice rules for any text you write

- Short declarative sentences. Lead with the verb. One idea per sentence.
- Sentence case for headings.
- No exclamation marks, no em-dashes, no superlatives, no adverbs, no
  hacker-larp phrasing ("pwn", "1337").
- Terms: `lab`, `flag`, `solve`, `writeup`. Difficulty: `easy`, `medium`,
  `hard`, `insane`, lowercase in prose, uppercase only in mono badges.
- Put values in code spans: ports, commands, formats.

## Hard rules

- Flag format: `^duck\{[a-z0-9_]{16,40}\}$`. Plaintext flags appear only
  inside lab service files, never in `lab.yml`, lab `README.md`, `wiki/`,
  or anything outside `labs/`.
- Base images pinned to full version tags. No runtime network calls.
- One documented host port per lab.
- Code is Apache-2.0, written content is CC-BY-4.0. Do not relicense.

## Commands

```bash
python3 scripts/validate.py              # structure + metadata
python3 scripts/validate.py --compose    # + docker compose config
python3 scripts/check.py labs/web/duck-cross
python3 scripts/make_badges.py           # regenerate badges and chips
python3 scripts/make_lab_pdf.py --all --strict   # rebuild every lab sheet pdf
python3 scripts/sync_wiki.py bump        # hash-stamp asset refs (?v=)
python3 scripts/sync_wiki.py wiki        # publish wiki/ to the wiki repo
bash scripts/test_brand.sh               # integration-test the brand pipeline
python3 scripts/sync_site_content.py      # regenerate content/labs/ manually
python3 scripts/sync_site_content.py --check  # verify generated output matches
python3 scripts/score_lab.py --min 70     # score every lab, fail below 70
pnpm run build                            # build the library site
pnpm run dev                              # serve the site locally
```

CI runs the badge regeneration, version bumps, and wiki sync on every push
to `main` that touches labs, wiki, README, scripts, or assets. The labs
workflow also rebuilds each lab sheet with `make_lab_pdf.py --all --strict`,
so a layout whose boxes overflow its measure fails CI. Never edit generated
badges by hand; edit `scripts/make_badges.py` and regenerate. Never hand-edit
`?v=` values; run `sync_wiki.py bump`. Never hand-edit the sheet's layout;
edit `scripts/make_lab_pdf.py` or `templates/labsheet.cls`.

The `Sync wiki` step reads the `WIKI_PUSH_TOKEN` repository secret. A
fine-grained PAT with `Contents: Read and write` on
`Duckurity/openlabs.wiki` works; `GITHUB_TOKEN` is scoped to the main
repo and cannot reach the wiki. Without the secret, CI skips the push
and exits clean; run `sync_wiki.py wiki` from a workstation to push
with local git credentials.

<!-- contentbit:start -->

## contentbit content (generated — edits inside this block are overwritten)

This project validates Markdown content with contentbit. Documents are plain
Markdown plus directive blocks (`:::name{props} ... :::`), each with a schema.
Find the nearest `contentbit.config.*` or workspace package that declares
contentbit (it may be nested in a monorepo), and run commands from that
directory. The config holds the canonical content glob, registry, link fields,
and SEO config, so commands normally need no repeated project flags.
If the project has a `content:links` script, use it to build the internal-link
index; otherwise run `contentbit links <content glob>`.
If `contentbit.seo.config.ts` exists and the user is creating or revising a
search-targeted page, run `contentbit brief <key-or-slug> [content glob]` first
and treat the brief as the structure contract for the writer.

When writing or editing content:

1. Fetch the live authoring guide first — never guess block syntax:
   `contentbit instructions --audience llm`
2. For SEO-planned pages, fetch the page brief:
   `contentbit brief <key-or-slug>`
3. Write plain Markdown; use blocks where the guide's use-when guidance fits
   and satisfy any brief acceptance checks.
4. If sibling documents use `slug` / `linksTo`, read
   `.contentbit/link-index.json` from `contentbit links <content glob>` and
   author frontmatter links with existing slugs. When creating a linked page,
   include `keywords.primary` and `keywords.secondary` with search-intent
   phrases future agents can use to choose related pages.
5. Validate until clean (exit 0): `contentbit validate <file>`.
   Diagnostics print as `file:line:col severity CODE message` with fix hints.
   For link frontmatter, validate the full content glob so cross-file checks run.

When auditing content health:

- `contentbit doctor` prints a ranked,
  read-only repair plan: validation issues, link issues, thin sections,
  block-less long documents, and missing image alt text.
- `contentbit doctor --json` prints the
  same findings as structured JSON for agents and CI.
- `contentbit stats` prints raw JSON
  stats: outline word counts, block usage, link domains, and validation
  error/warning counts.
- `contentbit links [--fix]` builds
  `.contentbit/link-index.json`, reports dangling links/orphans, and rewrites
  alias references in `linksTo` when `--fix` is used.

If `contentbit` is unavailable, suggest `npx contentbit@latest init` instead
of inventing block syntax.

<!-- contentbit:end -->
