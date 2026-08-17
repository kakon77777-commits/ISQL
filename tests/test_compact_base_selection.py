import unittest
from pathlib import Path

from isql_core.compact_locality import build_compact_locality_index, select_compact_locality_base
from isql_core.delta import decode_delta_frame
from isql_core.locality import build_locality_index, select_locality_base
from isql_core.native import NativeSpectralFrame

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / 'validation'


def b(name: str) -> bytes:
    return (VAL / name).read_bytes()


def native(seq, marker: int, *, registry_hash: str = '11' * 32) -> bytes:
    return NativeSpectralFrame(
        address_digest=bytes([marker % 256]) * 32,
        resolution='R2',
        registry_revision=1,
        registry_hash=registry_hash,
        sequence=tuple(seq),
    ).to_bytes()


class CompactBaseSelectionTests(unittest.TestCase):
    def test_actual_byte_rerank_overrides_compact_recall_order(self):
        target = native([100] * 16, 9)
        misleading = native(([0, 200] * 8), 1)
        efficient = native([99] * 16, 2)
        frames = {'a.isql7': misleading, 'b.isql7': efficient}
        result = select_compact_locality_base(
            target,
            build_compact_locality_index(frames.items()),
            frames.__getitem__,
            top_k=2,
        )
        self.assertEqual(result.recall.candidates[0].frame_ref, 'a.isql7')
        self.assertEqual(result.selection.selected_base_ref, 'b.isql7')
        self.assertEqual(result.selection.mode, 'delta')
        self.assertEqual(decode_delta_frame(result.selection.frame, efficient).to_bytes(), target)

    def test_frozen_identical_neighbor_is_87_bytes(self):
        target = b('v07_memory_2_R2.isql7')
        frames = {
            'one.isql7': b('v07_memory_1_R2.isql7'),
            'three.isql7': b('v07_memory_3_R2.isql7'),
        }
        result = select_compact_locality_base(target, build_compact_locality_index(frames.items()), frames.__getitem__, top_k=2)
        self.assertEqual(result.selection.mode, 'delta')
        self.assertEqual(result.selection.selected_frame_bytes, 87)
        self.assertEqual(result.selection.selected_base_ref, 'one.isql7')

    def test_frozen_near_neighbor_is_97_bytes(self):
        target = b('v08_near_R2.isql7')
        frames = {
            'one.isql7': b('v07_memory_1_R2.isql7'),
            'two.isql7': b('v07_memory_2_R2.isql7'),
            'three.isql7': b('v07_memory_3_R2.isql7'),
        }
        result = select_compact_locality_base(target, build_compact_locality_index(frames.items()), frames.__getitem__, top_k=2)
        self.assertEqual(result.selection.mode, 'delta')
        self.assertEqual(result.selection.selected_frame_bytes, 97)

    def test_low_locality_falls_back_to_native(self):
        target = b('v07_memory_3_R2.isql7')
        frames = {
            'one.isql7': b('v07_memory_1_R2.isql7'),
            'two.isql7': b('v07_memory_2_R2.isql7'),
        }
        result = select_compact_locality_base(target, build_compact_locality_index(frames.items()), frames.__getitem__, top_k=2)
        self.assertEqual(result.selection.mode, 'native')
        self.assertEqual(result.selection.frame, target)

    def test_256_base_compact_matches_exhaustive_oracle_with_8_reranks(self):
        target_seq = [500 + (i % 17) for i in range(80)]
        target = native(target_seq, 250)
        good = target_seq[:]
        for i in range(64, 80):
            good[i] += 1
        frames = {'base-good.isql7': native(good, 249)}
        for i in range(255):
            seq = [((j * 83 + i * 197) % 2000) + 1000 for j in range(80)]
            frames[f'base-{i:03d}.isql7'] = native(seq, i)
        compact = select_compact_locality_base(
            target,
            build_compact_locality_index(frames.items()),
            frames.__getitem__,
            top_k=8,
            probe_factor=4,
        )
        oracle = select_locality_base(
            target,
            build_locality_index(frames.items()),
            frames.__getitem__,
            top_k=999,
        )
        self.assertEqual(compact.selection.selected_base_sha256, oracle.selected_base_sha256)
        self.assertEqual(compact.selection.selected_frame_bytes, oracle.selected_frame_bytes)
        self.assertEqual(compact.selection.mode, oracle.mode)
        self.assertEqual(compact.selection.recalled_candidate_count, 8)
        self.assertLessEqual(compact.recall.index_probe_count, 64)


if __name__ == '__main__':
    unittest.main()
