import json
from pathlib import Path
import unittest

from isql_core.errors import ISQLValidationError
from isql_core.native_ext import decode_isx_spectral_frame


VECTOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "conformance"
    / "isx1"
    / "experimental_vectors_v0.2.json"
)


class ISXConformanceVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))

    def test_positive_vectors_decode_to_declared_logical_values(self):
        for vector in self.vectors["positive"]:
            with self.subTest(vector=vector["name"]):
                raw = bytes.fromhex(vector["frame_hex"])
                frame = decode_isx_spectral_frame(raw)
                self.assertEqual(frame.resolution, vector["resolution"])
                self.assertEqual(frame.address_digest.hex(), vector["address_sha256"])
                self.assertEqual(frame.registry_revision, vector["registry_revision"])
                self.assertEqual(frame.registry_hash, vector["registry_hash"])
                self.assertEqual(
                    tuple(frame.sequence),
                    tuple(int(value, 16) for value in vector["sequence_hex"]),
                )
                self.assertEqual(frame.to_bytes(), raw)

    def test_invalid_vectors_fail_closed(self):
        for vector in self.vectors["invalid"]:
            with self.subTest(vector=vector["name"], reason=vector["reason"]):
                raw = bytes.fromhex(vector["frame_hex"])
                with self.assertRaises(ISQLValidationError):
                    decode_isx_spectral_frame(raw)


if __name__ == "__main__":
    unittest.main()
