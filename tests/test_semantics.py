import unittest

from isql_core.errors import ISQLValidationError
from isql_core.semantics import (
    CallableSemanticAnalyzer,
    SemanticAnalysis,
    SemanticCoordinateSet,
    SemanticRelation,
)


class SemanticCoordinateTests(unittest.TestCase):
    def sample(self):
        return SemanticCoordinateSet.from_dict({
            "summary": "ISQL separates stable address identity from adaptive memory representation.",
            "concepts": ["stable address", "adaptive memory", "multi-resolution"],
            "entities": ["ISQL"],
            "relations": [
                {"subject": "ISQL-ADDR", "predicate": "separate_from", "object": "ISQL-MEM"}
            ],
            "claims": ["Changing memory representation must not change source identity."],
            "intent": "define memory architecture",
            "uncertainty": ["semantic distance metric remains provisional"],
            "tags": ["memory", "addressing"],
            "language": "en",
        })

    def test_coordinate_round_trip(self):
        coords = self.sample()
        self.assertEqual(SemanticCoordinateSet.from_dict(coords.to_dict()), coords)
        self.assertEqual(coords.relations[0].predicate, "separate_from")

    def test_duplicate_concepts_are_canonicalized_preserving_order(self):
        coords = SemanticCoordinateSet.from_dict({
            "summary": "x",
            "concepts": ["alpha", "alpha", "beta"],
            "entities": [], "relations": [], "claims": [],
            "intent": None, "uncertainty": [], "tags": [], "language": "en",
        })
        self.assertEqual(coords.concepts, ("alpha", "beta"))

    def test_empty_summary_fails_closed(self):
        raw = self.sample().to_dict()
        raw["summary"] = ""
        with self.assertRaises(ISQLValidationError):
            SemanticCoordinateSet.from_dict(raw)

    def test_relation_requires_all_three_fields(self):
        with self.assertRaises(ISQLValidationError):
            SemanticRelation.from_dict({"subject": "A", "predicate": "links"})

    def test_analysis_requires_disclosed_analyzer_contract(self):
        coords = self.sample()
        with self.assertRaises(ISQLValidationError):
            SemanticAnalysis(analyzer_id="demo-ai", analyzer_contract="", coordinates=coords)

    def test_callable_analyzer_records_identity_and_accepts_dict_result(self):
        analyzer = CallableSemanticAnalyzer(
            analyzer_id="demo-ai/v1",
            analyzer_contract="isql-semantic-analysis/v1",
            fn=lambda text, context: self.sample().to_dict(),
        )
        result = analyzer.analyze("source", context={"domain": "memory"})
        self.assertEqual(result.analyzer_id, "demo-ai/v1")
        self.assertEqual(result.coordinates.summary, self.sample().summary)


if __name__ == "__main__":
    unittest.main()
