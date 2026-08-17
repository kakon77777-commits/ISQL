from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from .address import address_text
from .code import ISQLCode, parse_code
from .errors import ISQLValidationError

ENCODER_VERSION = "isql-mem-encoder/v0.1"
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)?", re.UNICODE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|[\r\n]+")


def _canonical_json(value: object) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ISQLValidationError("MEMORY_DATA_NOT_CANONICAL_JSON") from exc
    return text.encode("utf-8")


def _memory_code(resolution: str, address: ISQLCode, data: Mapping[str, Any]) -> ISQLCode:
    material = {
        "encoder": ENCODER_VERSION,
        "address": address.to_wire(),
        "resolution": resolution,
        "data": dict(data),
    }
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
        return cls(resolution=resolution, code=code, data=dict(data))


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    address: ISQLCode
    encoder_version: str
    source_type: str
    layers: dict[str, MemoryLayer]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "isql.memory-record/v0.1",
            "address": self.address.to_wire(),
            "encoder_version": self.encoder_version,
            "source_type": self.source_type,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MemoryRecord":
        if value.get("schema") != "isql.memory-record/v0.1":
            raise ISQLValidationError("INVALID_MEMORY_RECORD_SCHEMA")
        address = parse_code(str(value["address"]))
        if address.domain != "ADDR":
            raise ISQLValidationError("MEMORY_ADDRESS_NOT_ADDR_DOMAIN")
        raw_layers = value.get("layers")
        if not isinstance(raw_layers, dict):
            raise ISQLValidationError("MEMORY_LAYERS_MUST_BE_OBJECT")
        layers = {str(k): MemoryLayer.from_dict(v) for k, v in raw_layers.items()}
        return cls(
            address=address,
            encoder_version=str(value["encoder_version"]),
            source_type=str(value["source_type"]),
            layers=layers,
        )


def encode_text_memory(
    text: str,
    *,
    metadata: Mapping[str, Any] | None = None,
    source_ref: str | None = None,
    include_exact_source: bool = True,
) -> MemoryRecord:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    metadata_obj = dict(metadata or {})
    _canonical_json(metadata_obj)
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

    return MemoryRecord(
        address=address,
        encoder_version=ENCODER_VERSION,
        source_type="text",
        layers=layers,
    )
