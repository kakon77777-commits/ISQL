from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import unicodedata
from typing import Any, Mapping

from .errors import ISQLValidationError
from .spectral import SPECTRAL_NAMESPACES, SPECTRAL_REGISTRY_ID, SpectralRegistry

HIERARCHICAL_REGISTRY_SCHEMA = "isql.hierarchical-registry/v0.5"
HIERARCHICAL_REGISTRY_ID = "isql-hierarchical-registry/default"


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
        raise ISQLValidationError("HIERARCHICAL_DATA_NOT_CANONICAL_JSON") from exc


def _is_east_asian_atomic(ch: str) -> bool:
    code = ord(ch)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x3040 <= code <= 0x30FF
        or 0xAC00 <= code <= 0xD7AF
    )


def _is_word_char(ch: str) -> bool:
    if ch == "_":
        return True
    category = unicodedata.category(ch)
    return category[0] in {"L", "N", "M"}


def tokenize_registry_text(text: str) -> tuple[str, ...]:
    if not isinstance(text, str) or not text:
        raise ISQLValidationError("HIERARCHICAL_TEXT_REQUIRED")
    tokens: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            j = i + 1
            while j < len(text) and text[j].isspace() and text[j] == ch:
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        if _is_east_asian_atomic(ch):
            tokens.append(ch)
            i += 1
            continue
        if _is_word_char(ch):
            j = i + 1
            while j < len(text):
                nxt = text[j]
                if _is_east_asian_atomic(nxt) or not _is_word_char(nxt):
                    break
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        tokens.append(ch)
        i += 1
    if "".join(tokens) != text:
        raise ISQLValidationError("HIERARCHICAL_TOKENIZATION_NOT_EXACT")
    return tuple(tokens)


