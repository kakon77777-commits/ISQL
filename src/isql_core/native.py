from __future__ import annotations

from dataclasses import dataclass
import hashlib
import zlib

from .address import address_code_to_digest, digest_to_address_code
from .code import ISQLCode
from .errors import ISQLValidationError
from .spectral import SPECTRAL_REGISTRY_ID, SpectralPacket

NATIVE_MAGIC = b"ISN7"
NATIVE_VERSION = 7
NATIVE_KIND_SPECTRAL_MEMORY = 1
NATIVE_BLOCK_SIZE = 16
NATIVE_MAX_BIT_WIDTH = 64
NATIVE_MAX_SEQUENCE_ITEMS = 1_000_000
NATIVE_MAX_VARINT_BYTES = 10
_RESOLUTION_TO_ID = {"R1": 1, "R2": 2}
_ID_TO_RESOLUTION = {value: key for key, value in _RESOLUTION_TO_ID.items()}


def _require_hash(value: str) -> bytes:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ISQLValidationError("NATIVE_INVALID_REGISTRY_HASH")
    return bytes.fromhex(value)


def _uvarint_encode(value: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ISQLValidationError("NATIVE_UINT_REQUIRED")
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
            raise ISQLValidationError("TRUNCATED_NATIVE_VARINT")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            if pos - start > 1 and byte == 0:
                raise ISQLValidationError("NONCANONICAL_NATIVE_VARINT")
            return value, pos
        shift += 7
        if pos - start >= NATIVE_MAX_VARINT_BYTES:
            raise ISQLValidationError("NATIVE_VARINT_TOO_LARGE")


def _pack_block(values: tuple[int, ...]) -> bytes:
    if not values or len(values) > NATIVE_BLOCK_SIZE:
        raise ISQLValidationError("NATIVE_INVALID_BLOCK_LENGTH")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ISQLValidationError("NATIVE_SEQUENCE_UINT_REQUIRED")
    width = max(values).bit_length()
    if width > NATIVE_MAX_BIT_WIDTH:
        raise ISQLValidationError("NATIVE_VALUE_TOO_WIDE")
    out = bytearray((width,))
    if width == 0:
        return bytes(out)
    total_bits = width * len(values)
    padding = (-total_bits) % 8
    acc = 0
    for value in values:
        if value >= (1 << width):
            raise ISQLValidationError("NATIVE_VALUE_OUT_OF_BLOCK_RANGE")
        acc = (acc << width) | value
    acc <<= padding
    byte_count = (total_bits + 7) // 8
    out += acc.to_bytes(byte_count, "big")
    return bytes(out)


def _unpack_block(data: bytes, pos: int, count: int) -> tuple[tuple[int, ...], int]:
    if count <= 0 or count > NATIVE_BLOCK_SIZE:
        raise ISQLValidationError("NATIVE_INVALID_BLOCK_LENGTH")
    if pos >= len(data):
        raise ISQLValidationError("TRUNCATED_NATIVE_BLOCK_WIDTH")
    width = data[pos]
    pos += 1
    if width > NATIVE_MAX_BIT_WIDTH:
        raise ISQLValidationError("NATIVE_INVALID_BLOCK_WIDTH")
    if width == 0:
        return (0,) * count, pos
    total_bits = width * count
    byte_count = (total_bits + 7) // 8
    if pos + byte_count > len(data):
        raise ISQLValidationError("TRUNCATED_NATIVE_BLOCK")
    raw = data[pos : pos + byte_count]
    pos += byte_count
    acc = int.from_bytes(raw, "big")
    padding = (-total_bits) % 8
    if padding:
        mask = (1 << padding) - 1
        if acc & mask:
            raise ISQLValidationError("NATIVE_NONZERO_PADDING_BITS")
        acc >>= padding
    mask = (1 << width) - 1
    values = []
    for index in range(count):
        shift = width * (count - 1 - index)
        values.append((acc >> shift) & mask)
    if max(values).bit_length() != width:
        raise ISQLValidationError("NATIVE_NONCANONICAL_BLOCK_WIDTH")
    return tuple(values), pos


def _encode_sequence(sequence: tuple[int, ...]) -> bytes:
    if not isinstance(sequence, tuple) or not sequence:
        raise ISQLValidationError("NATIVE_SEQUENCE_REQUIRED")
    if len(sequence) > NATIVE_MAX_SEQUENCE_ITEMS:
        raise ISQLValidationError("NATIVE_SEQUENCE_TOO_LONG")
    out = bytearray()
    for start in range(0, len(sequence), NATIVE_BLOCK_SIZE):
        out += _pack_block(sequence[start : start + NATIVE_BLOCK_SIZE])
    return bytes(out)


def _decode_sequence(data: bytes, pos: int, item_count: int) -> tuple[tuple[int, ...], int]:
    if item_count <= 0 or item_count > NATIVE_MAX_SEQUENCE_ITEMS:
        raise ISQLValidationError("NATIVE_INVALID_SEQUENCE_LENGTH")
    remaining = item_count
    values: list[int] = []
    while remaining:
        count = min(NATIVE_BLOCK_SIZE, remaining)
        block, pos = _unpack_block(data, pos, count)
        values.extend(block)
        remaining -= count
    return tuple(values), pos


@dataclass(frozen=True, slots=True)
class NativeSpectralFrame:
    address_digest: bytes
    resolution: str
    registry_revision: int
    registry_hash: str
    sequence: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.address_digest, bytes) or len(self.address_digest) != 32:
            raise ISQLValidationError("NATIVE_ADDRESS_DIGEST_MUST_BE_32_BYTES")
        if self.resolution not in _RESOLUTION_TO_ID:
            raise ISQLValidationError("NATIVE_UNSUPPORTED_RESOLUTION")
        if not isinstance(self.registry_revision, int) or self.registry_revision < 0:
            raise ISQLValidationError("NATIVE_INVALID_REGISTRY_REVISION")
        _require_hash(self.registry_hash)
        if not isinstance(self.sequence, tuple) or not self.sequence:
            raise ISQLValidationError("NATIVE_SEQUENCE_REQUIRED")
        for value in self.sequence:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ISQLValidationError("NATIVE_SEQUENCE_UINT_REQUIRED")
            if value.bit_length() > NATIVE_MAX_BIT_WIDTH:
                raise ISQLValidationError("NATIVE_VALUE_TOO_WIDE")

    @property
    def address(self) -> ISQLCode:
        return digest_to_address_code(self.address_digest)

    @property
    def packet(self) -> SpectralPacket:
        return SpectralPacket(
            registry_id=SPECTRAL_REGISTRY_ID,
            registry_revision=self.registry_revision,
            registry_hash=self.registry_hash,
            sequence=self.sequence,
            registry_delta_bytes=0,
        )

    def to_bytes(self) -> bytes:
        body = bytearray(NATIVE_MAGIC)
        body += bytes((NATIVE_VERSION, NATIVE_KIND_SPECTRAL_MEMORY, _RESOLUTION_TO_ID[self.resolution], 0))
        body += self.address_digest
        body += _uvarint_encode(self.registry_revision)
        body += _require_hash(self.registry_hash)
        body += _uvarint_encode(len(self.sequence))
        body += _encode_sequence(self.sequence)
        checksum = zlib.crc32(body) & 0xFFFFFFFF
        return bytes(body) + checksum.to_bytes(4, "big")


