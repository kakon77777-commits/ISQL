from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from .code import ISQLCode
from .errors import ISQLExecutionError
from .memory import MemoryLayer, MemoryRecord, MemoryVariant
from .semantics import SemanticCoordinateSet
from .store import MemoryStore


@dataclass(frozen=True, slots=True)
class DecodeResult:
    code: ISQLCode
    address_wire: str
    resolution: str
    profile_id: str
    recovered_text: str | None
    data: dict[str, Any]
    exact: bool
    decoder_id: str
    decoder_contract: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.to_wire(),
            "address": self.address_wire,
            "resolution": self.resolution,
            "profile_id": self.profile_id,
            "recovered_text": self.recovered_text,
            "data": self.data,
            "exact": self.exact,
            "decoder_id": self.decoder_id,
            "decoder_contract": self.decoder_contract,
        }


class Decoder(Protocol):
    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        ...


def _locate_variant_layer(record: MemoryRecord, code: ISQLCode) -> tuple[MemoryVariant, MemoryLayer]:
    for variant in record.variants.values():
        layer = variant.layers.get(code.resolution)
        if layer is not None and layer.code == code:
            return variant, layer
    raise ISQLExecutionError("MEMORY_CODE_NOT_PRESENT_IN_RECORD")


class DeterministicMemoryDecoder:
    decoder_id = "deterministic-memory-decoder/v0.2"
    decoder_contract = "isql-memory-recovery/v0.2"

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        if code.domain != "MEM":
            raise ISQLExecutionError("DETERMINISTIC_MEMORY_DECODER_REQUIRES_MEM_CODE")
        record = self.store.find_by_memory_code(code)
        variant, layer = _locate_variant_layer(record, code)
        if variant.profile_id != "baseline":
            raise ISQLExecutionError("DETERMINISTIC_MEMORY_DECODER_REQUIRES_BASELINE_PROFILE")
        data = dict(layer.data)
        recovered: str | None = None
        exact = False
        if code.resolution == "R1":
            recovered = str(data.get("preview", "")) or None
        elif code.resolution == "R2":
            heads = data.get("sentence_heads", [])
            if isinstance(heads, list):
                recovered = " ".join(str(x) for x in heads) or None
        elif code.resolution == "R3":
            recovered = str(data.get("normalized_text", "")) or None
        elif code.resolution == "R4":
            if "exact_source" in data:
                recovered = str(data["exact_source"])
                exact = True
        return DecodeResult(
            code=code,
            address_wire=record.address.to_wire(),
            resolution=code.resolution,
            profile_id=variant.profile_id,
            recovered_text=recovered,
            data=data,
            exact=exact,
            decoder_id=self.decoder_id,
            decoder_contract=self.decoder_contract,
        )


class SemanticCoordinateDecoder:
    decoder_id = "semantic-coordinate-decoder/v0.2"
    decoder_contract = "isql-semantic-memory-recovery/v0.2"

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    @staticmethod
    def _realize_r1(data: Mapping[str, Any]) -> str | None:
        summary = str(data.get("summary", "")).strip()
        anchors = data.get("anchors", [])
        intent = data.get("intent")
        parts: list[str] = []
        if summary:
            parts.append(summary)
        if isinstance(anchors, list) and anchors:
            parts.append("Concepts: " + "; ".join(str(x) for x in anchors) + ".")
        if isinstance(intent, str) and intent.strip():
            parts.append("Intent: " + intent.strip() + ".")
        return " ".join(parts) or None

    @staticmethod
    def _realize_r2(data: Mapping[str, Any]) -> str | None:
        raw = data.get("coordinates")
        if not isinstance(raw, Mapping):
            raise ISQLExecutionError("SEMANTIC_R2_COORDINATES_REQUIRED")
        coords = SemanticCoordinateSet.from_dict(raw)
        parts: list[str] = [coords.summary]
        parts.extend(coords.claims)
        for rel in coords.relations:
            parts.append(f"{rel.subject} {rel.predicate} {rel.object}.")
        if coords.intent:
            parts.append(f"Intent: {coords.intent}.")
        return " ".join(x.strip() for x in parts if x.strip()) or None

    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        if code.domain != "MEM":
            raise ISQLExecutionError("SEMANTIC_COORDINATE_DECODER_REQUIRES_MEM_CODE")
        record = self.store.find_by_memory_code(code)
        variant, layer = _locate_variant_layer(record, code)
        if variant.profile_id != "semantic":
            raise ISQLExecutionError("SEMANTIC_COORDINATE_DECODER_REQUIRES_SEMANTIC_PROFILE")
        data = dict(layer.data)
        recovered: str | None = None
        exact = False
        if code.resolution == "R1":
            recovered = self._realize_r1(data)
        elif code.resolution == "R2":
            recovered = self._realize_r2(data)
        elif code.resolution == "R3":
            recovered = str(data.get("normalized_text", "")) or None
        elif code.resolution == "R4" and "exact_source" in data:
            recovered = str(data["exact_source"])
            exact = True
        return DecodeResult(
            code=code,
            address_wire=record.address.to_wire(),
            resolution=code.resolution,
            profile_id=variant.profile_id,
            recovered_text=recovered,
            data=data,
            exact=exact,
            decoder_id=self.decoder_id,
            decoder_contract=self.decoder_contract,
        )


