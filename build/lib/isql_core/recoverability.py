from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from .decoder import DecodeResult, DeterministicMemoryDecoder, NumericWireDecoder, SemanticCoordinateDecoder, SpectralCoordinateDecoder
from .memory import MemoryRecord
from .semantics import SemanticCoordinateSet
from .store import MemoryStore
from .spectral import SpectralPacket, SpectralRegistryStore, expand_spectral_packet
from .wire import decode_numeric_wire

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
class SpectralCompactionReport:
    verbose_coordinate_bytes: int
    packet_bytes: int
    registry_delta_bytes: int
    cold_total_bytes: int
    warm_ratio_vs_coordinates: float
    cold_ratio_vs_coordinates: float

    def to_dict(self) -> dict[str, object]:
        return {
            "verbose_coordinate_bytes": self.verbose_coordinate_bytes,
            "packet_bytes": self.packet_bytes,
            "registry_delta_bytes": self.registry_delta_bytes,
            "cold_total_bytes": self.cold_total_bytes,
            "warm_ratio_vs_coordinates": self.warm_ratio_vs_coordinates,
            "cold_ratio_vs_coordinates": self.cold_ratio_vs_coordinates,
        }


@dataclass(frozen=True, slots=True)
class NumericWireCompactionReport:
    verbose_coordinate_bytes: int
    spectral_packet_bytes: int
    wire_bytes: int
    registry_delta_bytes: int
    cold_total_bytes: int
    wire_vs_packet_ratio: float
    warm_ratio_vs_coordinates: float
    cold_ratio_vs_coordinates: float

    def to_dict(self) -> dict[str, object]:
        return {
            "verbose_coordinate_bytes": self.verbose_coordinate_bytes,
            "spectral_packet_bytes": self.spectral_packet_bytes,
            "wire_bytes": self.wire_bytes,
            "registry_delta_bytes": self.registry_delta_bytes,
            "cold_total_bytes": self.cold_total_bytes,
            "wire_vs_packet_ratio": self.wire_vs_packet_ratio,
            "warm_ratio_vs_coordinates": self.warm_ratio_vs_coordinates,
            "cold_ratio_vs_coordinates": self.cold_ratio_vs_coordinates,
        }


@dataclass(frozen=True, slots=True)
class ProfileRecoveryEntry:
    profile_id: str
    code: str
    layer_data_bytes: int
    recovery: RecoveryReport
    coordinate_fidelity: CoordinateFidelityReport | None
    compaction: SpectralCompactionReport | NumericWireCompactionReport | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "code": self.code,
            "layer_data_bytes": self.layer_data_bytes,
            "recovery": self.recovery.to_dict(),
            "coordinate_fidelity": self.coordinate_fidelity.to_dict() if self.coordinate_fidelity else None,
            "compaction": self.compaction.to_dict() if self.compaction else None,
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


def _coords_from_spectral_layer(record: MemoryRecord, store: MemoryStore, resolution: str) -> SemanticCoordinateSet | None:
    layer = record.get_layer("spectral", resolution)
    raw_packet = None
    if resolution in ("R1", "R2"):
        raw_packet = layer.data.get("packet")
    elif resolution == "R3":
        raw_packet = layer.data.get("spectral_packet")
    if not isinstance(raw_packet, dict):
        return None
    packet = SpectralPacket.from_dict(raw_packet)
    return expand_spectral_packet(packet, SpectralRegistryStore(store.root))


def _spectral_compaction(layer_data: dict[str, object], coords: SemanticCoordinateSet | None) -> SpectralCompactionReport | None:
    raw_packet = layer_data.get("packet")
    if not isinstance(raw_packet, dict) or coords is None:
        return None
    packet = SpectralPacket.from_dict(raw_packet)
    packet_bytes = len(packet.canonical_bytes())
    verbose_bytes = len(json.dumps(coords.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    cold_total = packet_bytes + packet.registry_delta_bytes
    return SpectralCompactionReport(
        verbose_coordinate_bytes=verbose_bytes,
        packet_bytes=packet_bytes,
        registry_delta_bytes=packet.registry_delta_bytes,
        cold_total_bytes=cold_total,
        warm_ratio_vs_coordinates=packet_bytes / verbose_bytes,
        cold_ratio_vs_coordinates=cold_total / verbose_bytes,
    )


def _coords_from_numeric_layer(record: MemoryRecord, store: MemoryStore, resolution: str) -> SemanticCoordinateSet | None:
    layer = record.get_layer("numeric", resolution)
    raw_wire = None
    if resolution in ("R1", "R2"):
        raw_wire = layer.data.get("wire")
    elif resolution == "R3":
        raw_wire = layer.data.get("wire")
    if not isinstance(raw_wire, str):
        return None
    packet = decode_numeric_wire(raw_wire)
    return expand_spectral_packet(packet, SpectralRegistryStore(store.root))


def _numeric_compaction(
    record: MemoryRecord,
    resolution: str,
    coords: SemanticCoordinateSet | None,
) -> NumericWireCompactionReport | None:
    if resolution not in ("R1", "R2") or coords is None:
        return None
    raw_wire = record.get_layer("numeric", resolution).data.get("wire")
    raw_packet = record.get_layer("spectral", resolution).data.get("packet")
    if not isinstance(raw_wire, str) or not isinstance(raw_packet, dict):
        return None
    packet = SpectralPacket.from_dict(raw_packet)
    wire_bytes = len(raw_wire.encode("ascii"))
    packet_bytes = len(packet.canonical_bytes())
    verbose_bytes = len(json.dumps(coords.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    cold_total = wire_bytes + packet.registry_delta_bytes
    return NumericWireCompactionReport(
        verbose_coordinate_bytes=verbose_bytes,
        spectral_packet_bytes=packet_bytes,
        wire_bytes=wire_bytes,
        registry_delta_bytes=packet.registry_delta_bytes,
        cold_total_bytes=cold_total,
        wire_vs_packet_ratio=wire_bytes / packet_bytes,
        warm_ratio_vs_coordinates=wire_bytes / verbose_bytes,
        cold_ratio_vs_coordinates=cold_total / verbose_bytes,
    )


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
        compaction = None
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
        elif profile_id == "spectral":
            decoded = SpectralCoordinateDecoder(store).decode(layer.code)
            coords = _coords_from_spectral_layer(record, store, resolution)
            fidelity = (
                evaluate_coordinate_fidelity(semantic_reference, coords)
                if semantic_reference is not None and coords is not None
                else None
            )
            compaction = _spectral_compaction(layer.data, coords)
        elif profile_id == "numeric":
            decoded = NumericWireDecoder(store).decode(layer.code)
            coords = _coords_from_numeric_layer(record, store, resolution)
            fidelity = (
                evaluate_coordinate_fidelity(semantic_reference, coords)
                if semantic_reference is not None and coords is not None
                else None
            )
            compaction = _numeric_compaction(record, resolution, coords)
        else:
            continue
        data_bytes = len(json.dumps(layer.data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        entries[profile_id] = ProfileRecoveryEntry(
            profile_id=profile_id,
            code=layer.code.to_wire(),
            layer_data_bytes=data_bytes,
            recovery=evaluate_recovery(source, decoded),
            coordinate_fidelity=fidelity,
            compaction=compaction,
        )
    return ProfileComparisonReport(
        address=record.address.to_wire(),
        resolution=resolution,
        profiles=entries,
    )
