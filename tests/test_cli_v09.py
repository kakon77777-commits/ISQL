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


class CLIV09Tests(unittest.TestCase):
    def test_index_build_info_and_select_delta(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            frames = d / 'frames'
            frames.mkdir()
            shutil.copy2(VAL / 'v07_memory_1_R2.isql7', frames / 'one.isql7')
            shutil.copy2(VAL / 'v07_memory_3_R2.isql7', frames / 'three.isql7')
            index = d / 'locality.json'
            built = run_cli('locality-index-build', '--frames-dir', str(frames), '--index', str(index))
            self.assertEqual(built.returncode, 0, built.stderr)
            meta = json.loads(built.stdout)
            self.assertEqual(meta['entry_count'], 2)
            self.assertTrue(index.exists())

            info = run_cli('locality-index-info', '--index', str(index))
            self.assertEqual(info.returncode, 0, info.stderr)
            self.assertEqual(json.loads(info.stdout)['index_hash'], meta['index_hash'])

            out = d / 'selected.bin'
            selected = run_cli(
                'locality-select',
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
            self.assertTrue(out.read_bytes().startswith(b'ISD8'))

    def test_select_falls_back_to_native(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            frames = d / 'frames'
            frames.mkdir()
            shutil.copy2(VAL / 'v07_memory_1_R2.isql7', frames / 'one.isql7')
            shutil.copy2(VAL / 'v07_memory_2_R2.isql7', frames / 'two.isql7')
            index = d / 'locality.json'
            self.assertEqual(run_cli('locality-index-build', '--frames-dir', str(frames), '--index', str(index)).returncode, 0)
            out = d / 'selected.bin'
            selected = run_cli(
                'locality-select',
                '--index', str(index),
                '--frames-dir', str(frames),
                '--target', str(VAL / 'v07_memory_3_R2.isql7'),
                '--out', str(out),
            )
            self.assertEqual(selected.returncode, 0, selected.stderr)
            payload = json.loads(selected.stdout)
            self.assertEqual(payload['mode'], 'native')
            self.assertIsNone(payload['selected_base_ref'])
            self.assertEqual(out.read_bytes(), (VAL / 'v07_memory_3_R2.isql7').read_bytes())


if __name__ == '__main__':
    unittest.main()
