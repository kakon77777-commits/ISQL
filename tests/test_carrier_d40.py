import unittest

from isql_core.carrier import pack_digit_wire, unpack_digit_carrier
from isql_core.errors import ISQLValidationError


def partial_width(digits: int) -> int:
    if digits == 0:
        return 0
    return ((10 ** digits - 1).bit_length() + 7) // 8


class CarrierD40Tests(unittest.TestCase):
    def test_boundary_lengths_round_trip_and_expected_payload_size(self):
        for n in range(1, 25):
            with self.subTest(n=n):
                wire = ("0" if n > 1 else "7") + "123456789012345678901234"[: n - 1]
                carrier = pack_digit_wire(wire, codec="d40")
                self.assertEqual(unpack_digit_carrier(carrier), wire)
                full, rem = divmod(n, 12)
                payload = full * 5 + partial_width(rem)
                # n <= 24 => digit count varint is one byte; header 7 + CRC 4.
                self.assertEqual(len(carrier), 11 + payload)

    def test_full_block_maximum_round_trip(self):
        wire = "999999999999"
        carrier = pack_digit_wire(wire, codec="d40")
        self.assertEqual(unpack_digit_carrier(carrier), wire)
        self.assertEqual(len(carrier), 16)

    def test_leading_zero_blocks_round_trip(self):
        wire = "00000000000100000000000200003"
        self.assertEqual(unpack_digit_carrier(pack_digit_wire(wire, codec="d40")), wire)

    def test_out_of_range_full_chunk_is_rejected(self):
        wire = "123456789012"
        carrier = bytearray(pack_digit_wire(wire, codec="d40"))
        payload_start = 7  # IPC6 + version + codec + one-byte digit count varint
        carrier[payload_start : payload_start + 5] = b"\xff" * 5
        with self.assertRaises(ISQLValidationError):
            unpack_digit_carrier(bytes(carrier))

    def test_d40_is_smaller_than_bcd_for_long_wire(self):
        wire = "95050" + "1234567890" * 100
        d40 = pack_digit_wire(wire, codec="d40")
        bcd = pack_digit_wire(wire, codec="bcd4")
        self.assertLess(len(d40), len(bcd))
        self.assertEqual(unpack_digit_carrier(d40), wire)


if __name__ == "__main__":
    unittest.main()
