from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from .code import ISQLCode
from .errors import ISQLExecutionError
from .store import MemoryStore


@dataclass(frozen=True, slots=True)
class DecodeResult:
    code: ISQLCode
    address_wire: str
    resolution: str
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
            "recovered_text": self.recovered_text,
            "data": self.data,
            "exact": self.exact,
            "decoder_id": self.decoder_id,
            "decoder_contract": self.decoder_contract,
        }


class Decoder(Protocol):
    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        ...


class DeterministicMemoryDecoder:
    decoder_id = "deterministic-memory-decoder/v0.1"
    decoder_contract = "isql-memory-recovery/v0.1"

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def decode(self, code: ISQLCode, *, context: Mapping[str, Any] | None = None) -> DecodeResult:
        if code.domain != "MEM":
            raise ISQLExecutionError("DETERMINISTIC_MEMORY_DECODER_REQUIRES_MEM_CODE")
        record = self.store.find_by_memory_code(code)
        layer = record.layers[code.resolution]
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
            recovered_text=rendered,
            data=base_result.data,
            exact=False,
            decoder_id=self.decoder_id,
            decoder_contract=self.decoder_contract,
        )
