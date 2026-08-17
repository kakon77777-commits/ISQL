import unittest

from isql_core.memory import encode_text_memory
from isql_core.semantics import SemanticAnalysis, SemanticCoordinateSet


class SemanticMemoryEncodingTests(unittest.TestCase):
    def analysis(self):
        coords = SemanticCoordinateSet.from_dict({
            "summary": "ISQL memory keeps a stable source address while allowing adaptive semantic representations.",
            "concepts": ["stable source address", "adaptive semantic memory", "multi-resolution recovery"],
            "entities": ["ISQL-ADDR", "ISQL-MEM"],
            "relations": [
                {"subject": "ISQL-ADDR", "predicate": "separate_from", "object": "ISQL-MEM"},
                {"subject": "ISQL-MEM", "predicate": "supports", "object": "multi-resolution recovery"},
            ],
            "claims": [
                "Changing an AI memory representation must not change the source address.",
                "R4 exact recovery remains source-contract-only.",
            ],
            "intent": "define AI-assisted memory encoding",
            "uncertainty": ["semantic fidelity metrics remain provisional"],
            "tags": ["memory", "addressing", "AI"],
            "language": "en",
        })
        return SemanticAnalysis(
            analyzer_id="gpt-test/v1",
            analyzer_contract="isql-semantic-analysis/v0.2",
            coordinates=coords,
        )

    def test_semantic_analysis_adds_semantic_variant_without_changing_address(self):
        text = "ISQL keeps address identity separate from memory representation."
        base = encode_text_memory(text)
        enriched = encode_text_memory(text, semantic_analysis=self.analysis())
        self.assertEqual(base.address, enriched.address)
        self.assertEqual(tuple(enriched.variants), ("baseline", "semantic"))
        self.assertEqual(base.layers["R2"].code, enriched.variants["baseline"].layers["R2"].code)

    def test_semantic_variant_discloses_analyzer(self):
        rec = encode_text_memory("source text", semantic_analysis=self.analysis())
        variant = rec.variants["semantic"]
        self.assertEqual(variant.analyzer_id, "gpt-test/v1")
        self.assertEqual(variant.analyzer_contract, "isql-semantic-analysis/v0.2")

    def test_semantic_r1_is_compact_gist_not_baseline_preview(self):
        rec = encode_text_memory("source text", semantic_analysis=self.analysis())
        r1 = rec.get_layer("semantic", "R1").data
        self.assertIn("summary", r1)
        self.assertIn("anchors", r1)
        self.assertIn("intent", r1)
        self.assertNotIn("preview", r1)
        self.assertLessEqual(len(r1["anchors"]), 5)

    def test_semantic_r2_contains_full_typed_coordinates(self):
        rec = encode_text_memory("source text", semantic_analysis=self.analysis())
        r2 = rec.get_layer("semantic", "R2").data
        self.assertEqual(r2["coordinates"]["summary"], self.analysis().coordinates.summary)
        self.assertEqual(r2["coordinates"]["relations"][0]["predicate"], "separate_from")

    def test_semantic_profile_has_distinct_mem_codes_at_every_resolution(self):
        rec = encode_text_memory("source text", semantic_analysis=self.analysis())
        for r in ("R0", "R1", "R2", "R3", "R4"):
            self.assertNotEqual(
                rec.get_layer("baseline", r).code,
                rec.get_layer("semantic", r).code,
            )

    def test_r4_contract_still_contains_exact_source_and_hash(self):
        text = "exact\n來源\n"
        rec = encode_text_memory(text, semantic_analysis=self.analysis())
        r4 = rec.get_layer("semantic", "R4").data
        self.assertEqual(r4["exact_source"], text)
        self.assertIn("exact_sha256", r4)
        self.assertEqual(rec.address, encode_text_memory(text).address)


if __name__ == "__main__":
    unittest.main()