def encode_native_spectral_frame(address: ISQLCode, packet: SpectralPacket, resolution: str) -> bytes:
    if not isinstance(packet, SpectralPacket):
        raise ISQLValidationError("NATIVE_SPECTRAL_PACKET_REQUIRED")
    if packet.registry_id != SPECTRAL_REGISTRY_ID:
        raise ISQLValidationError("NATIVE_UNSUPPORTED_REGISTRY_ID")
    frame = NativeSpectralFrame(
        address_digest=address_code_to_digest(address),
        resolution=resolution,
        registry_revision=packet.registry_revision,
        registry_hash=packet.registry_hash,
        sequence=packet.sequence,
    )
    return frame.to_bytes()


def decode_native_spectral_frame(frame: bytes) -> NativeSpectralFrame:
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("NATIVE_FRAME_BYTES_REQUIRED")
    data = bytes(frame)
    if len(data) < 4 + 4 + 32 + 1 + 32 + 1 + 1 + 4:
        raise ISQLValidationError("TRUNCATED_NATIVE_FRAME")
    body = data[:-4]
    actual = int.from_bytes(data[-4:], "big")
    expected = zlib.crc32(body) & 0xFFFFFFFF
    if actual != expected:
        raise ISQLValidationError("NATIVE_FRAME_CHECKSUM_MISMATCH")
    if not body.startswith(NATIVE_MAGIC):
        raise ISQLValidationError("INVALID_NATIVE_MAGIC")
    pos = len(NATIVE_MAGIC)
    version = body[pos]
    pos += 1
    if version != NATIVE_VERSION:
        raise ISQLValidationError("UNSUPPORTED_NATIVE_VERSION")
    kind = body[pos]
    pos += 1
    if kind != NATIVE_KIND_SPECTRAL_MEMORY:
        raise ISQLValidationError("UNSUPPORTED_NATIVE_KIND")
    resolution_id = body[pos]
    pos += 1
    resolution = _ID_TO_RESOLUTION.get(resolution_id)
    if resolution is None:
        raise ISQLValidationError("NATIVE_UNSUPPORTED_RESOLUTION")
    flags = body[pos]
    pos += 1
    if flags != 0:
        raise ISQLValidationError("NATIVE_UNSUPPORTED_FLAGS")
    address_digest = body[pos : pos + 32]
    if len(address_digest) != 32:
        raise ISQLValidationError("TRUNCATED_NATIVE_ADDRESS")
    pos += 32
    registry_revision, pos = _uvarint_decode(body, pos)
    if pos + 32 > len(body):
        raise ISQLValidationError("TRUNCATED_NATIVE_REGISTRY_HASH")
    registry_hash = body[pos : pos + 32].hex()
    pos += 32
    item_count, pos = _uvarint_decode(body, pos)
    sequence, pos = _decode_sequence(body, pos, item_count)
    if pos != len(body):
        raise ISQLValidationError("NATIVE_FRAME_TRAILING_BYTES")
    result = NativeSpectralFrame(
        address_digest=address_digest,
        resolution=resolution,
        registry_revision=registry_revision,
        registry_hash=registry_hash,
        sequence=sequence,
    )
    if result.to_bytes() != data:
        raise ISQLValidationError("NONCANONICAL_NATIVE_FRAME")
    return result


