"""Runtime-only disposable seed; flags never enter source or image layers."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = Path(os.getenv("LAST_REEL_STATE_DIR", "/run/last-reel"))


def initialize(state_dir: Path = DEFAULT_STATE) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    database = state_dir / "archive.sqlite"
    flag = "duck{" + secrets.token_hex(16) + "}"
    generation = secrets.token_hex(16)
    films = json.loads((ROOT / "database/films.json").read_text(encoding="utf-8"))
    with closing(sqlite3.connect(database)) as writer, writer:
        writer.executescript((ROOT / "database/schema.sql").read_text(encoding="utf-8"))
        writer.executemany(
            "INSERT INTO films(id,title,year,synopsis,genre,is_public) VALUES(:id,:title,:year,:synopsis,:genre,:is_public)",
            films,
        )
        writer.execute(
            "INSERT INTO clearance_records VALUES(1,9,?)",
            ("Release clearance is restricted. Archive release token: " + flag,),
        )
    database.chmod(0o400)
    (state_dir / "digest.json").write_text(
        json.dumps({"generation_id": generation, "flag_hash": hashlib.sha256(flag.encode()).hexdigest()}),
        encoding="utf-8",
    )
    (state_dir / "digest.json").chmod(0o400)
    return database


def digest(state_dir: Path = DEFAULT_STATE) -> dict[str, str]:
    return json.loads((state_dir / "digest.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    os.umask(0o077)
    initialize()
