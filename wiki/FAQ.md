## What do I need to run a lab?

Docker with Compose v2, and `python3` for the flag checker. Clone, enter a
lab, `docker compose up -d`, open the host port.

## Do I need an account?

No. There is no scoring server. You verify solves locally.

## Can I read the source to find the flag?

Yes. Reading the lab source is a legitimate solve. Open labs work that way.
The repository stores only the SHA-256 hash; the plaintext lives inside the
service.

## What is the flag format?

`duck{...}`. Lowercase letters, digits, and underscores between the braces,
16 to 40 characters.

## How do I grade a lab?

A four-tier ladder from `easy` to `insane`. Grades describe action, not
time. See [Tracks and Difficulty](Tracks-and-Difficulty).

## How do I write my own lab?

Copy `labs/_template/`, fill it in, run the validator, open a pull request.
See [Authoring a Lab](Authoring-a-Lab).

## What does CI check?

Structure, metadata, and flag hygiene. With `--compose` it also runs
`docker compose config`. A lab that passes can merge.

## Can I use `python:latest`?

No. Pin base images to full version tags. `python:3.12-alpine` yes,
`python:latest` no.

## What should I do with a broken lab?

Open an issue with the lab issue form, or a pull request with a fix. The
vulnerabilities inside labs are the product and need no report.

## What license covers my contribution?

By opening a pull request you agree your code falls under Apache-2.0 and
your written content under CC-BY-4.0. See the README for the split.

## Where do writeups go?

Anywhere you like. Publish them on your own site and link the lab so other
people can follow your path.
