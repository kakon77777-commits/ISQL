"""ISQL Core Runtime / ISQL-MEM v0.4 numeric wire encoding."""

from .code import ISQLCode, parse_code
from .semantics import SemanticAnalysis, SemanticCoordinateSet, SemanticRelation
from .spectral import (
    SpectralPacket,
    SpectralRegistry,
    SpectralRegistryStore,
    compile_spectral_packet,
    expand_spectral_packet,
)
from .wire import (
    NumericWireCompileResult,
    compile_numeric_wire,
    decode_numeric_wire,
    decode_uint,
    encode_numeric_wire,
    encode_uint,
)

__version__ = "0.4.0"

__all__ = [
    "ISQLCode",
    "parse_code",
    "SemanticAnalysis",
    "SemanticCoordinateSet",
    "SemanticRelation",
    "SpectralPacket",
    "SpectralRegistry",
    "SpectralRegistryStore",
    "compile_spectral_packet",
    "expand_spectral_packet",
    "NumericWireCompileResult",
    "compile_numeric_wire",
    "decode_numeric_wire",
    "decode_uint",
    "encode_numeric_wire",
    "encode_uint",
    "__version__",
]
