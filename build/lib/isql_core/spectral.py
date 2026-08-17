from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import ISQLValidationError

SPECTRAL_REGISTRY_SCHEMA = "isql.spectral-registry/v0.3"
SPECTRAL_REGISTRY_ID = "isql-spectral-registry/default"
SPECTRAL_NAMESPACES = (
    "summary",
    "atom",
    "predicate",
    "claim",
    "intent",
    "uncertainty",
    "tag",
    "language",
)


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ISQLValidationError("SPECTRAL_DATA_NOT_CANONICAL_JSON") from exc


def _clean_value(value: str) -> str:
    if not isinstance(value, str):
        raise ISQLValidationError("SPECTRAL_REGISTRY_VALUE_MUST_BE_TEXT")
    text = value.strip()
    if not text:
        raise ISQLValidationError("SPECTRAL_REGISTRY_VALUE_MUST_BE_NONEMPTY")
    return text


@dataclass(slots=True)
class SpectralRegistry:
    registry_id: str
    revision: int
    namespaces: dict[str, list[str]]

    @classmethod
    def empty(cls, registry_id: str = SPECTRAL_REGISTRY_ID) -> "SpectralRegistry":
        return cls(
            registry_id=registry_id,
            revision=0,
            namespaces={name: [] for name in SPECTRAL_NAMESPACES},
        )

    def __post_init__(self) -> None:
        if not isinstance(self.registry_id, str) or not self.registry_id.strip():
            raise ISQLValidationError("SPECTRAL_REGISTRY_ID_REQUIRED")
        if not isinstance(self.revision, int) or self.revision < 0:
            raise ISQLValidationError("INVALID_SPECTRAL_REGISTRY_REVISION")
        if set(self.namespaces) != set(SPECTRAL_NAMESPACES):
            raise ISQLValidationError("INVALID_SPECTRAL_REGISTRY_NAMESPACES")
        for namespace, values in self.namespaces.items():
            if not isinstance(values, list):
                raise ISQLValidationError("SPECTRAL_REGISTRY_NAMESPACE_MUST_BE_LIST")
            cleaned = [_clean_value(value) for value in values]
            if len(set(cleaned)) != len(cleaned):
                raise ISQLValidationError("SPECTRAL_REGISTRY_DUPLICATE_VALUE")
            self.namespaces[namespace] = cleaned

    def intern(self, namespace: str, value: str) -> int:
        if namespace not in self.namespaces:
            raise ISQLValidationError("UNKNOWN_SPECTRAL_NAMESPACE")
        text = _clean_value(value)
        values = self.namespaces[namespace]
        try:
            return values.index(text) + 1
        except ValueError:
            values.append(text)
            return len(values)

    def resolve(self, namespace: str, value_id: int) -> str:
        if namespace not in self.namespaces:
            raise ISQLValidationError("UNKNOWN_SPECTRAL_NAMESPACE")
        if not isinstance(value_id, int) or isinstance(value_id, bool) or value_id <= 0:
            raise ISQLValidationError("INVALID_SPECTRAL_VALUE_ID")
        values = self.namespaces[namespace]
        if value_id > len(values):
            raise ISQLValidationError("SPECTRAL_VALUE_ID_NOT_FOUND")
        return values[value_id - 1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SPECTRAL_REGISTRY_SCHEMA,
            "registry_id": self.registry_id,
            "revision": self.revision,
            "namespaces": {name: list(self.namespaces[name]) for name in SPECTRAL_NAMESPACES},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SpectralRegistry":
        if not isinstance(value, Mapping):
            raise ISQLValidationError("SPECTRAL_REGISTRY_MUST_BE_OBJECT")
        if value.get("schema") != SPECTRAL_REGISTRY_SCHEMA:
            raise ISQLValidationError("INVALID_SPECTRAL_REGISTRY_SCHEMA")
        raw_namespaces = value.get("namespaces")
        if not isinstance(raw_namespaces, Mapping):
            raise ISQLValidationError("SPECTRAL_REGISTRY_NAMESPACES_REQUIRED")
        namespaces: dict[str, list[str]] = {}
        for name in SPECTRAL_NAMESPACES:
            raw = raw_namespaces.get(name)
            if not isinstance(raw, list):
                raise ISQLValidationError("SPECTRAL_REGISTRY_NAMESPACE_MUST_BE_LIST")
            namespaces[name] = [str(x) for x in raw]
        return cls(
            registry_id=str(value.get("registry_id", "")),
            revision=int(value.get("revision", -1)),
            namespaces=namespaces,
        )

    def content_hash(self) -> str:
        return hashlib.sha256(_canonical_json(self.to_dict())).hexdigest()

    def clone(self) -> "SpectralRegistry":
        return SpectralRegistry.from_dict(self.to_dict())


class SpectralRegistryStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.registry_dir = self.root / "spectral_registry"
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_path(self) -> Path:
        return self.registry_dir / "current.json"

    def _revision_path(self, revision: int) -> Path:
        return self.registry_dir / f"rev-{revision:06d}.json"

    @staticmethod
    def _write(path: Path, registry: SpectralRegistry) -> None:
        payload = json.dumps(
            registry.to_dict(), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        ) + "\n"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)

    def load_current(self) -> SpectralRegistry:
        if not self.current_path.exists():
            return SpectralRegistry.empty()
        return SpectralRegistry.from_dict(json.loads(self.current_path.read_text(encoding="utf-8")))

    def load_revision(self, revision: int) -> SpectralRegistry:
        if revision == 0 and not self._revision_path(0).exists():
            return SpectralRegistry.empty()
        path = self._revision_path(revision)
        if not path.exists():
            raise ISQLValidationError("SPECTRAL_REGISTRY_REVISION_NOT_FOUND")
        return SpectralRegistry.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _assert_append_only(current: SpectralRegistry, candidate: SpectralRegistry) -> None:
        if current.registry_id != candidate.registry_id:
            raise ISQLValidationError("SPECTRAL_REGISTRY_ID_MISMATCH")
        for namespace in SPECTRAL_NAMESPACES:
            old = current.namespaces[namespace]
            new = candidate.namespaces[namespace]
            if len(new) < len(old) or new[: len(old)] != old:
                raise ISQLValidationError("SPECTRAL_REGISTRY_NOT_APPEND_ONLY")

    def commit(self, candidate: SpectralRegistry) -> SpectralRegistry:
        current = self.load_current()
        self._assert_append_only(current, candidate)
        same_content = all(
            candidate.namespaces[name] == current.namespaces[name]
            for name in SPECTRAL_NAMESPACES
        )
        if same_content:
            return current
        committed = candidate.clone()
        committed.revision = current.revision + 1
        self._write(self._revision_path(committed.revision), committed)
        self._write(self.current_path, committed)
        return committed

