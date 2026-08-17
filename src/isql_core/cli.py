from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .address import address_bytes, address_text
from .code import parse_code
from .decoder import DeterministicMemoryDecoder
from .errors import ISQLError
from .memory import encode_text_memory
from .recoverability import evaluate_recovery
from .registry import DomainRegistry
from .store import MemoryStore


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _load_text(args: argparse.Namespace) -> str:
    if getattr(args, "text", None) is not None:
        return args.text
    if getattr(args, "file", None) is not None:
        return Path(args.file).read_text(encoding="utf-8")
    raise ValueError("text or file required")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="isql-core", description="ISQL Core Runtime v0.1")
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

    sp = sub.add_parser("memory-decode", help="Decode a stored ISQL-MEM code")
    sp.add_argument("--store", required=True)
    sp.add_argument("--code", required=True)

    sp = sub.add_parser("recoverability", help="Measure exact/semantic recovery")
    sp.add_argument("--store", required=True)
    sp.add_argument("--code", required=True)
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-text")
    group.add_argument("--source-file")

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
            record = encode_text_memory(text, metadata=metadata, source_ref=args.source_ref)
            store = MemoryStore(args.store)
            store.put(record)
            print(_json(record.to_dict()))
            return 0

        if args.command == "memory-decode":
            code = parse_code(args.code)
            registry.validate_code(code)
            registry.require_executable(code.domain)
            result = DeterministicMemoryDecoder(MemoryStore(args.store)).decode(code)
            print(_json(result.to_dict()))
            return 0

        if args.command == "recoverability":
            code = parse_code(args.code)
            registry.validate_code(code)
            registry.require_executable(code.domain)
            source = args.source_text if args.source_text is not None else Path(args.source_file).read_text(encoding="utf-8")
            result = DeterministicMemoryDecoder(MemoryStore(args.store)).decode(code)
            report = evaluate_recovery(source, result)
            print(_json(report.to_dict()))
            return 0

        parser.error("unknown command")
        return 2
    except (ISQLError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
