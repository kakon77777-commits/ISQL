"""ISQL Core Runtime / ISQL-MEM v0.9 locality index and automatic base selection."""

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
    NativeBlockIndex,
    NativeMemoryCompileResult,
    NativeSpectralFrame,
    compile_native_memory,
    decode_native_sequence_block,
    decode_native_sequence_range,
    decode_native_spectral_frame,
    encode_native_spectral_frame,
    expand_native_memory,
    index_native_blocks,
    inspect_native_frame,
    render_native_debug,
)


from .delta import (
    DeltaBlockIndex,
    LocalityCompileResult,
    compile_locality_memory,
    decode_delta_block,
    decode_delta_frame,
    decode_delta_range,
    encode_delta_frame,
    index_delta_blocks,
    inspect_delta_frame,
)


from .locality import (
    LocalityBlockSignature,
    LocalityIndexEntry,
    LocalityIndex,
    LocalityCandidate,
    LocalityBaseEvaluation,
    LocalityBaseSelectionResult,
    signature_from_native,
    build_locality_index,
    recall_locality_candidates,
    select_locality_base,
    load_locality_index,
    save_locality_index,
)

from .wire import (
    NumericWireCompileResult,
    compile_numeric_wire,
    decode_numeric_wire,
    decode_uint,
    encode_numeric_wire,
    encode_uint,
)

__version__ = "0.9.0"

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
    "NativeBlockIndex",
    "NativeMemoryCompileResult",
    "NativeSpectralFrame",
    "compile_native_memory",
    "decode_native_sequence_block",
    "decode_native_sequence_range",
    "decode_native_spectral_frame",
    "encode_native_spectral_frame",
    "expand_native_memory",
    "index_native_blocks",
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
    "DeltaBlockIndex",
    "LocalityCompileResult",
    "compile_locality_memory",
    "decode_delta_block",
    "decode_delta_frame",
    "decode_delta_range",
    "encode_delta_frame",
    "index_delta_blocks",
    "inspect_delta_frame",
    "LocalityBlockSignature",
    "LocalityIndexEntry",
    "LocalityIndex",
    "LocalityCandidate",
    "LocalityBaseEvaluation",
    "LocalityBaseSelectionResult",
    "signature_from_native",
    "build_locality_index",
    "recall_locality_candidates",
    "select_locality_base",
    "load_locality_index",
    "save_locality_index",
    "__version__",
]
