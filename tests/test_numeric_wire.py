import tempfile
import unittest
from pathlib import Path

from isql_core.errors import ISQLValidationError
from isql_core.semantics import SemanticCoordinateSet
from isql_core.spectral import SpectralRegistryStore, compile_spectral_packet
from isql_core.wire import (
    decode_numeric_wire,
    decode_uint,
    encode_numeric_wire,
    encode_uint,
)


class NumericWireTests(unittest.TestCase):
    def coords(self):
        return SemanticCoordinateSet.from_dict({
            "summary": "ISQL separates stable address identity from adaptive memory representation.",
            "concepts": ["stable address", "adaptive memory", "multi-resolution recovery"],
            "entities": ["ISQL-ADDR", "ISQL-MEM"],
            "relations": [
                {"subject": "ISQL-ADDR", "predicate": "separate_from", "object": "ISQL-MEM"},
                {"subject": "ISQL-MEM", "predicate": "supports", "object": "multi-resolution recovery"},
            ],
            "claims": ["Memory representation changes must not change stable address identity."],
            "intent": "specify memory invariants",
            "uncertainty": ["compression ratio is empirical"],
            "tags": ["memory", "addressing"],
            "language": "en",
        })

    def test_uint_codec_round_trips_small_and_large_values(self):
        values = [0, 1, 9, 10, 123, 10**77 + 12345]
        for value in values:
            encoded = encode_uint(value)
            self.assertTrue(encoded.isascii() and encoded.isdigit())
            decoded, pos = decode_uint(encoded)
            self.assertEqual(decoded, value)
            self.assertEqual(pos, len(encoded))

    def test_numeric_wire_is_digits_only_and_round_trips_semantic_packet(self):
        with tempfile.TemporaryDirectory() as td:
            packet = compile_spectral_packet(self.coords(), SpectralRegistryStore(Path(td))).packet
            wire = encode_numeric_wire(packet)
            self.assertTrue(wire.isascii() and wire.isdigit())
            recovered = decode_numeric_wire(wire)
            self.assertEqual(recovered.registry_id, packet.registry_id)
            self.assertEqual(recovered.registry_revision, packet.registry_revision)
            self.assertEqual(recovered.registry_hash, packet.registry_hash)
            self.assertEqual(recovered.sequence, packet.sequence)
            self.assertEqual(recovered.registry_delta_bytes, 0)

    def test_checksum_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            packet = compile_spectral_packet(self.coords(), SpectralRegistryStore(Path(td))).packet
            wire = encode_numeric_wire(packet)
            replacement = "7" if wire[-1] != "7" else "8"
            bad = wire[:-1] + replacement
            with self.assertRaises(ISQLValidationError):
                decode_numeric_wire(bad)

    def test_trailing_digits_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            packet = compile_spectral_packet(self.coords(), SpectralRegistryStore(Path(td))).packet
            wire = encode_numeric_wire(packet)
            with self.assertRaises(ISQLValidationError):
                decode_numeric_wire(wire + "1")

    def test_noncanonical_uint_with_leading_zero_fails_closed(self):
        # "2" announces a two-digit payload; 01 is not canonical for integer 1.
        with self.assertRaises(ISQLValidationError):
            decode_uint("201")


if __name__ == "__main__":
    unittest.main()
