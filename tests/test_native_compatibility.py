import json
import unittest
from pathlib import Path

from isql_core.carrier import compile_digit_carrier
from isql_core.hierarchical import HierarchicalRegistryDelta
from isql_core.registry_wire import encode_registry_delta_wire

ROOT = Path(__file__).resolve().parents[1]


class NativeCompatibilityTests(unittest.TestCase):
    def test_v06_d40_registry_carrier_is_byte_for_byte_unchanged(self):
        wire = json.loads((ROOT / "validation" / "final_v05" / "installed_hierarchical_compile.json").read_text(encoding="utf-8"))["numeric_delta_wire"]["wire"]
        expected = (ROOT / "validation" / "v06_registry_cold_d40.ipc6").read_bytes()
        self.assertEqual(compile_digit_carrier(wire, codec="d40").carrier, expected)

    def test_v05_registry_numeric_wire_remains_exact(self):
        fixture = json.loads((ROOT / "validation" / "final_v05" / "installed_hierarchical_compile.json").read_text(encoding="utf-8"))
        expected = fixture["numeric_delta_wire"]["wire"]
        delta_dict = json.loads((ROOT / "validation" / "v05_live_store" / "hierarchical_registry" / "delta-000001.json").read_text(encoding="utf-8"))
        self.assertEqual(encode_registry_delta_wire(HierarchicalRegistryDelta.from_dict(delta_dict)), expected)


if __name__ == "__main__":
    unittest.main()
