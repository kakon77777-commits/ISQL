from __future__ import annotations

from dataclasses import dataclass
import zlib

from .errors import ISQLValidationError
from .hierarchical import HIERARCHICAL_REGISTRY_ID, HierarchicalRegistryDelta
from .spectral import SPECTRAL_NAMESPACES, SPECTRAL_REGISTRY_ID
from .wire import decode_uint, encode_uint

REGISTRY_WIRE_MAGIC = "95050"
REGISTRY_WIRE_VERSION = 5
REGISTRY_BINARY_MAGIC = b"HRD5"
MAX_REGISTRY_LEXEMES = 1_000_000
MAX_PROGRAMS_PER_NAMESPACE = 1_000_000
MAX_PROGRAM_LENGTH = 1_000_000
MAX_BINARY_VARINT_BYTES = 10


def _require_digits(text: str) -> None:
    if not isinstance(text, str) or not text or not text.isascii() or not text.isdigit():
        raise ISQLValidationError("REGISTRY_WIRE_DIGITS_REQUIRED")


def _require_hash(value: str) -> bytes:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ISQLValidationError("REGISTRY_WIRE_INVALID_HASH")
    return bytes.fromhex(value)


def _bvarint_encode(value: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ISQLValidationError("REGISTRY_BINARY_UINT_REQUIRED")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _bvarint_decode(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    start = pos
    while True:
        if pos >= len(data):
            raise ISQLValidationError("TRUNCATED_REGISTRY_BINARY_VARINT")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            if pos - start > 1 and byte == 0:
                raise ISQLValidationError("NONCANONICAL_REGISTRY_BINARY_VARINT")
            return value, pos
        shift += 7
        if pos - start >= MAX_BINARY_VARINT_BYTES:
            raise ISQLValidationError("REGISTRY_BINARY_VARINT_TOO_LARGE")


def _take(data: bytes, pos: int, count: int, error: str) -> tuple[bytes, int]:
    if count < 0 or pos + count > len(data):
        raise ISQLValidationError(error)
    return data[pos : pos + count], pos + count


def encode_registry_delta_binary(delta: HierarchicalRegistryDelta) -> bytes:
    if not isinstance(delta, HierarchicalRegistryDelta):
        raise ISQLValidationError("REGISTRY_BINARY_REQUIRES_DELTA")
    if delta.registry_id != HIERARCHICAL_REGISTRY_ID or delta.canonical_registry_id != SPECTRAL_REGISTRY_ID:
        raise ISQLValidationError("REGISTRY_BINARY_UNSUPPORTED_REGISTRY")

    out = bytearray(REGISTRY_BINARY_MAGIC)
    out += _bvarint_encode(delta.from_revision)
    out += _bvarint_encode(delta.to_revision)
    out += _require_hash(delta.previous_hierarchical_hash)
    out += _require_hash(delta.target_hierarchical_hash)
    out += _bvarint_encode(delta.canonical_revision)
    out += _require_hash(delta.canonical_hash)
    out += _bvarint_encode(delta.base_lexeme_count)
    out += _bvarint_encode(len(delta.new_lexemes))
    for lexeme in delta.new_lexemes:
        raw = lexeme.encode("utf-8")
        if not raw:
            raise ISQLValidationError("REGISTRY_BINARY_EMPTY_LEXEME")
        out += _bvarint_encode(len(raw))
        out += raw
    for namespace in SPECTRAL_NAMESPACES:
        programs = delta.new_programs[namespace]
        out += _bvarint_encode(len(programs))
        for program in programs:
            out += _bvarint_encode(len(program))
            for value_id in program:
                out += _bvarint_encode(value_id)

    checksum = zlib.crc32(out) & 0xFFFFFFFF
    out += checksum.to_bytes(4, "big")
    return bytes(out)


def decode_registry_delta_binary(payload: bytes) -> HierarchicalRegistryDelta:
    if not isinstance(payload, (bytes, bytearray)):
        raise ISQLValidationError("REGISTRY_BINARY_BYTES_REQUIRED")
    data = bytes(payload)
    if len(data) < len(REGISTRY_BINARY_MAGIC) + 4 or not data.startswith(REGISTRY_BINARY_MAGIC):
        raise ISQLValidationError("INVALID_REGISTRY_BINARY_MAGIC")
    body = data[:-4]
    expected = zlib.crc32(body) & 0xFFFFFFFF
    actual = int.from_bytes(data[-4:], "big")
    if expected != actual:
        raise ISQLValidationError("REGISTRY_BINARY_CHECKSUM_MISMATCH")

    pos = len(REGISTRY_BINARY_MAGIC)
    from_revision, pos = _bvarint_decode(body, pos)
    to_revision, pos = _bvarint_decode(body, pos)
    raw, pos = _take(body, pos, 32, "TRUNCATED_REGISTRY_BINARY_PREVIOUS_HASH")
    previous_hash = raw.hex()
    raw, pos = _take(body, pos, 32, "TRUNCATED_REGISTRY_BINARY_TARGET_HASH")
    target_hash = raw.hex()
    canonical_revision, pos = _bvarint_decode(body, pos)
    raw, pos = _take(body, pos, 32, "TRUNCATED_REGISTRY_BINARY_CANONICAL_HASH")
    canonical_hash = raw.hex()
    base_lexeme_count, pos = _bvarint_decode(body, pos)
    lexeme_count, pos = _bvarint_decode(body, pos)
    if lexeme_count > MAX_REGISTRY_LEXEMES:
        raise ISQLValidationError("REGISTRY_BINARY_TOO_MANY_LEXEMES")
    lexemes: list[str] = []
    for _ in range(lexeme_count):
        length, pos = _bvarint_decode(body, pos)
        raw, pos = _take(body, pos, length, "TRUNCATED_REGISTRY_BINARY_LEXEME")
        try:
            lexeme = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ISQLValidationError("REGISTRY_BINARY_INVALID_UTF8") from exc
        if not lexeme:
            raise ISQLValidationError("REGISTRY_BINARY_EMPTY_LEXEME")
        lexemes.append(lexeme)

    programs: dict[str, tuple[tuple[int, ...], ...]] = {}
    for namespace in SPECTRAL_NAMESPACES:
        count, pos = _bvarint_decode(body, pos)
        if count > MAX_PROGRAMS_PER_NAMESPACE:
            raise ISQLValidationError("REGISTRY_BINARY_TOO_MANY_PROGRAMS")
        rows: list[tuple[int, ...]] = []
        for _ in range(count):
            length, pos = _bvarint_decode(body, pos)
            if length <= 0 or length > MAX_PROGRAM_LENGTH:
                raise ISQLValidationError("INVALID_REGISTRY_BINARY_PROGRAM_LENGTH")
            ids: list[int] = []
            for _ in range(length):
                value_id, pos = _bvarint_decode(body, pos)
                ids.append(value_id)
            rows.append(tuple(ids))
        programs[namespace] = tuple(rows)
    if pos != len(body):
        raise ISQLValidationError("REGISTRY_BINARY_TRAILING_BYTES")

    return HierarchicalRegistryDelta(
        registry_id=HIERARCHICAL_REGISTRY_ID,
        from_revision=from_revision,
        to_revision=to_revision,
        previous_hierarchical_hash=previous_hash,
        target_hierarchical_hash=target_hash,
        canonical_registry_id=SPECTRAL_REGISTRY_ID,
        canonical_revision=canonical_revision,
        canonical_hash=canonical_hash,
        base_lexeme_count=base_lexeme_count,
        new_lexemes=tuple(lexemes),
        new_programs=programs,
    )


def encode_registry_delta_wire(delta: HierarchicalRegistryDelta) -> str:
    payload = encode_registry_delta_binary(delta)
    payload_int = int.from_bytes(payload, "big", signed=False)
    return (
        REGISTRY_WIRE_MAGIC
        + encode_uint(REGISTRY_WIRE_VERSION)
        + encode_uint(len(payload))
        + encode_uint(payload_int)
    )


def decode_registry_delta_wire(wire: str) -> HierarchicalRegistryDelta:
    _require_digits(wire)
    if not wire.startswith(REGISTRY_WIRE_MAGIC):
        raise ISQLValidationError("INVALID_REGISTRY_WIRE_MAGIC")
    pos = len(REGISTRY_WIRE_MAGIC)
    version, pos = decode_uint(wire, pos)
    if version != REGISTRY_WIRE_VERSION:
        raise ISQLValidationError("UNSUPPORTED_REGISTRY_WIRE_VERSION")
    payload_length, pos = decode_uint(wire, pos)
    if payload_length <= 0:
        raise ISQLValidationError("INVALID_REGISTRY_WIRE_PAYLOAD_LENGTH")
    payload_int, pos = decode_uint(wire, pos)
    if pos != len(wire):
        raise ISQLValidationError("REGISTRY_WIRE_TRAILING_DIGITS")
    if payload_int >= 1 << (8 * payload_length):
        raise ISQLValidationError("REGISTRY_WIRE_PAYLOAD_INTEGER_OUT_OF_RANGE")
    payload = payload_int.to_bytes(payload_length, "big", signed=False)
    return decode_registry_delta_binary(payload)


@dataclass(frozen=True, slots=True)
class RegistryWireCompileResult:
    wire: str
    wire_bytes: int
    structural_binary_bytes: int
    delta_json_bytes: int
    new_lexeme_utf8_bytes: int
    program_reference_count: int

    @property
    def wire_vs_delta_json_ratio(self) -> float:
        return self.wire_bytes / self.delta_json_bytes if self.delta_json_bytes else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "wire": self.wire,
            "wire_bytes": self.wire_bytes,
            "structural_binary_bytes": self.structural_binary_bytes,
            "delta_json_bytes": self.delta_json_bytes,
            "new_lexeme_utf8_bytes": self.new_lexeme_utf8_bytes,
            "program_reference_count": self.program_reference_count,
            "wire_vs_delta_json_ratio": self.wire_vs_delta_json_ratio,
        }


def compile_registry_delta_wire(delta: HierarchicalRegistryDelta) -> RegistryWireCompileResult:
    payload = encode_registry_delta_binary(delta)
    wire = encode_registry_delta_wire(delta)
    return RegistryWireCompileResult(
        wire=wire,
        wire_bytes=len(wire.encode("ascii")),
        structural_binary_bytes=len(payload),
        delta_json_bytes=len(delta.canonical_bytes()),
        new_lexeme_utf8_bytes=sum(len(text.encode("utf-8")) for text in delta.new_lexemes),
        program_reference_count=sum(
            len(program)
            for namespace in SPECTRAL_NAMESPACES
            for program in delta.new_programs[namespace]
        ),
    )
