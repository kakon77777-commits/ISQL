# ISQL-MEM v0.3 — Spectral Coordinate Compaction

## Purpose

v0.2 proved that AI-produced typed semantic coordinates could be stored and recovered with high coordinate fidelity, but the verbose JSON representation was larger than the deterministic baseline.

v0.3 adds a second representation layer:

$$
\text{SemanticAnalysis JSON}
\rightarrow
\text{Shared Spectral Registry}
\rightarrow
\text{Sparse Integer Coordinate Sequence}.
$$

The verbose semantic analysis remains the auditable authoring/provenance form. The spectral packet is the compact runtime form.

## Invariants

1. Stable `ISQL-ADDR` identity is independent of semantic analysis and registry state.
2. Existing `baseline` and `semantic` profile codes are unchanged.
3. The spectral registry is append-only; issued integer IDs never change meaning.
4. Packets record exact registry revision and SHA-256 registry hash.
5. Packet expansion is deterministic and fail-closed.
6. R4 exact recovery remains exact-source-contract-only.
7. Compression accounting separates packet bytes from registry growth bytes.

## Packet Model

A spectral packet stores integer coordinates for:

- summary;
- concepts;
- entities;
- relation triples;
- claims;
- intent;
- uncertainty;
- tags;
- language.

The runtime sequence is self-delimiting by counted fields. Human-readable semantic strings live in the shared versioned registry instead of being repeated in every memory record.

## Cold vs Warm Cost

For a packet $P$ and registry increment $\Delta G$:

$$
C_{\mathrm{warm}}=|P|,
$$

$$
C_{\mathrm{cold}}=|P|+|\Delta G|.
$$

The two must not be conflated. A first memory may pay vocabulary registration cost; later memories can reuse those IDs at zero registry delta.

## Current Scope

v0.3 is registry-backed integer-sequence compaction. It is **not yet** the final pure-numeric ISQL wire protocol, entropy coder, distributed registry, or learned coordinate ontology.
