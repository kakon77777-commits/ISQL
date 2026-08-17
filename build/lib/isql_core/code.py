from __future__ import annotations

from dataclasses import dataclass
import re

from .errors import ISQLValidationError

_WIRE_RE = re.compile(r"^ISQL(?P<version>[1-9][0-9]*):(?P<domain>[A-Z]+):(?P<resolution>R[0-4]):(?P<control>[A-Z]+)(?P<payload>[0-9]+)$")


@dataclass(frozen=True, slots=True)
class ISQLCode:
    protocol: str
    version: int
    domain: str
    resolution: str
    control: str
    payload: str

    def __post_init__(self) -> None:
        if self.protocol != "ISQL":
            raise ISQLValidationError("INVALID_PROTOCOL")
        if not isinstance(self.version, int) or self.version < 1:
            raise ISQLValidationError("INVALID_VERSION")
        if not re.fullmatch(r"[A-Z]+", self.domain):
            raise ISQLValidationError("INVALID_DOMAIN")
        if self.resolution not in {"R0", "R1", "R2", "R3", "R4"}:
            raise ISQLValidationError("INVALID_RESOLUTION")
        if not re.fullmatch(r"[A-Z]+", self.control):
            raise ISQLValidationError("INVALID_CONTROL")
        if not self.payload or not self.payload.isascii() or not self.payload.isdigit():
            raise ISQLValidationError("INVALID_PAYLOAD")

    def to_wire(self) -> str:
        return f"ISQL{self.version}:{self.domain}:{self.resolution}:{self.control}{self.payload}"

    def to_dict(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "version": self.version,
            "domain": self.domain,
            "resolution": self.resolution,
            "control": self.control,
            "payload": self.payload,
            "wire": self.to_wire(),
        }


def parse_code(value: str) -> ISQLCode:
    if not isinstance(value, str):
        raise ISQLValidationError("CODE_MUST_BE_STRING")
    match = _WIRE_RE.fullmatch(value)
    if not match:
        raise ISQLValidationError("INVALID_ISQL_CODE")
    return ISQLCode(
        protocol="ISQL",
        version=int(match.group("version")),
        domain=match.group("domain"),
        resolution=match.group("resolution"),
        control=match.group("control"),
        payload=match.group("payload"),
    )
