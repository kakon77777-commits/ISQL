# Release Notes

## v1.0.0 — Compact Machine-Native Locality Index

- Added canonical `ILI1` compact binary locality-index format with raw SHA-256 material, registry-binding deduplication, canonical varints, CRC32 validation, and encode/decode byte canonicality.
- Added bounded indexed recall using exact block postings plus registry/resolution total-sum neighbor tables; detailed heuristic scoring no longer requires a full entry scan per query.
- Preserved the rule that heuristic recall cannot decide storage; only actual `ISD8` byte reranking can choose a base.
- Added `locality-native-build`, `locality-native-info`, and `locality-native-select`.
- 256-base controlled corpus: JSON index 219,185 B → ILI1 37,421 B (17.07%); 64 metadata probes and 8 actual reranks still match exhaustive oracle and select 92 B from a 143 B target.
- 4096-base controlled corpus: ILI1 598,061 B (~146.01 B/entry); 64 metadata probes (1.5625%) and 8 actual reranks select the planted 92 B base.
- Retained v0.9 JSON locality index APIs/CLI for compatibility and inspection.
- Preserved v0.4 numeric wire, v0.5 registry wire, v0.6 D40 carrier, v0.7 ISN7, and v0.8 ISD8 frozen behavior.
- v1.0 remains an experimental runtime milestone, not a universal-compression or production-security claim.

## v0.9.0 — ISQL-MEM Locality Index and Automatic Base Selection

- Added rebuildable locality signatures/index for standalone `ISN7` bases.
- Added deterministic top-k recall using registry match, exact block fingerprints, coarse block sums, and item-count distance.
- Added actual-byte reranking: recalled candidates are really encoded as `ISD8`; heuristic score never decides the final base.
- Added automatic fallback to standalone `ISN7` when all deltas are larger.
- Added SHA-256 binding for loaded base refs and target self-exclusion.
- Added `locality-index-build`, `locality-index-info`, and `locality-select` CLI commands.
- Frozen identical-neighbor case: 121 B → 87 B; near-neighbor case: 121 B → 97 B; low-locality case remains 126 B standalone.
- 256-base deterministic corpus: top-8 rerank matches exhaustive 256-base oracle and selects 92 B from 143 B target, pruning 96.875% of actual delta encodes.
- Explicitly records current JSON index overhead: 220,384 B for 256 entries versus 36,595 B of indexed base frames; index is speed infrastructure, not compression.
- Preserves v0.4-v0.8 wire formats unchanged.

## v0.8.0 — ISQL-MEM Locality Delta Frames and Random Access

- Added one-hop `ISD8` locality delta frames referencing exact standalone `ISN7` bases by SHA-256.
- Added canonical per-block COPY, signed DELTA, and REPLACE modes.
- Added registry-binding inheritance with explicit override only when the target registry changes.
- Added native and delta block indexes plus block/range random-access decode.
- Added locality compiler that chooses delta only when smaller than standalone native.
- Added `delta-compile`, `delta-info`, `delta-decode`, `delta-block`, and `locality-compile` CLI commands.
- Preserved v0.7 `ISN7` frozen frames byte-for-byte.
- Live identical semantic neighbor: 121 B standalone → 87 B delta (5 COPY blocks).
- Live same-registry near neighbor: 121 B → 97 B delta (3 COPY + 2 DELTA).
- Live registry-growth low-locality target: candidate delta 168 B, selector keeps 126 B standalone.


## v0.7.0 — ISQL-MEM Machine-Native Canonical Representation

- Removed human-readable decimal text from the canonical memory requirement.
- Added `ISN7` binary spectral-memory frame.
- Stores stable source address as raw 32-byte SHA-256 material.
- Stores registry SHA-256 as raw 32-byte material.
- Added canonical 16-value block bit-packing for spectral integer sequences.
- Added `native-compile`, `native-decode`, `native-info`, and `native-debug` CLI commands.
- Debug rendering is explicitly non-canonical and never required for decode.
- Native decode verifies exact spectral registry revision/hash before semantic expansion.
- Preserved v0.4 numeric memory wire, v0.5 registry wire, and v0.6 D40 carrier byte-for-byte.
- Frozen R2 native frames are 121/121/126 B versus v0.6 D40 122/122/128 B with coordinate fidelity 1.0.

