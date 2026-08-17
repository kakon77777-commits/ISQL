from __future__ import annotations

from dataclasses import dataclass
import zlib

from .errors import ISQLValidationError
from .spectral import SPECTRAL_REGISTRY_ID, SpectralPacket

NUMERIC_WIRE_MAGIC = "94040"
NUMERIC_WIRE_VERSION = 4
MAX_UINT_DIGITS = 1_000_000
MAX_SEQUENCE_ITEMS = 1_000_000


def _require_ascii_digits(text: str, error: str) -> None:
    if not isinstance(text, str) or not text or not text.isascii() or not text.isdigit():
        raise ISQLValidationError(error)


def encode_uint(value: int) -> str:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ISQLValidationError("NUMERIC_WIRE_UINT_REQUIRED")
    digits = str(value)
    length = len(digits)
    if length <= 9:
        return f"{length}{digits}"
    length_digits = str(length)
    if len(length_digits) > 9:
        raise ISQLValidationError("NUMERIC_WIRE_UINT_TOO_LARGE")
    return f"0{len(length_digits)}{length_digits}{digits}"


def decode_uint(text: str, pos: int = 0) -> tuple[int, int]:
    _require_ascii_digits(text, "NUMERIC_WIRE_DIGITS_REQUIRED")
    if not isinstance(pos, int) or pos < 0 or pos >= len(text):
        raise ISQLValidationError("NUMERIC_WIRE_INVALID_POSITION")

    first = text[pos]
    pos += 1
    if first == "0":
        if pos >= len(text):
            raise ISQLValidationError("TRUNCATED_NUMERIC_WIRE_LENGTH")
        length_of_length = int(text[pos])
        pos += 1
        if length_of_length == 0:
            raise ISQLValidationError("INVALID_NUMERIC_WIRE_LENGTH_OF_LENGTH")
        if pos + length_of_length > len(text):
            raise ISQLValidationError("TRUNCATED_NUMERIC_WIRE_LENGTH")
        length_text = text[pos : pos + length_of_length]
        pos += length_of_length
        if length_text.startswith("0"):
            raise ISQLValidationError("NONCANONICAL_NUMERIC_WIRE_LENGTH")
        length = int(length_text)
        if length <= 9:
            raise ISQLValidationError("NONCANONICAL_NUMERIC_WIRE_EXTENDED_LENGTH")
    else:
        length = int(first)

    if length <= 0 or length > MAX_UINT_DIGITS:
        raise ISQLValidationError("INVALID_NUMERIC_WIRE_UINT_LENGTH")
    if pos + length > len(text):
        raise ISQLValidationError("TRUNCATED_NUMERIC_WIRE_UINT")
    payload = text[pos : pos + length]
    pos += length
    if length > 1 and payload.startswith("0"):
        raise ISQLValidationError("NONCANONICAL_NUMERIC_WIRE_UINT")
    return int(payload), pos


def _semantic_prefix(packet: SpectralPacket) -> str:
    if packet.registry_id != SPECTRAL_REGISTRY_ID:
        raise ISQLValidationError("NUMERIC_WIRE_UNSUPPORTED_REGISTRY_ID")
    hash_int = int(packet.registry_hash, 16)
    fields = [
        NUMERIC_WIRE_MAGIC,
        encode_uint(NUMERIC_WIRE_VERSION),
        encode_uint(packet.registry_revision),
        encode_uint(hash_int),
        encode_uint(len(packet.sequence)),
    ]
    fields.extend(encode_uint(value) for value in packet.sequence)
    return "".join(fields)


def encode_numeric_wire(packet: SpectralPacket) -> str:
    if not isinstance(packet, SpectralPacket):
        raise ISQLValidationError("NUMERIC_WIRE_REQUIRES_SPECTRAL_PACKET")
    prefix = _semantic_prefix(packet)
    checksum = zlib.crc32(prefix.encode("ascii")) & 0xFFFFFFFF
    return prefix + encode_uint(checksum)


def decode_numeric_wire(wire: str) -> SpectralPacket:
    _require_ascii_digits(wire, "NUMERIC_WIRE_DIGITS_REQUIRED")
    if not wire.startswith(NUMERIC_WIRE_MAGIC):
        raise ISQLValidationError("INVALID_NUMERIC_WIRE_MAGIC")
    pos = len(NUMERIC_WIRE_MAGIC)
    version, pos = decode_uint(wire, pos)
    if version != NUMERIC_WIRE_VERSION:
        raise ISQLValidationError("UNSUPPORTED_NUMERIC_WIRE_VERSION")
    revision, pos = decode_uint(wire, pos)
    hash_int, pos = decode_uint(wire, pos)
    if hash_int >= 1 << 256:
        raise ISQLValidationError("NUMERIC_WIRE_REGISTRY_HASH_OUT_OF_RANGE")
    registry_hash = f"{hash_int:064x}"
    count, pos = decode_uint(wire, pos)
    if count > MAX_SEQUENCE_ITEMS:
        raise ISQLValidationError("NUMERIC_WIRE_SEQUENCE_TOO_LARGE")
    sequence: list[int] = []
    for _ in range(count):
        value, pos = decode_uint(wire, pos)
        sequence.append(value)

    checksum_start = pos
    checksum, pos = decode_uint(wire, pos)
    if pos != len(wire):
        raise ISQLValidationError("NUMERIC_WIRE_TRAILING_DIGITS")
    expected = zlib.crc32(wire[:checksum_start].encode("ascii")) & 0xFFFFFFFF
    if checksum != expected:
        raise ISQLValidationError("NUMERIC_WIRE_CHECKSUM_MISMATCH")

    return SpectralPacket(
        registry_id=SPECTRAL_REGISTRY_ID,
        registry_revision=revision,
        registry_hash=registry_hash,
        sequence=tuple(sequence),
        registry_delta_bytes=0,
    )


@dataclass(frozen=True, slots=True)
class NumericWireCompileResult:
    wire: str
    wire_bytes: int
    spectral_packet_bytes: int

    @property
    def wire_vs_packet_ratio(self) -> float:
        return self.wire_bytes / self.spectral_packet_bytes

    def to_dict(self) -> dict[str, object]:
        return {
            "wire": self.wire,
            "wire_bytes": self.wire_bytes,
            "spectral_packet_bytes": self.spectral_packet_bytes,
            "wire_vs_packet_ratio": self.wire_vs_packet_ratio,
        }


def compile_numeric_wire(packet: SpectralPacket) -> NumericWireCompileResult:
    wire = encode_numeric_wire(packet)
    return NumericWireCompileResult(
        wire=wire,
        wire_bytes=len(wire.encode("ascii")),
        spectral_packet_bytes=len(packet.canonical_bytes()),
    )