SPECTRAL_PACKET_SCHEMA = "isql.spectral-packet/v0.3"


def _compact_registry_bytes(registry: SpectralRegistry) -> bytes:
    return _canonical_json(registry.to_dict())


def _require_id(value: Any, *, allow_zero: bool = False) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ISQLValidationError("SPECTRAL_PACKET_ID_MUST_BE_INTEGER")
    if value < 0 or (value == 0 and not allow_zero):
        raise ISQLValidationError("INVALID_SPECTRAL_PACKET_ID")
    return value


@dataclass(frozen=True, slots=True)
class SpectralPacket:
    registry_id: str
    registry_revision: int
    registry_hash: str
    sequence: tuple[int, ...]
    registry_delta_bytes: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.registry_id, str) or not self.registry_id.strip():
            raise ISQLValidationError("SPECTRAL_PACKET_REGISTRY_ID_REQUIRED")
        if not isinstance(self.registry_revision, int) or self.registry_revision < 0:
            raise ISQLValidationError("INVALID_SPECTRAL_PACKET_REGISTRY_REVISION")
        if (
            not isinstance(self.registry_hash, str)
            or len(self.registry_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in self.registry_hash)
        ):
            raise ISQLValidationError("INVALID_SPECTRAL_PACKET_REGISTRY_HASH")
        if not isinstance(self.registry_delta_bytes, int) or self.registry_delta_bytes < 0:
            raise ISQLValidationError("INVALID_SPECTRAL_REGISTRY_DELTA_BYTES")
        if not isinstance(self.sequence, tuple) or not self.sequence:
            raise ISQLValidationError("SPECTRAL_PACKET_SEQUENCE_REQUIRED")
        for value in self.sequence:
            _require_id(value, allow_zero=True)

    def to_dict(self) -> dict[str, Any]:
        # Short keys are intentional: this is the runtime/transport form.
        return {
            "s": SPECTRAL_PACKET_SCHEMA,
            "g": self.registry_id,
            "v": self.registry_revision,
            "h": self.registry_hash,
            "q": list(self.sequence),
            "d": self.registry_delta_bytes,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SpectralPacket":
        if not isinstance(value, Mapping):
            raise ISQLValidationError("SPECTRAL_PACKET_MUST_BE_OBJECT")
        if value.get("s") != SPECTRAL_PACKET_SCHEMA:
            raise ISQLValidationError("INVALID_SPECTRAL_PACKET_SCHEMA")
        raw_sequence = value.get("q")
        if not isinstance(raw_sequence, list):
            raise ISQLValidationError("SPECTRAL_PACKET_SEQUENCE_MUST_BE_LIST")
        return cls(
            registry_id=str(value.get("g", "")),
            registry_revision=int(value.get("v", -1)),
            registry_hash=str(value.get("h", "")),
            sequence=tuple(_require_id(x, allow_zero=True) for x in raw_sequence),
            registry_delta_bytes=int(value.get("d", 0)),
        )

    def canonical_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def with_registry_hash(self, registry_hash: str) -> "SpectralPacket":
        return SpectralPacket(
            registry_id=self.registry_id,
            registry_revision=self.registry_revision,
            registry_hash=registry_hash,
            sequence=self.sequence,
            registry_delta_bytes=self.registry_delta_bytes,
        )


@dataclass(frozen=True, slots=True)
class SpectralCompileResult:
    packet: SpectralPacket
    verbose_coordinate_bytes: int
    packet_bytes: int
    registry_before_bytes: int
    registry_after_bytes: int
    registry_delta_bytes: int

    @property
    def packet_ratio(self) -> float:
        return self.packet_bytes / self.verbose_coordinate_bytes

    @property
    def cold_total_ratio(self) -> float:
        return (self.packet_bytes + self.registry_delta_bytes) / self.verbose_coordinate_bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet": self.packet.to_dict(),
            "verbose_coordinate_bytes": self.verbose_coordinate_bytes,
            "packet_bytes": self.packet_bytes,
            "registry_before_bytes": self.registry_before_bytes,
            "registry_after_bytes": self.registry_after_bytes,
            "registry_delta_bytes": self.registry_delta_bytes,
            "packet_ratio": self.packet_ratio,
            "cold_total_ratio": self.cold_total_ratio,
        }


