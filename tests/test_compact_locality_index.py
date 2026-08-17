import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.locality import build_locality_index
from isql_core.compact_locality import (
    COMPACT_LOCALITY_MAGIC,
    CompactLocalityIndex,
    build_compact_locality_index,
)

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


def frame(name: str) -> bytes:
    return (VAL / name).read_bytes()


class CompactLocalityIndexTests(unittest.TestCase):
    def test_deterministic_round_trip_and_registry_dedup(self):
        frames = [
            ('one.isql7', frame('v07_memory_1_R2.isql7')),
            ('two.isql7', frame('v07_memory_2_R2.isql7')),
            ('three.isql7', frame('v07_memory_3_R2.isql7')),
        ]
        a = build_compact_locality_index(frames)
        b = build_compact_locality_index(reversed(frames))
        raw = a.to_bytes()
        self.assertEqual(raw, b.to_bytes())
        self.assertTrue(raw.startswith(COMPACT_LOCALITY_MAGIC))
        self.assertEqual(CompactLocalityIndex.from_bytes(raw).to_bytes(), raw)
        # one/two share a registry binding, three has a later registry.
        self.assertEqual(len(a.registry_bindings), 2)
        self.assertEqual(len(a.entries), 3)

    def test_conversion_preserves_legacy_metadata(self):
        legacy = build_locality_index([
            ('one.isql7', frame('v07_memory_1_R2.isql7')),
            ('three.isql7', frame('v07_memory_3_R2.isql7')),
        ])
        compact = CompactLocalityIndex.from_legacy(legacy)
        restored = compact.to_legacy()
        self.assertEqual(restored.to_dict(), legacy.to_dict())

    def test_unicode_frame_ref_round_trips(self):
        compact = build_compact_locality_index([
            ('記憶/一.isql7', frame('v07_memory_1_R2.isql7')),
        ])
        raw = compact.to_bytes()
        got = CompactLocalityIndex.from_bytes(raw)
        self.assertEqual(got.entries[0].frame_ref, '記憶/一.isql7')

    def test_crc_corruption_fails_closed(self):
        raw = bytearray(build_compact_locality_index([
            ('one.isql7', frame('v07_memory_1_R2.isql7')),
        ]).to_bytes())
        raw[-5] ^= 0x01
        with self.assertRaises(ISQLValidationError):
            CompactLocalityIndex.from_bytes(bytes(raw))

    def test_truncation_and_trailing_bytes_fail_closed(self):
        raw = build_compact_locality_index([
            ('one.isql7', frame('v07_memory_1_R2.isql7')),
        ]).to_bytes()
        with self.assertRaises(ISQLValidationError):
            CompactLocalityIndex.from_bytes(raw[:-1])
        # Recompute not needed: trailing bytes must fail even before canonical re-encode.
        with self.assertRaises(ISQLValidationError):
            CompactLocalityIndex.from_bytes(raw + b'\x00')

    def test_noncanonical_varint_fails_closed(self):
        raw = bytearray(build_compact_locality_index([]).to_bytes())
        # Layout for empty index body: magic(4), version(1), registry_count varint(1), entry_count varint(1), CRC(4).
        # Replace canonical zero registry count with 0x80 0x00 and repair CRC.
        import zlib
        body = bytes(raw[:-4])
        self.assertEqual(body[5], 0)
        mutated = body[:5] + b'\x80\x00' + body[6:]
        crc = zlib.crc32(mutated) & 0xFFFFFFFF
        with self.assertRaises(ISQLValidationError):
            CompactLocalityIndex.from_bytes(mutated + crc.to_bytes(4, 'big'))


if __name__ == '__main__':
    unittest.main()
