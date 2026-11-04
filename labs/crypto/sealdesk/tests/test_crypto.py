"""Tests for SealDesk's CBC receipt and the deliberately observable check path."""

from __future__ import annotations

import base64
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import crypto


AES_KEY = bytes(range(32))
MAC_KEY = bytes(range(32, 64))


def decode_field(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def encode_field(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class ReceiptOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(crypto, "app.crypto must implement the receipt contract")

    def test_original_receipt_passes_both_decryption_and_authentication(self) -> None:
        receipt = crypto.seal_receipt(b"one receipt", AES_KEY, MAC_KEY, iv=b"I" * 16)

        self.assertTrue(crypto.check_receipt(receipt, AES_KEY, MAC_KEY))

    def test_valid_padding_with_an_invalid_tag_is_a_distinct_failure(self) -> None:
        receipt = crypto.seal_receipt(b"one receipt", AES_KEY, MAC_KEY, iv=b"I" * 16)
        receipt["tag"] = encode_field(b"X" * 32)

        with self.assertRaises(crypto.UntrustedEnvelope):
            crypto.check_receipt(receipt, AES_KEY, MAC_KEY)

    def test_invalid_padding_is_reported_before_mac_rejection(self) -> None:
        receipt = crypto.seal_receipt(b"123456789012345", AES_KEY, MAC_KEY, iv=b"I" * 16)
        iv = bytearray(decode_field(receipt["iv"]))
        iv[-1] ^= 1  # Turn the one-byte PKCS#7 suffix into an invalid zero byte.
        receipt["iv"] = encode_field(bytes(iv))
        receipt["tag"] = encode_field(b"X" * 32)

        with self.assertRaises(crypto.DamagedEnvelope):
            crypto.check_receipt(receipt, AES_KEY, MAC_KEY)

    def test_single_block_truncation_and_modified_iv_reach_the_padding_check(self) -> None:
        receipt = crypto.seal_receipt(b"short", AES_KEY, MAC_KEY, iv=b"I" * 16)
        ciphertext = decode_field(receipt["ciphertext"])
        original_iv = decode_field(receipt["iv"])
        decryptor = crypto.Cipher(crypto.algorithms.AES(AES_KEY), crypto.modes.CBC(original_iv)).decryptor()
        original_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        intermediate = bytes(left ^ right for left, right in zip(original_plaintext, original_iv))
        chosen_plaintext = b"A" * 15 + b"\x01"
        attacker_iv = bytes(left ^ right for left, right in zip(intermediate, chosen_plaintext))
        probe = copy.deepcopy(receipt)
        probe["iv"] = encode_field(attacker_iv)
        probe["ciphertext"] = encode_field(ciphertext[:16])
        probe["tag"] = encode_field(b"X" * 32)

        with self.assertRaises(crypto.UntrustedEnvelope):
            crypto.check_receipt(probe, AES_KEY, MAC_KEY)


if __name__ == "__main__":
    unittest.main()
