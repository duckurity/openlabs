"""Ephemeral per-container state for SealDesk's synthetic case."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any

from app.crypto import (
    VERSION,
    decode_field,
    encode_field,
    open_authenticated_receipt,
    seal_receipt,
)

STATE_DIR = Path(os.environ.get("SEALDESK_STATE_DIR", "/run/sealdesk"))
STATE_FILENAME = "instance.json"
DOCUMENT_ID = "CASE-4107"
_STATE_FIELDS = frozenset({
    "schema_version", "generation_id", "document_id", "access_code", "flag",
    "encryption_key", "mac_key", "receipt",
})
_HEX_32 = re.compile(r"[0-9a-f]{32}\Z")
_FLAG = re.compile(r"duck\{[a-z0-9_]{16,40}\}\Z")


@dataclass(frozen=True, slots=True)
class RuntimeState:
    generation_id: str
    document_id: str
    access_code: str = field(repr=False)
    flag: str = field(repr=False)
    encryption_key: bytes = field(repr=False)
    mac_key: bytes = field(repr=False)
    receipt: dict[str, str]

    @property
    def flag_hash(self) -> str:
        return hashlib.sha256(self.flag.encode("utf-8")).hexdigest()

    def public_case(self) -> dict[str, Any]:
        """Return the fictional case file; never include its code or flag."""
        return {
            "case_id": "SD-4107",
            "document_id": self.document_id,
            "document_title": "Harbor Office continuity plan",
            "sender": "Harbor Office Records",
            "recipient": "Mara Chen",
            "issued_on": "2026-09-18",
            "note": "The signed copy is held until its delivery receipt is accepted.",
            "receipt": dict(self.receipt),
        }

    def private_payload(self) -> dict[str, Any]:
        """Serialize the secret state for a mode-0600 file on container tmpfs."""
        return {
            "schema_version": 1,
            "generation_id": self.generation_id,
            "document_id": self.document_id,
            "access_code": self.access_code,
            "flag": self.flag,
            "encryption_key": encode_field(self.encryption_key),
            "mac_key": encode_field(self.mac_key),
            "receipt": dict(self.receipt),
        }


def generate_state() -> RuntimeState:
    """Create one new instance with unrelated keys, code, flag, and generation."""
    generation_id = secrets.token_hex(16)
    access_code = secrets.token_hex(16)
    flag = f"duck{{{secrets.token_hex(12)}}}"
    encryption_key = secrets.token_bytes(32)
    mac_key = secrets.token_bytes(32)
    plaintext = f"SDR1|{DOCUMENT_ID}|{access_code}".encode("ascii")
    receipt = seal_receipt(plaintext, encryption_key, mac_key)
    return RuntimeState(
        generation_id=generation_id,
        document_id=DOCUMENT_ID,
        access_code=access_code,
        flag=flag,
        encryption_key=encryption_key,
        mac_key=mac_key,
        receipt=receipt,
    )


def _state_from_payload(payload: Any) -> RuntimeState:
    if not isinstance(payload, dict) or set(payload) != _STATE_FIELDS:
        raise ValueError("runtime state has an invalid shape")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("runtime state version is unsupported")

    generation_id = payload["generation_id"]
    document_id = payload["document_id"]
    access_code = payload["access_code"]
    flag = payload["flag"]
    if not isinstance(generation_id, str) or not _HEX_32.fullmatch(generation_id):
        raise ValueError("runtime generation identifier is invalid")
    if document_id != DOCUMENT_ID:
        raise ValueError("runtime document identifier is invalid")
    if not isinstance(access_code, str) or not _HEX_32.fullmatch(access_code):
        raise ValueError("runtime access code is invalid")
    if not isinstance(flag, str) or not _FLAG.fullmatch(flag):
        raise ValueError("runtime flag is invalid")

    encryption_key = decode_field(payload["encryption_key"])
    mac_key = decode_field(payload["mac_key"])
    if len(encryption_key) != 32 or len(mac_key) != 32:
        raise ValueError("runtime key material is invalid")
    receipt = payload["receipt"]
    if not isinstance(receipt, dict):
        raise ValueError("runtime receipt is invalid")
    state = RuntimeState(
        generation_id=generation_id,
        document_id=document_id,
        access_code=access_code,
        flag=flag,
        encryption_key=encryption_key,
        mac_key=mac_key,
        receipt=dict(receipt),
    )
    expected_plaintext = f"{VERSION}|{document_id}|{access_code}".encode("ascii")
    if not hmac.compare_digest(
        open_authenticated_receipt(state.receipt, state.encryption_key, state.mac_key),
        expected_plaintext,
    ):
        raise ValueError("runtime receipt does not match its recovery code")
    return state


def load_state(path: Path) -> RuntimeState:
    """Read and validate the private runtime state without exposing its values."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("runtime state is unavailable or malformed") from error
    try:
        return _state_from_payload(payload)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("runtime state failed validation") from error


def initialize_state(state_dir: Path = STATE_DIR) -> RuntimeState:
    """Create the instance once; keep it stable across an ordinary process restart."""
    directory = Path(state_dir)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(directory, 0o700)
    path = directory / STATE_FILENAME
    if path.exists():
        return load_state(path)

    state = generate_state()
    serialized = (json.dumps(state.private_payload(), sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return load_state(path)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(serialized)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return state


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"--initialize", "--flag-hash-json"}:
        print("usage: python -m app.state (--initialize | --flag-hash-json)", file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == "--initialize":
            initialize_state()
            print("SealDesk runtime state is ready.")
            return 0
        state = load_state(STATE_DIR / STATE_FILENAME)
    except (OSError, ValueError) as error:
        print(f"SealDesk runtime state is unavailable ({type(error).__name__}).", file=sys.stderr)
        return 1
    print(json.dumps({"flag_hash": state.flag_hash}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
