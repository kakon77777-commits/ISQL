import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from isql_core.registry_wire import decode_registry_delta_wire
from isql_core.semantics import SemanticAnalysis
from isql_core.spectral import SpectralRegistryStore, compile_spectral_packet
from isql_core.wire import compile_numeric_wire

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))


def run_cli(*args: str):
    return subprocess.run(
        [sys.executable, "-m", "isql_core", *args],
        cwd=ROOT,
        env=ENV,
        text=True,
        capture_output=True,
    )


class CLIV05Tests(unittest.TestCase):
    def test_registry_compile_hierarchical_and_decode_wire(self):
        with tempfile.TemporaryDirectory() as td:
            # Seed canonical spectral registry through existing v0.4 CLI.
            analysis = (ROOT / "validation" / "v04_analysis_1.json").read_text(encoding="utf-8")
            seeded = run_cli("numeric-wire-compile", "--store", td, "--semantic-analysis-json", analysis)
            self.assertEqual(seeded.returncode, 0, seeded.stderr)

            compiled = run_cli("registry-compile-hierarchical", "--store", td)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            out = json.loads(compiled.stdout)
            wire = out["numeric_delta_wire"]["wire"]
            self.assertTrue(wire.isascii() and wire.isdigit())

            decoded = run_cli("registry-decode-wire", "--wire", wire)
            self.assertEqual(decoded.returncode, 0, decoded.stderr)
            delta = json.loads(decoded.stdout)["delta"]
            self.assertEqual(delta["canonical_hash"], out["canonical_registry_hash"])

    def test_registry_compare_reports_structural_and_wire_costs(self):
        with tempfile.TemporaryDirectory() as td:
            analysis = (ROOT / "validation" / "v04_analysis_1.json").read_text(encoding="utf-8")
            self.assertEqual(run_cli("numeric-wire-compile", "--store", td, "--semantic-analysis-json", analysis).returncode, 0)
            self.assertEqual(run_cli("registry-compile-hierarchical", "--store", td).returncode, 0)
            p = run_cli("registry-compare", "--store", td)
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertGreater(out["canonical_registry_json_bytes"], 0)
            self.assertGreater(out["hierarchical_registry_json_bytes"], 0)
            self.assertGreater(out["latest_delta_json_bytes"], 0)
            self.assertGreater(out["latest_numeric_delta_wire_bytes"], 0)
            self.assertGreater(out["latest_structural_binary_bytes"], 0)

    def test_v04_numeric_memory_wire_is_byte_for_byte_unchanged(self):
        fixture_analysis = json.loads((ROOT / "validation" / "v04_analysis_1.json").read_text(encoding="utf-8"))
        expected = json.loads((ROOT / "validation" / "final_installed_compile_cold.json").read_text(encoding="utf-8"))["numeric_wire"]["wire"]
        with tempfile.TemporaryDirectory() as td:
            analysis = SemanticAnalysis.from_dict(fixture_analysis)
            spectral = compile_spectral_packet(analysis.coordinates, SpectralRegistryStore(td))
            actual = compile_numeric_wire(spectral.packet).wire
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
