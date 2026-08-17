# Release Notes

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
