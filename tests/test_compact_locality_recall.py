import unittest
from pathlib import Path

from isql_core.compact_locality import build_compact_locality_index, recall_compact_candidates
from isql_core.native import NativeSpectralFrame

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


def b(name: str) -> bytes:
    return (VAL / name).read_bytes()


def native(seq, marker: int) -> bytes:
    return NativeSpectralFrame(
        address_digest=bytes([marker % 256]) * 32,
        resolution='R2',
        registry_revision=1,
        registry_hash='11' * 32,
        sequence=tuple(seq),
    ).to_bytes()


class CompactLocalityRecallTests(unittest.TestCase):
    def test_frozen_identical_neighbor_is_first(self):
        index = build_compact_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
            ('three.isql7', b('v07_memory_3_R2.isql7')),
        ])
        result = recall_compact_candidates(b('v07_memory_2_R2.isql7'), index, top_k=2)
        self.assertEqual(result.candidates[0].frame_ref, 'one.isql7')
        self.assertEqual(result.candidates[0].exact_block_count, 5)
        self.assertLessEqual(result.index_probe_count, result.entry_count)

    def test_frozen_near_neighbor_prefers_same_registry(self):
        index = build_compact_locality_index([
            ('one.isql7', b('v07_memory_1_R2.isql7')),
            ('two.isql7', b('v07_memory_2_R2.isql7')),
            ('three.isql7', b('v07_memory_3_R2.isql7')),
        ])
        result = recall_compact_candidates(b('v08_near_R2.isql7'), index, top_k=2)
        self.assertEqual(result.candidates[0].frame_ref, 'one.isql7')
        self.assertTrue(result.candidates[0].same_registry)
        self.assertGreaterEqual(result.candidates[0].exact_block_count, 3)

    def test_256_entry_recall_uses_bounded_probe_set(self):
        target_seq = list(range(80))
        target = native(target_seq, 250)
        good = target_seq[:]
        for i in range(64, 80):
            good[i] += 1
        frames = [('base-good.isql7', native(good, 249))]
        for i in range(255):
            seq = [((j * 37 + i * 101) % 997) + 200 for j in range(80)]
            frames.append((f'base-{i:03d}.isql7', native(seq, i)))
        index = build_compact_locality_index(frames)
        result = recall_compact_candidates(target, index, top_k=8, probe_factor=4)
        self.assertEqual(result.candidates[0].frame_ref, 'base-good.isql7')
        self.assertEqual(result.entry_count, 256)
        self.assertLessEqual(result.index_probe_count, 64)
        self.assertLessEqual(result.probe_ratio, 0.25)
        self.assertEqual(len(result.candidates), 8)

    def test_target_self_is_excluded(self):
        target = b('v07_memory_1_R2.isql7')
        index = build_compact_locality_index([
            ('self.isql7', target),
            ('two.isql7', b('v07_memory_2_R2.isql7')),
        ])
        result = recall_compact_candidates(target, index, top_k=8)
        self.assertEqual([row.frame_ref for row in result.candidates], ['two.isql7'])


if __name__ == '__main__':
    unittest.main()
