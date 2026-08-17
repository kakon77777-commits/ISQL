# ISQL-MEM v0.8 — Locality Delta Frames and Random-Access Partial Decode

## Position

v0.7 established the machine-native standalone `ISN7` frame. v0.8 adds an optional one-hop locality layer without changing `ISN7` bytes.

$$
\boxed{\text{ISN7 base} + \text{ISD8 delta} \rightarrow \text{target memory}}
$$

`ISD8` is not a recursive history log. Its base must be a standalone `ISN7` frame.

## Block modes

Each target block contains up to 16 spectral integers and is encoded canonically as exactly one of:

- `COPY`: target block equals aligned base coordinates;
- `DELTA`: signed differences, zigzag encoded and bit-packed, only when strictly smaller than replacement;
- `REPLACE`: ordinary v0.7 unsigned bit-packed target block.

Ties choose `REPLACE`. Exact equality always chooses `COPY`.

## Frame binding

An `ISD8` frame stores:

- target raw stable-address digest;
- exact SHA-256 of the base `ISN7` frame;
- target resolution;
- target item count;
- optional registry revision/hash override;
- block mode directory;
- block payloads;
- CRC32 accidental-corruption guard.

If target and base share registry revision/hash, the binding is inherited and the 32-byte hash is not duplicated.

## Locality selector

The locality compiler always constructs the standalone target `ISN7` frame and a candidate `ISD8` frame. Delta is selected only when:

$$
|ISD8| < |ISN7|.
$$

Otherwise v0.8 stores the standalone target. Locality is therefore opportunistic and cannot increase selected storage size.

## Random access

Both standalone and delta representations expose block indexing. A caller can retrieve a specific coordinate block without unpacking unrelated blocks.

The v0.8 proof test deliberately damages a later delta payload while recomputing frame CRC. Decoding block 0 still succeeds, while full-frame decode fails. This demonstrates that random block access does not materialize unrelated target payloads.

## Frozen live results

| Case | Standalone ISN7 | Candidate ISD8 | Selected | Block modes |
|---|---:|---:|---:|---|
| identical semantic neighbor | 121 B | 87 B | 87 B delta | 5 COPY |
| same-registry near neighbor | 121 B | 97 B | 97 B delta | 3 COPY + 2 DELTA |
| registry growth / low locality | 126 B | 168 B | 126 B native | 5 REPLACE + override |

Ratios for the two locality-positive cases are about 71.9% and 80.2% of standalone native size.

## Compatibility

v0.8 is additive:

- v0.4 numeric memory wire unchanged;
- v0.5 registry numeric wire unchanged;
- v0.6 D40 carrier unchanged;
- v0.7 `ISN7` frozen frames unchanged.

## Next frontier

v0.8 does not search for the best base automatically. A future locality index can rank candidate bases using registry-aware coordinate signatures, while preserving the one-hop decode bound.
