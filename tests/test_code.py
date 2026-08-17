import unittest

from isql_core.code import ISQLCode, parse_code
from isql_core.errors import ISQLValidationError


class CodeTests(unittest.TestCase):
    def test_parse_round_trip_memory_code(self):
        code = parse_code("ISQL1:MEM:R2:XRQ123456789")
        self.assertEqual(code.protocol, "ISQL")
        self.assertEqual(code.version, 1)
        self.assertEqual(code.domain, "MEM")
        self.assertEqual(code.resolution, "R2")
        self.assertEqual(code.control, "XRQ")
        self.assertEqual(code.payload, "123456789")
        self.assertEqual(code.to_wire(), "ISQL1:MEM:R2:XRQ123456789")

    def test_payload_preserves_500_digits_exactly(self):
        payload = "1234567890" * 50
        code = parse_code(f"ISQL1:SEM:R1:X{payload}")
        self.assertEqual(code.payload, payload)
        self.assertEqual(len(code.payload), 500)

    def test_code_constructor_is_canonical(self):
        code = ISQLCode(protocol="ISQL", version=1, domain="ADDR", resolution="R0", control="H", payload="123")
        self.assertEqual(code.to_wire(), "ISQL1:ADDR:R0:H123")

    def test_invalid_protocol_rejected(self):
        with self.assertRaises(ISQLValidationError):
            parse_code("XYZ1:MEM:R2:X123")

    def test_invalid_resolution_rejected(self):
        with self.assertRaises(ISQLValidationError):
            parse_code("ISQL1:MEM:Q2:X123")

    def test_payload_must_be_digits(self):
        with self.assertRaises(ISQLValidationError):
            parse_code("ISQL1:MEM:R2:X12A3")

    def test_control_must_be_letters(self):
        with self.assertRaises(ISQLValidationError):
            parse_code("ISQL1:MEM:R2:X1A23")


if __name__ == "__main__":
    unittest.main()
