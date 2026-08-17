import hashlib
import unittest
from pathlib import Path

from isql_core.delta import decode_delta_frame
from isql_core.errors import ISQLValidationError
from isql_core.locality import build_locality_index, recall_locality_candidates, select_locality_base
from isql_core.native import NativeSpectralFrame

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


def b(name: str) -> bytes:
    return (VAL / name).read_bytes()


def native(seq, *, marker: int) -> bytes:
    return NativeSpectralFrame(
        address_digest=bytes([marker]) * 32,
        resolution='R2',
        registry_revision=1,
        registry_hash='11' * 32,
        sequence=tuple(seq),
    ).to_bytes()


class BaseSelectionTests(unittest.TestCase):
    def test_exact_byte_reranking_can_override_heuristic_order(self):
        target = native([100] * 16, marker=9)
        misleading = native(([0, 200] * 8), marker=1)  # same block sum, large per-coordinate deltas
        efficient = native([99] * 16, marker=2)        # worse sum score, tiny deltas
        frames = {'a.isql7': misleading, 'b.isql7': efficient}
        index = build_locality_index(list(frames.items()))
        recalled = recall_locality_candidates(target, index, top_k=2)
        self.assertEqual(recalled[0].frame_ref, 'a.isql7')
        result = select_locality_base(target, index, frames.__getitem__, top_k=2)
        self.assertEqual(result.mode, 'delta')
        self.assertEqual(result.selected_base_ref, 'b.isql7')
        self.assertLess(result.selected_frame_bytes, len(target))
        self.assertEqual(decode_delta_frame(result.frame, efficient).to_bytes(), target)

    def test_frozen_identical_neighbor_selects_delta(self):
        target = b('v07_memory_2_R2.isql7')
        frames = {
            'one.isql7': b('v07_memory_1_R2.isql7'),
            'three.isql7': b('v07_memory_3_R2.isql7'),
        }
        result = select_locality_base(target, build_locality_index(frames.items()), frames.__getitem__, top_k=2)
        self.assertEqual(result.mode, 'delta')
        self.assertEqual(result.selected_frame_bytes, 87)
        base = frames[result.selected_base_ref]
        self.assertEqual(decode_delta_frame(result.frame, base).to_bytes(), target)

    def test_low_locality_falls_back_to_native(self):
        target = b('v07_memory_3_R2.isql7')
        frames = {
            'one.isql7': b('v07_memory_1_R2.isql7'),
            'two.isql7': b('v07_memory_2_R2.isql7'),
        }
        result = select_locality_base(target, build_locality_index(frames.items()), frames.__getitem__, top_k=2)
        self.assertEqual(result.mode, 'native')
        self.assertEqual(result.frame, target)
        self.assertEqual(result.selected_frame_bytes, len(target))
        self.assertIsNone(result.selected_base_ref)

    def test_missing_base_ref_fails_closed(self):
        target = b('v07_memory_2_R2.isql7')
        base = b('v07_memory_1_R2.isql7')
        index = build_locality_index([('one.isql7', base)])
        def missing(_):
            raise FileNotFoundError('gone')
        with self.assertRaises(ISQLValidationError):
            select_locality_base(target, index, missing, top_k=1)

    def test_corrupt_or_wrong_base_fails_closed_by_hash(self):
        target = b('v07_memory_2_R2.isql7')
        base = b('v07_memory_1_R2.isql7')
        index = build_locality_index([('one.isql7', base)])
        with self.assertRaises(ISQLValidationError):
            select_locality_base(target, index, lambda _: base + b'x', top_k=1)

    def test_top_k_result_matches_exhaustive_oracle_on_frozen_corpus(self):
        target = b('v08_near_R2.isql7')
        frames = {
            'one.isql7': b('v07_memory_1_R2.isql7'),
            'two.isql7': b('v07_memory_2_R2.isql7'),
            'three.isql7': b('v07_memory_3_R2.isql7'),
        }
        index = build_locality_index(frames.items())
        fast = select_locality_base(target, index, frames.__getitem__, top_k=2)
        oracle = select_locality_base(target, index, frames.__getitem__, top_k=99)
        self.assertEqual(fast.mode, oracle.mode)
        self.assertEqual(fast.selected_frame_bytes, oracle.selected_frame_bytes)
        self.assertEqual(fast.selected_base_sha256, oracle.selected_base_sha256)


if __name__ == '__main__':
    unittest.main()
