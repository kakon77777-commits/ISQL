import unittest

from isql_core.errors import ISQLValidationError
from isql_core.carrier import pack_digit_wire, unpack_digit_carrier


class CarrierBCDTests(unittest.TestCase):
    def test_even_digits_round_trip(self):
        wire = "940401234567890123"
        carrier = pack_digit_wire(wire, codec="bcd4")
        self.assertEqual(unpack_digit_carrier(carrier), wire)

    def test_odd_digits_round_trip_and_leading_zeros(self):
        wire = "0001234567897"
        carrier = pack_digit_wire(wire, codec="bcd4")
        self.assertEqual(unpack_digit_carrier(carrier), wire)

    def test_same_wire_same_carrier(self):
        wire = "950506789012345"
        self.assertEqual(pack_digit_wire(wire, codec="bcd4"), pack_digit_wire(wire, codec="bcd4"))

    def test_rejects_non_ascii_digits(self):
        with self.assertRaises(ISQLValidationError):
            pack_digit_wire("１２３", codec="bcd4")
        with self.assertRaises(ISQLValidationError):
            pack_digit_wire("12a3", codec="bcd4")

    def test_bad_odd_sentinel_is_rejected(self):
        wire = "12345"
        carrier = bytearray(pack_digit_wire(wire, codec="bcd4"))
        carrier[-5] = (carrier[-5] & 0xF0) | 0x0E
        with self.assertRaises(ISQLValidationError):
            unpack_digit_carrier(bytes(carrier))

    def test_crc_mismatch_is_rejected(self):
        carrier = bytearray(pack_digit_wire("123456789", codec="bcd4"))
        carrier[-1] ^= 0x01
        with self.assertRaises(ISQLValidationError):
            unpack_digit_carrier(bytes(carrier))

    def test_truncation_is_rejected(self):
        carrier = pack_digit_wire("123456789", codec="bcd4")
        with self.assertRaises(ISQLValidationError):
            unpack_digit_carrier(carrier[:-1])


if __name__ == "__main__":
    unittest.main()
