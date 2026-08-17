from __future__ import annotations

from dataclasses import dataclass
import hashlib
import zlib

from .errors import ISQLValidationError
from .native import (
    NATIVE_BLOCK_SIZE,
    NATIVE_MAX_BIT_WIDTH,
    NativeSpectralFrame,
    _ID_TO_RESOLUTION,
    _RESOLUTION_TO_ID,
    _pack_block,
    _unpack_block,
    _uvarint_decode,
    _uvarint_encode,
    _native_body_and_sequence_start,
    decode_native_sequence_block,
    decode_native_spectral_frame,
)

DELTA_MAGIC = b"ISD8"
DELTA_VERSION = 8
DELTA_KIND_SPECTRAL_MEMORY = 1
DELTA_FLAG_REGISTRY_OVERRIDE = 0x01
DELTA_MODE_COPY = 0
DELTA_MODE_DELTA = 1
DELTA_MODE_REPLACE = 2
DELTA_MAX_BIT_WIDTH = NATIVE_MAX_BIT_WIDTH + 1


@dataclass(frozen=True, slots=True)
class DeltaBlockIndex:
    block_index: int
    item_start: int
    item_count: int
    mode: int
    payload_offset: int
    payload_length: int


@dataclass(frozen=True, slots=True)
class ParsedDeltaHeader:
    resolution: str
    target_address_digest: bytes
    base_frame_sha256: bytes
    registry_override: bool
    registry_revision: int | None
    registry_hash: str | None
    item_count: int
    blocks: tuple[DeltaBlockIndex, ...]
    body: bytes


def _zigzag_encode(value: int) -> int:
    return value * 2 if value >= 0 else (-value * 2) - 1


def _zigzag_decode(value: int) -> int:
    return value // 2 if value % 2 == 0 else -((value // 2) + 1)


