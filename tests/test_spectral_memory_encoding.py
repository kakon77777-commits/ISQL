import tempfile
import unittest
from pathlib import Path

from isql_core.memory import encode_text_memory
from isql_core.semantics import SemanticAnalysis, SemanticCoordinateSet
from isql_core.spectral import SpectralPacket, SpectralRegistryStore, expand_spectral_packet


class SpectralMemoryEncodingTests(unittest.TestCase):
    def analysis(self):
        return SemanticAnalysis(
            analyzer_id="test-ai/v1",
            analyzer_contract="isql-semantic-analysis/v0.2",
            coordinates=SemanticCoordinateSet.from_dict({
                "summary": "ISQL separates stable source identity from adaptive memory.",
                "concepts": ["stable source identity", "adaptive memory", "multi-resolution recovery"],
                "entities": ["ISQL-ADDR", "ISQL-MEM"],
                "relations": [
                    {"subject": "ISQL-ADDR", "predicate": "separate_from", "object": "ISQL-MEM"},
                ],
                "claims": ["Memory representation changes do not change stable source identity."],
                "intent": "specify memory invariants",
                "uncertainty": ["compression ratio is empirical"],
                "tags": ["memory", "addressing"],
                "language": "en",
            }),
        )

    def test_spectral_profile_is_added_without_changing_existing_identity_or_codes(self):
        text = "ISQL keeps address identity separate from memory representation."
        base = encode_text_memory(text, semantic_analysis=self.analysis())
        with tempfile.TemporaryDirectory() as td:
            enriched = encode_text_memory(
                text,
                semantic_analysis=self.analysis(),
                spectral_registry_store=SpectralRegistryStore(Path(td)),
            )
            self.assertEqual(base.address, enriched.address)
            self.assertEqual(tuple(enriched.variants), ("baseline", "semantic", "spectral"))
            for profile in ("baseline", "semantic"):
                for resolution in ("R0", "R1", "R2", "R3", "R4"):
                    self.assertEqual(
                        base.get_layer(profile, resolution).code,
                        enriched.get_layer(profile, resolution).code,
                    )

    def test_spectral_r1_r2_store_packets_not_verbose_coordinate_strings(self):
        with tempfile.TemporaryDirectory() as td:
            registry_store = SpectralRegistryStore(Path(td))
            rec = encode_text_memory(
                "source text",
                semantic_analysis=self.analysis(),
                spectral_registry_store=registry_store,
            )
            for resolution in ("R1", "R2"):
                data = rec.get_layer("spectral", resolution).data
                self.assertEqual(set(data), {"packet"})
                packet = SpectralPacket.from_dict(data["packet"])
                self.assertTrue(packet.sequence)
            self.assertNotIn("coordinates", rec.get_layer("spectral", "R2").data)

    def test_cold_profile_charges_registry_growth_to_full_r2_packet(self):
        with tempfile.TemporaryDirectory() as td:
            registry_store = SpectralRegistryStore(Path(td))
            rec = encode_text_memory(
                "source text",
                semantic_analysis=self.analysis(),
                spectral_registry_store=registry_store,
            )
            r2 = SpectralPacket.from_dict(rec.get_layer("spectral", "R2").data["packet"])
            r1 = SpectralPacket.from_dict(rec.get_layer("spectral", "R1").data["packet"])
            self.assertGreater(r2.registry_delta_bytes, 0)
            self.assertEqual(r1.registry_delta_bytes, 0)

    def test_spectral_r2_packet_expands_to_full_semantic_coordinates(self):
        with tempfile.TemporaryDirectory() as td:
            registry_store = SpectralRegistryStore(Path(td))
            rec = encode_text_memory(
                "source text",
                semantic_analysis=self.analysis(),
                spectral_registry_store=registry_store,
            )
            packet = SpectralPacket.from_dict(rec.get_layer("spectral", "R2").data["packet"])
            recovered = expand_spectral_packet(packet, registry_store)
            self.assertEqual(recovered.to_dict(), self.analysis().coordinates.to_dict())

    def test_spectral_r4_keeps_exact_contract(self):
        text = "exact source\n"
        with tempfile.TemporaryDirectory() as td:
            rec = encode_text_memory(
                text,
                semantic_analysis=self.analysis(),
                spectral_registry_store=SpectralRegistryStore(Path(td)),
            )
            r4 = rec.get_layer("spectral", "R4").data
            self.assertEqual(r4["exact_source"], text)
            self.assertIn("exact_sha256", r4)


if __name__ == "__main__":
    unittest.main()
