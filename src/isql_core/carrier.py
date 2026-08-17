from __future__ import annotations

from dataclasses import dataclass
import hashlib
import zlib

from .errors import ISQLValidationError

CARRIER_MAGIC = b"IPC6"
CARRIER_VERSION = 6
CODEC_BCD4 = 1
CODEC_D40 = 2
MAX_DIGITS = 10_000_000
MAX_VARINT_BYTES = 10

_CODEC_NAME_TO_ID = {"bcd4": CODEC_BCD4, "d40": CODEC_D40}
_CODEC_ID_TO_NAME = {value: key for key, value in _CODEC_NAME_TO_ID.items()}


def _require_digits(wire: str) -> None:
    if not isinstance(wire, str) or not wire or not wire.isascii() or not wire.isdigit():
        raise ISQLValidationError("CARRIER_ASCII_DIGITS_REQUIRED")
    if len(wire) > MAX_DIGITS:
        raise ISQLValidationError("CARRIER_TOO_MANY_DIGITS")


def _uvarint_encode(value: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ISQLValidationError("CARRIER_UINT_REQUIRED")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _uvarint_decode(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    start = pos
    while True:
        if pos >= len(data):
            raise ISQLValidationError("TRUNCATED_CARRIER_VARINT")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            if pos - start > 1 and byte == 0:
                raise ISQLValidationError("NONCANONICAL_CARRIER_VARINT")
            return value, pos
        shift += 7
        if pos - start >= MAX_VARINT_BYTES:
            raise ISQLValidationError("CARRIER_VARINT_TOO_LARGE")


def _pack_bcd4(wire: str) -> bytes:
    out = bytearray()
    for pos in range(0, len(wire), 2):
        high = ord(wire[pos]) - 48
        if pos + 1 < len(wire):
            low = ord(wire[pos + 1]) - 48
        else:
            low = 0x0F
        out.append((high << 4) | low)
    return bytes(out)


def _unpack_bcd4(payload: bytes, digit_count: int) -> str:
    expected = (digit_count + 1) // 2
    if len(payload) != expected:
        raise ISQLValidationError("CARRIER_BCD4_LENGTH_MISMATCH")
    chars: list[str] = []
    for index, byte in enumerate(payload):
        high = byte >> 4
        low = byte & 0x0F
        if high > 9:
            raise ISQLValidationError("CARRIER_BCD4_INVALID_DIGIT")
        chars.append(chr(48 + high))
        is_last = index == len(payload) - 1
        if is_last and digit_count % 2:
            if low != 0x0F:
                raise ISQLValidationError("CARRIER_BCD4_INVALID_SENTINEL")
        else:
            if low > 9:
                raise ISQLValidationError("CARRIER_BCD4_INVALID_DIGIT")
            chars.append(chr(48 + low))
    text = "".join(chars)
    if len(text) != digit_count:
        raise ISQLValidationError("CARRIER_BCD4_DECODE_LENGTH_MISMATCH")
    return text


def _d40_partial_width(digits: int) -> int:
    if digits < 0 or digits > 11:
        raise ISQLValidationError("CARRIER_D40_INVALID_PARTIAL_WIDTH")
    if digits == 0:
        return 0
    return ((10 ** digits - 1).bit_length() + 7) // 8


def _pack_d40(wire: str) -> bytes:
    out = bytearray()
    full, rem = divmod(len(wire), 12)
    for index in range(full):
        chunk = wire[index * 12 : (index + 1) * 12]
        value = int(chunk)
        out += value.to_bytes(5, "big")
    if rem:
        chunk = wire[full * 12 :]
        value = int(chunk)
        out += value.to_bytes(_d40_partial_width(rem), "big")
    return bytes(out)


def _unpack_d40(payload: bytes, digit_count: int) -> str:
    full, rem = divmod(digit_count, 12)
    expected = full * 5 + _d40_partial_width(rem)
    if len(payload) != expected:
        raise ISQLValidationError("CARRIER_D40_LENGTH_MISMATCH")
    pos = 0
    parts: list[str] = []
    for _ in range(full):
        value = int.from_bytes(payload[pos : pos + 5], "big")
        pos += 5
        if value >= 10 ** 12:
            raise ISQLValidationError("CARRIER_D40_BLOCK_OUT_OF_RANGE")
        parts.append(f"{value:012d}")
    if rem:
        width = _d40_partial_width(rem)
        value = int.from_bytes(payload[pos : pos + width], "big")
        pos += width
        if value >= 10 ** rem:
            raise ISQLValidationError("CARRIER_D40_BLOCK_OUT_OF_RANGE")
        parts.append(f"{value:0{rem}d}")
    if pos != len(payload):
        raise ISQLValidationError("CARRIER_D40_TRAILING_BYTES")
    text = "".join(parts)
    if len(text) != digit_count:
        raise ISQLValidationError("CARRIER_D40_DECODE_LENGTH_MISMATCH")
    return text


def _payload_length(codec_id: int, digit_count: int) -> int:
    if codec_id == CODEC_BCD4:
        return (digit_count + 1) // 2
    if codec_id == CODEC_D40:
        full, rem = divmod(digit_count, 12)
        return full * 5 + _d40_partial_width(rem)
    raise ISQLValidationError("CARRIER_UNKNOWN_CODEC")


def pack_digit_wire(wire: str, codec: str = "d40") -> bytes:
    _require_digits(wire)
    codec_id = _CODEC_NAME_TO_ID.get(codec)
    if codec_id is None:
        raise ISQLValidationError("CARRIER_UNKNOWN_CODEC")
    if codec_id == CODEC_BCD4:
        payload = _pack_bcd4(wire)
    elif codec_id == CODEC_D40:
        payload = _pack_d40(wire)
    else:
        raise ISQLValidationError("CARRIER_UNKNOWN_CODEC")
    header = CARRIER_MAGIC + bytes((CARRIER_VERSION, codec_id)) + _uvarint_encode(len(wire))
    checksum = zlib.crc32(wire.encode("ascii")) & 0xFFFFFFFF
    return header + payload + checksum.to_bytes(4, "big")


def unpack_digit_carrier(carrier: bytes) -> str:
    if not isinstance(carrier, (bytes, bytearray)):
        raise ISQLValidationError("CARRIER_BYTES_REQUIRED")
    data = bytes(carrier)
    if len(data) < len(CARRIER_MAGIC) + 2 + 1 + 4:
        raise ISQLValidationError("TRUNCATED_CARRIER")
    if not data.startswith(CARRIER_MAGIC):
        raise ISQLValidationError("INVALID_CARRIER_MAGIC")
    pos = len(CARRIER_MAGIC)
    version = data[pos]
    pos += 1
    if version != CARRIER_VERSION:
        raise ISQLValidationError("UNSUPPORTED_CARRIER_VERSION")
    codec_id = data[pos]
    pos += 1
    if codec_id not in _CODEC_ID_TO_NAME:
        raise ISQLValidationError("CARRIER_UNKNOWN_CODEC")
    digit_count, pos = _uvarint_decode(data, pos)
    if digit_count <= 0 or digit_count > MAX_DIGITS:
        raise ISQLValidationError("CARRIER_INVALID_DIGIT_COUNT")
    payload_length = _payload_length(codec_id, digit_count)
    expected_length = pos + payload_length + 4
    if len(data) != expected_length:
        raise ISQLValidationError("CARRIER_LENGTH_MISMATCH")
    payload = data[pos : pos + payload_length]
    pos += payload_length
    checksum = int.from_bytes(data[pos : pos + 4], "big")
    if codec_id == CODEC_BCD4:
        wire = _unpack_bcd4(payload, digit_count)
    elif codec_id == CODEC_D40:
        wire = _unpack_d40(payload, digit_count)
    else:
        raise ISQLValidationError("CARRIER_UNKNOWN_CODEC")
    expected = zlib.crc32(wire.encode("ascii")) & 0xFFFFFFFF
    if checksum != expected:
        raise ISQLValidationError("CARRIER_CHECKSUM_MISMATCH")
    return wire


@dataclass(frozen=True, slots=True)
class CarrierCompileResult:
    codec: str
    carrier: bytes
    wire_bytes: int
    carrier_bytes: int
    payload_bytes: int
    carrier_sha256: str

    @property
    def carrier_vs_wire_ratio(self) -> float:
        return self.carrier_bytes / self.wire_bytes

    def to_dict(self) -> dict[str, object]:
        return {
            "codec": self.codec,
            "wire_bytes": self.wire_bytes,
            "carrier_bytes": self.carrier_bytes,
            "payload_bytes": self.payload_bytes,
            "carrier_vs_wire_ratio": self.carrier_vs_wire_ratio,
            "carrier_sha256": self.carrier_sha256,
        }


def compile_digit_carrier(wire: str, codec: str = "d40") -> CarrierCompileResult:
    _require_digits(wire)
    codec_id = _CODEC_NAME_TO_ID.get(codec)
    if codec_id is None:
        raise ISQLValidationError("CARRIER_UNKNOWN_CODEC")
    carrier = pack_digit_wire(wire, codec=codec)
    payload_bytes = _payload_length(codec_id, len(wire))
    return CarrierCompileResult(
        codec=codec,
        carrier=carrier,
        wire_bytes=len(wire.encode("ascii")),
        carrier_bytes=len(carrier),
        payload_bytes=payload_bytes,
        carrier_sha256=hashlib.sha256(carrier).hexdigest(),
    )


def inspect_digit_carrier(carrier: bytes) -> dict[str, object]:
    wire = unpack_digit_carrier(carrier)
    data = bytes(carrier)
    pos = len(CARRIER_MAGIC)
    version = data[pos]
    pos += 1
    codec_id = data[pos]
    pos += 1
    digit_count, pos = _uvarint_decode(data, pos)
    codec = _CODEC_ID_TO_NAME[codec_id]
    payload_bytes = _payload_length(codec_id, digit_count)
    return {
        "schema": "isql.digit-carrier-info/v0.6",
        "version": version,
        "codec": codec,
        "digit_count": digit_count,
        "wire_bytes": len(wire.encode("ascii")),
        "payload_bytes": payload_bytes,
        "carrier_bytes": len(data),
        "carrier_vs_wire_ratio": len(data) / len(wire.encode("ascii")),
        "carrier_sha256": hashlib.sha256(data).hexdigest(),
    }