def _append_counted(sequence: list[int], values: list[int]) -> None:
    sequence.append(len(values))
    sequence.extend(values)


def compile_spectral_packet(
    coords: "SemanticCoordinateSet",
    store: SpectralRegistryStore,
) -> SpectralCompileResult:
    # Local import avoids a module cycle and keeps the registry layer reusable.
    from .semantics import SemanticCoordinateSet

    if not isinstance(coords, SemanticCoordinateSet):
        raise ISQLValidationError("SPECTRAL_COMPILER_REQUIRES_SEMANTIC_COORDINATES")
    registry = store.load_current()
    before_bytes = len(_compact_registry_bytes(registry))

    summary_id = registry.intern("summary", coords.summary)
    concept_ids = [registry.intern("atom", x) for x in coords.concepts]
    entity_ids = [registry.intern("atom", x) for x in coords.entities]
    relation_ids = [
        (
            registry.intern("atom", rel.subject),
            registry.intern("predicate", rel.predicate),
            registry.intern("atom", rel.object),
        )
        for rel in coords.relations
    ]
    claim_ids = [registry.intern("claim", x) for x in coords.claims]
    intent_id = registry.intern("intent", coords.intent) if coords.intent else 0
    uncertainty_ids = [registry.intern("uncertainty", x) for x in coords.uncertainty]
    tag_ids = [registry.intern("tag", x) for x in coords.tags]
    language_id = registry.intern("language", coords.language)

    committed = store.commit(registry)
    after_bytes = len(_compact_registry_bytes(committed))

    sequence: list[int] = [summary_id]
    _append_counted(sequence, concept_ids)
    _append_counted(sequence, entity_ids)
    sequence.append(len(relation_ids))
    for subject_id, predicate_id, object_id in relation_ids:
        sequence.extend((subject_id, predicate_id, object_id))
    _append_counted(sequence, claim_ids)
    sequence.append(intent_id)
    _append_counted(sequence, uncertainty_ids)
    _append_counted(sequence, tag_ids)
    sequence.append(language_id)

    registry_delta_bytes = max(0, after_bytes - before_bytes)
    packet = SpectralPacket(
        registry_id=committed.registry_id,
        registry_revision=committed.revision,
        registry_hash=committed.content_hash(),
        sequence=tuple(sequence),
        registry_delta_bytes=registry_delta_bytes,
    )
    verbose_bytes = len(_canonical_json(coords.to_dict()))
    packet_bytes = len(packet.canonical_bytes())
    return SpectralCompileResult(
        packet=packet,
        verbose_coordinate_bytes=verbose_bytes,
        packet_bytes=packet_bytes,
        registry_before_bytes=before_bytes,
        registry_after_bytes=after_bytes,
        registry_delta_bytes=registry_delta_bytes,
    )


