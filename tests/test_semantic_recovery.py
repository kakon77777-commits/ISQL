import tempfile
import unittest
from pathlib import Path

from isql_core.decoder import DeterministicMemoryDecoder, SemanticCoordinateDecoder
from isql_core.errors import ISQLExecutionError
from isql_core.memory import encode_text_memory
from isql_core.recoverability import (
    SemanticReference,
    compare_memory_profiles,
    evaluate_coordinate_fidelity,
)
from isql_core.semantics import SemanticAnalysis, SemanticCoordinateSet
from isql_core.store import MemoryStore


class SemanticRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.tmp.name))
        self.text = (
            "ISQL keeps stable source addressing separate from adaptive AI memory. "
            "Semantic memory can use multiple resolutions while exact recovery remains restricted to R4."
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
        self.record = encode_text_memory(self.text, semantic_analysis=self.analysis)
        self.store.put(self.record)

    def tearDown(self):
        self.tmp.cleanup()

    def test_semantic_r1_decoder_realizes_gist_and_stays_non_exact(self):
        decoder = SemanticCoordinateDecoder(self.store)
        result = decoder.decode(self.record.get_layer("semantic", "R1").code)
        self.assertEqual(result.profile_id, "semantic")
        self.assertFalse(result.exact)
        self.assertIn("ISQL separates stable source identity", result.recovered_text)
        self.assertIn("multi-resolution recovery", result.recovered_text)

    def test_semantic_r2_decoder_realizes_claims_and_relations(self):
        result = SemanticCoordinateDecoder(self.store).decode(self.record.get_layer("semantic", "R2").code)
        self.assertFalse(result.exact)
        self.assertIn("AI memory changes must not alter source identity.", result.recovered_text)
        self.assertIn("source address separate_from memory representation", result.recovered_text)

    def test_baseline_decoder_rejects_semantic_profile_code(self):
        code = self.record.get_layer("semantic", "R1").code
        with self.assertRaises(ISQLExecutionError):
            DeterministicMemoryDecoder(self.store).decode(code)

    def test_coordinate_fidelity_is_one_for_identical_reference(self):
        reference = SemanticReference.from_coordinates(self.coords)
        report = evaluate_coordinate_fidelity(reference, self.coords)
        self.assertEqual(report.concept_f1, 1.0)
        self.assertEqual(report.entity_recall, 1.0)
        self.assertEqual(report.relation_recall, 1.0)
        self.assertEqual(report.claim_recall, 1.0)
        self.assertEqual(report.intent_match, 1.0)
        self.assertEqual(report.aggregate, 1.0)

    def test_coordinate_fidelity_exposes_partial_recall(self):
        reference = SemanticReference.from_coordinates(self.coords)
        partial = SemanticCoordinateSet.from_dict({
            "summary": "partial",
            "concepts": ["AI memory"],
            "entities": ["ISQL"],
            "relations": [],
            "claims": [],
            "intent": None,
            "uncertainty": [],
            "tags": [],
            "language": "en",
        })
        report = evaluate_coordinate_fidelity(reference, partial)
        self.assertGreater(report.concept_recall, 0.0)
        self.assertLess(report.concept_recall, 1.0)
        self.assertEqual(report.relation_recall, 0.0)
        self.assertLess(report.aggregate, 1.0)

    def test_profile_comparison_reports_same_address_and_coordinate_fidelity(self):
        report = compare_memory_profiles(
            self.text,
            self.record,
            store=self.store,
            resolution="R2",
            semantic_reference=SemanticReference.from_coordinates(self.coords),
        )
        self.assertEqual(report.address, self.record.address.to_wire())
        self.assertEqual(set(report.profiles), {"baseline", "semantic"})
        self.assertEqual(report.profiles["semantic"].coordinate_fidelity.aggregate, 1.0)
        self.assertIsNone(report.profiles["baseline"].coordinate_fidelity)
        self.assertGreater(report.profiles["semantic"].layer_data_bytes, 0)


if __name__ == "__main__":
    unittest.main()
