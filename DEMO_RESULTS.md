# ISQL-MEM v0.3 Live Spectral Compaction Results

## Experiment

Three distinct source texts were stored under three distinct stable `ISQL-ADDR` values.

- Memory 1 uses the initial semantic vocabulary and pays the cold registry creation cost.
- Memory 2 uses different surface wording but the same semantic coordinate vocabulary.
- Memory 3 reuses most prior vocabulary while adding a few new spectral/compaction concepts.

All records contain baseline, semantic, and spectral profiles.

## R2 results

| Memory | Semantic layer bytes | Spectral layer bytes | Packet bytes | Registry delta | Cold total | Warm ratio vs coordinates | Cold ratio vs coordinates | Coordinate fidelity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2265 | 332 | 321 | 1607 | 1928 | 0.1506 | 0.9047 | 1.0000 |
| 2 | 2265 | 329 | 318 | 0 | 318 | 0.1492 | 0.1492 | 1.0000 |
| 3 | 2296 | 343 | 332 | 310 | 642 | 0.1536 | 0.2969 | 1.0000 |

## Interpretation

The v0.2 negative result was that verbose semantic JSON preserved structure but was larger than the deterministic baseline. v0.3 changes the runtime representation rather than adding more semantic prose.

For this controlled fixture:

$$
\text{packet size}\approx 0.15\times\text{verbose coordinate size}
$$

after vocabulary is already registered.

The first memory still pays registry construction cost. That cost is not hidden: packet + registry growth is 1928 B, about 90.5% of the corresponding verbose coordinate representation.

The third memory demonstrates partial reuse: a small registry delta is paid only for newly introduced vocabulary.

Coordinate fidelity is 1.0 because the packet deterministically expands back to the same typed semantic coordinates used by the semantic profile. Text token recovery remains unchanged between semantic and spectral decoders for the same coordinates; v0.3 is compressing representation, not inventing a better semantic analyzer.

## What this does not prove

This does not prove universal semantic compression, optimal coding, or that every corpus will reach the same ratios. Registry amortization depends on vocabulary reuse. The current packet remains a registry-backed integer sequence encoded in compact JSON metadata, not the final pure-numeric ISQL wire format.
