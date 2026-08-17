# ISQL-MEM v0.5 — Hierarchical Spectral Registry Compaction

## Purpose

v0.5 moves the remaining textual shared spectral registry into a derived hierarchical representation while keeping the canonical `SpectralRegistry` authoritative and append-only.

The pipeline is:

$$
\text{Canonical Registry}
\rightarrow
\text{Shared Lexemes}
\rightarrow
\text{Value Programs}
\rightarrow
\text{Incremental Structural Delta}
\rightarrow
\text{Digits-Only Registry Wire}.
$$

## Semantic identity boundary

The hierarchical layer never reassigns canonical IDs. `(namespace, value_id)` remains semantic identity; lexeme IDs are only a compiled representation. Every compiled revision must reconstruct the exact canonical UTF-8 strings and reproduce the canonical registry SHA-256.

## Exact lexeme layer

Registry text is reversibly tokenized. Repeated words, punctuation, spaces, and East-Asian characters can reuse lexeme IDs across values and revisions. The tokenizer performs no semantic normalization.

## Incremental revision delta

Because the canonical registry is append-only, a v0.5 delta contains only:

- newly interned lexemes;
- newly appended value programs;
- revision lineage;
- canonical and hierarchical hashes.

A no-op canonical revision requires no registry transfer.

## Numeric registry wire

A compact binary structural frame is encoded into a decimal big-integer carrier. The externally visible wire contains ASCII `0-9` only. CRC32 detects accidental corruption; canonical SHA-256 remains the semantic integrity binding.

The decimal carrier is intentionally reported separately from the compact structural frame because ASCII decimal has lower information density than binary bytes.

## Live experiment

Using the same three-memory corpus as v0.4:

| Case | Canonical JSON append delta | Hierarchical structural frame | Ratio | Digits-only wire |
|---|---:|---:|---:|---:|
| Cold bootstrap | 1902 B | 1452 B | 76.3% | 3515 B |
| Warm identical vocabulary | 0 B | 0 B required | — | 0 B required |
| Partial vocabulary growth | 600 B | 368 B | 61.3% | 902 B |

All three memories retained coordinate fidelity `1.0`, and every hierarchical revision reconstructed the exact canonical registry hash.

The result is intentionally two-sided:

1. **Hierarchical semantic structure compacts registry updates.**
2. **ASCII decimal transport expands the compact binary frame.**

Therefore the next transport problem is physical digit packing, not semantic-registry organization.

## Invariants

- v0.4 numeric memory wire remains byte-for-byte unchanged.
- canonical spectral IDs never change.
- hierarchical lexeme/program tables are append-only.
- exact UTF-8 reconstruction is mandatory.
- wrong previous hash/revision fails closed.
- R4 exact-source semantics are untouched.
