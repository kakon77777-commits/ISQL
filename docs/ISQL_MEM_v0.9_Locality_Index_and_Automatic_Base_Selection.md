# ISQL-MEM v0.9 — Locality Index and Automatic Base Selection

## Purpose

v0.8 proved that one-hop `ISD8` delta frames can reduce nearby machine-native memories and can fall back to standalone `ISN7` when locality is poor. v0.9 removes the manual-base requirement.

The new pipeline is:

$$
\boxed{
\text{Target ISN7}
\rightarrow
\text{Locality Signature}
\rightarrow
\text{Top-k Recall}
\rightarrow
\text{Actual ISD8 Byte Rerank}
\rightarrow
\min(\text{best ISD8},\text{standalone ISN7})
}
$$

The heuristic never decides the final representation. It only reduces the number of bases that receive a real delta encode.

## Derived index

Each standalone `ISN7` base contributes:

- frame reference;
- frame SHA-256;
- source-address digest;
- resolution;
- registry revision/hash;
- item count and frame size;
- per-16-coordinate block: 64-bit fingerprint, item count, sum, and maximum value.

The index contains no canonical memory and may be deleted and rebuilt.

## Recall

Candidates are ranked deterministically by:

1. exact registry match;
2. exact block fingerprint count;
3. coarse normalized block-sum distance;
4. item-count distance;
5. frame SHA-256 tie-break.

This score is intentionally cheap and fallible.

## Exact reranking

For every recalled base $b$, the runtime computes the real candidate:

$$
d_b=\operatorname{EncodeISD8}(b,t).
$$

Then:

$$
b^*=\arg\min_b |d_b|.
$$

The delta is selected only if:

$$
|d_{b^*}|<|t|.
$$

Otherwise v0.9 writes the original standalone target.

## Adversarial heuristic test

A synthetic test deliberately constructs:

- candidate A with the same block sum as the target but large positive/negative per-coordinate differences;
- candidate B with a slightly worse block-sum score but every coordinate only one unit away.

The heuristic ranks A first. Actual-byte reranking selects B. This verifies:

$$
\boxed{\text{heuristic similarity}\neq\text{storage decision}.}
$$

## Live results

| Case | Candidate pool | Exact reranks | Standalone | Selected | Result |
|---|---:|---:|---:|---:|---|
| Frozen identical neighbor | 2 | 2 | 121 B | **87 B** | ISD8 |
| Frozen near neighbor | 3 | 2 | 121 B | **97 B** | ISD8 |
| Frozen low locality | 2 | 2 | **126 B** | **126 B** | ISN7 fallback |
| Synthetic 256-base corpus | 256 | **8** | 143 B | **92 B** | ISD8 |

All four indexed selections match an exhaustive actual-byte oracle over the same candidate pools.

The 256-base case prunes:

$$
1-\frac{8}{256}=\boxed{96.875\%}
$$

of expensive actual-delta evaluations while selecting the same base and same 92-byte frame as exhaustive search.

## Explicit cost of the v0.9 index

The current JSON index is intentionally auditable rather than compact. In the 256-base synthetic corpus:

- base frames total: 36,595 B;
- locality index JSON: 220,384 B.

Therefore the index is **not** a memory-compression representation. It is rebuildable speed infrastructure. Future work may replace its storage form without changing `ISN7`, `ISD8`, or semantic identity.

## Safety / invariants

- Only standalone `ISN7` frames may enter the base index.
- `ISD8` frames are never indexed as bases, preventing multi-hop chains.
- The target frame itself is excluded by SHA-256.
- Base bytes loaded for reranking must match the indexed SHA-256.
- Missing or modified base references fail closed.
- Index order and rebuild are deterministic.
- v0.4 numeric wire, v0.5 registry wire, v0.6 carriers, v0.7 `ISN7`, and v0.8 `ISD8` formats are unchanged.

## CLI

```bash
isql-core locality-index-build \
  --frames-dir ./bases \
  --index ./locality.json
```

```bash
isql-core locality-index-info --index ./locality.json
```

```bash
isql-core locality-select \
  --index ./locality.json \
  --frames-dir ./bases \
  --target ./new-memory.isql7 \
  --top-k 8 \
  --out ./selected.bin
```

The output is either `ISD8` or the original standalone `ISN7`.
