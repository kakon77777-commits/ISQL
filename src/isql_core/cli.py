from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .address import address_bytes, address_text
from .code import parse_code
from .decoder import DeterministicMemoryDecoder, NumericWireDecoder, SemanticCoordinateDecoder, SpectralCoordinateDecoder
from .errors import ISQLError, ISQLExecutionError
from .memory import MemoryRecord, encode_text_memory
from .recoverability import SemanticReference, compare_memory_profiles, evaluate_recovery
from .registry import DomainRegistry
from .semantics import SemanticAnalysis
from .store import MemoryStore
from .spectral import SpectralRegistryStore, compile_spectral_packet
from .hierarchical import (
    HierarchicalRegistryStore,
    compile_hierarchical_registry,
    make_hierarchical_delta,
)
from .registry_wire import (
    compile_registry_delta_wire,
    decode_registry_delta_wire,
)
from .wire import compile_numeric_wire, decode_numeric_wire
from .carrier import compile_digit_carrier, inspect_digit_carrier, unpack_digit_carrier


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _load_text(args: argparse.Namespace) -> str:
    if getattr(args, "text", None) is not None:
        return args.text
    if getattr(args, "file", None) is not None:
        return Path(args.file).read_text(encoding="utf-8")
    raise ValueError("text or file required")


def _load_source(args: argparse.Namespace) -> str:
    if getattr(args, "source_text", None) is not None:
        return args.source_text
    if getattr(args, "source_file", None) is not None:
        return Path(args.source_file).read_text(encoding="utf-8")
    raise ValueError("source text or file required")


