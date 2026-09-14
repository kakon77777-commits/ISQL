import unittest
import zlib

from isql_core.address import address_bytes, address_code_to_digest
from isql_core.errors import ISQLValidationError
from isql_core.native import decode_native_spectral_frame, encode_native_spectral_frame
from isql_core.native_ext import (
    ISX_MAX_BIT_WIDTH,
    decode_isx_sequence_block,
    decode_isx_sequence_range,
    decode_isx_spectral_frame,
    encode_isx_spectral_frame,
    index_isx_blocks,
)
from isql_core.spectral import SPECTRAL_REGISTRY_ID, SpectralPacket


def packet(sequence):
    return SpectralPacket(
        registry_id=SPECTRAL_REGISTRY_ID,
        registry_revision=1,
        registry_hash="12" * 32,
        sequence=tuple(sequence),
        registry_delta_bytes=0,
    )


def with_crc(body: bytes) -> bytes:
    return body + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "big")


class ISXFrameTests(unittest.TestCase):
    def test_round_trip_width_boundaries(self):
        widths = (0, 1, 7, 8, 9, 63, 64, 65, 127, 128, 129, 254, 255, 256, 257, 511, 512, 1024, 4096)
        for width in widths:
            with self.subTest(width=width):
                sequence = (0, 0, 0) if width == 0 else ((1 << width) - 1, 1, 0)
                address = address_bytes(f"isx-width-{width}".encode("ascii"))
                frame = encode_isx_spectral_frame(address, packet(sequence), "R2")
                decoded = decode_isx_spectral_frame(frame)
                self.assertEqual(decoded.address_digest, address_code_to_digest(address))
                self.assertEqual(decoded.sequence, sequence)
                self.assertEqual(decoded.registry_revision, 1)
                self.assertEqual(decoded.registry_hash, "12" * 32)
                self.assertEqual(decoded.resolution, "R2")
                self.assertEqual(decoded.to_bytes(), frame)
                blocks = index_isx_blocks(frame)
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0].bit_width, width)

    def test_width_header_transition_at_254_255_256(self):
        expected_header_lengths = {254: 1, 255: 3, 256: 3}
        for width, expected_length in expected_header_lengths.items():
            with self.subTest(width=width):
                frame = encode_isx_spectral_frame(
                    address_bytes(f"header-{width}".encode("ascii")),
                    packet(((1 << width) - 1,)),
                    "R1",
                )
                block = index_isx_blocks(frame)[0]
                self.assertEqual(block.bit_width, width)
                self.assertEqual(block.width_header_length, expected_length)

    def test_random_access_across_mixed_width_blocks(self):
        first = tuple(range(16))
        second = ((1 << 256) - 1,) + tuple(range(1, 16))
        third = ((1 << 65) - 1, 7, 3)
        sequence = first + second + third
        frame = encode_isx_spectral_frame(address_bytes(b"random-access"), packet(sequence), "R2")
        blocks = index_isx_blocks(frame)
        self.assertEqual([block.bit_width for block in blocks], [4, 256, 65])
        self.assertEqual(decode_isx_sequence_block(frame, 0), first)
        self.assertEqual(decode_isx_sequence_block(frame, 1), second)
        self.assertEqual(decode_isx_sequence_block(frame, 2), third)
        self.assertEqual(decode_isx_sequence_range(frame, 1, 2), second + third)

    def test_public_isn7_still_rejects_65_bit_value(self):
        wide = packet((1 << 64,))  # bit_length == 65
        with self.assertRaises(ISQLValidationError):
            encode_native_spectral_frame(address_bytes(b"public-stays-64"), wide, "R2")
        frame = encode_isx_spectral_frame(address_bytes(b"experimental-wide"), wide, "R2")
        self.assertEqual(decode_isx_spectral_frame(frame).sequence, wide.sequence)

    def test_format_families_reject_each_other(self):
        narrow = packet((1, 2, 3))
        native = encode_native_spectral_frame(address_bytes(b"native"), narrow, "R2")
        isx = encode_isx_spectral_frame(address_bytes(b"isx"), narrow, "R2")
        with self.assertRaises(ISQLValidationError):
            decode_isx_spectral_frame(native)
        with self.assertRaises(ISQLValidationError):
            decode_native_spectral_frame(isx)

    def test_all_zero_block_is_canonical(self):
        frame = encode_isx_spectral_frame(address_bytes(b"zero"), packet((0,) * 16), "R1")
        block = index_isx_blocks(frame)[0]
        self.assertEqual(block.bit_width, 0)
        self.assertEqual(block.encoded_length, 1)
        self.assertEqual(decode_isx_spectral_frame(frame).sequence, (0,) * 16)

    def test_noncanonical_extended_width_below_255_fails_closed(self):
        # Header size is 74 bytes for revision=1 and item_count=1.
        # Start from canonical width=1, then over-encode that width as FF 01.
        frame = encode_isx_spectral_frame(address_bytes(b"noncanonical-width"), packet((1,)), "R2")
        body = bytearray(frame[:-4])
        self.assertEqual(body[74], 1)
        body[74:75] = bytes((0xFF, 0x01))
        with self.assertRaises(ISQLValidationError):
            decode_isx_spectral_frame(with_crc(bytes(body)))

    def test_nonminimal_block_width_fails_closed(self):
        # Canonical one-item value 1 has width=1. Rewrite it as width=2 with payload 01xxxxxx.
        frame = encode_isx_spectral_frame(address_bytes(b"nonminimal"), packet((1,)), "R2")
        body = bytearray(frame[:-4])
        self.assertEqual(body[74], 1)
        body[74] = 2
        body[75] = 0b01000000
        with self.assertRaises(ISQLValidationError):
            decode_isx_spectral_frame(with_crc(bytes(body)))

    def test_nonzero_padding_bits_fail_closed(self):
        # Three values max=3 => width=2, six data bits followed by two zero padding bits.
        frame = encode_isx_spectral_frame(address_bytes(b"padding"), packet((1, 2, 3)), "R2")
        body = bytearray(frame[:-4])
        self.assertEqual(body[74], 2)
        body[75] |= 0x01
        with self.assertRaises(ISQLValidationError):
            decode_isx_spectral_frame(with_crc(bytes(body)))

    def test_checksum_corruption_fails_closed(self):
        frame = bytearray(encode_isx_spectral_frame(address_bytes(b"crc"), packet((1 << 256, 7)), "R2"))
        frame[-1] ^= 1
        with self.assertRaises(ISQLValidationError):
            decode_isx_spectral_frame(bytes(frame))

    def test_truncation_fails_closed(self):
        frame = encode_isx_spectral_frame(address_bytes(b"truncated"), packet((1 << 256, 7)), "R2")
        with self.assertRaises(ISQLValidationError):
            decode_isx_spectral_frame(frame[:-2])

    def test_runtime_width_cap_fails_closed(self):
        too_wide = 1 << ISX_MAX_BIT_WIDTH  # bit_length == cap + 1
        with self.assertRaises(ISQLValidationError):
            encode_isx_spectral_frame(address_bytes(b"too-wide"), packet((too_wide,)), "R2")

    def test_invalid_random_access_ranges_fail_closed(self):
        frame = encode_isx_spectral_frame(address_bytes(b"range"), packet(tuple(range(20))), "R2")
        with self.assertRaises(ISQLValidationError):
            decode_isx_sequence_block(frame, 2)
        with self.assertRaises(ISQLValidationError):
            decode_isx_sequence_range(frame, 1, 2)
        with self.assertRaises(ISQLValidationError):
            decode_isx_sequence_range(frame, -1, 1)


if __name__ == "__main__":
    unittest.main()
