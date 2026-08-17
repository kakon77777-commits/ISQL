import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.hierarchical import (
    HierarchicalRegistry,
    compile_hierarchical_registry,
    reconstruct_spectral_registry,
)
from isql_core.spectral import SpectralRegistryStore


class HierarchicalCompileTests(unittest.TestCase):
    def _canonical(self, root: Path):
        store = SpectralRegistryStore(root)
        reg = store.load_current()
        reg.intern("atom", "semantic memory")
        reg.intern("atom", "semantic recovery")
        reg.intern("claim", "Semantic memory preserves stable identity.")
        reg.intern("language", "en")
        return store.commit(reg)

    def test_compile_reconstructs_exact_canonical_registry_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            canonical = self._canonical(Path(td))
            result = compile_hierarchical_registry(canonical)
            rebuilt = reconstruct_spectral_registry(result.registry)
            self.assertEqual(rebuilt.to_dict(), canonical.to_dict())
            self.assertEqual(rebuilt.content_hash(), canonical.content_hash())
            self.assertEqual(result.registry.canonical_hash, canonical.content_hash())

    def test_compile_preserves_canonical_value_positions(self):
        with tempfile.TemporaryDirectory() as td:
            canonical = self._canonical(Path(td))
            compiled = compile_hierarchical_registry(canonical).registry
            rebuilt = reconstruct_spectral_registry(compiled)
            self.assertEqual(rebuilt.resolve("atom", 1), "semantic memory")
            self.assertEqual(rebuilt.resolve("atom", 2), "semantic recovery")

    def test_append_compile_keeps_old_lexeme_ids_and_programs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SpectralRegistryStore(root)
            reg = store.load_current()
            reg.intern("atom", "semantic memory")
            first = store.commit(reg)
            h1 = compile_hierarchical_registry(first).registry
            old_lexemes = tuple(h1.lexemes)
            old_program = h1.programs["atom"][0]

            reg2 = store.load_current()
            reg2.intern("atom", "semantic recovery")
            second = store.commit(reg2)
            r2 = compile_hierarchical_registry(second, previous=h1)
            self.assertEqual(tuple(r2.registry.lexemes[: len(old_lexemes)]), old_lexemes)
            self.assertEqual(r2.registry.programs["atom"][0], old_program)
            self.assertGreater(r2.new_program_count, 0)

    def test_noop_compile_adds_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            canonical = self._canonical(Path(td))
            h1 = compile_hierarchical_registry(canonical).registry
            result = compile_hierarchical_registry(canonical, previous=h1)
            self.assertEqual(result.new_lexeme_count, 0)
            self.assertEqual(result.new_program_count, 0)
            self.assertEqual(result.registry.to_dict(), h1.to_dict())

    def test_non_append_only_previous_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            canonical = self._canonical(Path(td))
            h1 = compile_hierarchical_registry(canonical).registry
            h1.programs["atom"][0] = h1.encode_value("tampered")
            with self.assertRaises(ISQLValidationError):
                compile_hierarchical_registry(canonical, previous=h1)


if __name__ == "__main__":
    unittest.main()
