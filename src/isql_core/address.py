from __future__ import annotations

import hashlib

from .code import ISQLCode
from .errors import ISQLValidationError


def _digest_to_decimal(digest: bytes) -> str:
    return str(int.from_bytes(digest, byteorder="big", signed=False))


def digest_to_address_code(digest: bytes) -> ISQLCode:
    if not isinstance(digest, (bytes, bytearray, memoryview)):
        raise ISQLValidationError("ADDRESS_DIGEST_BYTES_REQUIRED")
    raw = bytes(digest)
    if len(raw) != 32:
        raise ISQLValidationError("ADDRESS_DIGEST_MUST_BE_32_BYTES")
    return ISQLCode(
        protocol="ISQL",
        version=1,
        domain="ADDR",
        resolution="R0",
        control="H",
        payload=_digest_to_decimal(raw),
    )


def address_code_to_digest(code: ISQLCode) -> bytes:
    if not isinstance(code, ISQLCode):
        raise ISQLValidationError("ADDRESS_CODE_REQUIRED")
    if code.protocol != "ISQL" or code.version != 1 or code.domain != "ADDR" or code.resolution != "R0" or code.control != "H":
        raise ISQLValidationError("ADDRESS_CODE_NOT_SHA256_ADDR")
    value = int(code.payload)
    if value < 0 or value >= 1 << 256:
        raise ISQLValidationError("ADDRESS_DIGEST_INTEGER_OUT_OF_RANGE")
    return value.to_bytes(32, "big")


def address_bytes(data: bytes) -> ISQLCode:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    digest = hashlib.sha256(bytes(data)).digest()
    return digest_to_address_code(digest)


def address_text(text: str) -> ISQLCode:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return address_bytes(text.encode("utf-8"))


def verify_address(data: bytes, code: ISQLCode) -> bool:
    if code.domain != "ADDR" or code.resolution != "R0" or code.control != "H":
        return False
    return address_bytes(data) == code
