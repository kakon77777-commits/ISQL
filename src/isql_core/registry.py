from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .code import ISQLCode
from .errors import ISQLExecutionError, ISQLValidationError


@dataclass(frozen=True, slots=True)
class DomainDefinition:
    id: str
    description: str
    resolutions: tuple[str, ...]
    executable: bool


class DomainRegistry:
    def __init__(self, protocol_version: int, domains: dict[str, DomainDefinition]) -> None:
        self.protocol_version = protocol_version
        self._domains = dict(domains)

    @classmethod
    def load(cls, path: str | Path) -> "DomainRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") != "isql.domain-registry/v1":
            raise ISQLValidationError("INVALID_DOMAIN_REGISTRY_SCHEMA")
        version = data.get("protocol_version")
        if version != 1:
            raise ISQLValidationError("UNSUPPORTED_PROTOCOL_VERSION")
        domains: dict[str, DomainDefinition] = {}
        for item in data.get("domains", []):
            did = str(item["id"])
            if did in domains:
                raise ISQLValidationError("DUPLICATE_DOMAIN_ID")
            domains[did] = DomainDefinition(
                id=did,
                description=str(item.get("description", "")),
                resolutions=tuple(str(x) for x in item.get("resolutions", [])),
                executable=bool(item.get("executable", False)),
            )
        return cls(protocol_version=version, domains=domains)

    @classmethod
    def load_default(cls) -> "DomainRegistry":
        return cls.load(Path(__file__).resolve().parent / "data" / "domains.json")

    def domain_ids(self) -> tuple[str, ...]:
        return tuple(self._domains)

    def get(self, domain_id: str) -> DomainDefinition:
        try:
            return self._domains[domain_id]
        except KeyError as exc:
            raise ISQLValidationError("UNKNOWN_DOMAIN") from exc

    def validate_code(self, code: ISQLCode) -> None:
        if code.version != self.protocol_version:
            raise ISQLValidationError("PROTOCOL_VERSION_MISMATCH")
        domain = self.get(code.domain)
        if code.resolution not in domain.resolutions:
            raise ISQLValidationError("RESOLUTION_NOT_ALLOWED_FOR_DOMAIN")

    def require_executable(self, domain_id: str) -> None:
        domain = self.get(domain_id)
        if not domain.executable:
            raise ISQLExecutionError("DOMAIN_NOT_EXECUTABLE")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "isql.domain-registry/v1",
            "protocol_version": self.protocol_version,
            "domains": [
                {
                    "id": d.id,
                    "description": d.description,
                    "resolutions": list(d.resolutions),
                    "executable": d.executable,
                }
                for d in self._domains.values()
            ],
        }
