import tempfile
import unittest
from pathlib import Path

from isql_core.memory import encode_text_memory
from isql_core.semantics import SemanticAnalysis
from isql_core.spectral import SpectralPacket, SpectralRegistryStore, expand_spectral_packet
from isql_core.wire import decode_numeric_wire


def analysis():
    return SemanticAnalysis.from_dict({
        "schema": "isql.semantic-analysis/v0.2",
        "analyzer_id": "test-ai/v1",
        "analyzer_contract": "isql-semantic-analysis/v0.2",
        "coordinates": {
            "summary": "ISQL separates stable address identity from adaptive memory representation.",
            "concepts": ["stable address", "adaptive memory", "multi-resolution recovery"],
            "entities": ["ISQL-ADDR", "ISQL-MEM"],
            "relations": [
                {"subject": "ISQL-ADDR", "predicate": "separate_from", "object": "ISQL-MEM"},
                {"subject": "ISQL-MEM", "predicate": "supports", "object": "multi-resolution recovery"},
            ],
            "claims": ["Memory representation changes must not change stable address identity."],
            "intent": "specify memory invariants",
            "uncertainty": ["compression ratio is empirical"],
            "tags": ["memory", "addressing"],
            "language": "en",
        },
    })


class NumericMemoryEncodingTests(unittest.TestCase):
    def test_numeric_profile_is_additive_and_does_not_change_existing_codes(self):
        text = "ISQL keeps stable address identity separate from adaptive memory."
        with tempfile.TemporaryDirectory() as td_before, tempfile.TemporaryDirectory() as td_after:
            before = encode_text_memory(
                text,
                semantic_analysis=analysis(),
                spectral_registry_store=SpectralRegistryStore(Path(td_before)),
            )
            after = encode_text_memory(
                text,
                semantic_analysis=analysis(),
                spectral_registry_store=SpectralRegistryStore(Path(td_after)),
                numeric_wire=True,
            )
            self.assertEqual(before.address, after.address)
            self.assertEqual(set(after.variants), {"baseline", "semantic", "spectral", "numeric"})
            for profile in ("baseline", "semantic", "spectral"):
                for resolution in ("R0", "R1", "R2", "R3", "R4"):
                    self.assertEqual(
                        before.get_layer(profile, resolution).code,
                        after.get_layer(profile, resolution).code,
                    )

    def test_numeric_r1_r2_store_only_digits_wire(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record = encode_text_memory(
                "ISQL keeps stable address identity separate from adaptive memory.",
                semantic_analysis=analysis(),
                spectral_registry_store=SpectralRegistryStore(root),
                numeric_wire=True,
            )
            for resolution in ("R1", "R2"):
                data = record.get_layer("numeric", resolution).data
                self.assertEqual(set(data), {"wire"})
                self.assertTrue(data["wire"].isascii() and data["wire"].isdigit())

    def test_numeric_r2_wire_recovers_same_coordinates_as_spectral_r2(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SpectralRegistryStore(root)
            record = encode_text_memory(
                "ISQL keeps stable address identity separate from adaptive memory.",
                semantic_analysis=analysis(),
                spectral_registry_store=store,
                numeric_wire=True,
            )
            numeric_packet = decode_numeric_wire(record.get_layer("numeric", "R2").data["wire"])
            numeric_coords = expand_spectral_packet(numeric_packet, store)
            spectral_packet = SpectralPacket.from_dict(record.get_layer("spectral", "R2").data["packet"])
            spectral_coords = expand_spectral_packet(spectral_packet, store)
            self.assertEqual(numeric_coords.to_dict(), spectral_coords.to_dict())

    def test_numeric_r4_keeps_exact_source_contract(self):
        text = "Exact source must stay exact."
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record = encode_text_memory(
                text,
                semantic_analysis=analysis(),
                spectral_registry_store=SpectralRegistryStore(root),
                numeric_wire=True,
            )
            r4 = record.get_layer("numeric", "R4").data
            self.assertEqual(r4["exact_source"], text)
            self.assertIn("exact_sha256", r4)


if __name__ == "__main__":
    unittest.main()
