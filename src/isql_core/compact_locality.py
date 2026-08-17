from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import zlib
from typing import Iterable

from .errors import ISQLValidationError
from .locality import (
    LocalityBlockSignature,
    LocalityIndex,
    LocalityIndexEntry,
    build_locality_index,
)
from .native import _uvarint_decode, _uvarint_encode

COMPACT_LOCALITY_MAGIC = b"ILI1"
COMPACT_LOCALITY_VERSION = 1
_RESOLUTION_TO_ID = {"R1": 1, "R2": 2}
_ID_TO_RESOLUTION = {value: key for key, value in _RESOLUTION_TO_ID.items()}


def _hash_bytes(value: str, code: str) -> bytes:
    if not isinstance(value, str) or len(value) != 64:
        raise ISQLValidationError(code)
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ISQLValidationError(code) from exc
    if len(raw) != 32:
        raise ISQLValidationError(code)
    return raw


def _read_exact(data: bytes, pos: int, size: int, code: str) -> tuple[bytes, int]:
    end = pos + size
    if end > len(data):
        raise ISQLValidationError(code)
    return data[pos:end], end


@dataclass(frozen=True, slots=True, order=True)
class CompactRegistryBinding:
    revision: int
    registry_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 0:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_REGISTRY_REVISION")
        _hash_bytes(self.registry_hash, "COMPACT_LOCALITY_INVALID_REGISTRY_HASH")


@dataclass(frozen=True, slots=True)
class CompactLocalityEntry:
    frame_ref: str
    frame_sha256: str
    address_sha256: str
    resolution: str
    registry_binding_id: int
    item_count: int
    frame_bytes: int
    blocks: tuple[LocalityBlockSignature, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.frame_ref, str) or not self.frame_ref:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_FRAME_REF")
        try:
            encoded = self.frame_ref.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_FRAME_REF") from exc
        if b"\x00" in encoded or "\\" in self.frame_ref:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_FRAME_REF")
        parts = self.frame_ref.split("/")
        if self.frame_ref.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_FRAME_REF")
        _hash_bytes(self.frame_sha256, "COMPACT_LOCALITY_INVALID_FRAME_HASH")
        _hash_bytes(self.address_sha256, "COMPACT_LOCALITY_INVALID_ADDRESS_HASH")
        if self.resolution not in _RESOLUTION_TO_ID:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_RESOLUTION")
        if not isinstance(self.registry_binding_id, int) or isinstance(self.registry_binding_id, bool) or self.registry_binding_id < 0:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_REGISTRY_BINDING_ID")
        if not isinstance(self.item_count, int) or isinstance(self.item_count, bool) or self.item_count <= 0:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_ITEM_COUNT")
        if not isinstance(self.frame_bytes, int) or isinstance(self.frame_bytes, bool) or self.frame_bytes <= 0:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_FRAME_BYTES")
        expected_blocks = (self.item_count + 15) // 16
        if len(self.blocks) != expected_blocks:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_BLOCK_COUNT")
        for index, block in enumerate(self.blocks):
            if block.block_index != index:
                raise ISQLValidationError("COMPACT_LOCALITY_NONCANONICAL_BLOCK_ORDER")


