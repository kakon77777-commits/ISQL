import dataclasses
import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.hierarchical import (
    HierarchicalRegistry,
    HierarchicalRegistryStore,
    apply_hierarchical_delta,
    compile_hierarchical_registry,
    make_hierarchical_delta,
)
from isql_core.spectral import SpectralRegistryStore


class HierarchicalDeltaTests(unittest.TestCase):
    def _two_revisions(self, root: Path):
        store = SpectralRegistryStore(root / "canonical")
        r = store.load_current()
        r.intern("atom", "semantic memory")
        r.intern("language", "en")
        c1 = store.commit(r)
        h1 = compile_hierarchical_registry(c1).registry

        r2 = store.load_current()
        r2.intern("atom", "semantic recovery")
        r2.intern("claim", "Semantic memory supports semantic recovery.")
        c2 = store.commit(r2)
        h2 = compile_hierarchical_registry(c2, previous=h1).registry
        return h1, h2

    def test_cold_delta_replays_exact_revision(self):
        with tempfile.TemporaryDirectory() as td:
            h1, _ = self._two_revisions(Path(td))
            empty = HierarchicalRegistry.empty()
            delta = make_hierarchical_delta(empty, h1)
            rebuilt = apply_hierarchical_delta(empty, delta)
            self.assertEqual(rebuilt.to_dict(), h1.to_dict())
            self.assertGreater(len(delta.new_lexemes), 0)

    def test_noop_delta_has_no_new_material(self):
        with tempfile.TemporaryDirectory() as td:
            h1, _ = self._two_revisions(Path(td))
            delta = make_hierarchical_delta(h1, h1)
            self.assertEqual(delta.new_lexemes, ())
            self.assertTrue(all(not rows for rows in delta.new_programs.values()))
            self.assertEqual(apply_hierarchical_delta(h1, delta).to_dict(), h1.to_dict())

    def test_partial_delta_contains_only_appended_material(self):
        with tempfile.TemporaryDirectory() as td:
            h1, h2 = self._two_revisions(Path(td))
            delta = make_hierarchical_delta(h1, h2)
            self.assertEqual(delta.base_lexeme_count, len(h1.lexemes))
            self.assertEqual(len(delta.new_programs["atom"]), 1)
            self.assertEqual(len(delta.new_programs["claim"]), 1)
            rebuilt = apply_hierarchical_delta(h1, delta)
            self.assertEqual(rebuilt.content_hash(), h2.content_hash())

    def test_previous_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            h1, h2 = self._two_revisions(Path(td))
            delta = make_hierarchical_delta(h1, h2)
            bad = dataclasses.replace(delta, previous_hierarchical_hash="0" * 64)
            with self.assertRaises(ISQLValidationError):
                apply_hierarchical_delta(h1, bad)


    def test_store_allows_late_cold_bootstrap_to_current_canonical_revision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, h2 = self._two_revisions(root)
            store = HierarchicalRegistryStore(root / "late-compiled")
            committed = store.commit(h2)
            self.assertEqual(committed.revision, 2)
            delta = store.load_delta(2)
            self.assertEqual(delta.from_revision, 0)
            self.assertEqual(delta.to_revision, 2)
            self.assertEqual(apply_hierarchical_delta(HierarchicalRegistry.empty(), delta).to_dict(), h2.to_dict())

    def test_store_persists_revision_delta_and_current(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            h1, h2 = self._two_revisions(root)
            store = HierarchicalRegistryStore(root / "compiled")
            committed1 = store.commit(h1)
            committed2 = store.commit(h2)
            self.assertEqual(store.load_revision(committed1.revision).to_dict(), h1.to_dict())
            self.assertEqual(store.load_revision(committed2.revision).to_dict(), h2.to_dict())
            delta2 = store.load_delta(committed2.revision)
            self.assertEqual(apply_hierarchical_delta(h1, delta2).to_dict(), h2.to_dict())


if __name__ == "__main__":
    unittest.main()
