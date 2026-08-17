import tempfile
import unittest
from pathlib import Path

from isql_core.memory import encode_text_memory
from isql_core.native import (
    compile_native_memory,
    decode_native_spectral_frame,
    expand_native_memory,
    inspect_native_frame,
    render_native_debug,
)
from isql_core.semantics import SemanticAnalysis
from isql_core.spectral import SpectralPacket, SpectralRegistryStore, expand_spectral_packet


def analysis():
    return SemanticAnalysis.from_dict({
        "schema": "isql.semantic-analysis/v0.2",
        "analyzer_id": "test-ai/v1",
        "analyzer_contract": "isql-semantic-analysis/v0.2",
        "coordinates": {
            "summary": "Machine-native ISQL does not require human-readable decimal text.",
            "concepts": ["machine-native representation", "stable address", "spectral coordinates"],
            "entities": ["ISQL-MEM", "AI"],
            "relations": [
                {"subject": "ISQL-MEM", "predicate": "used_by", "object": "AI"},
                {"subject": "ISQL-MEM", "predicate": "stores", "object": "spectral coordinates"},
            ],
            "claims": ["Human-readable decimal text is an inspection view, not canonical memory."],
            "intent": "define machine-native canonical memory",
            "uncertainty": [],
            "tags": ["native", "memory"],
            "language": "en",
        },
    })


class NativeMemoryTests(unittest.TestCase):
    def _record(self, root: Path):
        store = SpectralRegistryStore(root)
        record = encode_text_memory(
            "ISQL memory is machine-native and intended for AI consumption.",
            semantic_analysis=analysis(),
            spectral_registry_store=store,
        )
        return store, record

    def test_compile_native_r2_binds_same_packet_and_address(self):
        with tempfile.TemporaryDirectory() as td:
            store, record = self._record(Path(td))
            result = compile_native_memory(record, resolution="R2")
            frame = decode_native_spectral_frame(result.frame)
            packet = SpectralPacket.from_dict(record.get_layer("spectral", "R2").data["packet"])
            self.assertEqual(frame.address, record.address)
            self.assertEqual(frame.packet.registry_revision, packet.registry_revision)
            self.assertEqual(frame.packet.registry_hash, packet.registry_hash)
            self.assertEqual(frame.packet.sequence, packet.sequence)
            self.assertEqual(result.frame_bytes, len(result.frame))

    def test_expand_native_equals_spectral_coordinate_decode(self):
        with tempfile.TemporaryDirectory() as td:
            store, record = self._record(Path(td))
            result = compile_native_memory(record, resolution="R2")
            native_coords = expand_native_memory(result.frame, store)
            packet = SpectralPacket.from_dict(record.get_layer("spectral", "R2").data["packet"])
            spectral_coords = expand_spectral_packet(packet, store)
            self.assertEqual(native_coords.to_dict(), spectral_coords.to_dict())

    def test_registry_mismatch_fails_during_native_expand(self):
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            store1, record = self._record(Path(td1))
            result = compile_native_memory(record, resolution="R2")
            other_store = SpectralRegistryStore(Path(td2))
            with self.assertRaises(Exception):
                expand_native_memory(result.frame, other_store)

    def test_inspection_and_debug_are_noncanonical_views(self):
        with tempfile.TemporaryDirectory() as td:
            store, record = self._record(Path(td))
            result = compile_native_memory(record, resolution="R1")
            info = inspect_native_frame(result.frame)
            debug = render_native_debug(result.frame)
            self.assertEqual(info["schema"], "isql.native-frame-info/v0.7")
            self.assertEqual(info["resolution"], "R1")
            self.assertIn("address", debug)
            self.assertIn("NON-CANONICAL DEBUG VIEW", debug)
            self.assertEqual(decode_native_spectral_frame(result.frame).to_bytes(), result.frame)


if __name__ == "__main__":
    unittest.main()
