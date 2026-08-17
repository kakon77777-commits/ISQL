# ISQL Core Runtime v1.0 — Compact Machine-Native Locality Index

**Release:** ISQL Core Runtime v1.0.0  
**Index format:** `ILI1`  
**Status:** Experimental engineering runtime

## 1. Purpose

v0.9 completed automatic one-hop delta-base selection, but its locality index was an auditable JSON structure whose storage cost was much larger than the base frames themselves. v1.0 removes that human-readable index from the AI runtime path.

The new pipeline is:

$$
\boxed{
\text{ISN7 base pool}
\rightarrow
\text{ILI1 compact derived index}
\rightarrow
\text{bounded indexed recall}
\rightarrow
\text{actual ISD8 byte rerank}
\rightarrow
\min(\text{ISD8},\text{ISN7})
}
$$

The index remains disposable derived infrastructure. It can be rebuilt from standalone `ISN7` bases and never defines memory identity.

## 2. ILI1 binary representation

`ILI1` stores:

- format version;
- deduplicated `(registry revision, raw 32-byte registry SHA-256)` table;
- canonical sorted base entries;
- raw 32-byte frame SHA-256;
- raw 32-byte source-address SHA-256;
- resolution;
- registry-table ID;
- item/frame counts;
- per-block 8-byte fingerprints, sums, maxima, and item counts;
- CRC32 accidental-corruption guard.

It does **not** store JSON property names or hexadecimal hash strings.

Canonical invariant:

$$
\boxed{
\operatorname{Encode}(\operatorname{Decode}(b))=b.
}
$$

Malformed magic/version, noncanonical varints, invalid table references, bad UTF-8 refs, truncation, trailing bytes, and checksum mismatch fail closed.

## 3. Search model

Loading `ILI1` builds transient machine indexes:

1. exact block-fingerprint postings;
2. registry-local rows sorted by total coordinate sum;
3. resolution-local rows sorted by total coordinate sum.

The query path does not linearly calculate the full v0.9 heuristic for every base. Instead it creates a bounded metadata probe set from exact postings and nearest sorted rows, then applies the existing heuristic only to that set.

For top-k $k$ and probe factor $f$:

$$
P\le 2kf
$$

in the current v1.0 policy.

The target frame is excluded by SHA-256.

## 4. Heuristic remains non-authoritative

Candidate recall is only a search accelerator.

For every recalled base $b_i$, v1.0 still computes the real one-hop frame:

$$
d_i=|\operatorname{ISD8}(b_i,t)|.
$$

Storage selection remains:

$$
\operatorname{Select}(t)=
\begin{cases}
\operatorname{ISD8}(b^*,t), & \min_i d_i<|t|,\\
t,&\text{otherwise}.
\end{cases}
$$

A dedicated adversarial test deliberately makes the heuristic rank the wrong base first; actual-byte reranking still selects the smaller delta.

## 5. 256-base oracle experiment

Deterministic synthetic corpus:

- entries: 256;
- target standalone: 143 B;
- planted near base: four identical coordinate blocks plus one small signed-delta block;
- exhaustive oracle optimum: 92 B.

Results:

| Metric | v0.9 JSON / exhaustive context | v1.0 ILI1 |
|---|---:|---:|
| Index bytes | 219,185 B | **37,421 B** |
| Index ratio | 100% | **17.07%** |
| Metadata entries fully scored | 256 in exhaustive oracle | **64** |
| Actual ISD8 reranks | 256 exhaustive | **8** |
| Selected base | `base-good.isql7` | `base-good.isql7` |
| Selected frame | 92 B | **92 B** |

Thus:

$$
\boxed{
\text{ILI1 size}\approx0.171\times\text{JSON index size}
}
$$

while top-8 final selection matches the exhaustive byte oracle on this fixture.

## 6. 4096-base structural scale experiment

A deterministic 4096-base corpus uses the same planted near-base construction.

Results:

- `ILI1` bytes: **598,061 B**;
- average compact bytes per indexed base: **146.01 B**;
- metadata probe set: **64/4096 = 1.5625%**;
- actual ISD8 reranks: **8**;
- selected base: `base-good.isql7`;
- selected delta: **92 B** from a 143 B standalone target.

No wall-clock speed claim is made because sandbox process timing is not stable. The release claim is structural: query-time detailed heuristic work and expensive delta encoding are bounded independently of total corpus size under the tested index policy.

## 7. Compatibility

v1.0 is additive.

The following remain unchanged and covered by regression tests:

- v0.4 digits-only numeric memory wire;
- v0.5 numeric registry wire;
- v0.6 D40 carrier;
- v0.7 `ISN7` native frame;
- v0.8 `ISD8` delta frame;
- v0.9 JSON locality index APIs and CLI.

The v0.9 JSON index is retained as an inspection/legacy form. `ILI1` is the recommended runtime index.

## 8. CLI

Build compact runtime index:

```bash
isql-core locality-native-build \
  --frames-dir ./bases \
  --index locality.ili1
```

Inspect metadata:

```bash
isql-core locality-native-info --index locality.ili1
```

Select base and write ISD8/ISN7:

```bash
isql-core locality-native-select \
  --index locality.ili1 \
  --frames-dir ./bases \
  --target target.isql7 \
  --out selected.bin \
  --top-k 8 \
  --probe-factor 4
```

## 9. v1.0 boundary

The first coherent ISQL memory runtime now spans:

$$
\boxed{
\text{AI semantic coordinates}
\rightarrow
\text{shared spectral registry}
\rightarrow
\text{machine-native ISN7}
\rightarrow
\text{one-hop ISD8 locality}
\rightarrow
\text{machine-native ILI1 retrieval}
\rightarrow
\text{actual-byte automatic storage choice}
}
$$

v1.0 does not claim universal semantic compression, globally optimal nearest-neighbor search, or production cryptographic security. It marks the first version where the primary memory, delta, registry, and locality-selection path can remain machine-native end to end.