class CallableAIDecoder:
    """Adapter for an external/AI reconstruction function.

    The callable receives the deterministic base result plus explicit context.
    This adapter never changes address identity and never upgrades a semantic
    reconstruction to exact recovery.
    """

    def __init__(
        self,
        *,
        base: Decoder,
        decoder_id: str,
        decoder_contract: str,
        fn: Callable[[DecodeResult, Mapping[str, Any]], str],
    ) -> None:
        self.base = base
        self.decoder_id = decoder_id
        self.decoder_contract = decoder_contract
        self.fn = fn

    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        base_result = self.base.decode(code, context=context)
        rendered = self.fn(base_result, dict(context or {}))
        if not isinstance(rendered, str):
            raise ISQLExecutionError("AI_DECODER_MUST_RETURN_TEXT")
        return DecodeResult(
            code=base_result.code,
            address_wire=base_result.address_wire,
            resolution=base_result.resolution,
            profile_id=base_result.profile_id,
            recovered_text=rendered,
            data=base_result.data,
            exact=False,
            decoder_id=self.decoder_id,
            decoder_contract=self.decoder_contract,
        )


class SpectralCoordinateDecoder:
    decoder_id = "spectral-coordinate-decoder/v0.3"
    decoder_contract = "isql-spectral-memory-recovery/v0.3"

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def _coords_from_packet_data(self, data: Mapping[str, Any]) -> SemanticCoordinateSet:
        from .spectral import SpectralPacket, SpectralRegistryStore, expand_spectral_packet

        raw = data.get("packet")
        if not isinstance(raw, Mapping):
            raise ISQLExecutionError("SPECTRAL_PACKET_REQUIRED")
        packet = SpectralPacket.from_dict(raw)
        return expand_spectral_packet(packet, SpectralRegistryStore(self.store.root))

    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        if code.domain != "MEM":
            raise ISQLExecutionError("SPECTRAL_COORDINATE_DECODER_REQUIRES_MEM_CODE")
        record = self.store.find_by_memory_code(code)
        variant, layer = _locate_variant_layer(record, code)
        if variant.profile_id != "spectral":
            raise ISQLExecutionError("SPECTRAL_COORDINATE_DECODER_REQUIRES_SPECTRAL_PROFILE")
        data = dict(layer.data)
        recovered: str | None = None
        exact = False
        if code.resolution in ("R1", "R2"):
            coords = self._coords_from_packet_data(data)
            parts: list[str] = [coords.summary]
            if code.resolution == "R1":
                if coords.concepts:
                    parts.append("Concepts: " + "; ".join(coords.concepts) + ".")
            else:
                parts.extend(coords.claims)
                for rel in coords.relations:
                    parts.append(f"{rel.subject} {rel.predicate} {rel.object}.")
            if coords.intent:
                parts.append(f"Intent: {coords.intent}.")
            recovered = " ".join(x.strip() for x in parts if x.strip()) or None
        elif code.resolution == "R3":
            recovered = str(data.get("normalized_text", "")) or None
        elif code.resolution == "R4" and "exact_source" in data:
            recovered = str(data["exact_source"])
            exact = True
        return DecodeResult(
            code=code,
            address_wire=record.address.to_wire(),
            resolution=code.resolution,
            profile_id=variant.profile_id,
            recovered_text=recovered,
            data=data,
            exact=exact,
            decoder_id=self.decoder_id,
            decoder_contract=self.decoder_contract,
        )

class NumericWireDecoder:
    decoder_id = "numeric-wire-decoder/v0.4"
    decoder_contract = "isql-numeric-wire-memory-recovery/v0.4"

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def _coords_from_wire_data(self, data: Mapping[str, Any]) -> SemanticCoordinateSet:
        from .spectral import SpectralRegistryStore, expand_spectral_packet
        from .wire import decode_numeric_wire

        raw = data.get("wire")
        if not isinstance(raw, str):
            raise ISQLExecutionError("NUMERIC_WIRE_REQUIRED")
        packet = decode_numeric_wire(raw)
        return expand_spectral_packet(packet, SpectralRegistryStore(self.store.root))

    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        if code.domain != "MEM":
            raise ISQLExecutionError("NUMERIC_WIRE_DECODER_REQUIRES_MEM_CODE")
        record = self.store.find_by_memory_code(code)
        variant, layer = _locate_variant_layer(record, code)
        if variant.profile_id != "numeric":
            raise ISQLExecutionError("NUMERIC_WIRE_DECODER_REQUIRES_NUMERIC_PROFILE")
        data = dict(layer.data)
        recovered: str | None = None
        exact = False
        if code.resolution in ("R1", "R2"):
            coords = self._coords_from_wire_data(data)
            parts: list[str] = [coords.summary]
            if code.resolution == "R1":
                if coords.concepts:
                    parts.append("Concepts: " + "; ".join(coords.concepts) + ".")
            else:
                parts.extend(coords.claims)
                for rel in coords.relations:
                    parts.append(f"{rel.subject} {rel.predicate} {rel.object}.")
            if coords.intent:
                parts.append(f"Intent: {coords.intent}.")
            recovered = " ".join(x.strip() for x in parts if x.strip()) or None
        elif code.resolution == "R3":
            recovered = str(data.get("normalized_text", "")) or None
        elif code.resolution == "R4" and "exact_source" in data:
            recovered = str(data["exact_source"])
            exact = True
        return DecodeResult(
            code=code,
            address_wire=record.address.to_wire(),
            resolution=code.resolution,
            profile_id=variant.profile_id,
            recovered_text=recovered,
            data=data,
            exact=exact,
            decoder_id=self.decoder_id,
            decoder_contract=self.decoder_contract,
        )
