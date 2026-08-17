import unittest
import zlib

from isql_core.address import address_bytes, address_code_to_digest
from isql_core.errors import ISQLValidationError
from isql_core.native import decode_native_spectral_frame, encode_native_spectral_frame
from isql_core.spectral import SPECTRAL_REGISTRY_ID, SpectralPacket


def packet(sequence=(1, 0, 3, 7, 15, 16, 31, 2, 1, 0, 9, 4, 3, 2, 1, 8)):
    return SpectralPacket(
        registry_id=SPECTRAL_REGISTRY_ID,
        registry_revision=1,
        registry_hash="12" * 32,
        sequence=tuple(sequence),
        registry_delta_bytes=999,
    )


def with_crc(body: bytes) -> bytes:
    return body + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "big")


class NativeFrameTests(unittest.TestCase):
    def test_native_frame_round_trip_and_canonical_reencode(self):
        address = address_bytes(b"native-frame")
        original = packet()
        frame = encode_native_spectral_frame(address, original, "R2")
        decoded = decode_native_spectral_frame(frame)
        self.assertEqual(decoded.address_digest, address_code_to_digest(address))
        self.assertEqual(decoded.registry_revision, original.registry_revision)
        self.assertEqual(decoded.registry_hash, original.registry_hash)
        self.assertEqual(decoded.sequence, original.sequence)
        self.assertEqual(decoded.resolution, "R2")
        self.assertEqual(decoded.to_bytes(), frame)

    def test_all_zero_block_is_canonical(self):
        frame = encode_native_spectral_frame(address_bytes(b"z"), packet((0,) * 16), "R1")
        decoded = decode_native_spectral_frame(frame)
        self.assertEqual(decoded.sequence, (0,) * 16)
        self.assertEqual(decoded.to_bytes(), frame)

    def test_large_registry_ids_round_trip(self):
        seq = (0, 1, 255, 256, 65535, (1 << 40) - 1)
        frame = encode_native_spectral_frame(address_bytes(b"large"), packet(seq), "R2")
        self.assertEqual(decode_native_spectral_frame(frame).sequence, seq)

    def test_checksum_corruption_fails_closed(self):
        frame = bytearray(encode_native_spectral_frame(address_bytes(b"crc"), packet(), "R2"))
        frame[-1] ^= 1
        with self.assertRaises(ISQLValidationError):
            decode_native_spectral_frame(bytes(frame))

    def test_truncation_fails_closed(self):
        frame = encode_native_spectral_frame(address_bytes(b"trunc"), packet(), "R2")
        with self.assertRaises(ISQLValidationError):
            decode_native_spectral_frame(frame[:-2])

    def test_invalid_block_width_fails_closed(self):
        # revision=1 and item_count=16 are one-byte varints; first width is offset 74.
        frame = encode_native_spectral_frame(address_bytes(b"width"), packet(), "R2")
        body = bytearray(frame[:-4])
        body[74] = 65
        with self.assertRaises(ISQLValidationError):
            decode_native_spectral_frame(with_crc(bytes(body)))

    def test_nonzero_padding_bits_fail_closed(self):
        # Three values max=3 => width 2, six data bits followed by two zero padding bits.
        frame = encode_native_spectral_frame(address_bytes(b"pad"), packet((1, 2, 3)), "R2")
        body = bytearray(frame[:-4])
        # first width byte at 74, then one payload byte; set a padding bit.
        body[75] |= 0x01
        with self.assertRaises(ISQLValidationError):
            decode_native_spectral_frame(with_crc(bytes(body)))

    def test_unsupported_resolution_fails(self):
        with self.assertRaises(ISQLValidationError):
            encode_native_spectral_frame(address_bytes(b"r"), packet(), "R3")


if __name__ == "__main__":
    unittest.main()