@dataclass(slots=True)
class HierarchicalRegistry:
    registry_id: str
    revision: int
    canonical_registry_id: str
    canonical_revision: int
    canonical_hash: str
    lexemes: list[str]
    programs: dict[str, list[tuple[int, ...]]]

    @classmethod
    def empty(cls) -> "HierarchicalRegistry":
        canonical = SpectralRegistry.empty()
        return cls(
            registry_id=HIERARCHICAL_REGISTRY_ID,
            revision=0,
            canonical_registry_id=SPECTRAL_REGISTRY_ID,
            canonical_revision=0,
            canonical_hash=canonical.content_hash(),
            lexemes=[],
            programs={name: [] for name in SPECTRAL_NAMESPACES},
        )

    def __post_init__(self) -> None:
        if not isinstance(self.registry_id, str) or not self.registry_id:
            raise ISQLValidationError("HIERARCHICAL_REGISTRY_ID_REQUIRED")
        if not isinstance(self.revision, int) or self.revision < 0:
            raise ISQLValidationError("INVALID_HIERARCHICAL_REVISION")
        if self.canonical_registry_id != SPECTRAL_REGISTRY_ID:
            raise ISQLValidationError("HIERARCHICAL_CANONICAL_REGISTRY_ID_MISMATCH")
        if not isinstance(self.canonical_revision, int) or self.canonical_revision < 0:
            raise ISQLValidationError("INVALID_HIERARCHICAL_CANONICAL_REVISION")
        if (
            not isinstance(self.canonical_hash, str)
            or len(self.canonical_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in self.canonical_hash)
        ):
            raise ISQLValidationError("INVALID_HIERARCHICAL_CANONICAL_HASH")
        if not isinstance(self.lexemes, list):
            raise ISQLValidationError("HIERARCHICAL_LEXEMES_MUST_BE_LIST")
        if len(set(self.lexemes)) != len(self.lexemes):
            raise ISQLValidationError("HIERARCHICAL_DUPLICATE_LEXEME")
        for lexeme in self.lexemes:
            if not isinstance(lexeme, str) or not lexeme:
                raise ISQLValidationError("HIERARCHICAL_LEXEME_MUST_BE_TEXT")
        if set(self.programs) != set(SPECTRAL_NAMESPACES):
            raise ISQLValidationError("INVALID_HIERARCHICAL_NAMESPACES")
        for namespace, programs in self.programs.items():
            if not isinstance(programs, list):
                raise ISQLValidationError("HIERARCHICAL_PROGRAMS_MUST_BE_LIST")
            cleaned: list[tuple[int, ...]] = []
            for program in programs:
                if not isinstance(program, tuple):
                    program = tuple(program)
                if not program:
                    raise ISQLValidationError("HIERARCHICAL_PROGRAM_REQUIRED")
                for value in program:
                    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                        raise ISQLValidationError("INVALID_HIERARCHICAL_LEXEME_ID")
                    if value > len(self.lexemes):
                        raise ISQLValidationError("HIERARCHICAL_LEXEME_ID_NOT_FOUND")
                cleaned.append(tuple(program))
            self.programs[namespace] = cleaned

    def intern_lexeme(self, text: str) -> int:
        if not isinstance(text, str) or not text:
            raise ISQLValidationError("HIERARCHICAL_LEXEME_MUST_BE_TEXT")
        try:
            return self.lexemes.index(text) + 1
        except ValueError:
            self.lexemes.append(text)
            return len(self.lexemes)

    def encode_value(self, text: str) -> tuple[int, ...]:
        return tuple(self.intern_lexeme(token) for token in tokenize_registry_text(text))

    def decode_value(self, program: tuple[int, ...]) -> str:
        if not isinstance(program, tuple) or not program:
            raise ISQLValidationError("HIERARCHICAL_PROGRAM_REQUIRED")
        parts: list[str] = []
        for value_id in program:
            if not isinstance(value_id, int) or isinstance(value_id, bool) or value_id <= 0:
                raise ISQLValidationError("INVALID_HIERARCHICAL_LEXEME_ID")
            if value_id > len(self.lexemes):
                raise ISQLValidationError("HIERARCHICAL_LEXEME_ID_NOT_FOUND")
            parts.append(self.lexemes[value_id - 1])
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": HIERARCHICAL_REGISTRY_SCHEMA,
            "registry_id": self.registry_id,
            "revision": self.revision,
            "canonical_registry_id": self.canonical_registry_id,
            "canonical_revision": self.canonical_revision,
            "canonical_hash": self.canonical_hash,
            "lexemes": list(self.lexemes),
            "programs": {
                name: [list(program) for program in self.programs[name]]
                for name in SPECTRAL_NAMESPACES
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HierarchicalRegistry":
        if not isinstance(value, Mapping) or value.get("schema") != HIERARCHICAL_REGISTRY_SCHEMA:
            raise ISQLValidationError("INVALID_HIERARCHICAL_REGISTRY_SCHEMA")
        raw_programs = value.get("programs")
        if not isinstance(raw_programs, Mapping):
            raise ISQLValidationError("HIERARCHICAL_PROGRAMS_REQUIRED")
        return cls(
            registry_id=str(value.get("registry_id", "")),
            revision=int(value.get("revision", -1)),
            canonical_registry_id=str(value.get("canonical_registry_id", "")),
            canonical_revision=int(value.get("canonical_revision", -1)),
            canonical_hash=str(value.get("canonical_hash", "")),
            lexemes=[str(x) for x in value.get("lexemes", [])],
            programs={
                name: [tuple(int(x) for x in program) for program in raw_programs.get(name, [])]
                for name in SPECTRAL_NAMESPACES
            },
        )

    def content_hash(self) -> str:
        return hashlib.sha256(_canonical_json(self.to_dict())).hexdigest()

    def clone(self) -> "HierarchicalRegistry":
        return HierarchicalRegistry.from_dict(self.to_dict())

@dataclass(frozen=True, slots=True)
class HierarchicalCompileResult:
    registry: HierarchicalRegistry
    new_lexeme_count: int
    new_program_count: int
    canonical_json_bytes: int
    hierarchical_json_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry": self.registry.to_dict(),
            "new_lexeme_count": self.new_lexeme_count,
            "new_program_count": self.new_program_count,
            "canonical_json_bytes": self.canonical_json_bytes,
            "hierarchical_json_bytes": self.hierarchical_json_bytes,
        }


def reconstruct_spectral_registry(compiled: HierarchicalRegistry) -> SpectralRegistry:
    if not isinstance(compiled, HierarchicalRegistry):
        raise ISQLValidationError("HIERARCHICAL_RECONSTRUCT_REQUIRES_REGISTRY")
    namespaces: dict[str, list[str]] = {}
    for namespace in SPECTRAL_NAMESPACES:
        namespaces[namespace] = [
            compiled.decode_value(program) for program in compiled.programs[namespace]
        ]
    rebuilt = SpectralRegistry(
        registry_id=compiled.canonical_registry_id,
        revision=compiled.canonical_revision,
        namespaces=namespaces,
    )
    if rebuilt.content_hash() != compiled.canonical_hash:
        raise ISQLValidationError("HIERARCHICAL_CANONICAL_HASH_MISMATCH")
    return rebuilt


