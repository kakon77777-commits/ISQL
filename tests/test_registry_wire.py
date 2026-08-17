import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.hierarchical import (
    HierarchicalRegistry,
    compile_hierarchical_registry,
    make_hierarchical_delta,
)
from isql_core.registry_wire import (
    decode_registry_delta_binary,
    decode_registry_delta_wire,
    encode_registry_delta_binary,
    encode_registry_delta_wire,
)
from isql_core.spectral import SpectralRegistryStore


class RegistryWireTests(unittest.TestCase):
    def _delta(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        store = SpectralRegistryStore(root)
        reg = store.load_current()
        reg.intern("atom", "語義記憶")
        reg.intern("atom", "semantic memory")
        reg.intern("claim", "Semantic memory preserves identity.")
        reg.intern("language", "zh-Hant")
        canonical = store.commit(reg)
        compiled = compile_hierarchical_registry(canonical).registry
        return td, make_hierarchical_delta(HierarchicalRegistry.empty(), compiled)


    def test_structural_binary_frame_round_trips_exact_delta(self):
        td, delta = self._delta()
        self.addCleanup(td.cleanup)
        payload = encode_registry_delta_binary(delta)
        self.assertIsInstance(payload, bytes)
        self.assertEqual(decode_registry_delta_binary(payload).to_dict(), delta.to_dict())

    def test_wire_is_ascii_digits_only_and_round_trips(self):
        td, delta = self._delta()
        self.addCleanup(td.cleanup)
        wire = encode_registry_delta_wire(delta)
        self.assertTrue(wire.isascii())
        self.assertTrue(wire.isdigit())
        decoded = decode_registry_delta_wire(wire)
        self.assertEqual(decoded.to_dict(), delta.to_dict())

    def test_unicode_lexemes_round_trip_exact_utf8(self):
        td, delta = self._delta()
        self.addCleanup(td.cleanup)
        decoded = decode_registry_delta_wire(encode_registry_delta_wire(delta))
        self.assertIn("語", decoded.new_lexemes)
        self.assertIn("義", decoded.new_lexemes)
        self.assertIn("記", decoded.new_lexemes)
        self.assertIn("憶", decoded.new_lexemes)

    def test_hashes_are_preserved(self):
        td, delta = self._delta()
        self.addCleanup(td.cleanup)
        decoded = decode_registry_delta_wire(encode_registry_delta_wire(delta))
        self.assertEqual(decoded.previous_hierarchical_hash, delta.previous_hierarchical_hash)
        self.assertEqual(decoded.target_hierarchical_hash, delta.target_hierarchical_hash)
        self.assertEqual(decoded.canonical_hash, delta.canonical_hash)

    def test_truncated_wire_fails_closed(self):
        td, delta = self._delta()
        self.addCleanup(td.cleanup)
        wire = encode_registry_delta_wire(delta)
        with self.assertRaises(ISQLValidationError):
            decode_registry_delta_wire(wire[:-3])

    def test_corrupted_wire_fails_closed(self):
        td, delta = self._delta()
        self.addCleanup(td.cleanup)
        wire = encode_registry_delta_wire(delta)
        pos = len(wire) // 2
        changed = "0" if wire[pos] != "0" else "1"
        bad = wire[:pos] + changed + wire[pos + 1 :]
        with self.assertRaises(ISQLValidationError):
            decode_registry_delta_wire(bad)


if __name__ == "__main__":
    unittest.main()
