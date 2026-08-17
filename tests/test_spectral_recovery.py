import tempfile
import unittest
from pathlib import Path

from isql_core.decoder import SpectralCoordinateDecoder
from isql_core.memory import encode_text_memory
from isql_core.recoverability import SemanticReference, compare_memory_profiles
from isql_core.semantics import SemanticAnalysis, SemanticCoordinateSet
from isql_core.spectral import SpectralPacket, SpectralRegistryStore, expand_spectral_packet
from isql_core.store import MemoryStore


class SpectralRecoveryTests(unittest.TestCase):
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
        )
        self.store.put(self.record)

    def tearDown(self):
        self.tmp.cleanup()

    def test_spectral_r2_decoder_expands_packet_and_stays_non_exact(self):
        result = SpectralCoordinateDecoder(self.store).decode(self.record.get_layer("spectral", "R2").code)
        self.assertEqual(result.profile_id, "spectral")
        self.assertFalse(result.exact)
        self.assertIn("AI memory changes must not alter source identity.", result.recovered_text)
        self.assertIn("source address separate_from memory representation", result.recovered_text)

    def test_spectral_r4_is_exact_only_via_source_contract(self):
        result = SpectralCoordinateDecoder(self.store).decode(self.record.get_layer("spectral", "R4").code)
        self.assertTrue(result.exact)
        self.assertEqual(result.recovered_text, self.text)

    def test_profile_comparison_includes_spectral_compaction_and_exact_coordinate_fidelity(self):
        report = compare_memory_profiles(
            self.text,
            self.record,
            store=self.store,
            resolution="R2",
            semantic_reference=SemanticReference.from_coordinates(self.coords),
        )
        self.assertEqual(set(report.profiles), {"baseline", "semantic", "spectral"})
        spectral = report.profiles["spectral"]
        self.assertEqual(spectral.coordinate_fidelity.aggregate, 1.0)
        self.assertIsNotNone(spectral.compaction)
        self.assertLess(spectral.compaction.packet_bytes, report.profiles["semantic"].layer_data_bytes)
        self.assertGreaterEqual(spectral.compaction.cold_total_bytes, spectral.compaction.packet_bytes)

    def test_second_memory_with_same_coordinates_has_zero_registry_delta(self):
        second = encode_text_memory(
            self.text + " Additional surface wording.",
            semantic_analysis=self.analysis,
            spectral_registry_store=self.registry_store,
        )
        self.store.put(second)
        packet = SpectralPacket.from_dict(second.get_layer("spectral", "R2").data["packet"])
        self.assertEqual(packet.registry_delta_bytes, 0)
        recovered = expand_spectral_packet(packet, self.registry_store)
        self.assertEqual(recovered.to_dict(), self.coords.to_dict())


if __name__ == "__main__":
    unittest.main()
