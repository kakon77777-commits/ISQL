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


class CLIV06Tests(unittest.TestCase):
    def test_pack_unpack_and_info_binary_carrier(self):
        wire = "95050" + "1234567890" * 80
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "wire.ipc6"
            packed = run_cli("carrier-pack", "--wire", wire, "--codec", "d40", "--out", str(out_file))
            self.assertEqual(packed.returncode, 0, packed.stderr)
            meta = json.loads(packed.stdout)
            self.assertEqual(meta["codec"], "d40")
            self.assertEqual(meta["wire_bytes"], len(wire))
            self.assertTrue(out_file.read_bytes().startswith(b"IPC6"))

            unpacked = run_cli("carrier-unpack", "--file", str(out_file))
            self.assertEqual(unpacked.returncode, 0, unpacked.stderr)
            self.assertEqual(unpacked.stdout.strip(), wire)

            info = run_cli("carrier-info", "--file", str(out_file))
            self.assertEqual(info.returncode, 0, info.stderr)
            info_obj = json.loads(info.stdout)
            self.assertEqual(info_obj["codec"], "d40")
            self.assertEqual(info_obj["digit_count"], len(wire))
            self.assertEqual(info_obj["carrier_bytes"], len(out_file.read_bytes()))

    def test_bcd4_cli_round_trip(self):
        wire = "000123456789"
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "wire.ipc6"
            self.assertEqual(run_cli("carrier-pack", "--wire", wire, "--codec", "bcd4", "--out", str(out_file)).returncode, 0)
            unpacked = run_cli("carrier-unpack", "--file", str(out_file))
            self.assertEqual(unpacked.stdout.strip(), wire)

    def test_invalid_carrier_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.bin"
            path.write_bytes(b"not-a-carrier")
            p = run_cli("carrier-info", "--file", str(path))
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("ERROR:", p.stderr)


if __name__ == "__main__":
    unittest.main()
