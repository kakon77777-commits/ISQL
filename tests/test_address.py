import unittest

from isql_core.address import address_bytes, address_text, verify_address
from isql_core.code import parse_code


class AddressTests(unittest.TestCase):
    def test_same_bytes_same_address(self):
        a = address_bytes(b"hello")
        b = address_bytes(b"hello")
        self.assertEqual(a, b)
        self.assertEqual(a.domain, "ADDR")
        self.assertEqual(a.resolution, "R0")
        self.assertEqual(a.control, "H")

    def test_different_bytes_different_address(self):
        self.assertNotEqual(address_bytes(b"hello"), address_bytes(b"hello!"))

    def test_address_payload_is_decimal_digits_only(self):
        code = address_bytes(b"hello")
        self.assertTrue(code.payload.isdigit())
        self.assertGreater(len(code.payload), 50)

    def test_text_is_utf8_addressed(self):
        self.assertEqual(address_text("中文"), address_bytes("中文".encode("utf-8")))

    def test_verify_address(self):
        code = address_text("stable source")
        self.assertTrue(verify_address("stable source".encode("utf-8"), code))
        self.assertFalse(verify_address(b"changed source", code))

    def test_wire_round_trip(self):
        code = address_text("abc")
        self.assertEqual(parse_code(code.to_wire()), code)


if __name__ == "__main__":
    unittest.main()
