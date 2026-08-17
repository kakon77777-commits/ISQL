import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from isql_core.memory import encode_text_memory
from isql_core.semantics import SemanticAnalysis
from isql_core.spectral import SpectralRegistryStore

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


def analysis():
    return SemanticAnalysis.from_dict({
        "schema": "isql.semantic-analysis/v0.2",
        "analyzer_id": "cli-ai/v1",
        "analyzer_contract": "isql-semantic-analysis/v0.2",
        "coordinates": {
            "summary": "ISQL v0.7 uses machine-native canonical memory.",
            "concepts": ["machine-native memory", "spectral coordinates"],
            "entities": ["ISQL-MEM", "AI"],
            "relations": [{"subject": "ISQL-MEM", "predicate": "used_by", "object": "AI"}],
            "claims": ["Human readability is not required."],
            "intent": "test native cli",
            "uncertainty": [],
            "tags": ["native"],
            "language": "en",
        },
    })


class CLIV07Tests(unittest.TestCase):
    def _fixture(self, td: str):
        root = Path(td)
        record = encode_text_memory(
            "ISQL v0.7 memory is for AI, not direct human reading.",
            semantic_analysis=analysis(),
            spectral_registry_store=SpectralRegistryStore(root),
        )
        record_path = root / "record.json"
        record_path.write_text(json.dumps(record.to_dict(), ensure_ascii=False), encoding="utf-8")
        return root, record_path

    def test_native_compile_decode_info_and_debug(self):
        with tempfile.TemporaryDirectory() as td:
            root, record_path = self._fixture(td)
            out = root / "memory.isql7"
            compiled = run_cli("native-compile", "--record", str(record_path), "--resolution", "R2", "--out", str(out))
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            meta = json.loads(compiled.stdout)
            self.assertEqual(meta["schema"], "isql.native-memory-compile/v0.7")
            self.assertTrue(out.read_bytes().startswith(b"ISN7"))

            info = run_cli("native-info", "--input", str(out))
            self.assertEqual(info.returncode, 0, info.stderr)
            self.assertEqual(json.loads(info.stdout)["resolution"], "R2")

            decoded = run_cli("native-decode", "--store", str(root), "--input", str(out))
            self.assertEqual(decoded.returncode, 0, decoded.stderr)
            coords = json.loads(decoded.stdout)
            self.assertEqual(coords["summary"], analysis().coordinates.summary)

            debug = run_cli("native-debug", "--input", str(out))
            self.assertEqual(debug.returncode, 0, debug.stderr)
            self.assertIn("NON-CANONICAL DEBUG VIEW", debug.stdout)

    def test_native_decode_rejects_wrong_registry_store(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as other:
            root, record_path = self._fixture(td)
            out = root / "memory.isql7"
            self.assertEqual(run_cli("native-compile", "--record", str(record_path), "--resolution", "R2", "--out", str(out)).returncode, 0)
            decoded = run_cli("native-decode", "--store", other, "--input", str(out))
            self.assertNotEqual(decoded.returncode, 0)
            self.assertIn("ERROR:", decoded.stderr)


if __name__ == "__main__":
    unittest.main()
