"""ISQL Core Runtime / ISQL-MEM v0.7 machine-native canonical representation."""

from .code import ISQLCode, parse_code
from .address import address_code_to_digest, digest_to_address_code
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

from .native import (
    NativeMemoryCompileResult,
    NativeSpectralFrame,
    compile_native_memory,
    decode_native_spectral_frame,
    encode_native_spectral_frame,
    expand_native_memory,
    inspect_native_frame,
    render_native_debug,
)

from .wire import (
    NumericWireCompileResult,
    compile_numeric_wire,
    decode_numeric_wire,
    decode_uint,
    encode_numeric_wire,
    encode_uint,
)

__version__ = "0.7.0"

__all__ = [
    "ISQLCode",
    "parse_code",
    "address_code_to_digest",
    "digest_to_address_code",
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
    "NativeMemoryCompileResult",
    "NativeSpectralFrame",
    "compile_native_memory",
    "decode_native_spectral_frame",
    "encode_native_spectral_frame",
    "expand_native_memory",
    "inspect_native_frame",
    "render_native_debug",
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
