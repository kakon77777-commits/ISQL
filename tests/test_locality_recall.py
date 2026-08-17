import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.locality import build_locality_index, recall_locality_candidates

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


def b(name: str) -> bytes:
    return (VAL / name).read_bytes()


class LocalityRecallTests(unittest.TestCase):
    def test_same_registry_exact_neighbor_ranks_first(self):
        index = build_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
            ('three.isql7', b('v07_memory_3_R2.isql7')),
        ])
        rows = recall_locality_candidates(b('v07_memory_2_R2.isql7'), index, top_k=2)
        self.assertEqual(rows[0].frame_ref, 'one.isql7')
        self.assertTrue(rows[0].same_registry)
        self.assertEqual(rows[0].exact_block_count, 5)
        self.assertFalse(rows[1].same_registry)

    def test_near_coordinate_target_prefers_same_registry_neighbor(self):
        index = build_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
            ('three.isql7', b('v07_memory_3_R2.isql7')),
        ])
        rows = recall_locality_candidates(b('v08_near_R2.isql7'), index, top_k=2)
        self.assertEqual(rows[0].frame_ref, 'one.isql7')
        self.assertTrue(rows[0].same_registry)
        self.assertGreater(rows[0].exact_block_count, 0)
        self.assertLess(rows[0].normalized_sum_distance, rows[1].normalized_sum_distance)

    def test_target_self_is_excluded_by_frame_hash(self):
        target = b('v07_memory_1_R2.isql7')
        index = build_locality_index([
            ('self.isql7', target),
            ('two.isql7', b('v07_memory_2_R2.isql7')),
        ])
        rows = recall_locality_candidates(target, index, top_k=8)
        self.assertEqual([r.frame_ref for r in rows], ['two.isql7'])

    def test_ties_are_deterministic_by_frame_hash(self):
        index = build_locality_index([
            ('two.isql7', b('v07_memory_2_R2.isql7')),
            ('one.isql7', b('v07_memory_1_R2.isql7')),
        ])
        rows = recall_locality_candidates(b('v08_near_R2.isql7'), index, top_k=8)
        hashes = [r.frame_sha256 for r in rows]
        self.assertEqual(hashes, sorted(hashes))

    def test_invalid_top_k_rejected(self):
        index = build_locality_index([])
        with self.assertRaises(ISQLValidationError):
            recall_locality_candidates(b('v07_memory_1_R2.isql7'), index, top_k=0)


if __name__ == '__main__':
    unittest.main()
