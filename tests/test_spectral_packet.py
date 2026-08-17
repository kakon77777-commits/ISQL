import json
import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.semantics import SemanticCoordinateSet
from isql_core.spectral import (
    SpectralRegistryStore,
    compile_spectral_packet,
    expand_spectral_packet,
)


class SpectralPacketTests(unittest.TestCase):
    def coords(self):
        return SemanticCoordinateSet.from_dict({
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
        })

    def test_compile_emits_integer_only_sparse_sequence_and_no_source_phrases(self):
        with tempfile.TemporaryDirectory() as td:
            result = compile_spectral_packet(self.coords(), SpectralRegistryStore(Path(td)))
            self.assertTrue(result.packet.sequence)
            self.assertTrue(all(isinstance(x, int) and x >= 0 for x in result.packet.sequence))
            encoded = json.dumps(result.packet.to_dict(), ensure_ascii=False)
            self.assertNotIn("stable address", encoded)
            self.assertNotIn("ISQL-ADDR", encoded)
            self.assertGreater(result.registry_delta_bytes, 0)

    def test_packet_round_trip_recovers_exact_coordinate_set(self):
        with tempfile.TemporaryDirectory() as td:
            store = SpectralRegistryStore(Path(td))
            result = compile_spectral_packet(self.coords(), store)
            recovered = expand_spectral_packet(result.packet, store)
            self.assertEqual(recovered.to_dict(), self.coords().to_dict())

    def test_same_vocabulary_reuses_registry_revision_and_sequence(self):
        with tempfile.TemporaryDirectory() as td:
            store = SpectralRegistryStore(Path(td))
            first = compile_spectral_packet(self.coords(), store)
            second = compile_spectral_packet(self.coords(), store)
            self.assertEqual(first.packet.registry_revision, second.packet.registry_revision)
            self.assertEqual(first.packet.sequence, second.packet.sequence)
            self.assertEqual(second.registry_delta_bytes, 0)

    def test_relation_nodes_reuse_atom_ids(self):
        with tempfile.TemporaryDirectory() as td:
            store = SpectralRegistryStore(Path(td))
            result = compile_spectral_packet(self.coords(), store)
            reg = store.load_revision(result.packet.registry_revision)
            addr_id = reg.namespaces["atom"].index("ISQL-ADDR") + 1
            mem_id = reg.namespaces["atom"].index("ISQL-MEM") + 1
            # Decode the packet and verify relation nodes resolve through the same atom namespace.
            recovered = expand_spectral_packet(result.packet, store)
            self.assertEqual(recovered.relations[0].subject, reg.resolve("atom", addr_id))
            self.assertEqual(recovered.relations[0].object, reg.resolve("atom", mem_id))

    def test_registry_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            store = SpectralRegistryStore(Path(td))
            result = compile_spectral_packet(self.coords(), store)
            bad = result.packet.with_registry_hash("0" * 64)
            with self.assertRaises(ISQLValidationError):
                expand_spectral_packet(bad, store)


if __name__ == "__main__":
    unittest.main()
