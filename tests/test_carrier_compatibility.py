import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from isql_core.carrier import compile_digit_carrier, pack_digit_wire, unpack_digit_carrier
from isql_core.registry_wire import encode_registry_delta_wire
from isql_core.hierarchical import HierarchicalRegistryDelta
from isql_core.semantics import SemanticAnalysis
from isql_core.spectral import SpectralRegistryStore, compile_spectral_packet
from isql_core.wire import compile_numeric_wire

ROOT = Path(__file__).resolve().parents[1]


class CarrierCompatibilityTests(unittest.TestCase):
    def test_v04_numeric_memory_wire_is_unchanged(self):
        fixture_analysis = json.loads((ROOT / "validation" / "v04_analysis_1.json").read_text(encoding="utf-8"))
        expected = json.loads((ROOT / "validation" / "final_installed_compile_cold.json").read_text(encoding="utf-8"))["numeric_wire"]["wire"]
        with tempfile.TemporaryDirectory() as td:
            spectral = compile_spectral_packet(SemanticAnalysis.from_dict(fixture_analysis).coordinates, SpectralRegistryStore(td))
            actual = compile_numeric_wire(spectral.packet).wire
        self.assertEqual(actual, expected)

    def test_v05_registry_wire_is_unchanged(self):
        fixture = json.loads((ROOT / "validation" / "final_v05" / "installed_hierarchical_compile.json").read_text(encoding="utf-8"))
        expected = fixture["numeric_delta_wire"]["wire"]
        delta_dict = json.loads((ROOT / "validation" / "v05_live_store" / "hierarchical_registry" / "delta-000001.json").read_text(encoding="utf-8"))
        delta = HierarchicalRegistryDelta.from_dict(delta_dict)
        self.assertEqual(encode_registry_delta_wire(delta), expected)

    def test_compile_result_reports_exact_metrics_and_hash(self):
        wire = "95050" + "1234567890" * 100
        result = compile_digit_carrier(wire, codec="d40")
        self.assertEqual(result.wire_bytes, len(wire))
        self.assertEqual(result.carrier_bytes, len(result.carrier))
        self.assertEqual(result.carrier_sha256, hashlib.sha256(result.carrier).hexdigest())
        self.assertEqual(unpack_digit_carrier(result.carrier), wire)
        self.assertAlmostEqual(result.carrier_vs_wire_ratio, len(result.carrier) / len(wire))

    def test_d40_beats_bcd4_on_v05_registry_wire(self):
        wire = json.loads((ROOT / "validation" / "final_v05" / "installed_hierarchical_compile.json").read_text(encoding="utf-8"))["numeric_delta_wire"]["wire"]
        d40 = compile_digit_carrier(wire, codec="d40")
        bcd = compile_digit_carrier(wire, codec="bcd4")
        self.assertLess(d40.carrier_bytes, bcd.carrier_bytes)
        self.assertEqual(unpack_digit_carrier(d40.carrier), wire)
        self.assertEqual(unpack_digit_carrier(bcd.carrier), wire)


if __name__ == "__main__":
    unittest.main()
