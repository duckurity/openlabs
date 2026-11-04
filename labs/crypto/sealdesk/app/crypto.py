"""SealDesk receipt cryptography.

The check order intentionally distinguishes invalid PKCS#7 padding from later
HMAC rejection. This is the lab's sole vulnerability; production code must
verify an authentication tag before decrypting or unpadding ciphertext.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

VERSION = "SDR1"
BLOCK_SIZE = 16
TAG_SIZE = hashlib.sha256().digest_size
MAX_CIPHERTEXT_BYTES = 256
RECEIPT_FIELDS = frozenset({"version", "iv", "ciphertext", "tag"})
_B64URL = re.compile(r"[A-Za-z0-9_-]+\Z")


class ReceiptFormatError(ValueError):
    """The public envelope is not in the bounded wire format."""


class DamagedEnvelope(ValueError):
    """AES-CBC decryption produced invalid PKCS#7 padding."""


class UntrustedEnvelope(ValueError):
    """Padding was valid but the independent HMAC did not verify."""


def encode_field(value: bytes) -> str:
    """Encode canonical unpadded Base64URL for one public receipt field."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def decode_field(value: Any) -> bytes:
    """Decode one canonical, bounded-character Base64URL field."""
    if not isinstance(value, str) or not _B64URL.fullmatch(value):
        raise ReceiptFormatError("receipt field is not canonical Base64URL")
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as error:
        raise ReceiptFormatError("receipt field is not canonical Base64URL") from error
    if encode_field(decoded) != value:
        raise ReceiptFormatError("receipt field is not canonical Base64URL")
    return decoded


def _validate_keys(encryption_key: bytes, mac_key: bytes) -> None:
    if not isinstance(encryption_key, bytes) or len(encryption_key) != 32:
        raise ValueError("AES-256 requires a 32-byte key")
    if not isinstance(mac_key, bytes) or len(mac_key) < 32:
        raise ValueError("HMAC requires a key of at least 32 bytes")


def _mac_input(version: str, iv: bytes, ciphertext: bytes) -> bytes:
    version_bytes = version.encode("ascii")
    return (
        len(version_bytes).to_bytes(1, "big")
        + version_bytes
        + len(iv).to_bytes(2, "big")
        + iv
        + len(ciphertext).to_bytes(4, "big")
        + ciphertext
    )


def _tag(version: str, iv: bytes, ciphertext: bytes, mac_key: bytes) -> bytes:
    return hmac.new(mac_key, _mac_input(version, iv, ciphertext), hashlib.sha256).digest()


def seal_receipt(
    plaintext: bytes,
    encryption_key: bytes,
    mac_key: bytes,
    *,
    iv: bytes | None = None,
) -> dict[str, str]:
    """Create a versioned AES-CBC/PKCS#7 receipt with an independent HMAC."""
    _validate_keys(encryption_key, mac_key)
    if not isinstance(plaintext, bytes):
        raise TypeError("plaintext must be bytes")
    actual_iv = secrets.token_bytes(BLOCK_SIZE) if iv is None else iv
    if not isinstance(actual_iv, bytes) or len(actual_iv) != BLOCK_SIZE:
        raise ValueError("AES-CBC requires a 16-byte IV")

    padder = padding.PKCS7(BLOCK_SIZE * 8).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(encryption_key), modes.CBC(actual_iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return {
        "version": VERSION,
        "iv": encode_field(actual_iv),
        "ciphertext": encode_field(ciphertext),
        "tag": encode_field(_tag(VERSION, actual_iv, ciphertext, mac_key)),
    }


def parse_receipt(payload: Any) -> tuple[str, bytes, bytes, bytes]:
    """Validate the public framing before the intentionally vulnerable check."""
    if not isinstance(payload, dict) or set(payload) != RECEIPT_FIELDS:
        raise ReceiptFormatError("receipt must contain exactly four fields")
    if payload["version"] != VERSION:
        raise ReceiptFormatError("unsupported receipt version")

    iv = decode_field(payload["iv"])
    ciphertext = decode_field(payload["ciphertext"])
    tag = decode_field(payload["tag"])
    if len(iv) != BLOCK_SIZE:
        raise ReceiptFormatError("receipt IV has the wrong length")
    if not ciphertext or len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise ReceiptFormatError("receipt ciphertext length is outside the limit")
    if len(ciphertext) % BLOCK_SIZE:
        raise ReceiptFormatError("receipt ciphertext is not block-aligned")
    if len(tag) != TAG_SIZE:
        raise ReceiptFormatError("receipt tag has the wrong length")
    return VERSION, iv, ciphertext, tag


def open_authenticated_receipt(
    payload: Any, encryption_key: bytes, mac_key: bytes
) -> bytes:
    """Return receipt plaintext only after the independent HMAC verifies.

    This internal loader helper is not used by the HTTP API; the public checker
    continues to discard plaintext and exposes only the intended error classes.
    """
    _validate_keys(encryption_key, mac_key)
    version, iv, ciphertext, supplied_tag = parse_receipt(payload)
    decryptor = Cipher(algorithms.AES(encryption_key), modes.CBC(iv)).decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Intentional vulnerability: the exception class creates the first public
    # response class before authenticity is checked. Do not log the exception.
    unpadder = padding.PKCS7(BLOCK_SIZE * 8).unpadder()
    try:
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    except ValueError:
        raise DamagedEnvelope("receipt padding is invalid") from None

    expected_tag = _tag(version, iv, ciphertext, mac_key)
    if not hmac.compare_digest(expected_tag, supplied_tag):
        raise UntrustedEnvelope("receipt authentication failed")
    return plaintext


def check_receipt(payload: Any, encryption_key: bytes, mac_key: bytes) -> bool:
    """Decrypt, unpad, then authenticate (the intentional padding oracle)."""
    open_authenticated_receipt(payload, encryption_key, mac_key)
    return True
