# ISQL

**ISQL Public 1.0 — Protocol / Conformance / Research Boundary**
中文標題：ISQL 公開版 1.0：協議、相容性測試與研究邊界

**Status:** Public Core Specification Boundary
**Basis:** ISQL Core Runtime v1.0.0
**Primary audience:** third-party implementers, AI/agent runtime developers, auditors, researchers

> This document specifies the Public 1.0 boundary, but cross-implementation interoperability is **not yet independently proven**. A second implementation plus a complete golden/invalid conformance vector set remains a release gate for claiming independent protocol interoperability.

---

## What this repository is

The canonical public description of ISQL 1.0 is
**[`public-boundary/ISQL_Public_1.0_Protocol_Conformance_Research_Boundary.md`](public-boundary/ISQL_Public_1.0_Protocol_Conformance_Research_Boundary.md)**.

It is not a new algorithm version and not v1.1. Its purpose is to take the completed **ISQL Core Runtime v1.0.0** — a research/engineering result — and organize it into a **public stable boundary** that a third party can understand, implement independently, verify, and critique.

Core principle:

```text
Specification > Conformance Vectors > Reference Implementation
```

The Python reference runtime (`docs/RUNTIME_NOTES.md`, `src/`) is **an** implementation. It is not ISQL itself.

## Public vs. Experimental

Starting at v1.0, ISQL formally splits into two governance lines:

- **Public ISQL** — stable identity, canonical encodings, deterministic decode, independent implementations, backward compatibility, reproducible test vectors, fail-closed behavior, explicit versioning, externally auditable claims. Priority: stability over novelty velocity.
- **Experimental / Internal ISQL** — free to change coordinate topology, registry architecture, memory organization, AI decoder, index/search architecture, compression, or break backward compatibility. Nothing here becomes Public protocol just because it works in an experimental branch — promotion requires: research candidate → independent validation → specification → conformance vectors → public release.

### Internal Meta-Core alignment — non-normative

The Internal line now explicitly distinguishes the ISQL Meta-Core abstraction from any one wire format or reference runtime. In particular, the current Python `ISN7` implementation's `NATIVE_MAX_BIT_WIDTH = 64` is a **current implementation / Public 1.0 wire ceiling**, not a claim that ISQL semantic state is ontologically limited to 64-bit values.

Internal research separates:

```text
semantic width != logical representation width != carrier width != machine word width
semantic address != exact identity != physical placement
entity identity != exact mutable-state revision
```

Existing Public 1.0 `ISN7` bytes are unchanged. Any future extended-width encoding must use an explicit experimental/new format boundary rather than silently reinterpreting the stable Public grammar.

See [`docs/internal/ISQL_MetaCore_Internal_Architecture_v0.1.md`](docs/internal/ISQL_MetaCore_Internal_Architecture_v0.1.md) for the non-normative architecture alignment, responsibility split across Origin/Core/DSR/SEDB integration, and the staged W1→W5 experimental promotion path.

## Public 1.0 stable core

`(Identity, Registry Binding, ISN7, ISD8, ILI1, Exact/Semantic Recovery Boundary, Fail-Closed Canonicality)`

- **ISN7** — canonical standalone machine-native memory frame.
- **ISD8** — optional one-hop locality delta frame; base MUST be a standalone ISN7 (decode depth ≤ 1).
- **ILI1** — compact machine-native locality index; derived and rebuildable, never itself a source of identity.
- **Registry binding** — every canonical object binds `(registry revision, registry SHA-256)`; wrong revision/hash fails closed.
- **Exact vs. semantic recovery** — an AI decoder producing "the same meaning" MUST NOT be represented as exact recovery.

What is explicitly **not** canonical meaning: Python class/file layout, CLI spelling, the current semantic-analyzer prompt/model, current heuristic coefficients, current benchmark fixtures, or any of the v0.4–v0.6/v0.9 legacy wire formats. Those are reference, legacy, or research artifacts — replacing them does not stop something from being ISQL.

## Conformance classes

| Class | Requires | Scope |
|---|---|---|
| C1 | — | Core Decoder |
| C2 | C1 | Core Encoder (`Encode(Decode(b)) = b`) |
| C3 | C2 | Memory Runtime (stable identity, registry binding, ISN7/ISD8 construction) |
| C4 | C3 | Locality Runtime (index, recall, mandatory actual-byte rerank) |
| C5 | — (optional) | AI Semantic Adapter (model-neutral, provenance-tracked) |

A third party does not need to import the Python package, reuse its classes, or match its CLI — only produce the same canonical logical result/bytes against the normative vectors.

## What Public 1.0 does **not** claim

Universal compression optimum, a completed AGI-native universal language, lossless semantic reconstruction for arbitrary information, a globally optimal semantic ontology, a production cryptographic protocol, universal ANN superiority, or that natural language has been replaced. `CRC32` is accidental-corruption detection only; `SHA-256` is used for identity/binding, not for encryption, authentication, or secrecy.

## Documents in this repository

- **[`public-boundary/ISQL_Public_1.0_Protocol_Conformance_Research_Boundary.md`](public-boundary/ISQL_Public_1.0_Protocol_Conformance_Research_Boundary.md)** — the full normative/public-boundary specification (46 sections: conformance classes, wire canonicality, golden/invalid vector requirements, compatibility policy, benchmark boundary, acceptance gate).
- **[`public-boundary/PUBLIC_BOUNDARY_v1.json`](public-boundary/PUBLIC_BOUNDARY_v1.json)** — machine-readable component classification (public-stable / public-replaceable / legacy-experimental / research-internal).
- **[`public-boundary/SOURCE_BASIS.md`](public-boundary/SOURCE_BASIS.md)** — which v1.0 artifacts this boundary was derived from.
- **[`public-boundary/CONFORMANCE_VECTOR_FORMAT_v1.example.json`](public-boundary/CONFORMANCE_VECTOR_FORMAT_v1.example.json)** — starter format for future golden/invalid conformance vectors.
- **[`docs/RUNTIME_NOTES.md`](docs/RUNTIME_NOTES.md)** — the Python `isql-core` v1.0.0 reference-implementation README: quickstart, CLI, and the full v0.1→v1.0 controlled-experiment results. Non-normative.
- **[`docs/internal/ISQL_MetaCore_Internal_Architecture_v0.1.md`](docs/internal/ISQL_MetaCore_Internal_Architecture_v0.1.md)** — non-normative Internal architecture alignment: Meta-Core separation rules, width independence, dual addressing, repo responsibilities, and the experimental promotion path.
- **[`docs/`](docs/)** — per-version design docs (`ISQL_MEM_v0.x_*.md`) and superpowers plans/specs behind each release.

## Acceptance gate (not yet complete)

- [x] Stable-core specification
- [x] Boundary manifest
- [ ] Golden vectors (positive/invalid)
- [x] Python reference runtime
- [ ] Second independent decoder implementation
- [ ] Benchmark protocol separated from benchmark results

Until a second independent implementation passes the core vectors, this repository can specify the Public 1.0 protocol boundary, but **cross-implementation interoperability is not yet independently proven** — that distinction must stay explicit.

## Quickstart (reference implementation)

```bash
pip install -e .
isql-core locality-native-build --frames-dir ./bases --index locality.ili1
isql-core locality-native-info --index locality.ili1
isql-core locality-native-select --index locality.ili1 --frames-dir ./bases \
  --target target.isql7 --out selected.bin --top-k 8 --probe-factor 4
```

See [`docs/RUNTIME_NOTES.md`](docs/RUNTIME_NOTES.md) for the full CLI surface, every historical version's controlled results (v0.4 through v1.0), and non-goals.
