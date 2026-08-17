from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from .errors import ISQLExecutionError, ISQLValidationError


def _clean_text(value: Any, *, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ISQLValidationError(f"{field.upper()}_MUST_BE_TEXT")
    out = value.strip()
    if not allow_empty and not out:
        raise ISQLValidationError(f"{field.upper()}_MUST_BE_NONEMPTY")
    return out


def _string_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ISQLValidationError(f"{field.upper()}_MUST_BE_LIST")
    seen: set[str] = set()
    out: list[str] = []
    for item in value:
        text = _clean_text(item, field=field)
        if text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class SemanticRelation:
    subject: str
    predicate: str
    object: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _clean_text(self.subject, field="relation_subject"))
        object.__setattr__(self, "predicate", _clean_text(self.predicate, field="relation_predicate"))
        object.__setattr__(self, "object", _clean_text(self.object, field="relation_object"))

    def to_dict(self) -> dict[str, str]:
        return {"subject": self.subject, "predicate": self.predicate, "object": self.object}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticRelation":
        if not isinstance(value, Mapping):
            raise ISQLValidationError("RELATION_MUST_BE_OBJECT")
        required = ("subject", "predicate", "object")
        if any(key not in value for key in required):
            raise ISQLValidationError("RELATION_REQUIRES_SUBJECT_PREDICATE_OBJECT")
        return cls(
            subject=str(value["subject"]),
            predicate=str(value["predicate"]),
            object=str(value["object"]),
        )


@dataclass(frozen=True, slots=True)
class SemanticCoordinateSet:
    summary: str
    concepts: tuple[str, ...]
    entities: tuple[str, ...]
    relations: tuple[SemanticRelation, ...]
    claims: tuple[str, ...]
    intent: str | None
    uncertainty: tuple[str, ...]
    tags: tuple[str, ...]
    language: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _clean_text(self.summary, field="summary"))
        object.__setattr__(self, "language", _clean_text(self.language, field="language"))
        if self.intent is not None:
            object.__setattr__(self, "intent", _clean_text(self.intent, field="intent"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "concepts": list(self.concepts),
            "entities": list(self.entities),
            "relations": [x.to_dict() for x in self.relations],
            "claims": list(self.claims),
            "intent": self.intent,
            "uncertainty": list(self.uncertainty),
            "tags": list(self.tags),
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticCoordinateSet":
        if not isinstance(value, Mapping):
            raise ISQLValidationError("SEMANTIC_COORDINATES_MUST_BE_OBJECT")
        relations_raw = value.get("relations", [])
        if not isinstance(relations_raw, list):
            raise ISQLValidationError("RELATIONS_MUST_BE_LIST")
        intent_raw = value.get("intent")
        if intent_raw is not None and not isinstance(intent_raw, str):
            raise ISQLValidationError("INTENT_MUST_BE_TEXT_OR_NULL")
        return cls(
            summary=_clean_text(value.get("summary"), field="summary"),
            concepts=_string_tuple(value.get("concepts", []), field="concepts"),
            entities=_string_tuple(value.get("entities", []), field="entities"),
            relations=tuple(SemanticRelation.from_dict(x) for x in relations_raw),
            claims=_string_tuple(value.get("claims", []), field="claims"),
            intent=intent_raw.strip() if isinstance(intent_raw, str) and intent_raw.strip() else None,
            uncertainty=_string_tuple(value.get("uncertainty", []), field="uncertainty"),
            tags=_string_tuple(value.get("tags", []), field="tags"),
            language=_clean_text(value.get("language"), field="language"),
        )


@dataclass(frozen=True, slots=True)
class SemanticAnalysis:
    analyzer_id: str
    analyzer_contract: str
    coordinates: SemanticCoordinateSet

    def __post_init__(self) -> None:
        object.__setattr__(self, "analyzer_id", _clean_text(self.analyzer_id, field="analyzer_id"))
        object.__setattr__(self, "analyzer_contract", _clean_text(self.analyzer_contract, field="analyzer_contract"))
        if not isinstance(self.coordinates, SemanticCoordinateSet):
            raise ISQLValidationError("COORDINATES_MUST_BE_SEMANTIC_COORDINATE_SET")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "isql.semantic-analysis/v0.2",
            "analyzer_id": self.analyzer_id,
            "analyzer_contract": self.analyzer_contract,
            "coordinates": self.coordinates.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticAnalysis":
        if not isinstance(value, Mapping):
            raise ISQLValidationError("SEMANTIC_ANALYSIS_MUST_BE_OBJECT")
        if value.get("schema") not in (None, "isql.semantic-analysis/v0.2"):
            raise ISQLValidationError("INVALID_SEMANTIC_ANALYSIS_SCHEMA")
        coords = value.get("coordinates")
        if not isinstance(coords, Mapping):
            raise ISQLValidationError("SEMANTIC_ANALYSIS_COORDINATES_REQUIRED")
        return cls(
            analyzer_id=str(value.get("analyzer_id", "")),
            analyzer_contract=str(value.get("analyzer_contract", "")),
            coordinates=SemanticCoordinateSet.from_dict(coords),
        )


class SemanticAnalyzer(Protocol):
    def analyze(self, text: str, *, context: Mapping[str, Any] | None = None) -> SemanticAnalysis:
        ...


class CallableSemanticAnalyzer:
    """Adapter for external/AI semantic analyzers without imposing an SDK dependency."""

    def __init__(
        self,
        *,
        analyzer_id: str,
        analyzer_contract: str,
        fn: Callable[[str, Mapping[str, Any]], SemanticCoordinateSet | Mapping[str, Any]],
    ) -> None:
        self.analyzer_id = _clean_text(analyzer_id, field="analyzer_id")
        self.analyzer_contract = _clean_text(analyzer_contract, field="analyzer_contract")
        self.fn = fn

    def analyze(self, text: str, *, context: Mapping[str, Any] | None = None) -> SemanticAnalysis:
        result = self.fn(text, dict(context or {}))
        if isinstance(result, SemanticCoordinateSet):
            coords = result
        elif isinstance(result, Mapping):
            coords = SemanticCoordinateSet.from_dict(result)
        else:
            raise ISQLExecutionError("SEMANTIC_ANALYZER_MUST_RETURN_COORDINATES")
        return SemanticAnalysis(
            analyzer_id=self.analyzer_id,
            analyzer_contract=self.analyzer_contract,
            coordinates=coords,
        )
