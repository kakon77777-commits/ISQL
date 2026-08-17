import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.compact_locality import (
    build_compact_locality_index,
    load_compact_locality_index,
    save_compact_locality_index,
)

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


def b(name: str) -> bytes:
    return (VAL / name).read_bytes()


class CompactLocalityPersistenceTests(unittest.TestCase):
    def test_save_load_and_hash_are_deterministic(self):
        index = build_compact_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
            ('three.isql7', b('v07_memory_3_R2.isql7')),
        ])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'index.ili1'
            save_compact_locality_index(path, index)
            loaded = load_compact_locality_index(path)
            self.assertEqual(loaded.to_bytes(), index.to_bytes())
            self.assertEqual(loaded.content_hash(), index.content_hash())
            self.assertEqual(len(loaded.content_hash()), 64)

    def test_corrupted_file_is_rejected(self):
        index = build_compact_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
        ])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'index.ili1'
            save_compact_locality_index(path, index)
            raw = bytearray(path.read_bytes())
            raw[-6] ^= 1
            path.write_bytes(raw)
            with self.assertRaises(ISQLValidationError):
                load_compact_locality_index(path)

    def test_binary_conversion_preserves_every_legacy_entry_field(self):
        index = build_compact_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
            ('two.isql7', b('v07_memory_2_R2.isql7')),
            ('three.isql7', b('v07_memory_3_R2.isql7')),
        ])
        before = index.to_legacy().to_dict()
        after = type(index).from_bytes(index.to_bytes()).to_legacy().to_dict()
        self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