def _pack_uint_block(values: tuple[int, ...], *, max_width: int) -> bytes:
    if not values or len(values) > NATIVE_BLOCK_SIZE:
        raise ISQLValidationError("DELTA_INVALID_BLOCK_LENGTH")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ISQLValidationError("DELTA_UINT_REQUIRED")
    width = max(values).bit_length()
    if width > max_width:
        raise ISQLValidationError("DELTA_VALUE_TOO_WIDE")
    out = bytearray((width,))
    if width == 0:
        return bytes(out)
    total_bits = width * len(values)
    padding = (-total_bits) % 8
    acc = 0
    for value in values:
        acc = (acc << width) | value
    acc <<= padding
    out += acc.to_bytes((total_bits + 7) // 8, "big")
    return bytes(out)


def _unpack_uint_block(payload: bytes, count: int, *, max_width: int) -> tuple[int, ...]:
    if count <= 0 or count > NATIVE_BLOCK_SIZE:
        raise ISQLValidationError("DELTA_INVALID_BLOCK_LENGTH")
    if not payload:
        raise ISQLValidationError("TRUNCATED_DELTA_BLOCK")
    width = payload[0]
    if width > max_width:
        raise ISQLValidationError("DELTA_INVALID_BLOCK_WIDTH")
    if width == 0:
        if len(payload) != 1:
            raise ISQLValidationError("DELTA_BLOCK_TRAILING_BYTES")
        return (0,) * count
    total_bits = width * count
    byte_count = (total_bits + 7) // 8
    if len(payload) != 1 + byte_count:
        raise ISQLValidationError("DELTA_BLOCK_LENGTH_MISMATCH")
    acc = int.from_bytes(payload[1:], "big")
    padding = (-total_bits) % 8
    if padding:
        mask = (1 << padding) - 1
        if acc & mask:
            raise ISQLValidationError("DELTA_NONZERO_PADDING_BITS")
        acc >>= padding
    mask = (1 << width) - 1
    values = []
    for index in range(count):
        shift = width * (count - 1 - index)
        values.append((acc >> shift) & mask)
    if max(values).bit_length() != width:
        raise ISQLValidationError("DELTA_NONCANONICAL_BLOCK_WIDTH")
    return tuple(values)


def _delta_payload(base: tuple[int, ...], target: tuple[int, ...]) -> bytes:
    if len(base) != len(target):
        raise ISQLValidationError("DELTA_BLOCK_LENGTH_MISMATCH")
    encoded = tuple(_zigzag_encode(t - b) for b, t in zip(base, target))
    return _pack_uint_block(encoded, max_width=DELTA_MAX_BIT_WIDTH)


def _decode_delta_payload(payload: bytes, base: tuple[int, ...]) -> tuple[int, ...]:
    encoded = _unpack_uint_block(payload, len(base), max_width=DELTA_MAX_BIT_WIDTH)
    out = []
    for base_value, raw in zip(base, encoded):
        value = base_value + _zigzag_decode(raw)
        if value < 0 or value.bit_length() > NATIVE_MAX_BIT_WIDTH:
            raise ISQLValidationError("DELTA_RECONSTRUCTED_VALUE_OUT_OF_RANGE")
        out.append(value)
    return tuple(out)


def _replace_payload(target: tuple[int, ...]) -> bytes:
    return _pack_block(target)


def _decode_replace_payload(payload: bytes, count: int) -> tuple[int, ...]:
    values, pos = _unpack_block(payload, 0, count)
    if pos != len(payload):
        raise ISQLValidationError("DELTA_REPLACE_TRAILING_BYTES")
    return values


def _choose_mode(base: tuple[int, ...] | None, target: tuple[int, ...]) -> tuple[int, bytes]:
    replace = _replace_payload(target)
    if base is not None and len(base) == len(target):
        if base == target:
            return DELTA_MODE_COPY, b""
        delta = _delta_payload(base, target)
        if len(delta) < len(replace):
            return DELTA_MODE_DELTA, delta
    return DELTA_MODE_REPLACE, replace



@dataclass(frozen=True, slots=True)
class _BaseNativeMeta:
    resolution: str
    registry_revision: int
    registry_hash: str
    item_count: int


def _base_native_meta(base_frame: bytes) -> _BaseNativeMeta:
    body, _, item_count = _native_body_and_sequence_start(base_frame)
    resolution_id = body[6]
    resolution = _ID_TO_RESOLUTION.get(resolution_id)
    if resolution is None:
        raise ISQLValidationError("DELTA_RESOLUTION_MISMATCH")
    pos = 8 + 32
    registry_revision, pos = _uvarint_decode(body, pos)
    if pos + 32 > len(body):
        raise ISQLValidationError("TRUNCATED_NATIVE_REGISTRY_HASH")
    registry_hash = body[pos : pos + 32].hex()
    return _BaseNativeMeta(
        resolution=resolution,
        registry_revision=registry_revision,
        registry_hash=registry_hash,
        item_count=item_count,
    )


def _base_block_for_target(base_frame: bytes, block_index: int, target_count: int) -> tuple[int, ...] | None:
    meta = _base_native_meta(base_frame)
    start = block_index * NATIVE_BLOCK_SIZE
    if start >= meta.item_count:
        return None
    try:
        block = decode_native_sequence_block(base_frame, block_index)
    except ISQLValidationError:
        return None
    sliced = tuple(block[:target_count])
    return sliced if len(sliced) == target_count else None


def encode_delta_frame(base_frame: bytes, target_frame: bytes) -> bytes:
    base = decode_native_spectral_frame(base_frame)
    target = decode_native_spectral_frame(target_frame)
    if base.resolution != target.resolution:
        raise ISQLValidationError("DELTA_RESOLUTION_MISMATCH")

    registry_override = (
        base.registry_revision != target.registry_revision
        or base.registry_hash != target.registry_hash
    )
    flags = DELTA_FLAG_REGISTRY_OVERRIDE if registry_override else 0

    directory: list[tuple[int, int]] = []
    payloads: list[bytes] = []
    for start in range(0, len(target.sequence), NATIVE_BLOCK_SIZE):
        target_block = target.sequence[start : start + NATIVE_BLOCK_SIZE]
        base_slice = base.sequence[start : start + len(target_block)]
        base_block = tuple(base_slice) if len(base_slice) == len(target_block) else None
        mode, payload = _choose_mode(base_block, tuple(target_block))
        directory.append((mode, len(payload)))
        payloads.append(payload)

    body = bytearray(DELTA_MAGIC)
    body += bytes((DELTA_VERSION, DELTA_KIND_SPECTRAL_MEMORY, _RESOLUTION_TO_ID[target.resolution], flags))
    body += target.address_digest
    body += hashlib.sha256(bytes(base_frame)).digest()
    if registry_override:
        body += _uvarint_encode(target.registry_revision)
        body += bytes.fromhex(target.registry_hash)
    body += _uvarint_encode(len(target.sequence))
    for mode, payload_len in directory:
        body.append(mode)
        body += _uvarint_encode(payload_len)
    for payload in payloads:
        body += payload
    checksum = zlib.crc32(body) & 0xFFFFFFFF
    return bytes(body) + checksum.to_bytes(4, "big")


def _parse_delta_header(frame: bytes, base_frame: bytes) -> ParsedDeltaHeader:
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("DELTA_FRAME_BYTES_REQUIRED")
    data = bytes(frame)
    if len(data) < 4 + 4 + 32 + 32 + 1 + 2 + 4:
        raise ISQLValidationError("TRUNCATED_DELTA_FRAME")
    body = data[:-4]
    actual = int.from_bytes(data[-4:], "big")
    expected = zlib.crc32(body) & 0xFFFFFFFF
    if actual != expected:
        raise ISQLValidationError("DELTA_FRAME_CHECKSUM_MISMATCH")
    if not body.startswith(DELTA_MAGIC):
        raise ISQLValidationError("INVALID_DELTA_MAGIC")

    base_meta = _base_native_meta(base_frame)
    pos = len(DELTA_MAGIC)
    version = body[pos]
    pos += 1
    if version != DELTA_VERSION:
        raise ISQLValidationError("UNSUPPORTED_DELTA_VERSION")
    kind = body[pos]
    pos += 1
    if kind != DELTA_KIND_SPECTRAL_MEMORY:
        raise ISQLValidationError("UNSUPPORTED_DELTA_KIND")
    resolution_id = body[pos]
    pos += 1
    resolution = _ID_TO_RESOLUTION.get(resolution_id)
    if resolution is None or resolution != base_meta.resolution:
        raise ISQLValidationError("DELTA_RESOLUTION_MISMATCH")
    flags = body[pos]
    pos += 1
    if flags & ~DELTA_FLAG_REGISTRY_OVERRIDE:
        raise ISQLValidationError("DELTA_UNSUPPORTED_FLAGS")
    registry_override = bool(flags & DELTA_FLAG_REGISTRY_OVERRIDE)

    if pos + 64 > len(body):
        raise ISQLValidationError("TRUNCATED_DELTA_FIXED_HEADER")
    target_address_digest = body[pos : pos + 32]
    pos += 32
    base_frame_sha256 = body[pos : pos + 32]
    pos += 32
    if base_frame_sha256 != hashlib.sha256(bytes(base_frame)).digest():
        raise ISQLValidationError("DELTA_BASE_FRAME_HASH_MISMATCH")

    registry_revision: int | None = None
    registry_hash: str | None = None
    if registry_override:
        registry_revision, pos = _uvarint_decode(body, pos)
        if pos + 32 > len(body):
            raise ISQLValidationError("TRUNCATED_DELTA_REGISTRY_HASH")
        registry_hash = body[pos : pos + 32].hex()
        pos += 32

    item_count, pos = _uvarint_decode(body, pos)
    if item_count <= 0:
        raise ISQLValidationError("DELTA_INVALID_SEQUENCE_LENGTH")
    block_count = (item_count + NATIVE_BLOCK_SIZE - 1) // NATIVE_BLOCK_SIZE

    directory_raw: list[tuple[int, int, int, int]] = []
    remaining = item_count
    item_start = 0
    for block_index in range(block_count):
        if pos >= len(body):
            raise ISQLValidationError("TRUNCATED_DELTA_DIRECTORY")
        mode = body[pos]
        pos += 1
        if mode not in (DELTA_MODE_COPY, DELTA_MODE_DELTA, DELTA_MODE_REPLACE):
            raise ISQLValidationError("DELTA_INVALID_BLOCK_MODE")
        payload_len, pos = _uvarint_decode(body, pos)
        count = min(NATIVE_BLOCK_SIZE, remaining)
        if mode == DELTA_MODE_COPY and payload_len != 0:
            raise ISQLValidationError("DELTA_COPY_PAYLOAD_MUST_BE_EMPTY")
        if mode != DELTA_MODE_COPY and payload_len <= 0:
            raise ISQLValidationError("DELTA_BLOCK_PAYLOAD_REQUIRED")
        directory_raw.append((mode, payload_len, item_start, count))
        remaining -= count
        item_start += count

    blocks: list[DeltaBlockIndex] = []
    payload_pos = pos
    for block_index, (mode, payload_len, item_start, count) in enumerate(directory_raw):
        if payload_pos + payload_len > len(body):
            raise ISQLValidationError("TRUNCATED_DELTA_PAYLOAD")
        blocks.append(DeltaBlockIndex(
            block_index=block_index,
            item_start=item_start,
            item_count=count,
            mode=mode,
            payload_offset=payload_pos,
            payload_length=payload_len,
        ))
        payload_pos += payload_len
    if payload_pos != len(body):
        raise ISQLValidationError("DELTA_FRAME_TRAILING_BYTES")

    return ParsedDeltaHeader(
        resolution=resolution,
        target_address_digest=target_address_digest,
        base_frame_sha256=base_frame_sha256,
        registry_override=registry_override,
        registry_revision=registry_revision,
        registry_hash=registry_hash,
        item_count=item_count,
        blocks=tuple(blocks),
        body=body,
    )


def _decode_target_block(parsed: ParsedDeltaHeader, base_frame: bytes, block: DeltaBlockIndex) -> tuple[int, ...]:
    count = block.item_count
    base_block = _base_block_for_target(base_frame, block.block_index, count)
    payload = parsed.body[block.payload_offset : block.payload_offset + block.payload_length]

    if block.mode == DELTA_MODE_COPY:
        if base_block is None:
            raise ISQLValidationError("DELTA_COPY_BASE_BLOCK_MISSING")
        target = base_block
    elif block.mode == DELTA_MODE_DELTA:
        if base_block is None:
            raise ISQLValidationError("DELTA_MODE_BASE_BLOCK_MISSING")
        target = _decode_delta_payload(payload, base_block)
    else:
        target = _decode_replace_payload(payload, count)

    canonical_mode, canonical_payload = _choose_mode(base_block, target)
    if block.mode != canonical_mode or payload != canonical_payload:
        raise ISQLValidationError("NONCANONICAL_DELTA_BLOCK")
    return target


def decode_delta_frame(frame: bytes, base_frame: bytes) -> NativeSpectralFrame:
    parsed = _parse_delta_header(frame, base_frame)
    base_meta = _base_native_meta(base_frame)
    values: list[int] = []
    for block in parsed.blocks:
        values.extend(_decode_target_block(parsed, base_frame, block))
    revision = parsed.registry_revision if parsed.registry_override else base_meta.registry_revision
    registry_hash = parsed.registry_hash if parsed.registry_override else base_meta.registry_hash
    result = NativeSpectralFrame(
        address_digest=parsed.target_address_digest,
        resolution=parsed.resolution,
        registry_revision=int(revision),
        registry_hash=str(registry_hash),
        sequence=tuple(values),
    )
    if encode_delta_frame(base_frame, result.to_bytes()) != bytes(frame):
        raise ISQLValidationError("NONCANONICAL_DELTA_FRAME")
    return result



def index_delta_blocks(frame: bytes, base_frame: bytes) -> tuple[DeltaBlockIndex, ...]:
    return _parse_delta_header(frame, base_frame).blocks


def decode_delta_block(frame: bytes, base_frame: bytes, block_index: int) -> tuple[int, ...]:
    if not isinstance(block_index, int) or isinstance(block_index, bool) or block_index < 0:
        raise ISQLValidationError("DELTA_INVALID_BLOCK_INDEX")
    parsed = _parse_delta_header(frame, base_frame)
    if block_index >= len(parsed.blocks):
        raise ISQLValidationError("DELTA_BLOCK_INDEX_OUT_OF_RANGE")
    return _decode_target_block(parsed, base_frame, parsed.blocks[block_index])


def decode_delta_range(frame: bytes, base_frame: bytes, start_block: int, block_count: int) -> tuple[int, ...]:
    if (
        not isinstance(start_block, int)
        or isinstance(start_block, bool)
        or start_block < 0
        or not isinstance(block_count, int)
        or isinstance(block_count, bool)
        or block_count <= 0
    ):
        raise ISQLValidationError("DELTA_INVALID_BLOCK_RANGE")
    parsed = _parse_delta_header(frame, base_frame)
    if start_block >= len(parsed.blocks) or start_block + block_count > len(parsed.blocks):
        raise ISQLValidationError("DELTA_BLOCK_RANGE_OUT_OF_RANGE")
    out: list[int] = []
    for index in range(start_block, start_block + block_count):
        out.extend(_decode_target_block(parsed, base_frame, parsed.blocks[index]))
    return tuple(out)


def inspect_delta_frame(frame: bytes, base_frame: bytes) -> dict[str, object]:
    parsed = _parse_delta_header(frame, base_frame)
    # Full decode is intentional here: inspection is also a canonicality check.
    target = decode_delta_frame(frame, base_frame)
    counts = {"copy": 0, "delta": 0, "replace": 0}
    for block in parsed.blocks:
        if block.mode == DELTA_MODE_COPY:
            counts["copy"] += 1
        elif block.mode == DELTA_MODE_DELTA:
            counts["delta"] += 1
        else:
            counts["replace"] += 1
    return {
        "schema": "isql.delta-frame-info/v0.8",
        "version": DELTA_VERSION,
        "kind": "spectral-memory-delta",
        "resolution": parsed.resolution,
        "target_address_sha256": parsed.target_address_digest.hex(),
        "base_frame_sha256": parsed.base_frame_sha256.hex(),
        "registry_override": parsed.registry_override,
        "registry_revision": target.registry_revision,
        "registry_hash": target.registry_hash,
        "sequence_items": parsed.item_count,
        "block_count": len(parsed.blocks),
        "mode_counts": counts,
        "frame_bytes": len(frame),
        "frame_sha256": hashlib.sha256(bytes(frame)).hexdigest(),
    }

@dataclass(frozen=True, slots=True)
class LocalityCompileResult:
    mode: str
    frame: bytes
    standalone_frame: bytes
    standalone_frame_bytes: int
    delta_candidate_bytes: int
    selected_frame_bytes: int
    bytes_saved_vs_standalone: int
    selected_ratio: float
    base_frame_sha256: str
    target_native_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "isql.locality-compile/v0.8",
            "mode": self.mode,
            "standalone_frame_bytes": self.standalone_frame_bytes,
            "delta_candidate_bytes": self.delta_candidate_bytes,
            "selected_frame_bytes": self.selected_frame_bytes,
            "bytes_saved_vs_standalone": self.bytes_saved_vs_standalone,
            "selected_ratio": self.selected_ratio,
            "base_frame_sha256": self.base_frame_sha256,
            "target_native_sha256": self.target_native_sha256,
        }


def compile_locality_memory(base_frame: bytes, target_record: "MemoryRecord", resolution: str = "R2") -> LocalityCompileResult:
    from .memory import MemoryRecord
    from .native import compile_native_memory

    if not isinstance(target_record, MemoryRecord):
        raise ISQLValidationError("LOCALITY_MEMORY_RECORD_REQUIRED")
    target_native = compile_native_memory(target_record, resolution=resolution).frame
    delta_candidate = encode_delta_frame(base_frame, target_native)
    if len(delta_candidate) < len(target_native):
        mode = "delta"
        selected = delta_candidate
    else:
        mode = "native"
        selected = target_native
    saved = len(target_native) - len(selected)
    return LocalityCompileResult(
        mode=mode,
        frame=selected,
        standalone_frame=target_native,
        standalone_frame_bytes=len(target_native),
        delta_candidate_bytes=len(delta_candidate),
        selected_frame_bytes=len(selected),
        bytes_saved_vs_standalone=saved,
        selected_ratio=len(selected) / len(target_native),
        base_frame_sha256=hashlib.sha256(bytes(base_frame)).hexdigest(),
        target_native_sha256=hashlib.sha256(target_native).hexdigest(),
    )
