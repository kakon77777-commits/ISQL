import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.spectral import SpectralRegistry, SpectralRegistryStore


class SpectralRegistryTests(unittest.TestCase):
    def test_intern_is_stable_and_namespace_local(self):
        reg = SpectralRegistry.empty()
        a1 = reg.intern("atom", "stable address")
        a2 = reg.intern("atom", "stable address")
        p1 = reg.intern("predicate", "separate_from")
        self.assertEqual(a1, a2)
        self.assertEqual(a1, 1)
        self.assertEqual(p1, 1)
        self.assertEqual(reg.resolve("atom", 1), "stable address")
        self.assertEqual(reg.resolve("predicate", 1), "separate_from")

    def test_existing_id_never_changes_after_append(self):
        reg = SpectralRegistry.empty()
        first = reg.intern("atom", "alpha")
        reg.intern("atom", "beta")
        self.assertEqual(first, 1)
        self.assertEqual(reg.resolve("atom", first), "alpha")

    def test_unknown_namespace_fails_closed(self):
        reg = SpectralRegistry.empty()
        with self.assertRaises(ISQLValidationError):
            reg.intern("unknown", "value")

    def test_store_commits_revision_snapshots_and_reloads_exact_revision(self):
        with tempfile.TemporaryDirectory() as td:
            store = SpectralRegistryStore(Path(td))
            reg = store.load_current()
            self.assertEqual(reg.revision, 0)
            reg.intern("atom", "alpha")
            committed = store.commit(reg)
            self.assertEqual(committed.revision, 1)
            self.assertEqual(store.load_current().resolve("atom", 1), "alpha")
            self.assertEqual(store.load_revision(1).content_hash(), committed.content_hash())
            reg2 = store.load_current()
            reg2.intern("atom", "beta")
            committed2 = store.commit(reg2)
            self.assertEqual(committed2.revision, 2)
            self.assertEqual(store.load_revision(1).resolve("atom", 1), "alpha")
            with self.assertRaises(ISQLValidationError):
                store.load_revision(1).resolve("atom", 2)

    def test_noop_commit_keeps_revision(self):
        with tempfile.TemporaryDirectory() as td:
            store = SpectralRegistryStore(Path(td))
            reg = store.load_current()
            reg.intern("atom", "alpha")
            committed = store.commit(reg)
            again = store.commit(store.load_current())
            self.assertEqual(again.revision, committed.revision)
            self.assertEqual(again.content_hash(), committed.content_hash())


if __name__ == "__main__":
    unittest.main()
