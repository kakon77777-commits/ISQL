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


def semantic_analysis_json():
    return json.dumps({
        "schema": "isql.semantic-analysis/v0.2",
        "analyzer_id": "cli-ai/v1",
        "analyzer_contract": "isql-semantic-analysis/v0.2",
        "coordinates": {
            "summary": "ISQL separates stable addressing from adaptive semantic memory.",
            "concepts": ["stable addressing", "semantic memory", "multi-resolution recovery"],
            "entities": ["ISQL"],
            "relations": [
                {"subject": "address", "predicate": "separate_from", "object": "memory"}
            ],
            "claims": ["Memory changes must not change the source address."],
            "intent": "define memory invariants",
            "uncertainty": [],
            "tags": ["memory", "ISQL"],
            "language": "en"
        }
    }, ensure_ascii=False)


class CLIV02Tests(unittest.TestCase):
    def encode(self, td: str):
        p = run_cli(
            "memory-encode", "--store", td,
            "--text", "ISQL keeps stable address identity separate from adaptive memory.",
            "--semantic-analysis-json", semantic_analysis_json(),
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_memory_encode_accepts_semantic_analysis_json(self):
        with tempfile.TemporaryDirectory() as td:
            data = self.encode(td)
            self.assertIn("semantic", data["variants"])
            self.assertEqual(data["variants"]["semantic"]["analyzer_id"], "cli-ai/v1")

    def test_memory_decode_auto_selects_semantic_decoder(self):
        with tempfile.TemporaryDirectory() as td:
            data = self.encode(td)
            code = data["variants"]["semantic"]["layers"]["R2"]["code"]
            p = run_cli("memory-decode", "--store", td, "--code", code)
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["profile_id"], "semantic")
            self.assertEqual(out["decoder_id"], "semantic-coordinate-decoder/v0.2")

    def test_memory_profiles_lists_both_profiles(self):
        with tempfile.TemporaryDirectory() as td:
            data = self.encode(td)
            p = run_cli("memory-profiles", "--store", td, "--address", data["address"])
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(set(out["profiles"]), {"baseline", "semantic"})
            self.assertEqual(out["profiles"]["semantic"]["analyzer_id"], "cli-ai/v1")

    def test_memory_compare_reports_baseline_and_semantic(self):
        with tempfile.TemporaryDirectory() as td:
            data = self.encode(td)
            source = "ISQL keeps stable address identity separate from adaptive memory."
            p = run_cli(
                "memory-compare", "--store", td,
                "--address", data["address"],
                "--resolution", "R2",
                "--source-text", source,
                "--semantic-reference-json", semantic_analysis_json(),
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(set(out["profiles"]), {"baseline", "semantic"})
            self.assertEqual(out["profiles"]["semantic"]["coordinate_fidelity"]["aggregate"], 1.0)

    def test_invalid_semantic_analysis_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = run_cli(
                "memory-encode", "--store", td,
                "--text", "x",
                "--semantic-analysis-json", '{"analyzer_id":"x"}',
            )
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("SEMANTIC_ANALYSIS_COORDINATES_REQUIRED", p.stderr)


if __name__ == "__main__":
    unittest.main()
