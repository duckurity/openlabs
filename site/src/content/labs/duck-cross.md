---
title: Duck Cross
tagline: A reports portal with a missing object-level authorization check.
track: web
difficulty: easy
port: "8080"
brief: >
  The duck cross portal collects crossing reports from wardens. Five reports
  are public. A restricted report holds something more interesting.
goal: >
  Find the restricted report and its flag, then verify the solve.
setup:
  - docker compose up -d
  - text: Open http://localhost:8080 in your browser.
steps:
  - text: Browse the portal and list the public crossing reports.
  - text: Look for how each report is requested and which one is served.
  - text: Reach the restricted report and read its flag.
  - text: Run the checker against the lab to verify the solve.
flag:
  format: duck{...}
  location: Inside the restricted report, served by the lab.
date: 2026-09-03
---

The duck cross portal collects crossing reports from wardens. Five reports
are public. One is restricted and holds something more interesting than a
warden's crossing slip.

The briefing is the whole story. The gap between what the portal intends to
show and what it will serve is the lab. Find that gap and the flag is inside
it.