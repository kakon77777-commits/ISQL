import json
import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.locality import LocalityIndex, build_locality_index, signature_from_native

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


class LocalityIndexTests(unittest.TestCase):
    def test_signature_is_deterministic_and_blocked(self):
        frame = (VAL / 'v07_memory_1_R2.isql7').read_bytes()
        a = signature_from_native(frame, frame_ref='a.isql7')
        b = signature_from_native(frame, frame_ref='a.isql7')
        self.assertEqual(a, b)
        self.assertEqual(a.item_count, 68)
        self.assertEqual(len(a.blocks), 5)
        self.assertEqual(len(a.frame_sha256), 64)
        self.assertEqual(len(a.registry_hash), 64)

    def test_build_is_order_independent(self):
        f1 = (VAL / 'v07_memory_1_R2.isql7').read_bytes()
        f2 = (VAL / 'v07_memory_2_R2.isql7').read_bytes()
        a = build_locality_index([('b.isql7', f2), ('a.isql7', f1)])
        b = build_locality_index([('a.isql7', f1), ('b.isql7', f2)])
        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertEqual(a.content_hash(), b.content_hash())

    def test_json_round_trip(self):
        frame = (VAL / 'v07_memory_1_R2.isql7').read_bytes()
        index = build_locality_index([('a.isql7', frame)])
        restored = LocalityIndex.from_dict(json.loads(json.dumps(index.to_dict())))
        self.assertEqual(restored, index)
        self.assertEqual(restored.content_hash(), index.content_hash())

    def test_non_native_input_rejected(self):
        base = (VAL / 'v07_memory_1_R2.isql7').read_bytes()
        delta = (VAL / 'v08_delta_identical.isqld8').read_bytes() if (VAL / 'v08_delta_identical.isqld8').exists() else b'ISD8bad'
        with self.assertRaises(ISQLValidationError):
            signature_from_native(delta, frame_ref='bad.bin')

    def test_duplicate_frame_ref_rejected(self):
        f1 = (VAL / 'v07_memory_1_R2.isql7').read_bytes()
        f2 = (VAL / 'v07_memory_2_R2.isql7').read_bytes()
        with self.assertRaises(ISQLValidationError):
            build_locality_index([('same.isql7', f1), ('same.isql7', f2)])


if __name__ == '__main__':
    unittest.main()
