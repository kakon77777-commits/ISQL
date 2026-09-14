from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import unicodedata
from typing import Iterable

from .errors import ISQLValidationError
from .semantics import SemanticAnalysis


SEMANTIC_ADDRESS_INDEX_SCHEMA = "isql.semantic-address-index/v0.1"
SEMANTIC_ADDRESS_SCHEMA = "isql.semantic-address/v0.1"

_ATOM_WEIGHTS: dict[str, int] = {
    "relation": 9,
    "entity": 7,
    "concept": 5,
    "intent": 4,
    "tag": 3,
    "claim": 2,
}


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _normalize_text(value: str, *, code: str) -> str:
    if not isinstance(value, str):
        raise ISQLValidationError(code)
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.split()).strip().casefold()
    if not normalized or "\x00" in normalized:
        raise ISQLValidationError(code)
    return normalized


def _require_hex64(value: str, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ISQLValidationError(code)
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ISQLValidationError(code) from exc
    if len(raw) != 32:
        raise ISQLValidationError(code)
    return value.lower()


@dataclass(frozen=True, slots=True, order=True)
class SemanticProfileBinding:
    analyzer_id: str
    revision: int
    contract_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "analyzer_id",
            _normalize_text(self.analyzer_id, code="SEMANTIC_PROFILE_ANALYZER_ID_INVALID"),
        )
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 0:
            raise ISQLValidationError("SEMANTIC_PROFILE_REVISION_INVALID")
        object.__setattr__(
            self,
            "contract_sha256",
            _require_hex64(self.contract_sha256, "SEMANTIC_PROFILE_CONTRACT_HASH_INVALID"),
        )

    @classmethod
    def from_analysis(cls, analysis: SemanticAnalysis, *, revision: int = 0) -> "SemanticProfileBinding":
        if not isinstance(analysis, SemanticAnalysis):
            raise ISQLValidationError("SEMANTIC_ANALYSIS_REQUIRED")
        return cls(
            analyzer_id=analysis.analyzer_id,
            revision=revision,
            contract_sha256=hashlib.sha256(analysis.analyzer_contract.encode("utf-8")).hexdigest(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "analyzer_id": self.analyzer_id,
            "revision": self.revision,
            "contract_sha256": self.contract_sha256,
        }


@dataclass(frozen=True, slots=True, order=True)
class SemanticAtom:
    kind: str
    value: str

    def __post_init__(self) -> None:
        if self.kind not in _ATOM_WEIGHTS:
            raise ISQLValidationError("SEMANTIC_ATOM_KIND_INVALID")
        object.__setattr__(
            self,
            "value",
            _normalize_text(self.value, code="SEMANTIC_ATOM_VALUE_INVALID"),
        )

    @property
    def weight(self) -> int:
        return _ATOM_WEIGHTS[self.kind]

    def evidence(self) -> str:
        return f"{self.kind}:{self.value}"

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True, slots=True)
class SemanticAddress:
    profile: SemanticProfileBinding
    language: str
    atoms: tuple[SemanticAtom, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile, SemanticProfileBinding):
            raise ISQLValidationError("SEMANTIC_PROFILE_BINDING_REQUIRED")
        object.__setattr__(
            self,
            "language",
            _normalize_text(self.language, code="SEMANTIC_ADDRESS_LANGUAGE_INVALID"),
        )
        if not isinstance(self.atoms, tuple) or not self.atoms:
            raise ISQLValidationError("SEMANTIC_ADDRESS_ATOMS_REQUIRED")
        canonical = tuple(sorted(set(self.atoms)))
        if canonical != self.atoms:
            raise ISQLValidationError("SEMANTIC_ADDRESS_ATOMS_NONCANONICAL")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SEMANTIC_ADDRESS_SCHEMA,
            "profile": self.profile.to_dict(),
            "language": self.language,
            "atoms": [atom.to_dict() for atom in self.atoms],
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def _relation_value(subject: str, predicate: str, object_: str) -> str:
    values = [
        _normalize_text(subject, code="SEMANTIC_RELATION_SUBJECT_INVALID"),
        _normalize_text(predicate, code="SEMANTIC_RELATION_PREDICATE_INVALID"),
        _normalize_text(object_, code="SEMANTIC_RELATION_OBJECT_INVALID"),
    ]
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def semantic_address_from_analysis(
    analysis: SemanticAnalysis,
    *,
    profile_revision: int = 0,
) -> SemanticAddress:
    if not isinstance(analysis, SemanticAnalysis):
        raise ISQLValidationError("SEMANTIC_ANALYSIS_REQUIRED")
    coords = analysis.coordinates
    atoms: set[SemanticAtom] = set()
    atoms.update(SemanticAtom("concept", value) for value in coords.concepts)
    atoms.update(SemanticAtom("entity", value) for value in coords.entities)
    atoms.update(SemanticAtom("claim", value) for value in coords.claims)
    atoms.update(SemanticAtom("tag", value) for value in coords.tags)
    if coords.intent is not None:
        atoms.add(SemanticAtom("intent", coords.intent))
    for relation in coords.relations:
        atoms.add(SemanticAtom(
            "relation",
            _relation_value(relation.subject, relation.predicate, relation.object),
        ))
    if not atoms:
        raise ISQLValidationError("SEMANTIC_ADDRESS_NO_SEARCHABLE_ATOMS")
    return SemanticAddress(
        profile=SemanticProfileBinding.from_analysis(analysis, revision=profile_revision),
        language=coords.language,
        atoms=tuple(sorted(atoms)),
    )


