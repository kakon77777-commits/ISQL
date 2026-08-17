from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from .address import address_text
from .code import ISQLCode, parse_code
from .errors import ISQLValidationError
from .semantics import SemanticAnalysis, SemanticCoordinateSet
from .spectral import SpectralPacket, SpectralRegistryStore, compile_spectral_packet
from .wire import encode_numeric_wire

ENCODER_VERSION = "isql-mem-encoder/v0.1"
SEMANTIC_ENCODER_VERSION = "isql-mem-semantic-encoder/v0.2"
SPECTRAL_ENCODER_VERSION = "isql-mem-spectral-encoder/v0.3"
NUMERIC_ENCODER_VERSION = "isql-mem-numeric-wire-encoder/v0.4"
MEMORY_RECORD_SCHEMA = "isql.memory-record/v0.2"
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)?", re.UNICODE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|[\r\n]+")
_PROFILE_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


def _canonical_json(value: object) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ISQLValidationError("MEMORY_DATA_NOT_CANONICAL_JSON") from exc
    return text.encode("utf-8")


def _validate_profile_id(profile_id: str) -> str:
    if not isinstance(profile_id, str) or not _PROFILE_RE.fullmatch(profile_id):
        raise ISQLValidationError("INVALID_MEMORY_PROFILE_ID")
    return profile_id


def _memory_code(
    resolution: str,
    address: ISQLCode,
    data: Mapping[str, Any],
    *,
    encoder_version: str = ENCODER_VERSION,
    profile_id: str = "baseline",
) -> ISQLCode:
    _validate_profile_id(profile_id)
    # Preserve v0.1 baseline code identity exactly for backward compatibility.
    material: dict[str, Any] = {
        "encoder": encoder_version,
        "address": address.to_wire(),
        "resolution": resolution,
        "data": dict(data),
    }
    if profile_id != "baseline":
        material["profile"] = profile_id
    digest = hashlib.sha256(_canonical_json(material)).digest()
    payload = str(int.from_bytes(digest, "big", signed=False))
    return ISQLCode(
        protocol="ISQL",
        version=1,
        domain="MEM",
        resolution=resolution,
        control="M",
        payload=payload,
    )


def _keywords(text: str, limit: int = 8) -> list[str]:
    tokens = [m.group(0).casefold() for m in _TOKEN_RE.finditer(text)]
    counts: dict[str, int] = {}
    first: dict[str, int] = {}
    for idx, token in enumerate(tokens):
        counts[token] = counts.get(token, 0) + 1
        first.setdefault(token, idx)
    ordered = sorted(counts, key=lambda t: (-counts[t], first[t], t))
    return ordered[:limit]


def _sentences(text: str, limit: int = 12) -> list[str]:
    chunks = [x.strip() for x in _SENTENCE_SPLIT_RE.split(text) if x.strip()]
    return chunks[:limit]


@dataclass(frozen=True, slots=True)
class MemoryLayer:
    resolution: str
    code: ISQLCode
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution": self.resolution,
            "code": self.code.to_wire(),
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MemoryLayer":
        resolution = str(value["resolution"])
        code = parse_code(str(value["code"]))
        if code.domain != "MEM" or code.resolution != resolution:
            raise ISQLValidationError("MEMORY_LAYER_CODE_MISMATCH")
        data = value.get("data")
        if not isinstance(data, dict):
            raise ISQLValidationError("MEMORY_LAYER_DATA_MUST_BE_OBJECT")
        _canonical_json(data)
        return cls(resolution=resolution, code=code, data=dict(data))