def _load_semantic_analysis(args: argparse.Namespace) -> SemanticAnalysis | None:
    raw: str | None = getattr(args, "semantic_analysis_json", None)
    path: str | None = getattr(args, "semantic_analysis_file", None)
    if raw is None and path is None:
        return None
    if raw is not None and path is not None:
        raise ValueError("use only one of --semantic-analysis-json/--semantic-analysis-file")
    data = json.loads(raw if raw is not None else Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("semantic analysis must decode to an object")
    return SemanticAnalysis.from_dict(data)


def _load_semantic_reference(args: argparse.Namespace) -> SemanticReference | None:
    raw: str | None = getattr(args, "semantic_reference_json", None)
    path: str | None = getattr(args, "semantic_reference_file", None)
    if raw is None and path is None:
        return None
    if raw is not None and path is not None:
        raise ValueError("use only one of --semantic-reference-json/--semantic-reference-file")
    data = json.loads(raw if raw is not None else Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("semantic reference must decode to an object")
    analysis = SemanticAnalysis.from_dict(data)
    return SemanticReference.from_coordinates(analysis.coordinates)


def _profile_for_code(record: MemoryRecord, code) -> str:
    for profile_id, variant in record.variants.items():
        layer = variant.layers.get(code.resolution)
        if layer is not None and layer.code == code:
            return profile_id
    raise ISQLExecutionError("MEMORY_CODE_PROFILE_NOT_FOUND")


def _decode_auto(store: MemoryStore, code):
    record = store.find_by_memory_code(code)
    profile_id = _profile_for_code(record, code)
    if profile_id == "baseline":
        return DeterministicMemoryDecoder(store).decode(code)
    if profile_id == "semantic":
        return SemanticCoordinateDecoder(store).decode(code)
    if profile_id == "spectral":
        return SpectralCoordinateDecoder(store).decode(code)
    if profile_id == "numeric":
        return NumericWireDecoder(store).decode(code)
    raise ISQLExecutionError("NO_DECODER_FOR_MEMORY_PROFILE")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="isql-core", description="ISQL Core Runtime / ISQL-MEM v0.6")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("parse", help="Parse an ISQL wire code")
    sp.add_argument("code")

    sub.add_parser("registry-info", help="Show the default domain registry")

    sp = sub.add_parser("address", help="Create deterministic ISQL-ADDR code")
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file")

    sp = sub.add_parser("memory-encode", help="Encode/store a text memory at R0-R4")
    sp.add_argument("--store", required=True)
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file")
    sp.add_argument("--metadata-json", default="{}")
    sp.add_argument("--source-ref")
    sem = sp.add_mutually_exclusive_group()
    sem.add_argument("--semantic-analysis-json")
    sem.add_argument("--semantic-analysis-file")
    sp.add_argument("--spectral", action="store_true", help="Compile semantic analysis into registry-backed spectral packets")
    sp.add_argument("--numeric-wire", action="store_true", help="Add digits-only numeric wire profile (implies spectral compilation)")

    sp = sub.add_parser("spectral-compile", help="Compile semantic analysis into a sparse spectral packet")
    sp.add_argument("--store", required=True)
    sem = sp.add_mutually_exclusive_group(required=True)
    sem.add_argument("--semantic-analysis-json")
    sem.add_argument("--semantic-analysis-file")


    sp = sub.add_parser("numeric-wire-compile", help="Compile semantic analysis into spectral packet plus digits-only numeric wire")
    sp.add_argument("--store", required=True)
    sem = sp.add_mutually_exclusive_group(required=True)
    sem.add_argument("--semantic-analysis-json")
    sem.add_argument("--semantic-analysis-file")

    sp = sub.add_parser("numeric-wire-decode", help="Decode a digits-only numeric wire into its spectral packet metadata")
    sp.add_argument("--wire", required=True)

    sp = sub.add_parser("spectral-registry-info", help="Inspect the shared spectral registry")
    sp.add_argument("--store", required=True)

    sp = sub.add_parser("registry-compile-hierarchical", help="Compile canonical spectral registry into hierarchical registry and numeric delta wire")
    sp.add_argument("--store", required=True)

    sp = sub.add_parser("registry-decode-wire", help="Decode a digits-only hierarchical registry delta wire")
    sp.add_argument("--wire", required=True)

    sp = sub.add_parser("registry-compare", help="Compare canonical, hierarchical, and numeric registry representations")
    sp.add_argument("--store", required=True)

    sp = sub.add_parser("carrier-pack", help="Pack a canonical digits-only wire into a binary physical carrier")
    sp.add_argument("--wire", required=True)
    sp.add_argument("--codec", choices=["bcd4", "d40"], default="d40")
    sp.add_argument("--out", required=True)

    sp = sub.add_parser("carrier-unpack", help="Unpack a binary physical carrier back to canonical digits")
    sp.add_argument("--file", required=True)

    sp = sub.add_parser("carrier-info", help="Inspect a binary physical carrier")
    sp.add_argument("--file", required=True)

    sp = sub.add_parser("memory-decode", help="Decode a stored ISQL-MEM code using its profile decoder")
    sp.add_argument("--store", required=True)
    sp.add_argument("--code", required=True)

    sp = sub.add_parser("recoverability", help="Measure exact/token recovery for any stored memory profile")
    sp.add_argument("--store", required=True)
    sp.add_argument("--code", required=True)
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-text")
    group.add_argument("--source-file")

    sp = sub.add_parser("memory-profiles", help="Inspect memory profiles under one stable address")
    sp.add_argument("--store", required=True)
    sp.add_argument("--address", required=True)

    sp = sub.add_parser("memory-compare", help="Compare baseline and semantic memory profiles")
    sp.add_argument("--store", required=True)
    sp.add_argument("--address", required=True)
    sp.add_argument("--resolution", required=True, choices=["R0", "R1", "R2", "R3", "R4"])
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-text")
    group.add_argument("--source-file")
    ref = sp.add_mutually_exclusive_group()
    ref.add_argument("--semantic-reference-json")
    ref.add_argument("--semantic-reference-file")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = DomainRegistry.load_default()
    try:
        if args.command == "parse":
            code = parse_code(args.code)
            registry.validate_code(code)
            print(_json(code.to_dict()))
            return 0

        if args.command == "registry-info":
            print(_json(registry.to_dict()))
            return 0

        if args.command == "address":
            if args.text is not None:
                code = address_text(args.text)
            else:
                code = address_bytes(Path(args.file).read_bytes())
            print(code.to_wire())
            return 0

        if args.command == "memory-encode":
            text = _load_text(args)
            metadata = json.loads(args.metadata_json)
            if not isinstance(metadata, dict):
                raise ValueError("--metadata-json must decode to an object")
            semantic_analysis = _load_semantic_analysis(args)
            if args.spectral and semantic_analysis is None:
                raise ValueError("--spectral requires semantic analysis")
            if args.numeric_wire and semantic_analysis is None:
                raise ValueError("--numeric-wire requires semantic analysis")
            spectral_enabled = bool(args.spectral or args.numeric_wire)
            record = encode_text_memory(
                text,
                metadata=metadata,
                source_ref=args.source_ref,
                semantic_analysis=semantic_analysis,
                spectral_registry_store=SpectralRegistryStore(args.store) if spectral_enabled else None,
                numeric_wire=args.numeric_wire,
            )
            store = MemoryStore(args.store)
            store.put(record)
            print(_json(record.to_dict()))
            return 0

        if args.command == "spectral-compile":
            semantic_analysis = _load_semantic_analysis(args)
            if semantic_analysis is None:
                raise ValueError("semantic analysis required")
            result = compile_spectral_packet(semantic_analysis.coordinates, SpectralRegistryStore(args.store))
            print(_json(result.to_dict()))
            return 0

        if args.command == "numeric-wire-compile":
            semantic_analysis = _load_semantic_analysis(args)
            if semantic_analysis is None:
                raise ValueError("semantic analysis required")
            spectral = compile_spectral_packet(semantic_analysis.coordinates, SpectralRegistryStore(args.store))
            numeric = compile_numeric_wire(spectral.packet)
            print(_json({
                "schema": "isql.numeric-wire-compile/v0.4",
                "spectral": spectral.to_dict(),
                "numeric_wire": numeric.to_dict(),
            }))
            return 0

        if args.command == "numeric-wire-decode":
            packet = decode_numeric_wire(args.wire)
            print(_json({
                "schema": "isql.numeric-wire-decode/v0.4",
                "packet": packet.to_dict(),
            }))
            return 0

        if args.command == "spectral-registry-info":
            registry = SpectralRegistryStore(args.store).load_current()
            print(_json({
                "schema": "isql.spectral-registry-info/v0.3",
                "registry_id": registry.registry_id,
                "revision": registry.revision,
                "registry_hash": registry.content_hash(),
                "counts": {name: len(values) for name, values in registry.namespaces.items()},
            }))
            return 0

        if args.command == "registry-compile-hierarchical":
            canonical = SpectralRegistryStore(args.store).load_current()
            hstore = HierarchicalRegistryStore(args.store)
            previous = hstore.load_current()
            compiled = compile_hierarchical_registry(canonical, previous=previous)
            if compiled.registry.content_hash() == previous.content_hash():
                committed = previous
                delta = make_hierarchical_delta(previous, previous)
            else:
                committed = hstore.commit(compiled.registry)
                delta = hstore.load_delta(committed.revision)
            wire = compile_registry_delta_wire(delta)
            print(_json({
                "schema": "isql.hierarchical-registry-compile/v0.5",
                "canonical_registry_revision": canonical.revision,
                "canonical_registry_hash": canonical.content_hash(),
                "hierarchical_revision": committed.revision,
                "hierarchical_hash": committed.content_hash(),
                "new_lexeme_count": len(delta.new_lexemes),
                "new_program_count": sum(len(rows) for rows in delta.new_programs.values()),
                "numeric_delta_wire": wire.to_dict(),
            }))
            return 0

        if args.command == "registry-decode-wire":
            delta = decode_registry_delta_wire(args.wire)
            print(_json({
                "schema": "isql.hierarchical-registry-wire-decode/v0.5",
                "delta": delta.to_dict(),
            }))
            return 0

        if args.command == "carrier-pack":
            result = compile_digit_carrier(args.wire, codec=args.codec)
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(result.carrier)
            payload = result.to_dict()
            payload["schema"] = "isql.digit-carrier-pack/v0.6"
            payload["output_file"] = str(out_path)
            print(_json(payload))
            return 0

        if args.command == "carrier-unpack":
            wire = unpack_digit_carrier(Path(args.file).read_bytes())
            print(wire)
            return 0

        if args.command == "carrier-info":
            print(_json(inspect_digit_carrier(Path(args.file).read_bytes())))
            return 0

        if args.command == "registry-compare":
            canonical = SpectralRegistryStore(args.store).load_current()
            hstore = HierarchicalRegistryStore(args.store)
            hierarchical = hstore.load_current()
            if hierarchical.revision == 0:
                raise ValueError("hierarchical registry has not been compiled")
            delta = hstore.load_delta(hierarchical.revision)
            wire = compile_registry_delta_wire(delta)
            canonical_bytes = len(json.dumps(canonical.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
            hierarchical_bytes = len(json.dumps(hierarchical.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
            print(_json({
                "schema": "isql.hierarchical-registry-compare/v0.5",
                "canonical_revision": canonical.revision,
                "canonical_registry_json_bytes": canonical_bytes,
                "hierarchical_registry_json_bytes": hierarchical_bytes,
                "latest_delta_json_bytes": len(delta.canonical_bytes()),
                "latest_numeric_delta_wire_bytes": wire.wire_bytes,
                "latest_structural_binary_bytes": wire.structural_binary_bytes,
                "new_lexeme_utf8_bytes": wire.new_lexeme_utf8_bytes,
                "program_reference_count": wire.program_reference_count,
            }))
            return 0

        if args.command == "memory-decode":
            code = parse_code(args.code)
            registry.validate_code(code)
            registry.require_executable(code.domain)
            result = _decode_auto(MemoryStore(args.store), code)
            print(_json(result.to_dict()))
            return 0

        if args.command == "recoverability":
            code = parse_code(args.code)
            registry.validate_code(code)
            registry.require_executable(code.domain)
            source = _load_source(args)
            result = _decode_auto(MemoryStore(args.store), code)
            report = evaluate_recovery(source, result)
            print(_json(report.to_dict()))
            return 0

        if args.command == "memory-profiles":
            address = parse_code(args.address)
            registry.validate_code(address)
            if address.domain != "ADDR":
                raise ValueError("--address must be an ADDR code")
            record = MemoryStore(args.store).get(address)
            profiles = {}
            for profile_id, variant in record.variants.items():
                profiles[profile_id] = {
                    "encoder_version": variant.encoder_version,
                    "analyzer_id": variant.analyzer_id,
                    "analyzer_contract": variant.analyzer_contract,
                    "layers": {r: layer.code.to_wire() for r, layer in variant.layers.items()},
                }
            print(_json({"address": record.address.to_wire(), "default_profile": record.default_profile, "profiles": profiles}))
            return 0

        if args.command == "memory-compare":
            address = parse_code(args.address)
            registry.validate_code(address)
            if address.domain != "ADDR":
                raise ValueError("--address must be an ADDR code")
            store = MemoryStore(args.store)
            record = store.get(address)
            source = _load_source(args)
            reference = _load_semantic_reference(args)
            report = compare_memory_profiles(
                source,
                record,
                store=store,
                resolution=args.resolution,
                semantic_reference=reference,
            )
            print(_json(report.to_dict()))
            return 0

        parser.error("unknown command")
        return 2
    except (ISQLError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
