# ISQL-MEM v0.4 — Numeric Wire Live Results

Date: 2026-08-17

The v0.4 experiment reuses the same three semantic-coordinate fixture family from v0.3 so the only new variable is numeric wire serialization.

## R2 results

| Memory | Verbose coordinates | v0.3 SpectralPacket JSON | v0.4 numeric wire | Registry delta | v0.4 total | Coordinate fidelity |
|---|---:|---:|---:|---:|---:|---:|
| 1 — cold registry | 2131 B | 321 B | **262 B** | 1607 B | **1869 B** | 1.000 |
| 2 — full vocabulary reuse | 2131 B | 318 B | **262 B** | **0 B** | **262 B** | 1.000 |
| 3 — partial vocabulary growth | 2162 B | 332 B | **278 B** | 310 B | **588 B** | 1.000 |

## Ratios

Memory 1:

- wire / SpectralPacket JSON: 0.8162
- wire / verbose coordinates: 0.1229
- wire + cold registry delta / verbose coordinates: **0.8771**

Memory 2:

- wire / SpectralPacket JSON: 0.8239
- wire / verbose coordinates: **0.1229**
- registry delta: **0 B**

Memory 3:

- wire / SpectralPacket JSON: 0.8373
- wire / verbose coordinates: 0.1286
- wire + registry delta / verbose coordinates: **0.2720**

## What changed from v0.3

v0.3 already replaced verbose relation objects and semantic strings with shared registry IDs and sparse integer tuple structure. v0.4 removes packet JSON framing from the runtime carrier.

The wire contains ASCII digits only and reconstructs the same:

- registry revision;
- full registry SHA-256 binding;
- sparse integer sequence;
- typed semantic coordinates.

All three fixtures round-trip to the original v0.2 coordinate sets exactly.

## Important negative boundary

The shared Spectral Registry is still a textual dictionary stored as JSON snapshots. Therefore v0.4 is **not** yet a fully numeric representation of the whole memory system.

The result demonstrated here is narrower:

> A registry-backed typed semantic packet can use a deterministic, separator-free, digits-only runtime carrier while preserving the typed coordinate set exactly.
