from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable
from pathlib import Path, PurePosixPath

from .errors import ISQLValidationError
from .native import NATIVE_BLOCK_SIZE, decode_native_spectral_frame

LOCALITY_INDEX_SCHEMA = "isql.locality-index/v0.9"


def _require_hex64(value: str, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ISQLValidationError(code)
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ISQLValidationError(code) from exc
    return value.lower()


def _require_nonempty_ref(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ISQLValidationError("LOCALITY_INVALID_FRAME_REF")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ISQLValidationError("LOCALITY_INVALID_FRAME_REF")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _block_fingerprint(values: tuple[int, ...]) -> str:
    h = hashlib.sha256()
    h.update(len(values).to_bytes(2, "big"))
    for value in values:
        width = max(1, (value.bit_length() + 7) // 8)
        h.update(width.to_bytes(1, "big"))
        h.update(value.to_bytes(width, "big"))
    return h.digest()[:8].hex()


@dataclass(frozen=True, slots=True)
class LocalityBlockSignature:
    block_index: int
    item_count: int
    fingerprint: str
    value_sum: int
    value_max: int

    def __post_init__(self) -> None:
        if not isinstance(self.block_index, int) or isinstance(self.block_index, bool) or self.block_index < 0:
            raise ISQLValidationError("LOCALITY_INVALID_BLOCK_INDEX")
        if not isinstance(self.item_count, int) or isinstance(self.item_count, bool) or not 1 <= self.item_count <= NATIVE_BLOCK_SIZE:
            raise ISQLValidationError("LOCALITY_INVALID_BLOCK_ITEM_COUNT")
        if not isinstance(self.fingerprint, str) or len(self.fingerprint) != 16:
            raise ISQLValidationError("LOCALITY_INVALID_BLOCK_FINGERPRINT")
        try:
            bytes.fromhex(self.fingerprint)
        except ValueError as exc:
            raise ISQLValidationError("LOCALITY_INVALID_BLOCK_FINGERPRINT") from exc
        for value, code in ((self.value_sum, "LOCALITY_INVALID_BLOCK_SUM"), (self.value_max, "LOCALITY_INVALID_BLOCK_MAX")):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ISQLValidationError(code)

    def to_dict(self) -> dict[str, object]:
        return {
            "block_index": self.block_index,
            "item_count": self.item_count,
            "fingerprint": self.fingerprint,
            "value_sum": self.value_sum,
            "value_max": self.value_max,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LocalityBlockSignature":
        if not isinstance(data, dict):
            raise ISQLValidationError("LOCALITY_BLOCK_OBJECT_REQUIRED")
        return cls(
            block_index=int(data["block_index"]),
            item_count=int(data["item_count"]),
            fingerprint=str(data["fingerprint"]),
            value_sum=int(data["value_sum"]),
            value_max=int(data["value_max"]),
        )


@dataclass(frozen=True, slots=True)
class LocalityIndexEntry:
    frame_ref: str
    frame_sha256: str
    address_sha256: str
    resolution: str
    registry_revision: int
    registry_hash: str
    item_count: int
    frame_bytes: int
    blocks: tuple[LocalityBlockSignature, ...]

    def __post_init__(self) -> None:
        _require_nonempty_ref(self.frame_ref)
        _require_hex64(self.frame_sha256, "LOCALITY_INVALID_FRAME_HASH")
        _require_hex64(self.address_sha256, "LOCALITY_INVALID_ADDRESS_HASH")
        _require_hex64(self.registry_hash, "LOCALITY_INVALID_REGISTRY_HASH")
        if self.resolution not in {"R1", "R2"}:
            raise ISQLValidationError("LOCALITY_INVALID_RESOLUTION")
        if not isinstance(self.registry_revision, int) or isinstance(self.registry_revision, bool) or self.registry_revision < 0:
            raise ISQLValidationError("LOCALITY_INVALID_REGISTRY_REVISION")
        if not isinstance(self.item_count, int) or isinstance(self.item_count, bool) or self.item_count <= 0:
            raise ISQLValidationError("LOCALITY_INVALID_ITEM_COUNT")
        if not isinstance(self.frame_bytes, int) or isinstance(self.frame_bytes, bool) or self.frame_bytes <= 0:
            raise ISQLValidationError("LOCALITY_INVALID_FRAME_BYTES")
        expected_blocks = (self.item_count + NATIVE_BLOCK_SIZE - 1) // NATIVE_BLOCK_SIZE
        if not isinstance(self.blocks, tuple) or len(self.blocks) != expected_blocks:
            raise ISQLValidationError("LOCALITY_INVALID_BLOCK_COUNT")
        for index, block in enumerate(self.blocks):
            if block.block_index != index:
                raise ISQLValidationError("LOCALITY_NONCANONICAL_BLOCK_ORDER")

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_ref": self.frame_ref,
            "frame_sha256": self.frame_sha256,
            "address_sha256": self.address_sha256,
            "resolution": self.resolution,
            "registry_revision": self.registry_revision,
            "registry_hash": self.registry_hash,
            "item_count": self.item_count,
            "frame_bytes": self.frame_bytes,
            "blocks": [block.to_dict() for block in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LocalityIndexEntry":
        if not isinstance(data, dict):
            raise ISQLValidationError("LOCALITY_ENTRY_OBJECT_REQUIRED")
        raw_blocks = data.get("blocks")
        if not isinstance(raw_blocks, list):
            raise ISQLValidationError("LOCALITY_BLOCKS_ARRAY_REQUIRED")
        return cls(
            frame_ref=str(data["frame_ref"]),
            frame_sha256=str(data["frame_sha256"]),
            address_sha256=str(data["address_sha256"]),
            resolution=str(data["resolution"]),
            registry_revision=int(data["registry_revision"]),
            registry_hash=str(data["registry_hash"]),
            item_count=int(data["item_count"]),
            frame_bytes=int(data["frame_bytes"]),
            blocks=tuple(LocalityBlockSignature.from_dict(row) for row in raw_blocks),
        )


@dataclass(frozen=True, slots=True)
class LocalityIndex:
    entries: tuple[LocalityIndexEntry, ...]

    def __post_init__(self) -> None:
        refs = [entry.frame_ref for entry in self.entries]
        if len(refs) != len(set(refs)):
            raise ISQLValidationError("LOCALITY_DUPLICATE_FRAME_REF")
        if tuple(sorted(self.entries, key=lambda e: (e.frame_ref, e.frame_sha256))) != self.entries:
            raise ISQLValidationError("LOCALITY_NONCANONICAL_ENTRY_ORDER")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": LOCALITY_INDEX_SCHEMA,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LocalityIndex":
        if not isinstance(data, dict) or data.get("schema") != LOCALITY_INDEX_SCHEMA:
            raise ISQLValidationError("LOCALITY_INVALID_INDEX_SCHEMA")
        raw = data.get("entries")
        if not isinstance(raw, list):
            raise ISQLValidationError("LOCALITY_ENTRIES_ARRAY_REQUIRED")
        entries = tuple(LocalityIndexEntry.from_dict(row) for row in raw)
        return cls(entries=entries)

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def signature_from_native(frame: bytes, *, frame_ref: str) -> LocalityIndexEntry:
    frame_ref = _require_nonempty_ref(frame_ref)
    native = decode_native_spectral_frame(frame)
    blocks: list[LocalityBlockSignature] = []
    for block_index, start in enumerate(range(0, len(native.sequence), NATIVE_BLOCK_SIZE)):
        values = tuple(native.sequence[start : start + NATIVE_BLOCK_SIZE])
        blocks.append(LocalityBlockSignature(
            block_index=block_index,
            item_count=len(values),
            fingerprint=_block_fingerprint(values),
            value_sum=sum(values),
            value_max=max(values),
        ))
    return LocalityIndexEntry(
        frame_ref=frame_ref,
        frame_sha256=hashlib.sha256(bytes(frame)).hexdigest(),
        address_sha256=native.address_digest.hex(),
        resolution=native.resolution,
        registry_revision=native.registry_revision,
        registry_hash=native.registry_hash,
        item_count=len(native.sequence),
        frame_bytes=len(frame),
        blocks=tuple(blocks),
    )


def build_locality_index(frames: Iterable[tuple[str, bytes]]) -> LocalityIndex:
    entries: list[LocalityIndexEntry] = []
    seen: set[str] = set()
    for frame_ref, frame in frames:
        ref = _require_nonempty_ref(frame_ref)
        if ref in seen:
            raise ISQLValidationError("LOCALITY_DUPLICATE_FRAME_REF")
        seen.add(ref)
        entries.append(signature_from_native(frame, frame_ref=ref))
    entries.sort(key=lambda e: (e.frame_ref, e.frame_sha256))
    return LocalityIndex(entries=tuple(entries))

@dataclass(frozen=True, slots=True)
class LocalityCandidate:
    frame_ref: str
    frame_sha256: str
    same_registry: bool
    exact_block_count: int
    comparable_block_count: int
    normalized_sum_distance: float
    item_count_distance: int
    frame_bytes: int

    def __post_init__(self) -> None:
        _require_nonempty_ref(self.frame_ref)
        _require_hex64(self.frame_sha256, "LOCALITY_INVALID_FRAME_HASH")
        if not isinstance(self.same_registry, bool):
            raise ISQLValidationError("LOCALITY_INVALID_REGISTRY_MATCH_FLAG")
        for value, code in (
            (self.exact_block_count, "LOCALITY_INVALID_EXACT_BLOCK_COUNT"),
            (self.comparable_block_count, "LOCALITY_INVALID_COMPARABLE_BLOCK_COUNT"),
            (self.item_count_distance, "LOCALITY_INVALID_ITEM_DISTANCE"),
            (self.frame_bytes, "LOCALITY_INVALID_FRAME_BYTES"),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ISQLValidationError(code)
        if not isinstance(self.normalized_sum_distance, float) or self.normalized_sum_distance < 0.0:
            raise ISQLValidationError("LOCALITY_INVALID_SUM_DISTANCE")

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_ref": self.frame_ref,
            "frame_sha256": self.frame_sha256,
            "same_registry": self.same_registry,
            "exact_block_count": self.exact_block_count,
            "comparable_block_count": self.comparable_block_count,
            "normalized_sum_distance": self.normalized_sum_distance,
            "item_count_distance": self.item_count_distance,
            "frame_bytes": self.frame_bytes,
        }


def _candidate_for(target: LocalityIndexEntry, entry: LocalityIndexEntry) -> LocalityCandidate:
    exact = 0
    numerator = 0
    target_total = 0
    max_blocks = max(len(target.blocks), len(entry.blocks))
    for index in range(max_blocks):
        t = target.blocks[index] if index < len(target.blocks) else None
        e = entry.blocks[index] if index < len(entry.blocks) else None
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
            entry.registry_revision == target.registry_revision
            and entry.registry_hash == target.registry_hash
        ),
        exact_block_count=exact,
        comparable_block_count=min(len(target.blocks), len(entry.blocks)),
        normalized_sum_distance=float(numerator / max(1, target_total)),
        item_count_distance=abs(entry.item_count - target.item_count),
        frame_bytes=entry.frame_bytes,
    )


def recall_locality_candidates(target_frame: bytes, index: LocalityIndex, *, top_k: int = 8) -> tuple[LocalityCandidate, ...]:
    if not isinstance(index, LocalityIndex):
        raise ISQLValidationError("LOCALITY_INDEX_REQUIRED")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ISQLValidationError("LOCALITY_INVALID_TOP_K")
    target = signature_from_native(target_frame, frame_ref="__target__")
    rows: list[LocalityCandidate] = []
    for entry in index.entries:
        if entry.frame_sha256 == target.frame_sha256:
            continue
        if entry.resolution != target.resolution:
            continue
        rows.append(_candidate_for(target, entry))
    rows.sort(key=lambda row: (
        0 if row.same_registry else 1,
        -row.exact_block_count,
        row.normalized_sum_distance,
        row.item_count_distance,
        row.frame_sha256,
    ))
    return tuple(rows[:top_k])

@dataclass(frozen=True, slots=True)
class LocalityBaseEvaluation:
    recall_rank: int
    frame_ref: str
    frame_sha256: str
    delta_bytes: int
    heuristic: LocalityCandidate

    def to_dict(self) -> dict[str, object]:
        return {
            "recall_rank": self.recall_rank,
            "frame_ref": self.frame_ref,
            "frame_sha256": self.frame_sha256,
            "delta_bytes": self.delta_bytes,
            "heuristic": self.heuristic.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class LocalityBaseSelectionResult:
    mode: str
    frame: bytes
    target_frame_sha256: str
    standalone_frame_bytes: int
    selected_frame_bytes: int
    bytes_saved_vs_standalone: int
    selected_ratio: float
    selected_base_ref: str | None
    selected_base_sha256: str | None
    best_delta_candidate_bytes: int | None
    candidate_pool_count: int
    recalled_candidate_count: int
    selected_recall_rank: int | None
    evaluations: tuple[LocalityBaseEvaluation, ...]

    def __post_init__(self) -> None:
        if self.mode not in {"native", "delta"}:
            raise ISQLValidationError("LOCALITY_INVALID_SELECTION_MODE")
        if self.mode == "delta" and (self.selected_base_ref is None or self.selected_base_sha256 is None):
            raise ISQLValidationError("LOCALITY_DELTA_BASE_REQUIRED")
        if self.mode == "native" and (self.selected_base_ref is not None or self.selected_base_sha256 is not None):
            raise ISQLValidationError("LOCALITY_NATIVE_BASE_MUST_BE_EMPTY")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "isql.locality-base-selection/v0.9",
            "mode": self.mode,
            "target_frame_sha256": self.target_frame_sha256,
            "standalone_frame_bytes": self.standalone_frame_bytes,
            "selected_frame_bytes": self.selected_frame_bytes,
            "bytes_saved_vs_standalone": self.bytes_saved_vs_standalone,
            "selected_ratio": self.selected_ratio,
            "selected_base_ref": self.selected_base_ref,
            "selected_base_sha256": self.selected_base_sha256,
            "best_delta_candidate_bytes": self.best_delta_candidate_bytes,
            "candidate_pool_count": self.candidate_pool_count,
            "recalled_candidate_count": self.recalled_candidate_count,
            "selected_recall_rank": self.selected_recall_rank,
            "evaluations": [row.to_dict() for row in self.evaluations],
        }


def select_locality_base(target_frame: bytes, index: LocalityIndex, frame_loader, *, top_k: int = 8) -> LocalityBaseSelectionResult:
    from .delta import encode_delta_frame

    # Validates that the target is canonical standalone ISN7 before candidate work.
    target_sig = signature_from_native(target_frame, frame_ref="__target__")
    compatible_entries = [
        entry for entry in index.entries
        if entry.frame_sha256 != target_sig.frame_sha256 and entry.resolution == target_sig.resolution
    ]
    recalled = recall_locality_candidates(target_frame, index, top_k=top_k)
    evaluations: list[LocalityBaseEvaluation] = []
    best: tuple[int, str, str, bytes] | None = None

    for rank, candidate in enumerate(recalled, start=1):
        try:
            loaded = frame_loader(candidate.frame_ref)
        except Exception as exc:
            raise ISQLValidationError("LOCALITY_BASE_REF_UNAVAILABLE") from exc
        if not isinstance(loaded, (bytes, bytearray, memoryview)):
            raise ISQLValidationError("LOCALITY_BASE_BYTES_REQUIRED")
        base = bytes(loaded)
        actual_hash = hashlib.sha256(base).hexdigest()
        if actual_hash != candidate.frame_sha256:
            raise ISQLValidationError("LOCALITY_BASE_HASH_MISMATCH")
        # Hash verification binds the loaded bytes to the indexed standalone frame;
        # encode_delta_frame performs the canonical ISN7 validation.
        delta = encode_delta_frame(base, target_frame)
        evaluation = LocalityBaseEvaluation(
            recall_rank=rank,
            frame_ref=candidate.frame_ref,
            frame_sha256=candidate.frame_sha256,
            delta_bytes=len(delta),
            heuristic=candidate,
        )
        evaluations.append(evaluation)
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
    return LocalityBaseSelectionResult(
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
        candidate_pool_count=len(compatible_entries),
        recalled_candidate_count=len(recalled),
        selected_recall_rank=(
            next((row.recall_rank for row in evaluations if row.frame_sha256 == base_hash), None)
            if base_hash is not None else None
        ),
        evaluations=tuple(evaluations),
    )


def save_locality_index(path: str | Path, index: LocalityIndex) -> None:
    if not isinstance(index, LocalityIndex):
        raise ISQLValidationError("LOCALITY_INDEX_REQUIRED")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(index.to_dict(), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_locality_index(path: str | Path) -> LocalityIndex:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ISQLValidationError("LOCALITY_INDEX_READ_FAILED") from exc
    return LocalityIndex.from_dict(data)
