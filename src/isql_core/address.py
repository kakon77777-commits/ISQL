from __future__ import annotations

import hashlib

from .code import ISQLCode


def _digest_to_decimal(digest: bytes) -> str:
    return str(int.from_bytes(digest, byteorder="big", signed=False))


def address_bytes(data: bytes) -> ISQLCode:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    digest = hashlib.sha256(bytes(data)).digest()
    return ISQLCode(
        protocol="ISQL",
        version=1,
        domain="ADDR",
        resolution="R0",
        control="H",
        payload=_digest_to_decimal(digest),
    )


def address_text(text: str) -> ISQLCode:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return address_bytes(text.encode("utf-8"))


def verify_address(data: bytes, code: ISQLCode) -> bool:
    if code.domain != "ADDR" or code.resolution != "R0" or code.control != "H":
        return False
    return address_bytes(data) == code
