from __future__ import annotations

from dataclasses import dataclass
import hashlib
import zlib

from .address import address_code_to_digest, digest_to_address_code
from .code import ISQLCode
from .errors import ISQLValidationError
from .spectral import SPECTRAL_REGISTRY_ID, SpectralPacket


ISX_MAGIC = b"ISX1"
ISX_VERSION = 1
ISX_KIND_SPECTRAL_MEMORY = 1
ISX_BLOCK_SIZE = 16
ISX_MAX_BIT_WIDTH = 4096
ISX_MAX_SEQUENCE_ITEMS = 1_000_000
ISX_MAX_VARINT_BYTES = 10
ISX_EXTENDED_WIDTH_MARKER = 0xFF

_RESOLUTION_TO_ID = {"R1": 1, "R2": 2}
_ID_TO_RESOLUTION = {value: key for key, value in _RESOLUTION_TO_ID.items()}


def _require_hash(value: str) -> bytes:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ISQLValidationError("ISX_INVALID_REGISTRY_HASH")
    return bytes.fromhex(value)


def _uvarint_encode(value: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ISQLValidationError("ISX_UINT_REQUIRED")
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
            raise ISQLValidationError("TRUNCATED_ISX_VARINT")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            if pos - start > 1 and byte == 0:
                raise ISQLValidationError("NONCANONICAL_ISX_VARINT")
            return value, pos
        shift += 7
        if pos - start >= ISX_MAX_VARINT_BYTES:
            raise ISQLValidationError("ISX_VARINT_TOO_LARGE")


def _width_encode(width: int) -> bytes:
    if not isinstance(width, int) or isinstance(width, bool) or width < 0:
        raise ISQLValidationError("ISX_INVALID_BLOCK_WIDTH")
    if width > ISX_MAX_BIT_WIDTH:
        raise ISQLValidationError("ISX_VALUE_TOO_WIDE")
    if width < ISX_EXTENDED_WIDTH_MARKER:
        return bytes((width,))
    return bytes((ISX_EXTENDED_WIDTH_MARKER,)) + _uvarint_encode(width)


def _width_decode(data: bytes, pos: int) -> tuple[int, int]:
    if pos >= len(data):
        raise ISQLValidationError("TRUNCATED_ISX_BLOCK_WIDTH")
    first = data[pos]
    pos += 1
    if first != ISX_EXTENDED_WIDTH_MARKER:
        return first, pos
    width, pos = _uvarint_decode(data, pos)
    if width < ISX_EXTENDED_WIDTH_MARKER:
        raise ISQLValidationError("NONCANONICAL_ISX_EXTENDED_WIDTH")
    if width > ISX_MAX_BIT_WIDTH:
        raise ISQLValidationError("ISX_INVALID_BLOCK_WIDTH")
    return width, pos


def _pack_block(values: tuple[int, ...]) -> bytes:
    if not values or len(values) > ISX_BLOCK_SIZE:
        raise ISQLValidationError("ISX_INVALID_BLOCK_LENGTH")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ISQLValidationError("ISX_SEQUENCE_UINT_REQUIRED")
    width = max(values).bit_length()
    if width > ISX_MAX_BIT_WIDTH:
        raise ISQLValidationError("ISX_VALUE_TOO_WIDE")
    out = bytearray(_width_encode(width))
    if width == 0:
        return bytes(out)
    total_bits = width * len(values)
    padding = (-total_bits) % 8
    acc = 0
    for value in values:
        if value >= (1 << width):
            raise ISQLValidationError("ISX_VALUE_OUT_OF_BLOCK_RANGE")
        acc = (acc << width) | value
    acc <<= padding
    byte_count = (total_bits + 7) // 8
    out += acc.to_bytes(byte_count, "big")
    return bytes(out)


def _unpack_block(data: bytes, pos: int, count: int) -> tuple[tuple[int, ...], int]:
    if count <= 0 or count > ISX_BLOCK_SIZE:
        raise ISQLValidationError("ISX_INVALID_BLOCK_LENGTH")
    width_start = pos
    width, pos = _width_decode(data, pos)
    if width == 0:
        return (0,) * count, pos
    total_bits = width * count
    byte_count = (total_bits + 7) // 8
    if pos + byte_count > len(data):
        raise ISQLValidationError("TRUNCATED_ISX_BLOCK")
    raw = data[pos : pos + byte_count]
    pos += byte_count
    acc = int.from_bytes(raw, "big")
    padding = (-total_bits) % 8
    if padding:
        mask = (1 << padding) - 1
        if acc & mask:
            raise ISQLValidationError("ISX_NONZERO_PADDING_BITS")
        acc >>= padding
    mask = (1 << width) - 1
    values = []
    for index in range(count):
        shift = width * (count - 1 - index)
        values.append((acc >> shift) & mask)
    result = tuple(values)
    if max(result).bit_length() != width:
        raise ISQLValidationError("ISX_NONCANONICAL_BLOCK_WIDTH")
    if _pack_block(result) != data[width_start:pos]:
        raise ISQLValidationError("NONCANONICAL_ISX_BLOCK")
    return result, pos


def _encode_sequence(sequence: tuple[int, ...]) -> bytes:
    if not isinstance(sequence, tuple) or not sequence:
        raise ISQLValidationError("ISX_SEQUENCE_REQUIRED")
    if len(sequence) > ISX_MAX_SEQUENCE_ITEMS:
        raise ISQLValidationError("ISX_SEQUENCE_TOO_LONG")
    out = bytearray()
    for start in range(0, len(sequence), ISX_BLOCK_SIZE):
        out += _pack_block(sequence[start : start + ISX_BLOCK_SIZE])
    return bytes(out)


def _decode_sequence(data: bytes, pos: int, item_count: int) -> tuple[tuple[int, ...], int]:
    if item_count <= 0 or item_count > ISX_MAX_SEQUENCE_ITEMS:
        raise ISQLValidationError("ISX_INVALID_SEQUENCE_LENGTH")
    remaining = item_count
    values: list[int] = []
    while remaining:
        count = min(ISX_BLOCK_SIZE, remaining)
        block, pos = _unpack_block(data, pos, count)
        values.extend(block)
        remaining -= count
    return tuple(values), pos


@dataclass(frozen=True, slots=True)
class ISXBlockIndex:
    block_index: int
    item_start: int
    item_count: int
    encoded_offset: int
    encoded_length: int
    width_header_length: int
    bit_width: int


def _isx_body_and_sequence_start(frame: bytes) -> tuple[bytes, int, int]:
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("ISX_FRAME_BYTES_REQUIRED")
    data = bytes(frame)
    if len(data) < 4 + 4 + 32 + 1 + 32 + 1 + 1 + 4:
        raise ISQLValidationError("TRUNCATED_ISX_FRAME")
    body = data[:-4]
    actual = int.from_bytes(data[-4:], "big")
    expected = zlib.crc32(body) & 0xFFFFFFFF
    if actual != expected:
        raise ISQLValidationError("ISX_FRAME_CHECKSUM_MISMATCH")
    if not body.startswith(ISX_MAGIC):
        raise ISQLValidationError("INVALID_ISX_MAGIC")
    pos = len(ISX_MAGIC)
    version = body[pos]
    pos += 1
    if version != ISX_VERSION:
        raise ISQLValidationError("UNSUPPORTED_ISX_VERSION")
    kind = body[pos]
    pos += 1
    if kind != ISX_KIND_SPECTRAL_MEMORY:
        raise ISQLValidationError("UNSUPPORTED_ISX_KIND")
    resolution_id = body[pos]
    pos += 1
    if resolution_id not in _ID_TO_RESOLUTION:
        raise ISQLValidationError("ISX_UNSUPPORTED_RESOLUTION")
    flags = body[pos]
    pos += 1
    if flags != 0:
        raise ISQLValidationError("ISX_UNSUPPORTED_FLAGS")
    if pos + 32 > len(body):
        raise ISQLValidationError("TRUNCATED_ISX_ADDRESS")
    pos += 32
    _, pos = _uvarint_decode(body, pos)
    if pos + 32 > len(body):
        raise ISQLValidationError("TRUNCATED_ISX_REGISTRY_HASH")
    pos += 32
    item_count, pos = _uvarint_decode(body, pos)
    if item_count <= 0 or item_count > ISX_MAX_SEQUENCE_ITEMS:
        raise ISQLValidationError("ISX_INVALID_SEQUENCE_LENGTH")
    return body, pos, item_count


def index_isx_blocks(frame: bytes) -> tuple[ISXBlockIndex, ...]:
    body, pos, item_count = _isx_body_and_sequence_start(frame)
    out: list[ISXBlockIndex] = []
    remaining = item_count
    item_start = 0
    block_index = 0
    while remaining:
        count = min(ISX_BLOCK_SIZE, remaining)
        encoded_offset = pos
        width_start = pos
        width, pos = _width_decode(body, pos)
        width_header_length = pos - width_start
        byte_count = (width * count + 7) // 8 if width else 0
        if pos + byte_count > len(body):
            raise ISQLValidationError("TRUNCATED_ISX_BLOCK")
        pos += byte_count
        out.append(
            ISXBlockIndex(
                block_index=block_index,
                item_start=item_start,
                item_count=count,
                encoded_offset=encoded_offset,
                encoded_length=width_header_length + byte_count,
                width_header_length=width_header_length,
                bit_width=width,
            )
        )
        remaining -= count
        item_start += count
        block_index += 1
    if pos != len(body):
        raise ISQLValidationError("ISX_FRAME_TRAILING_BYTES")
    return tuple(out)


def decode_isx_sequence_block(frame: bytes, block_index: int) -> tuple[int, ...]:
    if not isinstance(block_index, int) or isinstance(block_index, bool) or block_index < 0:
        raise ISQLValidationError("ISX_INVALID_BLOCK_INDEX")
    body, _, _ = _isx_body_and_sequence_start(frame)
    blocks = index_isx_blocks(frame)
    if block_index >= len(blocks):
        raise ISQLValidationError("ISX_BLOCK_INDEX_OUT_OF_RANGE")
    block = blocks[block_index]
    values, end = _unpack_block(body, block.encoded_offset, block.item_count)
    if end != block.encoded_offset + block.encoded_length:
        raise ISQLValidationError("ISX_BLOCK_LENGTH_MISMATCH")
    return values


def decode_isx_sequence_range(frame: bytes, start_block: int, block_count: int) -> tuple[int, ...]:
    if (
        not isinstance(start_block, int)
        or isinstance(start_block, bool)
        or start_block < 0
        or not isinstance(block_count, int)
        or isinstance(block_count, bool)
        or block_count <= 0
    ):
        raise ISQLValidationError("ISX_INVALID_BLOCK_RANGE")
    blocks = index_isx_blocks(frame)
    if start_block >= len(blocks) or start_block + block_count > len(blocks):
        raise ISQLValidationError("ISX_BLOCK_RANGE_OUT_OF_RANGE")
    out: list[int] = []
    for index in range(start_block, start_block + block_count):
        out.extend(decode_isx_sequence_block(frame, index))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class ISXSpectralFrame:
    address_digest: bytes
    resolution: str
    registry_revision: int
    registry_hash: str
    sequence: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.address_digest, bytes) or len(self.address_digest) != 32:
            raise ISQLValidationError("ISX_ADDRESS_DIGEST_MUST_BE_32_BYTES")
        if self.resolution not in _RESOLUTION_TO_ID:
            raise ISQLValidationError("ISX_UNSUPPORTED_RESOLUTION")
        if not isinstance(self.registry_revision, int) or self.registry_revision < 0:
            raise ISQLValidationError("ISX_INVALID_REGISTRY_REVISION")
        _require_hash(self.registry_hash)
        if not isinstance(self.sequence, tuple) or not self.sequence:
            raise ISQLValidationError("ISX_SEQUENCE_REQUIRED")
        for value in self.sequence:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ISQLValidationError("ISX_SEQUENCE_UINT_REQUIRED")
            if value.bit_length() > ISX_MAX_BIT_WIDTH:
                raise ISQLValidationError("ISX_VALUE_TOO_WIDE")

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
        body = bytearray(ISX_MAGIC)
        body += bytes(
            (
                ISX_VERSION,
                ISX_KIND_SPECTRAL_MEMORY,
                _RESOLUTION_TO_ID[self.resolution],
                0,
            )
        )
        body += self.address_digest
        body += _uvarint_encode(self.registry_revision)
        body += _require_hash(self.registry_hash)
        body += _uvarint_encode(len(self.sequence))
        body += _encode_sequence(self.sequence)
        checksum = zlib.crc32(body) & 0xFFFFFFFF
        return bytes(body) + checksum.to_bytes(4, "big")


