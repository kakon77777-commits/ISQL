import unittest

from isql_core.memory import MemoryLayer, MemoryRecord, MemoryVariant, encode_text_memory
from isql_core.address import address_text


class MemoryV02SchemaTests(unittest.TestCase):
    def test_record_exposes_baseline_variant_and_legacy_layers_view(self):
        rec = encode_text_memory("Alpha beta. Alpha gamma.")
        self.assertEqual(rec.default_profile, "baseline")
        self.assertIn("baseline", rec.variants)
        self.assertEqual(rec.layers, rec.variants["baseline"].layers)
        self.assertEqual(rec.encoder_version, rec.variants["baseline"].encoder_version)

    def test_memory_variant_requires_profile_id(self):
        rec = encode_text_memory("source")
        baseline = rec.variants["baseline"]
        self.assertIsInstance(baseline, MemoryVariant)
        self.assertEqual(baseline.profile_id, "baseline")
        self.assertEqual(tuple(baseline.layers), ("R0", "R1", "R2", "R3", "R4"))

    def test_v02_round_trip_preserves_variants(self):
        rec = encode_text_memory("round trip")
        raw = rec.to_dict()
        self.assertEqual(raw["schema"], "isql.memory-record/v0.2")
        loaded = MemoryRecord.from_dict(raw)
        self.assertEqual(loaded.to_dict(), raw)

    def test_v01_record_migrates_to_baseline_profile(self):
        rec = encode_text_memory("legacy source")
        layers = rec.layers
        legacy = {
            "schema": "isql.memory-record/v0.1",
            "address": rec.address.to_wire(),
            "encoder_version": rec.encoder_version,
            "source_type": "text",
            "layers": {k: v.to_dict() for k, v in layers.items()},
        }
        loaded = MemoryRecord.from_dict(legacy)
        self.assertEqual(loaded.default_profile, "baseline")
        self.assertEqual(tuple(loaded.variants), ("baseline",))
        self.assertEqual(loaded.layers["R4"].data["exact_source"], "legacy source")

    def test_get_layer_fails_closed_for_unknown_profile(self):
        rec = encode_text_memory("source")
        with self.assertRaises(KeyError):
            rec.get_layer("semantic", "R1")


if __name__ == "__main__":
    unittest.main()
