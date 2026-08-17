import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
VAL = ROOT / 'validation'


def run_cli(*args: str):
    return subprocess.run(
        [sys.executable, '-m', 'isql_core', *args],
        cwd=ROOT,
        env=ENV,
        text=True,
        capture_output=True,
    )


class CLIV10Tests(unittest.TestCase):
    def test_native_index_build_info_and_select(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            frames = d / 'frames'
            frames.mkdir()
            shutil.copy2(VAL / 'v07_memory_1_R2.isql7', frames / 'one.isql7')
            shutil.copy2(VAL / 'v07_memory_3_R2.isql7', frames / 'three.isql7')
            index = d / 'locality.ili1'
            built = run_cli('locality-native-build', '--frames-dir', str(frames), '--index', str(index))
            self.assertEqual(built.returncode, 0, built.stderr)
            meta = json.loads(built.stdout)
            self.assertEqual(meta['entry_count'], 2)
            self.assertEqual(meta['format'], 'ILI1')
            self.assertTrue(index.read_bytes().startswith(b'ILI1'))

            info = run_cli('locality-native-info', '--index', str(index))
            self.assertEqual(info.returncode, 0, info.stderr)
            info_payload = json.loads(info.stdout)
            self.assertEqual(info_payload['index_hash'], meta['index_hash'])
            self.assertEqual(info_payload['index_bytes'], index.stat().st_size)

            out = d / 'selected.bin'
            selected = run_cli(
                'locality-native-select',
                '--index', str(index),
                '--frames-dir', str(frames),
                '--target', str(VAL / 'v07_memory_2_R2.isql7'),
                '--out', str(out),
                '--top-k', '2',
            )
            self.assertEqual(selected.returncode, 0, selected.stderr)
            payload = json.loads(selected.stdout)
            self.assertEqual(payload['mode'], 'delta')
            self.assertEqual(payload['selected_frame_bytes'], 87)
            self.assertEqual(payload['selected_base_ref'], 'one.isql7')
            self.assertIn('compact_recall', payload)
            self.assertTrue(out.read_bytes().startswith(b'ISD8'))

    def test_corrupt_native_index_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            frames = d / 'frames'
            frames.mkdir()
            shutil.copy2(VAL / 'v07_memory_1_R2.isql7', frames / 'one.isql7')
            index = d / 'locality.ili1'
            self.assertEqual(run_cli('locality-native-build', '--frames-dir', str(frames), '--index', str(index)).returncode, 0)
            raw = bytearray(index.read_bytes())
            raw[-5] ^= 1
            index.write_bytes(raw)
            info = run_cli('locality-native-info', '--index', str(index))
            self.assertNotEqual(info.returncode, 0)
            self.assertIn('ERROR:', info.stderr)


if __name__ == '__main__':
    unittest.main()
