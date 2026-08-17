import unittest

from isql_core.address import address_bytes, address_code_to_digest, digest_to_address_code
from isql_core.code import ISQLCode
from isql_core.errors import ISQLValidationError


class NativeAddressTests(unittest.TestCase):
    def test_native_digest_round_trip_is_exact_32_bytes(self):
        code = address_bytes(b"native-isql")
        digest = address_code_to_digest(code)
        self.assertEqual(len(digest), 32)
        self.assertEqual(digest_to_address_code(digest), code)

    def test_leading_zero_digest_is_preserved(self):
        digest = b"\x00\x00" + bytes(range(30))
        code = digest_to_address_code(digest)
        self.assertEqual(address_code_to_digest(code), digest)

    def test_invalid_digest_length_fails_closed(self):
        with self.assertRaises(ISQLValidationError):
            digest_to_address_code(b"short")

    def test_non_address_code_fails_closed(self):
        code = ISQLCode(protocol="ISQL", version=1, domain="MEM", resolution="R0", control="M", payload="1")
        with self.assertRaises(ISQLValidationError):
            address_code_to_digest(code)


if __name__ == "__main__":
    unittest.main()