@dataclass(frozen=True, slots=True)
class MemoryVariant:
    profile_id: str
    encoder_version: str
    layers: dict[str, MemoryLayer]
    analyzer_id: str | None = None
    analyzer_contract: str | None = None

    def __post_init__(self) -> None:
        _validate_profile_id(self.profile_id)
        if not self.encoder_version:
            raise ISQLValidationError("MEMORY_VARIANT_ENCODER_REQUIRED")
        if set(self.layers) != {"R0", "R1", "R2", "R3", "R4"}:
            raise ISQLValidationError("MEMORY_VARIANT_REQUIRES_R0_TO_R4")
        for resolution, layer in self.layers.items():
            if layer.resolution != resolution:
                raise ISQLValidationError("MEMORY_VARIANT_LAYER_KEY_MISMATCH")
        if (self.analyzer_id is None) != (self.analyzer_contract is None):
            raise ISQLValidationError("ANALYZER_ID_CONTRACT_MUST_PAIR")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "profile_id": self.profile_id,
            "encoder_version": self.encoder_version,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
        }
        if self.analyzer_id is not None:
            out["analyzer_id"] = self.analyzer_id
            out["analyzer_contract"] = self.analyzer_contract
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MemoryVariant":
        raw_layers = value.get("layers")
        if not isinstance(raw_layers, dict):
            raise ISQLValidationError("MEMORY_VARIANT_LAYERS_MUST_BE_OBJECT")
        return cls(
            profile_id=str(value["profile_id"]),
            encoder_version=str(value["encoder_version"]),
            layers={str(k): MemoryLayer.from_dict(v) for k, v in raw_layers.items()},
            analyzer_id=str(value["analyzer_id"]) if value.get("analyzer_id") is not None else None,
            analyzer_contract=str(value["analyzer_contract"]) if value.get("analyzer_contract") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    address: ISQLCode
    source_type: str
    variants: dict[str, MemoryVariant]
    default_profile: str = "baseline"

    def __post_init__(self) -> None:
        if self.address.domain != "ADDR":
            raise ISQLValidationError("MEMORY_ADDRESS_NOT_ADDR_DOMAIN")
        _validate_profile_id(self.default_profile)
        if self.default_profile not in self.variants:
            raise ISQLValidationError("DEFAULT_MEMORY_PROFILE_MISSING")
        for key, variant in self.variants.items():
            if key != variant.profile_id:
                raise ISQLValidationError("MEMORY_VARIANT_KEY_MISMATCH")

    @property
    def layers(self) -> dict[str, MemoryLayer]:
        """Backward-compatible view of the default profile layers."""
        return self.variants[self.default_profile].layers

    @property
    def encoder_version(self) -> str:
        """Backward-compatible encoder version of the default profile."""
        return self.variants[self.default_profile].encoder_version

    def get_layer(self, profile_id: str, resolution: str) -> MemoryLayer:
        return self.variants[profile_id].layers[resolution]

    def to_dict(self) -> dict[str, Any]:
        # Keep v0.1 top-level encoder/layers as a compatibility view of the
        # default profile while making variants canonical in v0.2.
        return {
            "schema": MEMORY_RECORD_SCHEMA,
            "address": self.address.to_wire(),
            "source_type": self.source_type,
            "default_profile": self.default_profile,
            "encoder_version": self.encoder_version,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
            "variants": {k: v.to_dict() for k, v in self.variants.items()},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MemoryRecord":
        schema = value.get("schema")
        address = parse_code(str(value["address"]))
        if address.domain != "ADDR":
            raise ISQLValidationError("MEMORY_ADDRESS_NOT_ADDR_DOMAIN")

        if schema == "isql.memory-record/v0.1":
            raw_layers = value.get("layers")
            if not isinstance(raw_layers, dict):
                raise ISQLValidationError("MEMORY_LAYERS_MUST_BE_OBJECT")
            baseline = MemoryVariant(
                profile_id="baseline",
                encoder_version=str(value["encoder_version"]),
                layers={str(k): MemoryLayer.from_dict(v) for k, v in raw_layers.items()},
            )
            return cls(
                address=address,
                source_type=str(value["source_type"]),
                variants={"baseline": baseline},
                default_profile="baseline",
            )

        if schema != MEMORY_RECORD_SCHEMA:
            raise ISQLValidationError("INVALID_MEMORY_RECORD_SCHEMA")
        raw_variants = value.get("variants")
        if not isinstance(raw_variants, dict) or not raw_variants:
            raise ISQLValidationError("MEMORY_VARIANTS_MUST_BE_NONEMPTY_OBJECT")
        variants = {str(k): MemoryVariant.from_dict(v) for k, v in raw_variants.items()}
        return cls(
            address=address,
            source_type=str(value["source_type"]),
            variants=variants,
            default_profile=str(value.get("default_profile", "baseline")),
        )


def _baseline_variant(
    text: str,
    *,
    metadata_obj: dict[str, Any],
    source_ref: str | None,
    include_exact_source: bool,
) -> tuple[ISQLCode, MemoryVariant]:
    address = address_text(text)
    utf8 = text.encode("utf-8")
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    keywords = _keywords(text)
    sentences = _sentences(text)

    layer_data: dict[str, dict[str, Any]] = {
        "R0": {
            "address": address.to_wire(),
            "source_type": "text",
            "byte_length": len(utf8),
            "char_length": len(text),
        },
        "R1": {
            "preview": normalized_text[:160],
            "keywords": keywords,
        },
        "R2": {
            "keywords": keywords,
            "sentence_count_observed": len(_SENTENCE_SPLIT_RE.split(text)),
            "sentence_heads": sentences,
        },
        "R3": {
            "normalized_text": normalized_text,
            "metadata": metadata_obj,
        },
        "R4": {
            "exact_sha256": hashlib.sha256(utf8).hexdigest(),
            "source_ref": source_ref,
        },
    }
    if include_exact_source:
        layer_data["R4"]["exact_source"] = text

    layers: dict[str, MemoryLayer] = {}
    for resolution in ("R0", "R1", "R2", "R3", "R4"):
        data = layer_data[resolution]
        layers[resolution] = MemoryLayer(
            resolution=resolution,
            code=_memory_code(resolution, address, data),
            data=data,
        )
    return address, MemoryVariant(
        profile_id="baseline",
        encoder_version=ENCODER_VERSION,
        layers=layers,
    )



def _semantic_variant(
    text: str,
    *,
    address: ISQLCode,
    metadata_obj: dict[str, Any],
    source_ref: str | None,
    include_exact_source: bool,
    analysis: SemanticAnalysis,
) -> MemoryVariant:
    utf8 = text.encode("utf-8")
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    coords = analysis.coordinates
    analyzer = {
        "analyzer_id": analysis.analyzer_id,
        "analyzer_contract": analysis.analyzer_contract,
    }
    layer_data: dict[str, dict[str, Any]] = {
        "R0": {
            "address": address.to_wire(),
            "source_type": "text",
            "byte_length": len(utf8),
            "char_length": len(text),
            "profile": "semantic",
            "analyzer": analyzer,
        },
        "R1": {
            "summary": coords.summary,
            "anchors": list(coords.concepts[:5]),
            "intent": coords.intent,
            "tags": list(coords.tags[:6]),
            "language": coords.language,
            "analyzer": analyzer,
        },
        "R2": {
            "coordinates": coords.to_dict(),
            "analyzer": analyzer,
        },
        "R3": {
            "normalized_text": normalized_text,
            "metadata": metadata_obj,
            "semantic_analysis": analysis.to_dict(),
        },
        "R4": {
            "exact_sha256": hashlib.sha256(utf8).hexdigest(),
            "source_ref": source_ref,
            "profile": "semantic",
            "analyzer": analyzer,
        },
    }
    if include_exact_source:
        layer_data["R4"]["exact_source"] = text

    layers: dict[str, MemoryLayer] = {}
    for resolution in ("R0", "R1", "R2", "R3", "R4"):
        data = layer_data[resolution]
        layers[resolution] = MemoryLayer(
            resolution=resolution,
            code=_memory_code(
                resolution,
                address,
                data,
                encoder_version=SEMANTIC_ENCODER_VERSION,
                profile_id="semantic",
            ),
            data=data,
        )
    return MemoryVariant(
        profile_id="semantic",
        encoder_version=SEMANTIC_ENCODER_VERSION,
        layers=layers,
        analyzer_id=analysis.analyzer_id,
        analyzer_contract=analysis.analyzer_contract,
    )


def _spectral_variant(
    text: str,
    *,
    address: ISQLCode,
    metadata_obj: dict[str, Any],
    source_ref: str | None,
    include_exact_source: bool,
    analysis: SemanticAnalysis,
    registry_store: SpectralRegistryStore,
) -> MemoryVariant:
    utf8 = text.encode("utf-8")
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    coords = analysis.coordinates
    r1_coords = SemanticCoordinateSet(
        summary=coords.summary,
        concepts=coords.concepts[:5],
        entities=(),
        relations=(),
        claims=(),
        intent=coords.intent,
        uncertainty=(),
        tags=coords.tags[:6],
        language=coords.language,
    )
    # Compile the full R2 vocabulary first so its registry_delta_bytes carries
    # the honest cold-start registry growth. R1 then reuses that vocabulary.
    r2_compile = compile_spectral_packet(coords, registry_store)
    r1_compile = compile_spectral_packet(r1_coords, registry_store)
    analyzer = {
        "analyzer_id": analysis.analyzer_id,
        "analyzer_contract": analysis.analyzer_contract,
    }
    layer_data: dict[str, dict[str, Any]] = {
        "R0": {
            "address": address.to_wire(),
            "source_type": "text",
            "byte_length": len(utf8),
            "char_length": len(text),
            "profile": "spectral",
        },
        "R1": {"packet": r1_compile.packet.to_dict()},
        "R2": {"packet": r2_compile.packet.to_dict()},
        "R3": {
            "normalized_text": normalized_text,
            "metadata": metadata_obj,
            "semantic_analysis": analysis.to_dict(),
            "spectral_packet": r2_compile.packet.to_dict(),
        },
        "R4": {
            "exact_sha256": hashlib.sha256(utf8).hexdigest(),
            "source_ref": source_ref,
            "profile": "spectral",
            "analyzer": analyzer,
        },
    }
    if include_exact_source:
        layer_data["R4"]["exact_source"] = text

    layers: dict[str, MemoryLayer] = {}
    for resolution in ("R0", "R1", "R2", "R3", "R4"):
        data = layer_data[resolution]
        layers[resolution] = MemoryLayer(
            resolution=resolution,
            code=_memory_code(
                resolution,
                address,
                data,
                encoder_version=SPECTRAL_ENCODER_VERSION,
                profile_id="spectral",
            ),
            data=data,
        )
    return MemoryVariant(
        profile_id="spectral",
        encoder_version=SPECTRAL_ENCODER_VERSION,
        layers=layers,
        analyzer_id=analysis.analyzer_id,
        analyzer_contract=analysis.analyzer_contract,
    )



def _numeric_variant(
    text: str,
    *,
    address: ISQLCode,
    metadata_obj: dict[str, Any],
    source_ref: str | None,
    include_exact_source: bool,
    analysis: SemanticAnalysis,
    spectral_variant: MemoryVariant,
) -> MemoryVariant:
    utf8 = text.encode("utf-8")
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    r1_packet = SpectralPacket.from_dict(spectral_variant.layers["R1"].data["packet"])
    r2_packet = SpectralPacket.from_dict(spectral_variant.layers["R2"].data["packet"])
    r1_wire = encode_numeric_wire(r1_packet)
    r2_wire = encode_numeric_wire(r2_packet)
    analyzer = {
        "analyzer_id": analysis.analyzer_id,
        "analyzer_contract": analysis.analyzer_contract,
    }
    layer_data: dict[str, dict[str, Any]] = {
        "R0": {
            "address": address.to_wire(),
            "source_type": "text",
            "byte_length": len(utf8),
            "char_length": len(text),
            "profile": "numeric",
        },
        "R1": {"wire": r1_wire},
        "R2": {"wire": r2_wire},
        "R3": {
            "normalized_text": normalized_text,
            "metadata": metadata_obj,
            "wire": r2_wire,
        },
        "R4": {
            "exact_sha256": hashlib.sha256(utf8).hexdigest(),
            "source_ref": source_ref,
            "profile": "numeric",
            "analyzer": analyzer,
        },
    }
    if include_exact_source:
        layer_data["R4"]["exact_source"] = text

    layers: dict[str, MemoryLayer] = {}
    for resolution in ("R0", "R1", "R2", "R3", "R4"):
        data = layer_data[resolution]
        layers[resolution] = MemoryLayer(
            resolution=resolution,
            code=_memory_code(
                resolution,
                address,
                data,
                encoder_version=NUMERIC_ENCODER_VERSION,
                profile_id="numeric",
            ),
            data=data,
        )
    return MemoryVariant(
        profile_id="numeric",
        encoder_version=NUMERIC_ENCODER_VERSION,
        layers=layers,
        analyzer_id=analysis.analyzer_id,
        analyzer_contract=analysis.analyzer_contract,
    )

def encode_text_memory(
    text: str,
    *,
    metadata: Mapping[str, Any] | None = None,
    source_ref: str | None = None,
    include_exact_source: bool = True,
    semantic_analysis: SemanticAnalysis | None = None,
    spectral_registry_store: SpectralRegistryStore | None = None,
    numeric_wire: bool = False,
) -> MemoryRecord:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    metadata_obj = dict(metadata or {})
    _canonical_json(metadata_obj)
    address, baseline = _baseline_variant(
        text,
        metadata_obj=metadata_obj,
        source_ref=source_ref,
        include_exact_source=include_exact_source,
    )
    variants: dict[str, MemoryVariant] = {"baseline": baseline}
    if semantic_analysis is not None:
        if not isinstance(semantic_analysis, SemanticAnalysis):
            raise ISQLValidationError("SEMANTIC_ANALYSIS_MUST_BE_TYPED")
        variants["semantic"] = _semantic_variant(
            text,
            address=address,
            metadata_obj=metadata_obj,
            source_ref=source_ref,
            include_exact_source=include_exact_source,
            analysis=semantic_analysis,
        )
        if spectral_registry_store is not None:
            spectral_variant = _spectral_variant(
                text,
                address=address,
                metadata_obj=metadata_obj,
                source_ref=source_ref,
                include_exact_source=include_exact_source,
                analysis=semantic_analysis,
                registry_store=spectral_registry_store,
            )
            variants["spectral"] = spectral_variant
            if numeric_wire:
                variants["numeric"] = _numeric_variant(
                    text,
                    address=address,
                    metadata_obj=metadata_obj,
                    source_ref=source_ref,
                    include_exact_source=include_exact_source,
                    analysis=semantic_analysis,
                    spectral_variant=spectral_variant,
                )
        elif numeric_wire:
            raise ISQLValidationError("NUMERIC_WIRE_REQUIRES_SPECTRAL_REGISTRY")
    return MemoryRecord(
        address=address,
        source_type="text",
        variants=variants,
        default_profile="baseline",
    )
