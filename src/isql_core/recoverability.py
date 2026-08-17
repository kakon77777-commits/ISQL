from __future__ import annotations

from dataclasses import dataclass
import re

from .decoder import DecodeResult

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
    decoder_id: str
    decoder_contract: str
    exact: bool
    semantic_score: float
    source_chars: int
    recovered_chars: int

    def to_dict(self) -> dict[str, object]:
        return {
            "resolution": self.resolution,
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
        decoder_id=result.decoder_id,
        decoder_contract=result.decoder_contract,
        exact=exact,
        semantic_score=semantic_score,
        source_chars=len(source),
        recovered_chars=len(recovered),
    )