@dataclass(frozen=True, slots=True)
class NativeMemoryCompileResult:
    frame: bytes
    resolution: str
    frame_sha256: str
    frame_bytes: int
    sequence_items: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "isql.native-memory-compile/v0.7",
            "resolution": self.resolution,
            "frame_bytes": self.frame_bytes,
            "sequence_items": self.sequence_items,
            "frame_sha256": self.frame_sha256,
        }


def compile_native_memory(record: "MemoryRecord", resolution: str = "R2") -> NativeMemoryCompileResult:
    from .memory import MemoryRecord

    if not isinstance(record, MemoryRecord):
        raise ISQLValidationError("NATIVE_MEMORY_RECORD_REQUIRED")
    if resolution not in _RESOLUTION_TO_ID:
        raise ISQLValidationError("NATIVE_UNSUPPORTED_RESOLUTION")
    if "spectral" not in record.variants:
        raise ISQLValidationError("NATIVE_REQUIRES_SPECTRAL_PROFILE")
    layer = record.get_layer("spectral", resolution)
    raw_packet = layer.data.get("packet")
    if not isinstance(raw_packet, dict):
        raise ISQLValidationError("NATIVE_SPECTRAL_PACKET_MISSING")
    packet = SpectralPacket.from_dict(raw_packet)
    frame = encode_native_spectral_frame(record.address, packet, resolution)
    return NativeMemoryCompileResult(
        frame=frame,
        resolution=resolution,
        frame_sha256=hashlib.sha256(frame).hexdigest(),
        frame_bytes=len(frame),
        sequence_items=len(packet.sequence),
    )


def expand_native_memory(frame: bytes, registry_store: "SpectralRegistryStore") -> "SemanticCoordinateSet":
    from .spectral import SpectralRegistryStore, expand_spectral_packet

    if not isinstance(registry_store, SpectralRegistryStore):
        raise ISQLValidationError("NATIVE_SPECTRAL_REGISTRY_STORE_REQUIRED")
    parsed = decode_native_spectral_frame(frame)
    return expand_spectral_packet(parsed.packet, registry_store)


def inspect_native_frame(frame: bytes) -> dict[str, object]:
    parsed = decode_native_spectral_frame(frame)
    return {
        "schema": "isql.native-frame-info/v0.7",
        "version": NATIVE_VERSION,
        "kind": "spectral-memory",
        "resolution": parsed.resolution,
        "address_sha256": parsed.address_digest.hex(),
        "registry_revision": parsed.registry_revision,
        "registry_hash": parsed.registry_hash,
        "sequence_items": len(parsed.sequence),
        "max_coordinate": max(parsed.sequence),
        "frame_bytes": len(frame),
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
    }


def render_native_debug(frame: bytes) -> str:
    parsed = decode_native_spectral_frame(frame)
    return (
        "NON-CANONICAL DEBUG VIEW\n"
        f"address={parsed.address.to_wire()}\n"
        f"resolution={parsed.resolution}\n"
        f"registry_revision={parsed.registry_revision}\n"
        f"registry_hash={parsed.registry_hash}\n"
        f"sequence={','.join(str(x) for x in parsed.sequence)}\n"
    )
