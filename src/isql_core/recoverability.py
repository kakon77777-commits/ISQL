from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from .decoder import DecodeResult, DeterministicMemoryDecoder, SemanticCoordinateDecoder
from .memory import MemoryRecord
from .semantics import SemanticCoordinateSet
from .store import MemoryStore

_TOKEN_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)?", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {m.group(0).casefold() for m in _TOKEN_RE.finditer(text)}


def token_jaccard(source: str, recovered: str) -> float:
    a = _tokens(source)
    b = _tokens(recovered)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    resolution: str
    profile_id: str
    decoder_id: str
    decoder_contract: str
    exact: bool
    semantic_score: float
    source_chars: int
    recovered_chars: int

    def to_dict(self) -> dict[str, object]:
        return {
            "resolution": self.resolution,
            "profile_id": self.profile_id,
            "decoder_id": self.decoder_id,
            "decoder_contract": self.decoder_contract,
            "exact": self.exact,
            "semantic_score": self.semantic_score,
            "source_chars": self.source_chars,
            "recovered_chars": self.recovered_chars,
        }


def evaluate_recovery(source: str, result: DecodeResult) -> RecoveryReport:
    recovered = result.recovered_text or ""
    exact = bool(result.exact and recovered == source)
    semantic_score = token_jaccard(source, recovered)
    return RecoveryReport(
        resolution=result.resolution,
        profile_id=result.profile_id,
        decoder_id=result.decoder_id,
        decoder_contract=result.decoder_contract,
        exact=exact,
        semantic_score=semantic_score,
        source_chars=len(source),
        recovered_chars=len(recovered),
    )


def _norm_set(values: tuple[str, ...]) -> set[str]:
    return {x.strip().casefold() for x in values if x.strip()}


def _relation_set(coords: SemanticCoordinateSet) -> set[tuple[str, str, str]]:
    return {
        (r.subject.casefold(), r.predicate.casefold(), r.object.casefold())
        for r in coords.relations
    }


def _recall(reference: set[Any], observed: set[Any]) -> float:
    if not reference:
        return 1.0
    return len(reference & observed) / len(reference)


def _precision(reference: set[Any], observed: set[Any]) -> float:
    if not observed:
        return 1.0 if not reference else 0.0
    return len(reference & observed) / len(observed)


@dataclass(frozen=True, slots=True)
class SemanticReference:
    concepts: tuple[str, ...]
    entities: tuple[str, ...]
    relations: tuple[tuple[str, str, str], ...]
    claims: tuple[str, ...]
    intent: str | None

    @classmethod
    def from_coordinates(cls, coords: SemanticCoordinateSet) -> "SemanticReference":
        return cls(
            concepts=coords.concepts,
            entities=coords.entities,
            relations=tuple((r.subject, r.predicate, r.object) for r in coords.relations),
            claims=coords.claims,
            intent=coords.intent,
        )


@dataclass(frozen=True, slots=True)
class CoordinateFidelityReport:
    concept_precision: float
    concept_recall: float
    concept_f1: float
    entity_recall: float
    relation_recall: float
    claim_recall: float
    intent_match: float
    aggregate: float

    def to_dict(self) -> dict[str, float]:
        return {
            "concept_precision": self.concept_precision,
            "concept_recall": self.concept_recall,
            "concept_f1": self.concept_f1,
            "entity_recall": self.entity_recall,
            "relation_recall": self.relation_recall,
            "claim_recall": self.claim_recall,
            "intent_match": self.intent_match,
            "aggregate": self.aggregate,
        }


