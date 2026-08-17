# ISQL Core Runtime v0.3.0

ISQL Core Runtime v0.3.0 implements **ISQL-MEM v0.3 Spectral Coordinate Compaction** on top of the v0.1/v0.2 code-space, address, memory, AI semantic-analysis, and recoverability layers.

## What changed

A memory can now contain three profiles under the same stable address:

```text
baseline  -> deterministic v0.1 representation
semantic  -> verbose typed AI semantic coordinates (v0.2)
spectral  -> registry-backed sparse integer coordinates (v0.3)
```

The central pipeline is:

```text
source bytes
  -> stable ISQL-ADDR
  -> AI SemanticAnalysis (authoring/provenance)
  -> append-only Spectral Registry
  -> sparse SpectralPacket
  -> ISQL-MEM spectral R1/R2
  -> deterministic registry expansion
  -> semantic reconstruction / fidelity measurement
```

## Spectral registry

The shared registry has independent namespaces for summary, atom, predicate, claim, intent, uncertainty, tag, and language. IDs are namespace-local, positive integers, append-only, revisioned, and snapshot-addressable.

Every packet records:

- registry ID;
- exact registry revision;
- registry SHA-256 hash;
- sparse integer sequence;
- registry delta bytes charged by that compilation.

Unknown or mismatched registry revisions/hashes fail closed.

## Cold vs warm compaction

The live release experiment shows why registry cost must be separated from packet cost:

| Memory | Semantic R2 layer | Packet | Registry delta | Packet + delta | Coordinate fidelity |
|---|---:|---:|---:|---:|---:|
| 1 cold | 2265 B | 321 B | 1607 B | 1928 B | 1.000 |
| 2 same vocabulary | 2265 B | 318 B | 0 B | 318 B | 1.000 |
| 3 partial new vocabulary | 2296 B | 332 B | 310 B | 642 B | 1.000 |

The second memory demonstrates the intended amortization: after vocabulary is shared, the runtime packet is about 15% of the verbose coordinate representation for this fixture.

This is a small controlled experiment, not a universal compression benchmark.

## CLI

Create the v0.2 baseline + semantic profiles:

```bash
isql-core memory-encode --store ./memory --text "..." \
  --semantic-analysis-file analysis.json
```

Also compile the v0.3 spectral profile:

```bash
isql-core memory-encode --store ./memory --text "..." \
  --semantic-analysis-file analysis.json --spectral
```

Compile coordinates without creating a memory:

```bash
isql-core spectral-compile --store ./memory \
  --semantic-analysis-file analysis.json
```

Inspect the shared registry:

```bash
isql-core spectral-registry-info --store ./memory
```

Compare profiles:

```bash
isql-core memory-compare --store ./memory \
  --address ISQL1:ADDR:R0:H... --resolution R2 \
  --source-file source.txt --semantic-reference-file analysis.json
```

## Compatibility

- v0.1 memory records remain readable.
- v0.2 memory records remain readable.
- Existing baseline and semantic MEM codes are unchanged when a spectral profile is added.
- R4 remains the only layer allowed to declare exact recovery.

## Non-goals of v0.3

- no external AI SDK dependency;
- no embedding/vector database;
- no distributed registry synchronization;
- no concurrent registry writer protocol;
- no final pure-digit packet wire format;
- no claim that one fixture establishes general compression performance.
