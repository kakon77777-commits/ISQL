# ISQL Core Runtime v0.2.0 / ISQL-MEM v0.2

ISQL-MEM v0.2 upgrades the v0.1 memory prototype from one deterministic R0–R4 representation into a **profile-aware multi-resolution memory system**.

The core invariant remains:

$$
\boxed{\text{stable source address} \neq \text{memory representation}}
$$

A single exact source address may now contain multiple memory profiles:

```text
MemoryRecord
├─ address: ISQL1:ADDR:R0:...
├─ baseline
│  ├─ R0
│  ├─ R1
│  ├─ R2
│  ├─ R3
│  └─ R4
└─ semantic
   ├─ R0
   ├─ R1
   ├─ R2
   ├─ R3
   └─ R4
```

## What changed in v0.2

### 1. Profile-aware memory schema

`isql.memory-record/v0.2` stores independent `MemoryVariant` objects under one stable address. The old v0.1 record format is still readable and is migrated in memory to the `baseline` profile.

The default compatibility view still exposes:

```python
record.layers
record.encoder_version
```

as aliases for the `baseline` profile.

### 2. Deterministic baseline is preserved

The v0.1 baseline encoding remains available and its old MEM code construction is preserved:

- R0: locator
- R1: preview + keywords
- R2: sentence heads + keywords
- R3: normalized text + metadata
- R4: exact-source contract

Adding an AI semantic profile does not change the source address or baseline memory codes.

### 3. Typed AI-assisted semantic coordinates

External/AI analyzers can provide:

```json
{
  "schema": "isql.semantic-analysis/v0.2",
  "analyzer_id": "model-or-agent-id",
  "analyzer_contract": "isql-semantic-analysis/v0.2",
  "coordinates": {
    "summary": "...",
    "concepts": ["..."],
    "entities": ["..."],
    "relations": [
      {"subject": "...", "predicate": "...", "object": "..."}
    ],
    "claims": ["..."],
    "intent": "...",
    "uncertainty": ["..."],
    "tags": ["..."],
    "language": "en"
  }
}
```

The runtime has **no model SDK dependency**. An AI can generate this JSON externally, or an application can use `CallableSemanticAnalyzer`.

### 4. Semantic profile resolutions

- **R0** — locator + semantic profile provenance
- **R1** — summary / anchors / intent / tags
- **R2** — full typed semantic coordinates
- **R3** — normalized source + metadata + complete semantic analysis provenance
- **R4** — exact-source contract

R1/R2 semantic decoding is never labeled exact.

### 5. Separate recovery metrics

Text reconstruction still has transparent token Jaccard:

$$
J_{token}(x,\hat{x}).
$$

Semantic coordinates are evaluated separately using:

- concept precision / recall / F1
- entity recall
- relation recall
- claim recall
- intent match

and a transparent aggregate:

$$
F_{coord}
=\frac{F_{concept}+R_{entity}+R_{relation}+R_{claim}+M_{intent}}{5}.
$$

This deliberately does **not** pretend lexical overlap is semantic truth.

## CLI

### Baseline-only encode

```bash
isql-core memory-encode \
  --store ./memory \
  --text "Alpha beta. Alpha gamma."
```

### Encode baseline + semantic profile

```bash
isql-core memory-encode \
  --store ./memory \
  --file source.txt \
  --semantic-analysis-file semantic_analysis.json
```

or:

```bash
isql-core memory-encode \
  --store ./memory \
  --text "..." \
  --semantic-analysis-json '{...}'
```

### Inspect profiles

```bash
isql-core memory-profiles \
  --store ./memory \
  --address ISQL1:ADDR:R0:H...
```

### Decode any profile

`memory-decode` detects whether the MEM code belongs to `baseline` or `semantic` and chooses the correct decoder:

```bash
isql-core memory-decode \
  --store ./memory \
  --code ISQL1:MEM:R2:M...
```

### Compare profiles

```bash
isql-core memory-compare \
  --store ./memory \
  --address ISQL1:ADDR:R0:H... \
  --resolution R2 \
  --source-file source.txt \
  --semantic-reference-file semantic_reference.json
```

The output reports per profile:

- MEM code
- serialized layer data size
- token recovery score
- exact flag
- coordinate fidelity when a semantic reference is available

## v0.2 live experiment

The release includes an AI-authored semantic-coordinate fixture generated in this development session and a separate review fixture. It is a **mechanism test, not an independent scientific benchmark**.

For the bundled source, the measured comparison was:

| Resolution | Profile | Layer bytes | Token score | Coordinate fidelity | Exact |
|---|---|---:|---:|---:|---:|
| R0 | baseline | 165 | 0.0000 | — | false |
| R0 | semantic | 304 | 0.0000 | — | false |
| R1 | baseline | 238 | 0.1206 | — | false |
| R1 | semantic | 651 | 0.0995 | 0.3333 | false |
| R2 | baseline | 1284 | 0.5859 | — | false |
| R2 | semantic | 2265 | 0.3026 | **0.9800** | false |
| R3 | baseline | 2523 | 1.0000 | — | false |
| R3 | semantic | 4835 | 1.0000 | **0.9800** | false |
| R4 | baseline | 2608 | 1.0000 | — | true |
| R4 | semantic | 2747 | 1.0000 | — | true |

### Interpretation

The first semantic-coordinate implementation **does not compress better than the deterministic baseline**. At R2 it is larger and has lower lexical overlap, while preserving much more explicit structured semantic information against the supplied coordinate reference.

That result is intentional to preserve as evidence:

$$
\boxed{\text{semantic structure achieved} \not\Rightarrow \text{compression achieved}}
$$

The next technical problem is therefore not “add more semantic fields.” It is **spectral coordinate compaction**: stable IDs, shared registries, sparse relations, dictionary/reference reuse, and code-space coordinates that stop repeating natural-language labels inside every memory record.

## Important invariants

1. Address identity is derived only from exact source bytes.
2. AI analysis cannot modify address identity.
3. Baseline memory remains available.
4. AI/analyzer provenance is explicit.
5. R4 exactness remains source-contract-only.
6. External AI decoders cannot upgrade semantic reconstruction to exact recovery.
7. Unknown/malformed semantic data fails closed.
8. The core runtime does not require embeddings or network access.

## Version lineage

```text
ISQL Core Runtime v0.1
  deterministic R0–R4
        ↓
ISQL-MEM v0.2
  profile-aware baseline + semantic coordinates
        ↓
proposed v0.3
  spectral coordinate compaction / registry-backed semantic IDs
```
