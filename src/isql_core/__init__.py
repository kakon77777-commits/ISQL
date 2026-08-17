"""ISQL Core Runtime / ISQL-MEM v0.6 physical digit carrier packing."""

from .code import ISQLCode, parse_code
from .semantics import SemanticAnalysis, SemanticCoordinateSet, SemanticRelation
from .spectral import (
    SpectralPacket,
    SpectralRegistry,
    SpectralRegistryStore,
    compile_spectral_packet,
    expand_spectral_packet,
)

from .hierarchical import (
    HierarchicalRegistry,
    HierarchicalRegistryDelta,
    HierarchicalRegistryStore,
    compile_hierarchical_registry,
    reconstruct_spectral_registry,
)
from .registry_wire import (
    RegistryWireCompileResult,
    compile_registry_delta_wire,
    decode_registry_delta_binary,
    decode_registry_delta_wire,
    encode_registry_delta_binary,
    encode_registry_delta_wire,
)
from .carrier import (
    CarrierCompileResult,
    compile_digit_carrier,
    inspect_digit_carrier,
    pack_digit_wire,
    unpack_digit_carrier,
)

from .wire import (
    NumericWireCompileResult,
    compile_numeric_wire,
    decode_numeric_wire,
    decode_uint,
    encode_numeric_wire,
    encode_uint,
)

__version__ = "0.6.0"

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
    "HierarchicalRegistry",
    "HierarchicalRegistryDelta",
    "HierarchicalRegistryStore",
    "compile_hierarchical_registry",
    "reconstruct_spectral_registry",
    "RegistryWireCompileResult",
    "compile_registry_delta_wire",
    "decode_registry_delta_binary",
    "decode_registry_delta_wire",
    "encode_registry_delta_binary",
    "encode_registry_delta_wire",
    "CarrierCompileResult",
    "compile_digit_carrier",
    "inspect_digit_carrier",
    "pack_digit_wire",
    "unpack_digit_carrier",
    "NumericWireCompileResult",
    "compile_numeric_wire",
    "decode_numeric_wire",
    "decode_uint",
    "encode_numeric_wire",
    "encode_uint",
    "__version__",
]
