import unittest

from isql_core.errors import ISQLValidationError
from isql_core.semantic_addressing import (
    ExactStateRef,
    build_semantic_address_index,
    exact_state_ref,
    resolve_semantic_candidates,
    semantic_address_from_analysis,
    verify_exact_state,
)
from isql_core.semantics import SemanticAnalysis, SemanticCoordinateSet, SemanticRelation


def analysis(
    *,
    analyzer_id: str = "fixture-analyzer",
    contract: str = "fixture-contract-v1",
    concepts: tuple[str, ...] = (),
    entities: tuple[str, ...] = (),
    relations: tuple[SemanticRelation, ...] = (),
    claims: tuple[str, ...] = (),
    intent: str | None = None,
    tags: tuple[str, ...] = (),
    language: str = "en",
) -> SemanticAnalysis:
    return SemanticAnalysis(
        analyzer_id=analyzer_id,
        analyzer_contract=contract,
        coordinates=SemanticCoordinateSet(
            summary="fixture semantic summary",
            concepts=concepts,
            entities=entities,
            relations=relations,
            claims=claims,
            intent=intent,
            uncertainty=(),
            tags=tags,
            language=language,
        ),
    )


class DualAddressingPrototypeTests(unittest.TestCase):
    def test_same_bytes_keep_same_exact_identity_across_semantic_addresses(self):
        payload = b"same canonical state bytes"
        left = exact_state_ref("entity-1", payload)
        right = exact_state_ref("entity-1", payload)
        self.assertEqual(left, right)

        a = semantic_address_from_analysis(analysis(concepts=("memory",)))
        b = semantic_address_from_analysis(analysis(concepts=("world",)))
        self.assertNotEqual(a.content_hash(), b.content_hash())
        self.assertEqual(left.state_sha256, right.state_sha256)

    def test_similar_semantics_do_not_collapse_different_exact_states(self):
        semantic = analysis(concepts=("memory",), tags=("agent",))
        index = build_semantic_address_index([
            ("entity-a", b"state-a", semantic),
            ("entity-b", b"state-b", semantic),
        ])
        self.assertEqual(len(index.entries), 2)
        self.assertNotEqual(
            index.entries[0].exact.state_sha256,
            index.entries[1].exact.state_sha256,
        )

    def test_exact_verification_is_independent_of_semantic_match(self):
        exact = exact_state_ref("entity-a", b"authoritative bytes")
        self.assertTrue(verify_exact_state(b"authoritative bytes", exact))
        self.assertFalse(verify_exact_state(b"semantically similar bytes", exact))

    def test_profile_contract_isolation_fails_closed_to_empty_candidate_set(self):
        stored = analysis(contract="contract-v1", concepts=("memory",))
        query = analysis(contract="contract-v2", concepts=("memory",))
        index = build_semantic_address_index([("entity-a", b"state", stored)])
        result = resolve_semantic_candidates(
            semantic_address_from_analysis(query),
            index,
        )
        self.assertEqual(result.profile_entry_count, 0)
        self.assertEqual(result.probe_count, 0)
        self.assertEqual(result.candidates, ())

    def test_typed_evidence_ranks_more_complete_candidate_first(self):
        relation = SemanticRelation("alice", "owns", "memory-node")
        query = semantic_address_from_analysis(analysis(
            concepts=("memory", "agent"),
            entities=("alice",),
            relations=(relation,),
            intent="recover context",
            tags=("persistent",),
        ))
        index = build_semantic_address_index([
            (
                "entity-best",
                b"best",
                analysis(
                    concepts=("memory", "agent"),
                    entities=("alice",),
                    relations=(relation,),
                    intent="recover context",
                    tags=("persistent",),
                ),
            ),
            (
                "entity-mid",
                b"mid",
                analysis(concepts=("memory", "agent"), tags=("persistent",)),
            ),
            (
                "entity-low",
                b"low",
                analysis(concepts=("memory",)),
            ),
        ])
        result = resolve_semantic_candidates(query, index, top_k=3)
        self.assertEqual(
            [candidate.exact.entity_id for candidate in result.candidates],
            ["entity-best", "entity-mid", "entity-low"],
        )
        self.assertEqual(result.candidates[0].score, 1.0)
        self.assertGreater(result.candidates[1].score, result.candidates[2].score)
        self.assertIn(
            'relation:["alice","owns","memory-node"]',
            result.candidates[0].matched_atoms,
        )

    def test_inverted_index_reduces_probe_domain(self):
        records = []
        for index in range(20):
            records.append((
                f"entity-{index:02d}",
                f"state-{index}".encode("utf-8"),
                analysis(concepts=(f"concept-{index}",)),
            ))
        index = build_semantic_address_index(records)
        query = semantic_address_from_analysis(analysis(concepts=("concept-7",)))
        result = resolve_semantic_candidates(query, index)
        self.assertEqual(result.entry_count, 20)
        self.assertEqual(result.profile_entry_count, 20)
        self.assertEqual(result.probe_count, 1)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].exact.entity_id, "entity-07")
        self.assertLess(result.probe_ratio, 0.1)

    def test_nfkc_casefold_and_atom_order_are_canonical(self):
        left = semantic_address_from_analysis(analysis(
            concepts=("ＭＥＭＯＲＹ", "Agent"),
            tags=("Persistent   State",),
        ))
        right = semantic_address_from_analysis(analysis(
            concepts=("agent", "memory"),
            tags=("persistent state",),
        ))
        self.assertEqual(left, right)
        self.assertEqual(left.content_hash(), right.content_hash())

    def test_relation_type_does_not_collapse_into_concept_type(self):
        rel = SemanticRelation("alice", "owns", "node")
        address = semantic_address_from_analysis(analysis(
            concepts=('["alice","owns","node"]',),
            relations=(rel,),
        ))
        kinds = [atom.kind for atom in address.atoms]
        self.assertEqual(kinds.count("concept"), 1)
        self.assertEqual(kinds.count("relation"), 1)

    def test_physical_location_is_absent_from_address_and_exact_ref(self):
        address = semantic_address_from_analysis(analysis(concepts=("memory",)))
        exact = exact_state_ref("entity-a", b"state")
        self.assertNotIn("location", address.to_dict())
        self.assertEqual(set(exact.to_dict()), {"entity_id", "state_sha256"})

    def test_duplicate_exact_reference_is_rejected(self):
        semantic = analysis(concepts=("memory",))
        with self.assertRaisesRegex(ISQLValidationError, "SEMANTIC_INDEX_DUPLICATE_EXACT_REF"):
            build_semantic_address_index([
                ("entity-a", b"same", semantic),
                ("entity-a", b"same", semantic),
            ])

    def test_summary_or_language_alone_is_not_searchable_evidence(self):
        with self.assertRaisesRegex(ISQLValidationError, "SEMANTIC_ADDRESS_NO_SEARCHABLE_ATOMS"):
            semantic_address_from_analysis(analysis())

    def test_top_k_is_bounded_and_deterministic(self):
        semantic = analysis(concepts=("memory",))
        index = build_semantic_address_index([
            ("entity-c", b"c", semantic),
            ("entity-a", b"a", semantic),
            ("entity-b", b"b", semantic),
        ])
        query = semantic_address_from_analysis(semantic)
        first = resolve_semantic_candidates(query, index, top_k=2)
        second = resolve_semantic_candidates(query, index, top_k=2)
        self.assertEqual(first, second)
        self.assertEqual(
            [candidate.exact.entity_id for candidate in first.candidates],
            ["entity-a", "entity-b"],
        )

    def test_invalid_exact_state_ref_fails_closed(self):
        with self.assertRaises(ISQLValidationError):
            ExactStateRef(entity_id="entity-a", state_sha256="not-a-hash")


if __name__ == "__main__":
    unittest.main()
