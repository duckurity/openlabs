# dns-ecs-bypass

`medium` · `network`

## Brief

An internal DNS resolver is listening on UDP/5353. It hosts a zone that is
supposed to be reachable only from the internal network. A normal query gets
refused.

## Setup

Run these from the lab directory:

```bash
docker compose up -d
```

The resolver is reachable at `127.0.0.1:5353/udp`.

## Goal

Get past the access check and read the protected record. Verify the solve
from the lab directory:

```bash
python3 ../../../scripts/check.py .
```
