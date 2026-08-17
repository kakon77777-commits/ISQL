import unittest

from isql_core.address import address_bytes
from isql_core.errors import ISQLValidationError
from isql_core.native import (
    decode_native_sequence_block,
    decode_native_sequence_range,
    decode_native_spectral_frame,
    encode_native_spectral_frame,
    index_native_blocks,
)
from isql_core.spectral import SPECTRAL_REGISTRY_ID, SpectralPacket


def packet(sequence):
    return SpectralPacket(
        registry_id=SPECTRAL_REGISTRY_ID,
        registry_revision=3,
        registry_hash="34" * 32,
        sequence=tuple(sequence),
        registry_delta_bytes=0,
    )


class NativeRandomAccessTests(unittest.TestCase):
    def setUp(self):
        self.sequence = tuple(range(1, 44))
        self.frame = encode_native_spectral_frame(address_bytes(b"random-access"), packet(self.sequence), "R2")

    def test_index_describes_all_blocks_without_changing_frame(self):
        blocks = index_native_blocks(self.frame)
        self.assertEqual([b.item_count for b in blocks], [16, 16, 11])
        self.assertEqual([b.item_start for b in blocks], [0, 16, 32])
        self.assertEqual(decode_native_spectral_frame(self.frame).sequence, self.sequence)

    def test_decode_single_blocks_equals_full_decode_slices(self):
        full = decode_native_spectral_frame(self.frame).sequence
        for block_index, expected in enumerate((full[:16], full[16:32], full[32:])):
            self.assertEqual(decode_native_sequence_block(self.frame, block_index), expected)

    def test_decode_block_range_equals_full_decode_slice(self):
        self.assertEqual(decode_native_sequence_range(self.frame, 1, 2), self.sequence[16:])

    def test_invalid_block_index_fails_closed(self):
        with self.assertRaises(ISQLValidationError):
            decode_native_sequence_block(self.frame, 3)
        with self.assertRaises(ISQLValidationError):
            decode_native_sequence_range(self.frame, -1, 1)

    def test_corrupt_frame_checksum_fails_before_random_access(self):
        damaged = bytearray(self.frame)
        damaged[-1] ^= 1
        with self.assertRaises(ISQLValidationError):
            index_native_blocks(bytes(damaged))


if __name__ == "__main__":
    unittest.main()