def compile_hierarchical_registry(
    canonical: SpectralRegistry,
    previous: HierarchicalRegistry | None = None,
) -> HierarchicalCompileResult:
    if not isinstance(canonical, SpectralRegistry):
        raise ISQLValidationError("HIERARCHICAL_COMPILER_REQUIRES_SPECTRAL_REGISTRY")
    if canonical.registry_id != SPECTRAL_REGISTRY_ID:
        raise ISQLValidationError("HIERARCHICAL_UNSUPPORTED_CANONICAL_REGISTRY")

    base = previous.clone() if previous is not None else HierarchicalRegistry.empty()
    # A previous compiled revision is trusted only after exact reconstruction.
    previous_canonical = reconstruct_spectral_registry(base)
    if canonical.revision < previous_canonical.revision:
        raise ISQLValidationError("HIERARCHICAL_CANONICAL_REVISION_REGRESSION")
    for namespace in SPECTRAL_NAMESPACES:
        old_values = previous_canonical.namespaces[namespace]
        new_values = canonical.namespaces[namespace]
        if len(new_values) < len(old_values) or new_values[: len(old_values)] != old_values:
            raise ISQLValidationError("HIERARCHICAL_CANONICAL_NOT_APPEND_ONLY")

    before_lexemes = len(base.lexemes)
    before_programs = sum(len(x) for x in base.programs.values())
    for namespace in SPECTRAL_NAMESPACES:
        start = len(base.programs[namespace])
        for value in canonical.namespaces[namespace][start:]:
            base.programs[namespace].append(base.encode_value(value))

    base.revision = canonical.revision
    base.canonical_revision = canonical.revision
    base.canonical_hash = canonical.content_hash()

    # Validate the compiled artifact before returning it.
    rebuilt = reconstruct_spectral_registry(base)
    if rebuilt.to_dict() != canonical.to_dict():
        raise ISQLValidationError("HIERARCHICAL_RECONSTRUCTION_MISMATCH")

    return HierarchicalCompileResult(
        registry=base,
        new_lexeme_count=len(base.lexemes) - before_lexemes,
        new_program_count=sum(len(x) for x in base.programs.values()) - before_programs,
        canonical_json_bytes=len(_canonical_json(canonical.to_dict())),
        hierarchical_json_bytes=len(_canonical_json(base.to_dict())),
    )

HIERARCHICAL_DELTA_SCHEMA = "isql.hierarchical-registry-delta/v0.5"