def evaluate_coordinate_fidelity(
    reference: SemanticReference,
    observed: SemanticCoordinateSet,
) -> CoordinateFidelityReport:
    ref_concepts = _norm_set(reference.concepts)
    obs_concepts = _norm_set(observed.concepts)
    cp = _precision(ref_concepts, obs_concepts)
    cr = _recall(ref_concepts, obs_concepts)
    cf1 = 0.0 if cp + cr == 0 else 2 * cp * cr / (cp + cr)

    er = _recall(_norm_set(reference.entities), _norm_set(observed.entities))
    ref_rel = {(a.casefold(), b.casefold(), c.casefold()) for a, b, c in reference.relations}
    rr = _recall(ref_rel, _relation_set(observed))
    claim_r = _recall(_norm_set(reference.claims), _norm_set(observed.claims))
    if reference.intent is None:
        intent_match = 1.0 if observed.intent is None else 0.0
    else:
        intent_match = 1.0 if (observed.intent or "").casefold() == reference.intent.casefold() else 0.0
    aggregate = (cf1 + er + rr + claim_r + intent_match) / 5.0
    return CoordinateFidelityReport(
        concept_precision=cp,
        concept_recall=cr,
        concept_f1=cf1,
        entity_recall=er,
        relation_recall=rr,
        claim_recall=claim_r,
        intent_match=intent_match,
        aggregate=aggregate,
    )


@dataclass(frozen=True, slots=True)
class ProfileRecoveryEntry:
    profile_id: str
    code: str
    layer_data_bytes: int
    recovery: RecoveryReport
    coordinate_fidelity: CoordinateFidelityReport | None

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "code": self.code,
            "layer_data_bytes": self.layer_data_bytes,
            "recovery": self.recovery.to_dict(),
            "coordinate_fidelity": self.coordinate_fidelity.to_dict() if self.coordinate_fidelity else None,
        }


@dataclass(frozen=True, slots=True)
class ProfileComparisonReport:
    address: str
    resolution: str
    profiles: dict[str, ProfileRecoveryEntry]

    def to_dict(self) -> dict[str, object]:
        return {
            "address": self.address,
            "resolution": self.resolution,
            "profiles": {k: v.to_dict() for k, v in self.profiles.items()},
        }


def _coords_from_semantic_layer(record: MemoryRecord, resolution: str) -> SemanticCoordinateSet | None:
    layer = record.get_layer("semantic", resolution)
    data = layer.data
    if resolution == "R2" and isinstance(data.get("coordinates"), dict):
        return SemanticCoordinateSet.from_dict(data["coordinates"])
    if resolution == "R1":
        return SemanticCoordinateSet.from_dict({
            "summary": data.get("summary", "semantic memory"),
            "concepts": list(data.get("anchors", [])),
            "entities": [],
            "relations": [],
            "claims": [],
            "intent": data.get("intent"),
            "uncertainty": [],
            "tags": list(data.get("tags", [])),
            "language": data.get("language", "und"),
        })
    if resolution == "R3":
        raw = data.get("semantic_analysis")
        if isinstance(raw, dict) and isinstance(raw.get("coordinates"), dict):
            return SemanticCoordinateSet.from_dict(raw["coordinates"])
    return None


def compare_memory_profiles(
    source: str,
    record: MemoryRecord,
    *,
    store: MemoryStore,
    resolution: str,
    semantic_reference: SemanticReference | None = None,
) -> ProfileComparisonReport:
    entries: dict[str, ProfileRecoveryEntry] = {}
    for profile_id, variant in record.variants.items():
        layer = variant.layers[resolution]
        if profile_id == "baseline":
            decoded = DeterministicMemoryDecoder(store).decode(layer.code)
            fidelity = None
        elif profile_id == "semantic":
            decoded = SemanticCoordinateDecoder(store).decode(layer.code)
            coords = _coords_from_semantic_layer(record, resolution)
            fidelity = (
                evaluate_coordinate_fidelity(semantic_reference, coords)
                if semantic_reference is not None and coords is not None
                else None
            )
        else:
            continue
        data_bytes = len(json.dumps(layer.data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        entries[profile_id] = ProfileRecoveryEntry(
            profile_id=profile_id,
            code=layer.code.to_wire(),
            layer_data_bytes=data_bytes,
            recovery=evaluate_recovery(source, decoded),
            coordinate_fidelity=fidelity,
        )
    return ProfileComparisonReport(
        address=record.address.to_wire(),
        resolution=resolution,
        profiles=entries,
    )
