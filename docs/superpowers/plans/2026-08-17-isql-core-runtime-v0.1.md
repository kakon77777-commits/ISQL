# ISQL Core Runtime v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first executable ISQL Core code-base-space runtime implementing grammar/domain separation, deterministic address codes, multi-resolution memory records, decoder contracts, recoverability measurement, replayable canonical serialization, and a small CLI.

**Architecture:** A standard-library-only Python package. `ISQLCode` is the canonical wire object; `DomainRegistry` makes domain meaning explicit. `ISQL-ADDR` is deterministic and model-independent. `ISQL-MEM` stores R0–R4 representations while keeping exact-source identity separate. Decoder/recoverability are interfaces so AI-assisted decoders can be added later without changing identity rules.

**Tech Stack:** Python 3.11+, standard library, `unittest`, UTF-8 JSON.

## Global Constraints

- No floating-point conversion of arbitrary-length digit sequences.
- Canonical code must carry protocol version and domain.
- Address identity and memory representation are separate.
- Exact recovery and semantic recovery are separate success criteria.
- Unknown domains/control prefixes fail closed.
- RESERVED remains undefined unless explicitly enabled by a future registry version.
- AI decoder is an optional adapter, never canonical identity.
- No external packages or network calls in v0.1.
- Every production behavior starts with a failing test.

---

### Task 1: Grammar and canonical code object
- Create `src/isql_core/errors.py`, `src/isql_core/code.py`.
- Test parse/serialize for `ISQL1:MEM:R2:XRQ123456789` and `ISQL1:ADDR:R0:H123...`.
- Reject malformed version/domain/resolution/control/payload.

### Task 2: Domain registry
- Create `src/isql_core/registry.py`, `src/isql_core/data/domains.json`.
- Bootstrap `ADDR, MEM, SEM, STATE, EXEC, RESERVED`.
- RESERVED is parseable as a domain but not executable.

### Task 3: ISQL-ADDR profile
- Create `src/isql_core/address.py`.
- Deterministic SHA-256 content addressing converted to decimal digit payload.
- Same bytes => same address across runs; changed bytes => changed address.

### Task 4: ISQL-MEM multi-resolution profile
- Create `src/isql_core/memory.py`, `src/isql_core/store.py`.
- R0 locator, R1 skeleton, R2 structured memory, R3 rich reconstruction, R4 exact source reference.
- Store keyed by stable address; representations may change independently.

### Task 5: Decoder contracts and recoverability
- Create `src/isql_core/decoder.py`, `src/isql_core/recoverability.py`.
- Deterministic decoder for stored records plus callable AI-decoder adapter interface.
- Exact metric and token-Jaccard semantic metric kept separate.

### Task 6: CLI, docs, release verification
- Create `src/isql_core/cli.py`, `src/isql_core/__main__.py`, `pyproject.toml`, `README.md`.
- Commands: `parse`, `registry-info`, `address`, `memory-encode`, `memory-decode`, `recoverability`.
- Run full unittest, compileall, package import, UTF-8/JSON validation, checksums, ZIP.
