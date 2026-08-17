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


class CLIV03Tests(unittest.TestCase):
    def test_memory_encode_spectral_flag_adds_third_profile(self):
        with tempfile.TemporaryDirectory() as td:
            p = run_cli(
                "memory-encode", "--store", td,
                "--text", "ISQL keeps stable address identity separate from adaptive memory.",
                "--semantic-analysis-json", analysis_json(),
                "--spectral",
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            data = json.loads(p.stdout)
            self.assertEqual(set(data["variants"]), {"baseline", "semantic", "spectral"})

    def test_memory_decode_auto_selects_spectral_decoder(self):
        with tempfile.TemporaryDirectory() as td:
            enc = run_cli(
                "memory-encode", "--store", td,
                "--text", "ISQL keeps stable address identity separate from adaptive memory.",
                "--semantic-analysis-json", analysis_json(), "--spectral",
            )
            data = json.loads(enc.stdout)
            code = data["variants"]["spectral"]["layers"]["R2"]["code"]
            p = run_cli("memory-decode", "--store", td, "--code", code)
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["profile_id"], "spectral")
            self.assertEqual(out["decoder_id"], "spectral-coordinate-decoder/v0.3")

    def test_spectral_registry_info_and_compile_show_warm_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            first = run_cli(
                "spectral-compile", "--store", td,
                "--semantic-analysis-json", analysis_json(),
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            a = json.loads(first.stdout)
            self.assertGreater(a["registry_delta_bytes"], 0)
            second = run_cli(
                "spectral-compile", "--store", td,
                "--semantic-analysis-json", analysis_json(),
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            b = json.loads(second.stdout)
            self.assertEqual(b["registry_delta_bytes"], 0)
            info = run_cli("spectral-registry-info", "--store", td)
            self.assertEqual(info.returncode, 0, info.stderr)
            data = json.loads(info.stdout)
            self.assertGreater(data["revision"], 0)
            self.assertGreater(data["counts"]["atom"], 0)

    def test_memory_compare_includes_spectral_compaction(self):
        with tempfile.TemporaryDirectory() as td:
            source = "ISQL keeps stable address identity separate from adaptive memory."
            enc = run_cli(
                "memory-encode", "--store", td,
                "--text", source,
                "--semantic-analysis-json", analysis_json(), "--spectral",
            )
            data = json.loads(enc.stdout)
            p = run_cli(
                "memory-compare", "--store", td,
                "--address", data["address"],
                "--resolution", "R2", "--source-text", source,
                "--semantic-reference-json", analysis_json(),
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertIn("spectral", out["profiles"])
            self.assertIsNotNone(out["profiles"]["spectral"]["compaction"])
            self.assertEqual(out["profiles"]["spectral"]["coordinate_fidelity"]["aggregate"], 1.0)

    def test_spectral_flag_without_semantic_analysis_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = run_cli("memory-encode", "--store", td, "--text", "x", "--spectral")
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("--spectral requires semantic analysis", p.stderr)


if __name__ == "__main__":
    unittest.main()
