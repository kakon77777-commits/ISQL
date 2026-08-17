import hashlib
import unittest
import zlib

from isql_core.address import address_bytes, address_code_to_digest
from isql_core.errors import ISQLValidationError
from isql_core.native import NativeSpectralFrame, decode_native_spectral_frame
from isql_core.delta import (
    DELTA_MODE_COPY,
    DELTA_MODE_DELTA,
    DELTA_MODE_REPLACE,
    decode_delta_frame,
    encode_delta_frame,
    inspect_delta_frame,
)


def native_frame(label: bytes, sequence, *, revision=1, registry_hash="12" * 32):
    return NativeSpectralFrame(
        address_digest=address_code_to_digest(address_bytes(label)),
        resolution="R2",
        registry_revision=revision,
        registry_hash=registry_hash,
        sequence=tuple(sequence),
    ).to_bytes()


class DeltaFrameTests(unittest.TestCase):
    def test_identical_coordinates_use_copy_and_inherit_registry(self):
        base = native_frame(b"base", range(1, 33))
        target = native_frame(b"target", range(1, 33))
        delta = encode_delta_frame(base, target)
        info = inspect_delta_frame(delta, base)
        self.assertEqual(info["mode_counts"]["copy"], 2)
        self.assertEqual(info["mode_counts"]["delta"], 0)
        self.assertFalse(info["registry_override"])
        decoded = decode_delta_frame(delta, base)
        target_decoded = decode_native_spectral_frame(target)
        self.assertEqual(decoded.address_digest, target_decoded.address_digest)
        self.assertEqual(decoded.sequence, target_decoded.sequence)
        self.assertEqual(decoded.registry_hash, target_decoded.registry_hash)

    def test_small_signed_changes_use_delta_mode(self):
        base_seq = tuple([100] * 16 + [200] * 16)
        target_seq = tuple([101] * 16 + [198] * 16)
        base = native_frame(b"base-d", base_seq)
        target = native_frame(b"target-d", target_seq)
        delta = encode_delta_frame(base, target)
        info = inspect_delta_frame(delta, base)
        self.assertEqual(info["mode_counts"]["delta"], 2)
        self.assertEqual(decode_delta_frame(delta, base).sequence, target_seq)

    def test_unrelated_block_uses_replace(self):
        base = native_frame(b"base-r", [1] * 16)
        target_seq = tuple((1 << 40) - i * 1234567 for i in range(16))
        target = native_frame(b"target-r", target_seq)
        delta = encode_delta_frame(base, target)
        info = inspect_delta_frame(delta, base)
        self.assertEqual(info["mode_counts"]["replace"], 1)
        self.assertEqual(decode_delta_frame(delta, base).sequence, target_seq)

    def test_registry_override_round_trips(self):
        seq = tuple(range(20))
        base = native_frame(b"base-g", seq, revision=1, registry_hash="12" * 32)
        target = native_frame(b"target-g", seq, revision=2, registry_hash="34" * 32)
        delta = encode_delta_frame(base, target)
        info = inspect_delta_frame(delta, base)
        self.assertTrue(info["registry_override"])
        decoded = decode_delta_frame(delta, base)
        self.assertEqual(decoded.registry_revision, 2)
        self.assertEqual(decoded.registry_hash, "34" * 32)

    def test_wrong_base_hash_fails_closed(self):
        base = native_frame(b"base-h", range(20))
        target = native_frame(b"target-h", range(20))
        delta = encode_delta_frame(base, target)
        wrong = native_frame(b"wrong-h", range(20))
        with self.assertRaises(ISQLValidationError):
            decode_delta_frame(delta, wrong)

    def test_checksum_corruption_fails_closed(self):
        base = native_frame(b"base-c", range(20))
        target = native_frame(b"target-c", range(20))
        delta = bytearray(encode_delta_frame(base, target))
        delta[-1] ^= 1
        with self.assertRaises(ISQLValidationError):
            decode_delta_frame(bytes(delta), base)

    def test_noncanonical_mode_is_rejected(self):
        # Build a valid COPY frame, then turn first mode into REPLACE without a payload.
        base = native_frame(b"base-n", range(16))
        target = native_frame(b"target-n", range(16))
        delta = bytearray(encode_delta_frame(base, target))
        body = bytearray(delta[:-4])
        # Header: magic4 + four fixed bytes + address32 + basehash32 + item_count1.
        # First directory mode is therefore byte 73 for this fixture.
        self.assertEqual(body[73], DELTA_MODE_COPY)
        body[73] = DELTA_MODE_REPLACE
        checksum = zlib.crc32(body) & 0xFFFFFFFF
        bad = bytes(body) + checksum.to_bytes(4, "big")
        with self.assertRaises(ISQLValidationError):
            decode_delta_frame(bad, base)


if __name__ == "__main__":
    unittest.main()