class _SequenceReader:
    def __init__(self, sequence: tuple[int, ...]) -> None:
        self.sequence = sequence
        self.pos = 0

    def one(self, *, allow_zero: bool = False) -> int:
        if self.pos >= len(self.sequence):
            raise ISQLValidationError("TRUNCATED_SPECTRAL_PACKET")
        value = _require_id(self.sequence[self.pos], allow_zero=allow_zero)
        self.pos += 1
        return value

    def counted(self) -> list[int]:
        count = self.one(allow_zero=True)
        values = [self.one() for _ in range(count)]
        return values

    def finish(self) -> None:
        if self.pos != len(self.sequence):
            raise ISQLValidationError("SPECTRAL_PACKET_TRAILING_VALUES")


def expand_spectral_packet(
    packet: SpectralPacket,
    store: SpectralRegistryStore,
) -> "SemanticCoordinateSet":
    from .semantics import SemanticCoordinateSet, SemanticRelation

    if not isinstance(packet, SpectralPacket):
        raise ISQLValidationError("SPECTRAL_EXPAND_REQUIRES_PACKET")
    registry = store.load_revision(packet.registry_revision)
    if registry.registry_id != packet.registry_id:
        raise ISQLValidationError("SPECTRAL_PACKET_REGISTRY_ID_MISMATCH")
    if registry.content_hash() != packet.registry_hash:
        raise ISQLValidationError("SPECTRAL_PACKET_REGISTRY_HASH_MISMATCH")

    reader = _SequenceReader(packet.sequence)
    summary_id = reader.one()
    concept_ids = reader.counted()
    entity_ids = reader.counted()
    relation_count = reader.one(allow_zero=True)
    relations: list[SemanticRelation] = []
    for _ in range(relation_count):
        subject_id = reader.one()
        predicate_id = reader.one()
        object_id = reader.one()
        relations.append(
            SemanticRelation(
                subject=registry.resolve("atom", subject_id),
                predicate=registry.resolve("predicate", predicate_id),
                object=registry.resolve("atom", object_id),
            )
        )
    claim_ids = reader.counted()
    intent_id = reader.one(allow_zero=True)
    uncertainty_ids = reader.counted()
    tag_ids = reader.counted()
    language_id = reader.one()
    reader.finish()

    return SemanticCoordinateSet(
        summary=registry.resolve("summary", summary_id),
        concepts=tuple(registry.resolve("atom", x) for x in concept_ids),
        entities=tuple(registry.resolve("atom", x) for x in entity_ids),
        relations=tuple(relations),
        claims=tuple(registry.resolve("claim", x) for x in claim_ids),
        intent=registry.resolve("intent", intent_id) if intent_id else None,
        uncertainty=tuple(registry.resolve("uncertainty", x) for x in uncertainty_ids),
        tags=tuple(registry.resolve("tag", x) for x in tag_ids),
        language=registry.resolve("language", language_id),
    )