@dataclass(frozen=True, slots=True, order=True)
class ExactStateRef:
    entity_id: str
    state_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entity_id",
            _normalize_text(self.entity_id, code="EXACT_ENTITY_ID_INVALID"),
        )
        object.__setattr__(
            self,
            "state_sha256",
            _require_hex64(self.state_sha256, "EXACT_STATE_HASH_INVALID"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"entity_id": self.entity_id, "state_sha256": self.state_sha256}


def exact_state_ref(entity_id: str, state_bytes: bytes) -> ExactStateRef:
    if not isinstance(state_bytes, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("EXACT_STATE_BYTES_REQUIRED")
    raw = bytes(state_bytes)
    return ExactStateRef(
        entity_id=entity_id,
        state_sha256=hashlib.sha256(raw).hexdigest(),
    )


def verify_exact_state(state_bytes: bytes, exact: ExactStateRef) -> bool:
    if not isinstance(state_bytes, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("EXACT_STATE_BYTES_REQUIRED")
    if not isinstance(exact, ExactStateRef):
        raise ISQLValidationError("EXACT_STATE_REF_REQUIRED")
    return hashlib.sha256(bytes(state_bytes)).hexdigest() == exact.state_sha256


@dataclass(frozen=True, slots=True)
class SemanticAddressIndexEntry:
    exact: ExactStateRef
    address: SemanticAddress

    def __post_init__(self) -> None:
        if not isinstance(self.exact, ExactStateRef):
            raise ISQLValidationError("SEMANTIC_INDEX_EXACT_REF_REQUIRED")
        if not isinstance(self.address, SemanticAddress):
            raise ISQLValidationError("SEMANTIC_INDEX_ADDRESS_REQUIRED")

    def to_dict(self) -> dict[str, object]:
        return {"exact": self.exact.to_dict(), "address": self.address.to_dict()}


@dataclass(frozen=True, slots=True)
class SemanticAddressIndex:
    entries: tuple[SemanticAddressIndexEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise ISQLValidationError("SEMANTIC_INDEX_ENTRIES_REQUIRED")
        keys = [(entry.exact.entity_id, entry.exact.state_sha256) for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise ISQLValidationError("SEMANTIC_INDEX_DUPLICATE_EXACT_REF")
        expected = tuple(sorted(
            self.entries,
            key=lambda entry: (
                entry.address.profile,
                entry.exact.entity_id,
                entry.exact.state_sha256,
                entry.address.content_hash(),
            ),
        ))
        if expected != self.entries:
            raise ISQLValidationError("SEMANTIC_INDEX_ENTRIES_NONCANONICAL")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SEMANTIC_ADDRESS_INDEX_SCHEMA,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def build_semantic_address_index(
    records: Iterable[tuple[str, bytes, SemanticAnalysis]],
    *,
    profile_revision: int = 0,
) -> SemanticAddressIndex:
    entries: list[SemanticAddressIndexEntry] = []
    for entity_id, state_bytes, analysis in records:
        entries.append(SemanticAddressIndexEntry(
            exact=exact_state_ref(entity_id, state_bytes),
            address=semantic_address_from_analysis(
                analysis,
                profile_revision=profile_revision,
            ),
        ))
    entries.sort(key=lambda entry: (
        entry.address.profile,
        entry.exact.entity_id,
        entry.exact.state_sha256,
        entry.address.content_hash(),
    ))
    return SemanticAddressIndex(entries=tuple(entries))


@dataclass(slots=True)
class _SemanticSearchRuntime:
    postings: dict[tuple[SemanticProfileBinding, SemanticAtom], tuple[int, ...]]
    profile_entry_ids: dict[SemanticProfileBinding, tuple[int, ...]]


@lru_cache(maxsize=16)
def _search_runtime(index: SemanticAddressIndex) -> _SemanticSearchRuntime:
    postings_raw: dict[tuple[SemanticProfileBinding, SemanticAtom], list[int]] = defaultdict(list)
    profile_raw: dict[SemanticProfileBinding, list[int]] = defaultdict(list)
    for entry_id, entry in enumerate(index.entries):
        profile_raw[entry.address.profile].append(entry_id)
        for atom in entry.address.atoms:
            postings_raw[(entry.address.profile, atom)].append(entry_id)
    return _SemanticSearchRuntime(
        postings={key: tuple(value) for key, value in postings_raw.items()},
        profile_entry_ids={key: tuple(value) for key, value in profile_raw.items()},
    )


@dataclass(frozen=True, slots=True)
class SemanticCandidate:
    exact: ExactStateRef
    semantic_address_sha256: str
    score: float
    matched_weight: int
    query_weight: int
    matched_atoms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.exact, ExactStateRef):
            raise ISQLValidationError("SEMANTIC_CANDIDATE_EXACT_REF_REQUIRED")
        _require_hex64(
            self.semantic_address_sha256,
            "SEMANTIC_CANDIDATE_ADDRESS_HASH_INVALID",
        )
        if not isinstance(self.score, float) or not 0.0 <= self.score <= 1.0:
            raise ISQLValidationError("SEMANTIC_CANDIDATE_SCORE_INVALID")
        if self.matched_weight <= 0 or self.query_weight <= 0 or self.matched_weight > self.query_weight:
            raise ISQLValidationError("SEMANTIC_CANDIDATE_WEIGHT_INVALID")
        if not isinstance(self.matched_atoms, tuple) or not self.matched_atoms:
            raise ISQLValidationError("SEMANTIC_CANDIDATE_EVIDENCE_REQUIRED")

    def to_dict(self) -> dict[str, object]:
        return {
            "exact": self.exact.to_dict(),
            "semantic_address_sha256": self.semantic_address_sha256,
            "score": self.score,
            "matched_weight": self.matched_weight,
            "query_weight": self.query_weight,
            "matched_atoms": list(self.matched_atoms),
        }


@dataclass(frozen=True, slots=True)
class SemanticResolveResult:
    query_address_sha256: str
    entry_count: int
    profile_entry_count: int
    probe_count: int
    probe_ratio: float
    candidates: tuple[SemanticCandidate, ...]

    def __post_init__(self) -> None:
        _require_hex64(
            self.query_address_sha256,
            "SEMANTIC_RESOLVE_QUERY_HASH_INVALID",
        )
        for value, code in (
            (self.entry_count, "SEMANTIC_RESOLVE_ENTRY_COUNT_INVALID"),
            (self.profile_entry_count, "SEMANTIC_RESOLVE_PROFILE_COUNT_INVALID"),
            (self.probe_count, "SEMANTIC_RESOLVE_PROBE_COUNT_INVALID"),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ISQLValidationError(code)
        if self.profile_entry_count > self.entry_count or self.probe_count > self.profile_entry_count:
            raise ISQLValidationError("SEMANTIC_RESOLVE_COUNT_RELATION_INVALID")
        if not isinstance(self.probe_ratio, float) or not 0.0 <= self.probe_ratio <= 1.0:
            raise ISQLValidationError("SEMANTIC_RESOLVE_PROBE_RATIO_INVALID")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "isql.semantic-resolve-result/v0.1",
            "query_address_sha256": self.query_address_sha256,
            "entry_count": self.entry_count,
            "profile_entry_count": self.profile_entry_count,
            "probe_count": self.probe_count,
            "probe_ratio": self.probe_ratio,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def resolve_semantic_candidates(
    query: SemanticAddress,
    index: SemanticAddressIndex,
    *,
    top_k: int = 8,
) -> SemanticResolveResult:
    if not isinstance(query, SemanticAddress):
        raise ISQLValidationError("SEMANTIC_ADDRESS_REQUIRED")
    if not isinstance(index, SemanticAddressIndex):
        raise ISQLValidationError("SEMANTIC_ADDRESS_INDEX_REQUIRED")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ISQLValidationError("SEMANTIC_RESOLVE_TOP_K_INVALID")

    runtime = _search_runtime(index)
    profile_ids = runtime.profile_entry_ids.get(query.profile, ())
    candidate_ids: set[int] = set()
    for atom in query.atoms:
        candidate_ids.update(runtime.postings.get((query.profile, atom), ()))

    query_atoms = set(query.atoms)
    query_weight = sum(atom.weight for atom in query.atoms)
    candidates: list[SemanticCandidate] = []
    for entry_id in candidate_ids:
        entry = index.entries[entry_id]
        matched = tuple(sorted(query_atoms.intersection(entry.address.atoms)))
        if not matched:
            continue
        matched_weight = sum(atom.weight for atom in matched)
        candidates.append(SemanticCandidate(
            exact=entry.exact,
            semantic_address_sha256=entry.address.content_hash(),
            score=float(matched_weight / query_weight),
            matched_weight=matched_weight,
            query_weight=query_weight,
            matched_atoms=tuple(atom.evidence() for atom in matched),
        ))

    candidates.sort(key=lambda candidate: (
        -candidate.score,
        -candidate.matched_weight,
        candidate.exact.entity_id,
        candidate.exact.state_sha256,
    ))
    probe_count = len(candidate_ids)
    profile_count = len(profile_ids)
    return SemanticResolveResult(
        query_address_sha256=query.content_hash(),
        entry_count=len(index.entries),
        profile_entry_count=profile_count,
        probe_count=probe_count,
        probe_ratio=float(probe_count / max(1, profile_count)),
        candidates=tuple(candidates[:top_k]),
    )
