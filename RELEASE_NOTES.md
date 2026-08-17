# Release Notes

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
