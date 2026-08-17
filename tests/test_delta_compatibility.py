import json
import unittest
from pathlib import Path

from isql_core.memory import MemoryRecord
from isql_core.native import compile_native_memory

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation"


class DeltaCompatibilityTests(unittest.TestCase):
    def test_v07_frozen_native_frames_remain_byte_for_byte_unchanged(self):
        for i in (1, 2, 3):
            record = MemoryRecord.from_dict(json.loads((VAL / f"v04_record_{i}.json").read_text(encoding="utf-8")))
            rebuilt = compile_native_memory(record, resolution="R2").frame
            frozen = (VAL / f"v07_memory_{i}_R2.isql7").read_bytes()
            self.assertEqual(rebuilt, frozen)


if __name__ == "__main__":
    unittest.main()
