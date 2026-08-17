# ISQL-MEM v0.2 — Live Semantic Coordinate Experiment

## Purpose

Test whether one immutable ISQL-ADDR can carry both a deterministic memory profile and an AI-assisted semantic-coordinate profile, and measure both text recovery and structured coordinate fidelity.

This is a development-session mechanism test. The AI coordinate fixture and the review fixture were authored during the same development process and are **not independent scientific ground truth**.

## Stable identity

Both profiles are stored under exactly one source address. The semantic analyzer changes memory representation only; it does not participate in address generation.

## Results

| Resolution | Profile | Layer bytes | Token Jaccard | Coordinate aggregate | Exact |
|---|---|---:|---:|---:|---:|
| R0 | baseline | 165 | 0.0000 | — | false |
| R0 | semantic | 304 | 0.0000 | — | false |
| R1 | baseline | 238 | 0.1206 | — | false |
| R1 | semantic | 651 | 0.0995 | 0.3333 | false |
| R2 | baseline | 1284 | 0.5859 | — | false |
| R2 | semantic | 2265 | 0.3026 | 0.9800 | false |
| R3 | baseline | 2523 | 1.0000 | — | false |
| R3 | semantic | 4835 | 1.0000 | 0.9800 | false |
| R4 | baseline | 2608 | 1.0000 | — | true |
| R4 | semantic | 2747 | 1.0000 | — | true |

## Main finding

The semantic profile succeeds at explicit structured semantic preservation, but the current JSON representation is not compact. In particular, semantic R2 is larger than deterministic R2.

This creates a concrete next target:

$$
\boxed{\text{ISQL-MEM v0.3: registry-backed spectral coordinate compaction}}
$$

Instead of storing long natural-language concept/claim/relation labels repeatedly, v0.3 should test compact registry IDs, reusable coordinate dictionaries, sparse relation tuples, and shared semantic namespaces.