def _require_hash(value: str, error: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ISQLValidationError(error)
    return value


@dataclass(frozen=True, slots=True)
class HierarchicalRegistryDelta:
    registry_id: str
    from_revision: int
    to_revision: int
    previous_hierarchical_hash: str
    target_hierarchical_hash: str
    canonical_registry_id: str
    canonical_revision: int
    canonical_hash: str
    base_lexeme_count: int
    new_lexemes: tuple[str, ...]
    new_programs: dict[str, tuple[tuple[int, ...], ...]]

    def __post_init__(self) -> None:
        if self.registry_id != HIERARCHICAL_REGISTRY_ID:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_REGISTRY_ID")
        if not isinstance(self.from_revision, int) or self.from_revision < 0:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_FROM_REVISION")
        if not isinstance(self.to_revision, int) or self.to_revision < self.from_revision:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_TO_REVISION")
        _require_hash(self.previous_hierarchical_hash, "INVALID_HIERARCHICAL_DELTA_PREVIOUS_HASH")
        _require_hash(self.target_hierarchical_hash, "INVALID_HIERARCHICAL_DELTA_TARGET_HASH")
        if self.canonical_registry_id != SPECTRAL_REGISTRY_ID:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_CANONICAL_REGISTRY")
        if not isinstance(self.canonical_revision, int) or self.canonical_revision < 0:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_CANONICAL_REVISION")
        _require_hash(self.canonical_hash, "INVALID_HIERARCHICAL_DELTA_CANONICAL_HASH")
        if not isinstance(self.base_lexeme_count, int) or self.base_lexeme_count < 0:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_BASE_LEXEME_COUNT")
        if len(set(self.new_lexemes)) != len(self.new_lexemes):
            raise ISQLValidationError("HIERARCHICAL_DELTA_DUPLICATE_LEXEME")
        for text in self.new_lexemes:
            if not isinstance(text, str) or not text:
                raise ISQLValidationError("HIERARCHICAL_DELTA_LEXEME_MUST_BE_TEXT")
        if set(self.new_programs) != set(SPECTRAL_NAMESPACES):
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_NAMESPACES")
        max_lexeme = self.base_lexeme_count + len(self.new_lexemes)
        for programs in self.new_programs.values():
            for program in programs:
                if not isinstance(program, tuple) or not program:
                    raise ISQLValidationError("HIERARCHICAL_DELTA_PROGRAM_REQUIRED")
                for value_id in program:
                    if (
                        not isinstance(value_id, int)
                        or isinstance(value_id, bool)
                        or value_id <= 0
                        or value_id > max_lexeme
                    ):
                        raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_LEXEME_ID")

    def is_noop(self) -> bool:
        return not self.new_lexemes and all(not rows for rows in self.new_programs.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": HIERARCHICAL_DELTA_SCHEMA,
            "registry_id": self.registry_id,
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "previous_hierarchical_hash": self.previous_hierarchical_hash,
            "target_hierarchical_hash": self.target_hierarchical_hash,
            "canonical_registry_id": self.canonical_registry_id,
            "canonical_revision": self.canonical_revision,
            "canonical_hash": self.canonical_hash,
            "base_lexeme_count": self.base_lexeme_count,
            "new_lexemes": list(self.new_lexemes),
            "new_programs": {
                name: [list(program) for program in self.new_programs[name]]
                for name in SPECTRAL_NAMESPACES
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HierarchicalRegistryDelta":
        if not isinstance(value, Mapping) or value.get("schema") != HIERARCHICAL_DELTA_SCHEMA:
            raise ISQLValidationError("INVALID_HIERARCHICAL_DELTA_SCHEMA")
        raw_programs = value.get("new_programs")
        if not isinstance(raw_programs, Mapping):
            raise ISQLValidationError("HIERARCHICAL_DELTA_PROGRAMS_REQUIRED")
        raw_lexemes = value.get("new_lexemes")
        if not isinstance(raw_lexemes, list):
            raise ISQLValidationError("HIERARCHICAL_DELTA_LEXEMES_REQUIRED")
        return cls(
            registry_id=str(value.get("registry_id", "")),
            from_revision=int(value.get("from_revision", -1)),
            to_revision=int(value.get("to_revision", -1)),
            previous_hierarchical_hash=str(value.get("previous_hierarchical_hash", "")),
            target_hierarchical_hash=str(value.get("target_hierarchical_hash", "")),
            canonical_registry_id=str(value.get("canonical_registry_id", "")),
            canonical_revision=int(value.get("canonical_revision", -1)),
            canonical_hash=str(value.get("canonical_hash", "")),
            base_lexeme_count=int(value.get("base_lexeme_count", -1)),
            new_lexemes=tuple(str(x) for x in raw_lexemes),
            new_programs={
                name: tuple(
                    tuple(int(x) for x in program)
                    for program in raw_programs.get(name, [])
                )
                for name in SPECTRAL_NAMESPACES
            },
        )

    def canonical_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())


def _assert_hierarchical_extension(previous: HierarchicalRegistry, current: HierarchicalRegistry) -> None:
    if previous.registry_id != current.registry_id:
        raise ISQLValidationError("HIERARCHICAL_REGISTRY_LINEAGE_MISMATCH")
    if current.revision < previous.revision:
        raise ISQLValidationError("HIERARCHICAL_REVISION_REGRESSION")
    if len(current.lexemes) < len(previous.lexemes) or current.lexemes[: len(previous.lexemes)] != previous.lexemes:
        raise ISQLValidationError("HIERARCHICAL_LEXEMES_NOT_APPEND_ONLY")
    for namespace in SPECTRAL_NAMESPACES:
        old = previous.programs[namespace]
        new = current.programs[namespace]
        if len(new) < len(old) or new[: len(old)] != old:
            raise ISQLValidationError("HIERARCHICAL_PROGRAMS_NOT_APPEND_ONLY")


def make_hierarchical_delta(
    previous: HierarchicalRegistry,
    current: HierarchicalRegistry,
) -> HierarchicalRegistryDelta:
    if not isinstance(previous, HierarchicalRegistry) or not isinstance(current, HierarchicalRegistry):
        raise ISQLValidationError("HIERARCHICAL_DELTA_REQUIRES_REGISTRIES")
    # Both endpoints must be independently reconstructable before diffing.
    reconstruct_spectral_registry(previous)
    reconstruct_spectral_registry(current)
    _assert_hierarchical_extension(previous, current)
    return HierarchicalRegistryDelta(
        registry_id=current.registry_id,
        from_revision=previous.revision,
        to_revision=current.revision,
        previous_hierarchical_hash=previous.content_hash(),
        target_hierarchical_hash=current.content_hash(),
        canonical_registry_id=current.canonical_registry_id,
        canonical_revision=current.canonical_revision,
        canonical_hash=current.canonical_hash,
        base_lexeme_count=len(previous.lexemes),
        new_lexemes=tuple(current.lexemes[len(previous.lexemes):]),
        new_programs={
            namespace: tuple(current.programs[namespace][len(previous.programs[namespace]):])
            for namespace in SPECTRAL_NAMESPACES
        },
    )


def apply_hierarchical_delta(
    previous: HierarchicalRegistry,
    delta: HierarchicalRegistryDelta,
) -> HierarchicalRegistry:
    if not isinstance(previous, HierarchicalRegistry) or not isinstance(delta, HierarchicalRegistryDelta):
        raise ISQLValidationError("HIERARCHICAL_APPLY_REQUIRES_REGISTRY_AND_DELTA")
    if previous.content_hash() != delta.previous_hierarchical_hash:
        raise ISQLValidationError("HIERARCHICAL_DELTA_PREVIOUS_HASH_MISMATCH")
    if previous.revision != delta.from_revision:
        raise ISQLValidationError("HIERARCHICAL_DELTA_FROM_REVISION_MISMATCH")
    if len(previous.lexemes) != delta.base_lexeme_count:
        raise ISQLValidationError("HIERARCHICAL_DELTA_BASE_LEXEME_COUNT_MISMATCH")
    if any(x in previous.lexemes for x in delta.new_lexemes):
        raise ISQLValidationError("HIERARCHICAL_DELTA_REINTRODUCES_LEXEME")

    lexemes = list(previous.lexemes) + list(delta.new_lexemes)
    programs = {
        namespace: list(previous.programs[namespace]) + list(delta.new_programs[namespace])
        for namespace in SPECTRAL_NAMESPACES
    }
    rebuilt = HierarchicalRegistry(
        registry_id=delta.registry_id,
        revision=delta.to_revision,
        canonical_registry_id=delta.canonical_registry_id,
        canonical_revision=delta.canonical_revision,
        canonical_hash=delta.canonical_hash,
        lexemes=lexemes,
        programs=programs,
    )
    if rebuilt.content_hash() != delta.target_hierarchical_hash:
        raise ISQLValidationError("HIERARCHICAL_DELTA_TARGET_HASH_MISMATCH")
    reconstruct_spectral_registry(rebuilt)
    return rebuilt


class HierarchicalRegistryStore:
    def __init__(self, root: str | "Path") -> None:
        from pathlib import Path
        self.root = Path(root)
        self.registry_dir = self.root / "hierarchical_registry"
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_path(self):
        return self.registry_dir / "current.json"

    def _revision_path(self, revision: int):
        return self.registry_dir / f"rev-{revision:06d}.json"

    def _delta_path(self, revision: int):
        return self.registry_dir / f"delta-{revision:06d}.json"

    @staticmethod
    def _write_json(path, value: Mapping[str, Any]) -> None:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)

    def load_current(self) -> HierarchicalRegistry:
        if not self.current_path.exists():
            return HierarchicalRegistry.empty()
        return HierarchicalRegistry.from_dict(json.loads(self.current_path.read_text(encoding="utf-8")))

    def load_revision(self, revision: int) -> HierarchicalRegistry:
        if revision == 0 and not self._revision_path(0).exists():
            return HierarchicalRegistry.empty()
        path = self._revision_path(revision)
        if not path.exists():
            raise ISQLValidationError("HIERARCHICAL_REVISION_NOT_FOUND")
        return HierarchicalRegistry.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def load_delta(self, revision: int) -> HierarchicalRegistryDelta:
        path = self._delta_path(revision)
        if not path.exists():
            raise ISQLValidationError("HIERARCHICAL_DELTA_NOT_FOUND")
        return HierarchicalRegistryDelta.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def commit(self, candidate: HierarchicalRegistry) -> HierarchicalRegistry:
        current = self.load_current()
        if candidate.content_hash() == current.content_hash():
            return current
        if candidate.revision <= current.revision:
            raise ISQLValidationError("HIERARCHICAL_REVISION_NOT_FORWARD")
        delta = make_hierarchical_delta(current, candidate)
        replayed = apply_hierarchical_delta(current, delta)
        if replayed.to_dict() != candidate.to_dict():
            raise ISQLValidationError("HIERARCHICAL_STORE_REPLAY_MISMATCH")
        self._write_json(self._revision_path(candidate.revision), candidate.to_dict())
        self._write_json(self._delta_path(candidate.revision), delta.to_dict())
        self._write_json(self.current_path, candidate.to_dict())
        return candidate