## v0.6.0 — ISQL-MEM Physical Digit Carrier Packing

- Added transport-only `IPC6` binary carrier framing while preserving canonical digits-only wires.
- Added BCD4 baseline codec with exact odd-length sentinel validation.
- Added D40 bounded decimal packing: 12 digits → 5 bytes, with deterministic partial-block widths.
- Preserves leading zeros and avoids whole-wire arbitrary big-integer conversion.
- Added CRC32 accidental-corruption detection and fail-closed framing.
- Added `carrier-pack`, `carrier-unpack`, and `carrier-info` CLI commands.
- Preserved v0.4 numeric memory wires and v0.5 registry numeric wires byte-for-byte.
- Cold 3515-byte registry numeric wire packs to 1477 B, only 25 B above the 1452 B direct structural binary.
- Partial 902-byte registry numeric wire packs to 388 B, 20 B above the 368 B direct structural binary.

## v0.5.0 — ISQL-MEM Hierarchical Spectral Registry Compaction

- Added exact Unicode lexeme registry and namespace value programs.
- Added append-only hierarchical revision deltas and persistent revision store.
- Added exact canonical-registry reconstruction with SHA-256 verification.
- Added compact structural binary registry frames.
- Added digits-only numeric registry delta wire.
- Added `registry-compile-hierarchical`, `registry-decode-wire`, and `registry-compare` CLI commands.
- Preserved v0.4 numeric memory wire byte-for-byte.
- Live partial-vocabulary structural delta is 368 B versus a 600 B canonical JSON append delta (61.3%).
- Explicitly records that ASCII decimal transport is larger than the compact binary structural frame.


## v0.4.0 — ISQL-MEM Numeric Wire Encoding

- Adds a digits-only numeric wire carrier over v0.3 spectral packets.
- Adds a prefix-free decimal unsigned-integer codec with canonical length encoding.
- Binds numeric wire to exact spectral registry revision and full SHA-256 registry hash.
- Adds CRC32 accidental-corruption detection without treating it as cryptographic identity.
- Adds an additive `numeric` R0–R4 memory profile while preserving previous profile codes.
- Adds `NumericWireDecoder` and numeric compaction metrics.
- Adds `numeric-wire-compile`, `numeric-wire-decode`, and `memory-encode --numeric-wire`.
- Live fixtures preserve coordinate fidelity 1.0 while reducing v0.3 packet JSON from 318–332 B to 262–278 B in warm/partial cases.
- Explicitly retains the textual shared registry as a nonnumeric dependency; v0.4 is not yet a fully numeric universe.

## v0.3.0 — ISQL-MEM Spectral Coordinate Compaction

- Added append-only, revisioned `SpectralRegistry` with immutable issued IDs.
- Added registry snapshots and exact revision/hash packet binding.
- Added `SpectralPacket` sparse integer coordinate sequences.
- Added exact packet -> semantic-coordinate round-trip.
- Added third `spectral` memory profile without changing existing address/baseline/semantic codes.
- Added `SpectralCoordinateDecoder`.
- Added compaction metrics separating packet cost and registry-growth cost.
- Added `spectral-compile` and `spectral-registry-info` CLI commands.
- Added `memory-encode --spectral` and spectral-aware profile comparison.
- Preserved v0.1/v0.2 record compatibility and R4 exact-source boundary.
- Live controlled experiment demonstrated 1.0 coordinate fidelity for all three test memories; warm shared-vocabulary packet was ~15% of verbose coordinate bytes.

## v0.2.0

AI-assisted typed semantic memory profiles, semantic coordinate decoder, coordinate fidelity metrics, and baseline-vs-semantic comparison.
