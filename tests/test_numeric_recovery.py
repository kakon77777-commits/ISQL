import tempfile
import unittest
from pathlib import Path

from isql_core.decoder import NumericWireDecoder
from isql_core.memory import encode_text_memory
from isql_core.recoverability import SemanticReference, compare_memory_profiles
from isql_core.semantics import SemanticAnalysis, SemanticCoordinateSet
from isql_core.spectral import SpectralRegistryStore
from isql_core.store import MemoryStore


class NumericRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry_store = SpectralRegistryStore(self.root)
        self.store = MemoryStore(self.root)
        self.text = (
            "ISQL keeps stable source addressing separate from adaptive AI memory. "
            "Semantic memory uses multiple resolutions while exact recovery remains restricted to R4."
        )
        self.coords = SemanticCoordinateSet.from_dict({
            "summary": "ISQL separates stable source identity from adaptive multi-resolution AI memory.",
            "concepts": ["stable source identity", "AI memory", "multi-resolution recovery", "R4 exact recovery"],
            "entities": ["ISQL", "R4"],
            "relations": [
                {"subject": "source address", "predicate": "separate_from", "object": "memory representation"},
                {"subject": "R4", "predicate": "permits", "object": "exact recovery"},
            ],
            "claims": [
                "AI memory changes must not alter source identity.",
                "Exact recovery is restricted to R4.",
            ],
            "intent": "specify AI memory invariants",
            "uncertainty": [],
            "tags": ["ISQL", "memory"],
            "language": "en",
        })
        self.analysis = SemanticAnalysis(
            analyzer_id="test-ai/v1",
            analyzer_contract="isql-semantic-analysis/v0.2",
            coordinates=self.coords,
        )
        self.record = encode_text_memory(
            self.text,
            semantic_analysis=self.analysis,
            spectral_registry_store=self.registry_store,
            numeric_wire=True,
        )
        self.store.put(self.record)

    def tearDown(self):
        self.tmp.cleanup()

    def test_numeric_r2_decoder_recovers_coordinates_and_stays_non_exact(self):
        result = NumericWireDecoder(self.store).decode(self.record.get_layer("numeric", "R2").code)
        self.assertEqual(result.profile_id, "numeric")
        self.assertFalse(result.exact)
        self.assertIn("AI memory changes must not alter source identity.", result.recovered_text)
        self.assertIn("source address separate_from memory representation", result.recovered_text)

    def test_numeric_r4_is_exact_only_via_source_contract(self):
        result = NumericWireDecoder(self.store).decode(self.record.get_layer("numeric", "R4").code)
        self.assertTrue(result.exact)
        self.assertEqual(result.recovered_text, self.text)

    def test_profile_comparison_reports_numeric_wire_compaction_and_fidelity(self):
        report = compare_memory_profiles(
            self.text,
            self.record,
            store=self.store,
            resolution="R2",
            semantic_reference=SemanticReference.from_coordinates(self.coords),
        )
        self.assertEqual(set(report.profiles), {"baseline", "semantic", "spectral", "numeric"})
        numeric = report.profiles["numeric"]
        spectral = report.profiles["spectral"]
        self.assertEqual(numeric.coordinate_fidelity.aggregate, 1.0)
        self.assertIsNotNone(numeric.compaction)
        self.assertLess(numeric.compaction.wire_bytes, spectral.compaction.packet_bytes)
        self.assertLess(numeric.compaction.wire_vs_packet_ratio, 1.0)
        self.assertEqual(numeric.compaction.registry_delta_bytes, spectral.compaction.registry_delta_bytes)
        self.assertGreaterEqual(numeric.compaction.cold_total_bytes, numeric.compaction.wire_bytes)


if __name__ == "__main__":
    unittest.main()
