# duck-cross

`easy` · `web`

## Brief

The duck cross portal collects crossing reports from wardens. Five reports are public. One report stays restricted. Read it.

## Setup

Run these from the lab directory:

```bash
docker compose up -d
```

Open `http://localhost:8377`.

## Goal

Find the restricted report. Extract its flag. Verify the solve from the lab directory:

```bash
python3 ../../../scripts/check.py .
```

## Reference lifecycle

This lab is the M0 reference for L0–L6 evidence. Levels map to contract
validate, compose render, image build, bounded startup, player smoke, intended
solve via `scripts/check.py`, then teardown plus a second clean start.

CI runs `python3 scripts/prove_reference_lab.py` under compose project
`openlabs-ref-duck-cross`. Failure logs redact flag values.

Reset a CI-style run:

```bash
docker compose -p openlabs-ref-duck-cross down -v
```
