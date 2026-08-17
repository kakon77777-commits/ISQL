import json
import unittest
from pathlib import Path

import isql_core
from isql_core.locality import build_locality_index

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


class V10CompatibilityTests(unittest.TestCase):
    def test_package_version_is_1_0_0(self):
        self.assertEqual(isql_core.__version__, '1.0.0')

    def test_v09_json_locality_index_remains_byte_semantically_identical(self):
        frozen = json.loads((VAL / 'v09_locality_index.json').read_text(encoding='utf-8'))
        refs = {row['frame_ref'] for row in frozen['entries']}
        frames = []
        mapping = {
            'one.isql7': 'v07_memory_1_R2.isql7',
            'two.isql7': 'v07_memory_2_R2.isql7',
            'three.isql7': 'v07_memory_3_R2.isql7',
        }
        for ref in sorted(refs):
            frames.append((ref, (VAL / mapping[ref]).read_bytes()))
        rebuilt = build_locality_index(frames)
        self.assertEqual(rebuilt.to_dict(), frozen)


if __name__ == '__main__':
    unittest.main()
