import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


def analysis_obj():
    return {
        "schema": "isql.semantic-analysis/v0.2",
        "analyzer_id": "cli-ai/v1",
        "analyzer_contract": "isql-semantic-analysis/v0.2",
        "coordinates": {
            "summary": "ISQL separates stable addressing from adaptive semantic memory.",
            "concepts": ["stable addressing", "semantic memory", "multi-resolution recovery"],
            "entities": ["ISQL"],
            "relations": [{"subject": "address", "predicate": "separate_from", "object": "memory"}],
            "claims": ["Memory changes must not change the source address."],
            "intent": "define memory invariants",
            "uncertainty": [],
            "tags": ["memory", "ISQL"],
            "language": "en",
        },
    }


def analysis_json():
    return json.dumps(analysis_obj(), ensure_ascii=False)


class CLIV04Tests(unittest.TestCase):
    def test_numeric_wire_compile_and_decode_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            compiled = run_cli(
                "numeric-wire-compile", "--store", td,
                "--semantic-analysis-json", analysis_json(),
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            out = json.loads(compiled.stdout)
            wire = out["numeric_wire"]["wire"]
            self.assertTrue(wire.isascii() and wire.isdigit())
            decoded = run_cli("numeric-wire-decode", "--wire", wire)
            self.assertEqual(decoded.returncode, 0, decoded.stderr)
            packet = json.loads(decoded.stdout)
            self.assertEqual(packet["packet"]["q"], out["spectral"]["packet"]["q"])
            self.assertEqual(packet["packet"]["h"], out["spectral"]["packet"]["h"])

    def test_memory_encode_numeric_wire_adds_numeric_profile_and_decode_auto_selects(self):
        with tempfile.TemporaryDirectory() as td:
            enc = run_cli(
                "memory-encode", "--store", td,
                "--text", "ISQL keeps stable address identity separate from adaptive memory.",
                "--semantic-analysis-json", analysis_json(), "--numeric-wire",
            )
            self.assertEqual(enc.returncode, 0, enc.stderr)
            data = json.loads(enc.stdout)
            self.assertEqual(set(data["variants"]), {"baseline", "semantic", "spectral", "numeric"})
            code = data["variants"]["numeric"]["layers"]["R2"]["code"]
            dec = run_cli("memory-decode", "--store", td, "--code", code)
            self.assertEqual(dec.returncode, 0, dec.stderr)
            result = json.loads(dec.stdout)
            self.assertEqual(result["profile_id"], "numeric")
            self.assertEqual(result["decoder_id"], "numeric-wire-decoder/v0.4")

    def test_memory_compare_includes_numeric_compaction(self):
        with tempfile.TemporaryDirectory() as td:
            source = "ISQL keeps stable address identity separate from adaptive memory."
            enc = run_cli(
                "memory-encode", "--store", td, "--text", source,
                "--semantic-analysis-json", analysis_json(), "--numeric-wire",
            )
            data = json.loads(enc.stdout)
            p = run_cli(
                "memory-compare", "--store", td,
                "--address", data["address"], "--resolution", "R2",
                "--source-text", source,
                "--semantic-reference-json", analysis_json(),
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            numeric = out["profiles"]["numeric"]
            self.assertEqual(numeric["coordinate_fidelity"]["aggregate"], 1.0)
            self.assertLess(numeric["compaction"]["wire_vs_packet_ratio"], 1.0)

    def test_numeric_wire_without_semantic_analysis_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = run_cli("memory-encode", "--store", td, "--text", "x", "--numeric-wire")
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("--numeric-wire requires semantic analysis", p.stderr)


if __name__ == "__main__":
    unittest.main()