def encode_isx_spectral_frame(address: ISQLCode, packet: SpectralPacket, resolution: str) -> bytes:
    if not isinstance(packet, SpectralPacket):
        raise ISQLValidationError("ISX_SPECTRAL_PACKET_REQUIRED")
    if packet.registry_id != SPECTRAL_REGISTRY_ID:
        raise ISQLValidationError("ISX_UNSUPPORTED_REGISTRY_ID")
    frame = ISXSpectralFrame(
        address_digest=address_code_to_digest(address),
        resolution=resolution,
        registry_revision=packet.registry_revision,
        registry_hash=packet.registry_hash,
        sequence=packet.sequence,
    )
    return frame.to_bytes()


def decode_isx_spectral_frame(frame: bytes) -> ISXSpectralFrame:
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("ISX_FRAME_BYTES_REQUIRED")
    data = bytes(frame)
    body, pos, item_count = _isx_body_and_sequence_start(data)
    header_pos = len(ISX_MAGIC) + 4
    address_digest = body[header_pos : header_pos + 32]
    pos_meta = header_pos + 32
    registry_revision, pos_meta = _uvarint_decode(body, pos_meta)
    registry_hash = body[pos_meta : pos_meta + 32].hex()
    pos_meta += 32
    decoded_item_count, pos_meta = _uvarint_decode(body, pos_meta)
    if decoded_item_count != item_count or pos_meta != pos:
        raise ISQLValidationError("ISX_INTERNAL_HEADER_MISMATCH")
    resolution_id = body[len(ISX_MAGIC) + 2]
    resolution = _ID_TO_RESOLUTION.get(resolution_id)
    if resolution is None:
        raise ISQLValidationError("ISX_UNSUPPORTED_RESOLUTION")
    sequence, end = _decode_sequence(body, pos, item_count)
    if end != len(body):
        raise ISQLValidationError("ISX_FRAME_TRAILING_BYTES")
    result = ISXSpectralFrame(
        address_digest=address_digest,
        resolution=resolution,
        registry_revision=registry_revision,
        registry_hash=registry_hash,
        sequence=sequence,
    )
    if result.to_bytes() != data:
        raise ISQLValidationError("NONCANONICAL_ISX_FRAME")
    return result


def inspect_isx_frame(frame: bytes) -> dict[str, object]:
    parsed = decode_isx_spectral_frame(frame)
    blocks = index_isx_blocks(frame)
    return {
        "schema": "isql.experimental-native-frame-info/isx1",
        "experimental": True,
        "version": ISX_VERSION,
        "kind": "spectral-memory",
        "resolution": parsed.resolution,
        "address_sha256": parsed.address_digest.hex(),
        "registry_revision": parsed.registry_revision,
        "registry_hash": parsed.registry_hash,
        "sequence_items": len(parsed.sequence),
        "max_coordinate": max(parsed.sequence),
        "max_bit_width": max(block.bit_width for block in blocks),
        "frame_bytes": len(frame),
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
    }
