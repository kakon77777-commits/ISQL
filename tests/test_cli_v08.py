import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
VAL = ROOT / "validation"


def run_cli(*args: str):
    return subprocess.run(
        [sys.executable, "-m", "isql_core", *args],
        cwd=ROOT,
        env=ENV,
        text=True,
        capture_output=True,
    )


class CLIV08Tests(unittest.TestCase):
    def test_delta_compile_info_decode_and_block(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "neighbor.isqld8"
            restored = Path(td) / "restored.isql7"
            base = VAL / "v07_memory_1_R2.isql7"
            target = VAL / "v07_memory_2_R2.isql7"

            compiled = run_cli("delta-compile", "--base", str(base), "--target", str(target), "--out", str(out))
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            meta = json.loads(compiled.stdout)
            self.assertEqual(meta["schema"], "isql.delta-compile/v0.8")
            self.assertEqual(meta["mode_counts"]["copy"], 5)
            self.assertTrue(out.read_bytes().startswith(b"ISD8"))

            info = run_cli("delta-info", "--base", str(base), "--input", str(out))
            self.assertEqual(info.returncode, 0, info.stderr)
            self.assertEqual(json.loads(info.stdout)["sequence_items"], 68)

            block = run_cli("delta-block", "--base", str(base), "--input", str(out), "--block", "2")
            self.assertEqual(block.returncode, 0, block.stderr)
            self.assertEqual(len(json.loads(block.stdout)["values"]), 16)

            decoded = run_cli("delta-decode", "--base", str(base), "--input", str(out), "--out", str(restored))
            self.assertEqual(decoded.returncode, 0, decoded.stderr)
            self.assertEqual(restored.read_bytes(), target.read_bytes())

    def test_locality_compile_selects_delta_or_native(self):
        with tempfile.TemporaryDirectory() as td:
            out1 = Path(td) / "selected1.bin"
            r1 = run_cli(
                "locality-compile",
                "--base", str(VAL / "v07_memory_1_R2.isql7"),
                "--record", str(VAL / "v04_record_2.json"),
                "--out", str(out1),
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertEqual(json.loads(r1.stdout)["mode"], "delta")
            self.assertTrue(out1.read_bytes().startswith(b"ISD8"))

            out2 = Path(td) / "selected2.bin"
            r2 = run_cli(
                "locality-compile",
                "--base", str(VAL / "v07_memory_2_R2.isql7"),
                "--record", str(VAL / "v04_record_3.json"),
                "--out", str(out2),
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertEqual(json.loads(r2.stdout)["mode"], "native")
            self.assertTrue(out2.read_bytes().startswith(b"ISN7"))


if __name__ == "__main__":
    unittest.main()
