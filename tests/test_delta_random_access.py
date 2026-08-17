import unittest
import zlib

from isql_core.address import address_bytes, address_code_to_digest
from isql_core.delta import (
    decode_delta_block,
    decode_delta_frame,
    decode_delta_range,
    encode_delta_frame,
    index_delta_blocks,
)
from isql_core.errors import ISQLValidationError
from isql_core.native import NativeSpectralFrame


def native(label: bytes, seq):
    return NativeSpectralFrame(
        address_digest=address_code_to_digest(address_bytes(label)),
        resolution="R2",
        registry_revision=1,
        registry_hash="56" * 32,
        sequence=tuple(seq),
    ).to_bytes()


class DeltaRandomAccessTests(unittest.TestCase):
    def setUp(self):
        self.base_seq = tuple(range(1, 49))
        self.target_seq = tuple(
            list(self.base_seq[:16])
            + [x + 1 for x in self.base_seq[16:32]]
            + [((1 << 32) - x) for x in range(16)]
        )
        self.base = native(b"base-ra", self.base_seq)
        self.target = native(b"target-ra", self.target_seq)
        self.delta = encode_delta_frame(self.base, self.target)

    def test_block_index_and_single_block_decode_match_full_target(self):
        blocks = index_delta_blocks(self.delta, self.base)
        self.assertEqual(len(blocks), 3)
        self.assertEqual(decode_delta_block(self.delta, self.base, 0), self.target_seq[:16])
        self.assertEqual(decode_delta_block(self.delta, self.base, 1), self.target_seq[16:32])
        self.assertEqual(decode_delta_block(self.delta, self.base, 2), self.target_seq[32:])

    def test_range_decode_matches_full_target_slice(self):
        self.assertEqual(decode_delta_range(self.delta, self.base, 1, 2), self.target_seq[16:])

    def test_random_access_does_not_unpack_unrelated_corrupt_payload(self):
        blocks = index_delta_blocks(self.delta, self.base)
        last = blocks[-1]
        self.assertGreater(last.payload_length, 0)
        body = bytearray(self.delta[:-4])
        # Corrupt the third block's width byte but keep frame-level CRC valid.
        body[last.payload_offset] = 255
        damaged = bytes(body) + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "big")

        self.assertEqual(decode_delta_block(damaged, self.base, 0), self.target_seq[:16])
        with self.assertRaises(ISQLValidationError):
            decode_delta_frame(damaged, self.base)

    def test_invalid_delta_block_range_fails_closed(self):
        with self.assertRaises(ISQLValidationError):
            decode_delta_block(self.delta, self.base, 3)
        with self.assertRaises(ISQLValidationError):
            decode_delta_range(self.delta, self.base, 2, 2)


if __name__ == "__main__":
    unittest.main()
