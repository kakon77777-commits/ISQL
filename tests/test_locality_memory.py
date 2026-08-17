import json
import unittest
from pathlib import Path

from isql_core.delta import compile_locality_memory, decode_delta_frame
from isql_core.memory import MemoryRecord
from isql_core.native import decode_native_spectral_frame

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation"


class LocalityMemoryTests(unittest.TestCase):
    def test_identical_semantic_neighbor_selects_delta(self):
        base = (VAL / "v07_memory_1_R2.isql7").read_bytes()
        record = MemoryRecord.from_dict(json.loads((VAL / "v04_record_2.json").read_text(encoding="utf-8")))
        result = compile_locality_memory(base, record, resolution="R2")
        self.assertEqual(result.mode, "delta")
        self.assertLess(result.selected_frame_bytes, result.standalone_frame_bytes)
        reconstructed = decode_delta_frame(result.frame, base).to_bytes()
        self.assertEqual(reconstructed, result.standalone_frame)

    def test_registry_growth_and_low_locality_falls_back_to_native(self):
        base = (VAL / "v07_memory_2_R2.isql7").read_bytes()
        record = MemoryRecord.from_dict(json.loads((VAL / "v04_record_3.json").read_text(encoding="utf-8")))
        result = compile_locality_memory(base, record, resolution="R2")
        self.assertEqual(result.mode, "native")
        self.assertEqual(result.frame, result.standalone_frame)
        self.assertGreaterEqual(result.delta_candidate_bytes, result.standalone_frame_bytes)

    def test_selected_representation_preserves_target_identity_and_coordinates(self):
        base = (VAL / "v07_memory_1_R2.isql7").read_bytes()
        record = MemoryRecord.from_dict(json.loads((VAL / "v04_record_2.json").read_text(encoding="utf-8")))
        result = compile_locality_memory(base, record, resolution="R2")
        expected = decode_native_spectral_frame(result.standalone_frame)
        actual = decode_delta_frame(result.frame, base) if result.mode == "delta" else decode_native_spectral_frame(result.frame)
        self.assertEqual(actual.address_digest, expected.address_digest)
        self.assertEqual(actual.registry_revision, expected.registry_revision)
        self.assertEqual(actual.registry_hash, expected.registry_hash)
        self.assertEqual(actual.sequence, expected.sequence)


if __name__ == "__main__":
    unittest.main()
