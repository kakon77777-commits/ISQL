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


class CLITests(unittest.TestCase):
    def test_parse(self):
        p = run_cli("parse", "ISQL1:MEM:R2:X123")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data["domain"], "MEM")

    def test_registry_info(self):
        p = run_cli("registry-info")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(len(data["domains"]), 6)

    def test_address_text(self):
        p = run_cli("address", "--text", "hello")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(p.stdout.strip().startswith("ISQL1:ADDR:R0:H"))

    def test_memory_encode_decode_and_recoverability(self):
        with tempfile.TemporaryDirectory() as td:
            enc = run_cli("memory-encode", "--store", td, "--text", "Alpha beta. Alpha gamma.")
            self.assertEqual(enc.returncode, 0, enc.stderr)
            edata = json.loads(enc.stdout)
            r4 = edata["layers"]["R4"]["code"]

            dec = run_cli("memory-decode", "--store", td, "--code", r4)
            self.assertEqual(dec.returncode, 0, dec.stderr)
            ddata = json.loads(dec.stdout)
            self.assertTrue(ddata["exact"])
            self.assertEqual(ddata["recovered_text"], "Alpha beta. Alpha gamma.")

            rep = run_cli("recoverability", "--store", td, "--code", r4, "--source-text", "Alpha beta. Alpha gamma.")
            self.assertEqual(rep.returncode, 0, rep.stderr)
            rdata = json.loads(rep.stdout)
            self.assertTrue(rdata["exact"])
            self.assertEqual(rdata["semantic_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