@dataclass(frozen=True, slots=True)
class CompactLocalityIndex:
    registry_bindings: tuple[CompactRegistryBinding, ...]
    entries: tuple[CompactLocalityEntry, ...]

    def __post_init__(self) -> None:
        if tuple(sorted(self.registry_bindings)) != self.registry_bindings:
            raise ISQLValidationError("COMPACT_LOCALITY_NONCANONICAL_REGISTRY_ORDER")
        if len(set(self.registry_bindings)) != len(self.registry_bindings):
            raise ISQLValidationError("COMPACT_LOCALITY_DUPLICATE_REGISTRY_BINDING")
        refs = [entry.frame_ref for entry in self.entries]
        if len(refs) != len(set(refs)):
            raise ISQLValidationError("COMPACT_LOCALITY_DUPLICATE_FRAME_REF")
        if tuple(sorted(self.entries, key=lambda e: (e.frame_ref, e.frame_sha256))) != self.entries:
            raise ISQLValidationError("COMPACT_LOCALITY_NONCANONICAL_ENTRY_ORDER")
        for entry in self.entries:
            if entry.registry_binding_id >= len(self.registry_bindings):
                raise ISQLValidationError("COMPACT_LOCALITY_REGISTRY_BINDING_OUT_OF_RANGE")

    @classmethod
    def from_legacy(cls, index: LocalityIndex) -> "CompactLocalityIndex":
        if not isinstance(index, LocalityIndex):
            raise ISQLValidationError("LOCALITY_INDEX_REQUIRED")
        bindings = tuple(sorted({
            CompactRegistryBinding(entry.registry_revision, entry.registry_hash)
            for entry in index.entries
        }))
        binding_ids = {binding: idx for idx, binding in enumerate(bindings)}
        entries = []
        for entry in index.entries:
            binding = CompactRegistryBinding(entry.registry_revision, entry.registry_hash)
            entries.append(CompactLocalityEntry(
                frame_ref=entry.frame_ref,
                frame_sha256=entry.frame_sha256,
                address_sha256=entry.address_sha256,
                resolution=entry.resolution,
                registry_binding_id=binding_ids[binding],
                item_count=entry.item_count,
                frame_bytes=entry.frame_bytes,
                blocks=entry.blocks,
            ))
        entries.sort(key=lambda e: (e.frame_ref, e.frame_sha256))
        return cls(registry_bindings=bindings, entries=tuple(entries))

    def to_legacy(self) -> LocalityIndex:
        rows = []
        for entry in self.entries:
            binding = self.registry_bindings[entry.registry_binding_id]
            rows.append(LocalityIndexEntry(
                frame_ref=entry.frame_ref,
                frame_sha256=entry.frame_sha256,
                address_sha256=entry.address_sha256,
                resolution=entry.resolution,
                registry_revision=binding.revision,
                registry_hash=binding.registry_hash,
                item_count=entry.item_count,
                frame_bytes=entry.frame_bytes,
                blocks=entry.blocks,
            ))
        return LocalityIndex(entries=tuple(rows))

    def to_bytes(self) -> bytes:
        body = bytearray(COMPACT_LOCALITY_MAGIC)
        body.append(COMPACT_LOCALITY_VERSION)
        body += _uvarint_encode(len(self.registry_bindings))
        for binding in self.registry_bindings:
            body += _uvarint_encode(binding.revision)
            body += _hash_bytes(binding.registry_hash, "COMPACT_LOCALITY_INVALID_REGISTRY_HASH")
        body += _uvarint_encode(len(self.entries))
        for entry in self.entries:
            ref = entry.frame_ref.encode("utf-8")
            body += _uvarint_encode(len(ref))
            body += ref
            body += _hash_bytes(entry.frame_sha256, "COMPACT_LOCALITY_INVALID_FRAME_HASH")
            body += _hash_bytes(entry.address_sha256, "COMPACT_LOCALITY_INVALID_ADDRESS_HASH")
            body.append(_RESOLUTION_TO_ID[entry.resolution])
            body += _uvarint_encode(entry.registry_binding_id)
            body += _uvarint_encode(entry.item_count)
            body += _uvarint_encode(entry.frame_bytes)
            body += _uvarint_encode(len(entry.blocks))
            for block in entry.blocks:
                body += _uvarint_encode(block.item_count)
                body += bytes.fromhex(block.fingerprint)
                body += _uvarint_encode(block.value_sum)
                body += _uvarint_encode(block.value_max)
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return bytes(body) + crc.to_bytes(4, "big")

    @classmethod
    def from_bytes(cls, raw: bytes) -> "CompactLocalityIndex":
        if not isinstance(raw, (bytes, bytearray, memoryview)):
            raise ISQLValidationError("COMPACT_LOCALITY_BYTES_REQUIRED")
        data = bytes(raw)
        if len(data) < len(COMPACT_LOCALITY_MAGIC) + 1 + 1 + 1 + 4:
            raise ISQLValidationError("TRUNCATED_COMPACT_LOCALITY_INDEX")
        body = data[:-4]
        actual_crc = int.from_bytes(data[-4:], "big")
        if (zlib.crc32(body) & 0xFFFFFFFF) != actual_crc:
            raise ISQLValidationError("COMPACT_LOCALITY_CRC_MISMATCH")
        if not body.startswith(COMPACT_LOCALITY_MAGIC):
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_MAGIC")
        pos = len(COMPACT_LOCALITY_MAGIC)
        version = body[pos]
        pos += 1
        if version != COMPACT_LOCALITY_VERSION:
            raise ISQLValidationError("COMPACT_LOCALITY_UNSUPPORTED_VERSION")

        registry_count, pos = _uvarint_decode(body, pos)
        bindings = []
        for _ in range(registry_count):
            revision, pos = _uvarint_decode(body, pos)
            hash_bytes, pos = _read_exact(body, pos, 32, "TRUNCATED_COMPACT_LOCALITY_REGISTRY_HASH")
            bindings.append(CompactRegistryBinding(revision=revision, registry_hash=hash_bytes.hex()))

        entry_count, pos = _uvarint_decode(body, pos)
        entries = []
        for _ in range(entry_count):
            ref_len, pos = _uvarint_decode(body, pos)
            ref_bytes, pos = _read_exact(body, pos, ref_len, "TRUNCATED_COMPACT_LOCALITY_FRAME_REF")
            try:
                frame_ref = ref_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ISQLValidationError("COMPACT_LOCALITY_INVALID_FRAME_REF_UTF8") from exc
            frame_hash, pos = _read_exact(body, pos, 32, "TRUNCATED_COMPACT_LOCALITY_FRAME_HASH")
            address_hash, pos = _read_exact(body, pos, 32, "TRUNCATED_COMPACT_LOCALITY_ADDRESS_HASH")
            resolution_raw, pos = _read_exact(body, pos, 1, "TRUNCATED_COMPACT_LOCALITY_RESOLUTION")
            resolution = _ID_TO_RESOLUTION.get(resolution_raw[0])
            if resolution is None:
                raise ISQLValidationError("COMPACT_LOCALITY_INVALID_RESOLUTION")
            binding_id, pos = _uvarint_decode(body, pos)
            item_count, pos = _uvarint_decode(body, pos)
            frame_bytes, pos = _uvarint_decode(body, pos)
            block_count, pos = _uvarint_decode(body, pos)
            blocks = []
            for block_index in range(block_count):
                block_items, pos = _uvarint_decode(body, pos)
                fingerprint, pos = _read_exact(body, pos, 8, "TRUNCATED_COMPACT_LOCALITY_BLOCK_FINGERPRINT")
                value_sum, pos = _uvarint_decode(body, pos)
                value_max, pos = _uvarint_decode(body, pos)
                blocks.append(LocalityBlockSignature(
                    block_index=block_index,
                    item_count=block_items,
                    fingerprint=fingerprint.hex(),
                    value_sum=value_sum,
                    value_max=value_max,
                ))
            entries.append(CompactLocalityEntry(
                frame_ref=frame_ref,
                frame_sha256=frame_hash.hex(),
                address_sha256=address_hash.hex(),
                resolution=resolution,
                registry_binding_id=binding_id,
                item_count=item_count,
                frame_bytes=frame_bytes,
                blocks=tuple(blocks),
            ))
        if pos != len(body):
            raise ISQLValidationError("COMPACT_LOCALITY_TRAILING_BYTES")
        value = cls(registry_bindings=tuple(bindings), entries=tuple(entries))
        if value.to_bytes() != data:
            raise ISQLValidationError("COMPACT_LOCALITY_NONCANONICAL_ENCODING")
        return value

    def content_hash(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


def build_compact_locality_index(frames: Iterable[tuple[str, bytes]]) -> CompactLocalityIndex:
    return CompactLocalityIndex.from_legacy(build_locality_index(frames))


def save_compact_locality_index(path: str | Path, index: CompactLocalityIndex) -> None:
    if not isinstance(index, CompactLocalityIndex):
        raise ISQLValidationError("COMPACT_LOCALITY_INDEX_REQUIRED")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(index.to_bytes())


def load_compact_locality_index(path: str | Path) -> CompactLocalityIndex:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise ISQLValidationError("COMPACT_LOCALITY_INDEX_READ_FAILED") from exc
    return CompactLocalityIndex.from_bytes(raw)

from bisect import bisect_left
from collections import Counter, defaultdict
from functools import lru_cache

from .locality import LocalityCandidate, signature_from_native


@dataclass(frozen=True, slots=True)
class CompactRecallResult:
    candidates: tuple[LocalityCandidate, ...]
    index_probe_count: int
    entry_count: int
    probe_ratio: float

    def __post_init__(self) -> None:
        if self.index_probe_count < 0 or self.entry_count < 0 or self.index_probe_count > self.entry_count:
            raise ISQLValidationError("COMPACT_LOCALITY_INVALID_PROBE_COUNTS")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "isql.compact-locality-recall/v1.0",
            "entry_count": self.entry_count,
            "index_probe_count": self.index_probe_count,
            "probe_ratio": self.probe_ratio,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@dataclass(slots=True)
class _CompactSearchRuntime:
    exact_postings: dict[tuple[str, int, str], tuple[int, ...]]
    registry_rows: dict[tuple[str, int, str], tuple[tuple[int, str, int], ...]]
    resolution_rows: dict[str, tuple[tuple[int, str, int], ...]]
    total_sums: tuple[int, ...]
    frame_hash_to_id: dict[str, int]


@lru_cache(maxsize=16)
def _search_runtime(index: CompactLocalityIndex) -> _CompactSearchRuntime:
    exact: dict[tuple[str, int, str], list[int]] = defaultdict(list)
    registry_rows: dict[tuple[str, int, str], list[tuple[int, str, int]]] = defaultdict(list)
    resolution_rows: dict[str, list[tuple[int, str, int]]] = defaultdict(list)
    totals: list[int] = []
    for idx, entry in enumerate(index.entries):
        total = sum(block.value_sum for block in entry.blocks)
        totals.append(total)
        binding = index.registry_bindings[entry.registry_binding_id]
        reg_key = (entry.resolution, binding.revision, binding.registry_hash)
        row = (total, entry.frame_sha256, idx)
        registry_rows[reg_key].append(row)
        resolution_rows[entry.resolution].append(row)
        for block in entry.blocks:
            exact[(entry.resolution, block.block_index, block.fingerprint)].append(idx)
    exact_out: dict[tuple[str, int, str], tuple[int, ...]] = {}
    for key, ids in exact.items():
        exact_out[key] = tuple(sorted(ids, key=lambda i: index.entries[i].frame_sha256))
    reg_out = {key: tuple(sorted(rows)) for key, rows in registry_rows.items()}
    res_out = {key: tuple(sorted(rows)) for key, rows in resolution_rows.items()}
    return _CompactSearchRuntime(
        exact_postings=exact_out,
        registry_rows=reg_out,
        resolution_rows=res_out,
        total_sums=tuple(totals),
        frame_hash_to_id={entry.frame_sha256: idx for idx, entry in enumerate(index.entries)},
    )


def _nearest_row_ids(rows: tuple[tuple[int, str, int], ...], target_sum: int, limit: int) -> tuple[int, ...]:
    if limit <= 0 or not rows:
        return ()
    right = bisect_left(rows, (target_sum, "", -1))
    left = right - 1
    out: list[int] = []
    while len(out) < limit and (left >= 0 or right < len(rows)):
        left_row = rows[left] if left >= 0 else None
        right_row = rows[right] if right < len(rows) else None
        if left_row is None:
            chosen = right_row
            right += 1
        elif right_row is None:
            chosen = left_row
            left -= 1
        else:
            left_key = (abs(left_row[0] - target_sum), left_row[1])
            right_key = (abs(right_row[0] - target_sum), right_row[1])
            if left_key <= right_key:
                chosen = left_row
                left -= 1
            else:
                chosen = right_row
                right += 1
        assert chosen is not None
        out.append(chosen[2])
    return tuple(out)


def _candidate_from_compact(target: LocalityIndexEntry, index: CompactLocalityIndex, entry_id: int) -> LocalityCandidate:
    entry = index.entries[entry_id]
    binding = index.registry_bindings[entry.registry_binding_id]
    exact = 0
    numerator = 0
    target_total = 0
    max_blocks = max(len(target.blocks), len(entry.blocks))
    for block_index in range(max_blocks):
        t = target.blocks[block_index] if block_index < len(target.blocks) else None
        e = entry.blocks[block_index] if block_index < len(entry.blocks) else None
        if t is not None:
            target_total += t.value_sum
        if t is not None and e is not None:
            if t.fingerprint == e.fingerprint and t.item_count == e.item_count:
                exact += 1
            numerator += abs(t.value_sum - e.value_sum)
        elif t is not None:
            numerator += t.value_sum
        elif e is not None:
            numerator += e.value_sum
    return LocalityCandidate(
        frame_ref=entry.frame_ref,
        frame_sha256=entry.frame_sha256,
        same_registry=(
            binding.revision == target.registry_revision
            and binding.registry_hash == target.registry_hash
        ),
        exact_block_count=exact,
        comparable_block_count=min(len(target.blocks), len(entry.blocks)),
        normalized_sum_distance=float(numerator / max(1, target_total)),
        item_count_distance=abs(entry.item_count - target.item_count),
        frame_bytes=entry.frame_bytes,
    )


def recall_compact_candidates(
    target_frame: bytes,
    index: CompactLocalityIndex,
    *,
    top_k: int = 8,
    probe_factor: int = 4,
) -> CompactRecallResult:
    if not isinstance(index, CompactLocalityIndex):
        raise ISQLValidationError("COMPACT_LOCALITY_INDEX_REQUIRED")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ISQLValidationError("COMPACT_LOCALITY_INVALID_TOP_K")
    if not isinstance(probe_factor, int) or isinstance(probe_factor, bool) or probe_factor <= 0:
        raise ISQLValidationError("COMPACT_LOCALITY_INVALID_PROBE_FACTOR")

    target = signature_from_native(target_frame, frame_ref="__target__")
    runtime = _search_runtime(index)
    probe_limit = max(top_k, top_k * probe_factor * 2)
    exact_scan_limit = max(top_k, top_k * probe_factor)

    exact_hits: Counter[int] = Counter()
    for block in target.blocks:
        postings = runtime.exact_postings.get((target.resolution, block.block_index, block.fingerprint), ())
        for entry_id in postings[:exact_scan_limit]:
            if index.entries[entry_id].frame_sha256 != target.frame_sha256:
                exact_hits[entry_id] += 1

    candidate_ids: list[int] = []
    seen: set[int] = set()
    for entry_id, _hits in sorted(
        exact_hits.items(),
        key=lambda row: (-row[1], index.entries[row[0]].frame_sha256),
    ):
        if len(candidate_ids) >= probe_limit:
            break
        candidate_ids.append(entry_id)
        seen.add(entry_id)

    target_total = sum(block.value_sum for block in target.blocks)
    reg_key = (target.resolution, target.registry_revision, target.registry_hash)
    for entry_id in _nearest_row_ids(runtime.registry_rows.get(reg_key, ()), target_total, probe_limit):
        if len(candidate_ids) >= probe_limit:
            break
        entry = index.entries[entry_id]
        if entry.frame_sha256 == target.frame_sha256 or entry_id in seen:
            continue
        candidate_ids.append(entry_id)
        seen.add(entry_id)

    if len(candidate_ids) < probe_limit:
        for entry_id in _nearest_row_ids(runtime.resolution_rows.get(target.resolution, ()), target_total, probe_limit):
            if len(candidate_ids) >= probe_limit:
                break
            entry = index.entries[entry_id]
            if entry.frame_sha256 == target.frame_sha256 or entry_id in seen:
                continue
            candidate_ids.append(entry_id)
            seen.add(entry_id)

    candidates = [_candidate_from_compact(target, index, entry_id) for entry_id in candidate_ids]
    candidates.sort(key=lambda row: (
        0 if row.same_registry else 1,
        -row.exact_block_count,
        row.normalized_sum_distance,
        row.item_count_distance,
        row.frame_sha256,
    ))
    selected = tuple(candidates[:top_k])
    entry_count = len(index.entries)
    return CompactRecallResult(
        candidates=selected,
        index_probe_count=len(candidate_ids),
        entry_count=entry_count,
        probe_ratio=(len(candidate_ids) / entry_count if entry_count else 0.0),
    )

from .delta import encode_delta_frame
from .locality import LocalityBaseEvaluation, LocalityBaseSelectionResult


@dataclass(frozen=True, slots=True)
class CompactBaseSelectionResult:
    selection: LocalityBaseSelectionResult
    recall: CompactRecallResult

    def to_dict(self) -> dict[str, object]:
        payload = self.selection.to_dict()
        payload["schema"] = "isql.compact-locality-base-selection/v1.0"
        payload["compact_recall"] = self.recall.to_dict()
        return payload


def select_compact_locality_base(
    target_frame: bytes,
    index: CompactLocalityIndex,
    frame_loader,
    *,
    top_k: int = 8,
    probe_factor: int = 4,
) -> CompactBaseSelectionResult:
    recall = recall_compact_candidates(
        target_frame,
        index,
        top_k=top_k,
        probe_factor=probe_factor,
    )
    target_sig = signature_from_native(target_frame, frame_ref="__target__")
    runtime = _search_runtime(index)
    resolution_rows = runtime.resolution_rows.get(target_sig.resolution, ())
    candidate_pool_count = len(resolution_rows) - (1 if target_sig.frame_sha256 in runtime.frame_hash_to_id else 0)

    evaluations: list[LocalityBaseEvaluation] = []
    best: tuple[int, str, str, bytes] | None = None
    for rank, candidate in enumerate(recall.candidates, start=1):
        try:
            loaded = frame_loader(candidate.frame_ref)
        except Exception as exc:
            raise ISQLValidationError("COMPACT_LOCALITY_BASE_REF_UNAVAILABLE") from exc
        if not isinstance(loaded, (bytes, bytearray, memoryview)):
            raise ISQLValidationError("COMPACT_LOCALITY_BASE_BYTES_REQUIRED")
        base = bytes(loaded)
        actual_hash = hashlib.sha256(base).hexdigest()
        if actual_hash != candidate.frame_sha256:
            raise ISQLValidationError("COMPACT_LOCALITY_BASE_HASH_MISMATCH")
        delta = encode_delta_frame(base, target_frame)
        evaluations.append(LocalityBaseEvaluation(
            recall_rank=rank,
            frame_ref=candidate.frame_ref,
            frame_sha256=candidate.frame_sha256,
            delta_bytes=len(delta),
            heuristic=candidate,
        ))
        key = (len(delta), candidate.frame_sha256, candidate.frame_ref, delta)
        if best is None or key[:2] < best[:2]:
            best = key

    standalone_bytes = len(target_frame)
    if best is not None and best[0] < standalone_bytes:
        selected_bytes, selected_hash, selected_ref, selected_frame = best
        mode = "delta"
        frame = selected_frame
        base_ref: str | None = selected_ref
        base_hash: str | None = selected_hash
    else:
        selected_bytes = standalone_bytes
        mode = "native"
        frame = bytes(target_frame)
        base_ref = None
        base_hash = None

    best_delta = min((row.delta_bytes for row in evaluations), default=None)
    selection = LocalityBaseSelectionResult(
        mode=mode,
        frame=frame,
        target_frame_sha256=target_sig.frame_sha256,
        standalone_frame_bytes=standalone_bytes,
        selected_frame_bytes=selected_bytes,
        bytes_saved_vs_standalone=standalone_bytes - selected_bytes,
        selected_ratio=selected_bytes / standalone_bytes,
        selected_base_ref=base_ref,
        selected_base_sha256=base_hash,
        best_delta_candidate_bytes=best_delta,
        candidate_pool_count=candidate_pool_count,
        recalled_candidate_count=len(recall.candidates),
        selected_recall_rank=(
            next((row.recall_rank for row in evaluations if row.frame_sha256 == base_hash), None)
            if base_hash is not None else None
        ),
        evaluations=tuple(evaluations),
    )
    return CompactBaseSelectionResult(selection=selection, recall=recall)
