# ISQL Core Runtime v0.7.0

ISQL Core Runtime v0.7.0 implements **ISQL-MEM v0.7 Machine-Native Canonical Representation**. Human-readable decimal text is no longer a canonical requirement.

## v0.7 in one line

```text
semantic coordinates
→ spectral integer sequence
→ raw address + raw registry binding
→ ISN7 block-bit-packed binary frame
```

The canonical machine path does **not** call the v0.4 numeric-wire codec or v0.6 decimal carrier codecs. Decimal/text forms remain compatibility, inspection, and export views only.

### Frozen R2 live result

- 262 B ASCII numeric → 122 B D40 → **121 B native frame**.
- 262 B ASCII numeric → 122 B D40 → **121 B native frame**.
- 278 B ASCII numeric → 128 B D40 → **126 B native frame**.
- Coordinate round-trip fidelity: **1.0** for all three.
- Native frame stores raw 32-byte source address and raw 32-byte registry hash directly.

See `docs/ISQL_MEM_v0.7_Machine_Native_Canonical_Representation.md`.

---

## Historical v0.6 Runtime Notes
ISQL Core Runtime v0.6.0 implements **ISQL-MEM v0.6 Physical Digit Carrier Packing** without changing the canonical v0.4 numeric memory wire or v0.5 numeric registry wire.

## v0.6 in one line

```text
canonical digits-only wire
→ BCD4 / D40 physical packing
→ binary storage/transport
→ exact unpack to the same canonical digits
```

The canonical sequence remains digits-only. The binary carrier is transport-only and does not create a new memory profile.

### Live result

- 3515 B cold registry numeric wire → **1477 B D40 carrier**; direct v0.5 structural binary is 1452 B, so packed-numeric overhead is only **25 B / +1.72%**.
- 902 B partial-growth registry wire → **388 B D40 carrier** versus 368 B structural binary (**+20 B / +5.43%**).
- 262 B memory numeric wire → **122 B D40 carrier** (~46.6%).
- 278 B memory numeric wire → **128 B D40 carrier** (~46.0%).
- BCD4 provides a simpler ~50% payload-density baseline; D40 uses 12 decimal digits per 5 bytes.
- All carriers unpack byte-for-byte to the original numeric wire.

See `docs/ISQL_MEM_v0.6_Physical_Digit_Carrier_Packing.md`.

---

## Historical v0.5 Runtime Notes

ISQL Core Runtime v0.5.0 implements **ISQL-MEM v0.5 Hierarchical Spectral Registry Compaction** while preserving every v0.4 memory code and numeric wire.

## v0.5 in one line

```text
canonical spectral registry
→ shared lexeme registry
→ namespace value programs
→ incremental structural delta
→ digits-only registry wire
```

The canonical spectral registry remains authoritative. The hierarchical registry is a derived, exactly reconstructable representation.

### Live result

- Cold canonical JSON append delta: 1902 B → structural hierarchical delta: **1452 B (76.3%)**.
- Partial-vocabulary append delta: 600 B → **368 B (61.3%)**.
- Warm identical vocabulary: **0 B registry update required**.
- ASCII digits-only transport is larger (3515 B / 902 B), so v0.5 explicitly separates semantic structural compaction from physical decimal-carrier density.
- Coordinate fidelity remains **1.0** and canonical registry hashes reconstruct exactly.

See `docs/ISQL_MEM_v0.5_Hierarchical_Spectral_Registry_Compaction.md`.

---

## Historical v0.4 Runtime Notes

ISQL Core Runtime v0.4.0 implements **ISQL-MEM v0.4 Numeric Wire Encoding** on top of the v0.1–v0.3 code-space, stable addressing, multi-resolution memory, AI semantic analysis, and registry-backed spectral coordinate layers.

## Four coexisting memory profiles

One stable source address can now carry four independent representations:

```text
baseline  -> deterministic v0.1 representation
semantic  -> verbose typed AI semantic coordinates (v0.2)
spectral  -> registry-backed sparse integer coordinates (v0.3)
numeric   -> digits-only self-delimiting wire over spectral coordinates (v0.4)
```

Adding the `numeric` profile does not alter stable `ISQL-ADDR` identity or any existing baseline/semantic/spectral MEM code when compared from the same registry state.

## Numeric wire

The canonical v0.4 runtime carrier contains ASCII digits `0-9` only.

It serializes:

- numeric-wire magic;
- wire protocol version;
- exact spectral registry revision;
- full 256-bit spectral registry hash encoded as a decimal integer;
- spectral sequence item count;
- the sparse integer spectral sequence;
- CRC32 corruption guard.

There are no commas, braces, JSON keys, Base64 symbols, hexadecimal characters, separators, or floating-point values in the wire.

Integers use a self-delimiting decimal-length token. Lengths 1–9 use a one-digit length prefix. Larger decimal integers use an extended length-of-length form. Noncanonical leading zeros and malformed/truncated lengths fail closed.

CRC32 is only a transport corruption guard. Semantic identity remains bound by the full SHA-256 spectral registry hash and registry revision.

## Pipeline

```text
source bytes
  -> stable ISQL-ADDR
  -> AI SemanticAnalysis
  -> append-only Spectral Registry
  -> sparse SpectralPacket
  -> digits-only Numeric Wire
  -> ISQL-MEM numeric R1/R2
  -> NumericWireDecoder
  -> spectral packet reconstruction
  -> registry expansion
  -> semantic coordinates
  -> recovery / fidelity measurement
```

The v0.3 spectral sequence already removes relation-object JSON structure: relations are represented as counted subject/predicate/object integer tuples. v0.4 serializes that structural sequence without JSON framing overhead.

## Live v0.4 experiment

The release reuses the same three-memory fixture family used by v0.3.

| Memory | Verbose coords | Spectral packet JSON | Numeric wire | Registry delta | Numeric total | Coordinate fidelity |
|---|---:|---:|---:|---:|---:|---:|
| 1 cold | 2131 B | 321 B | **262 B** | 1607 B | **1869 B** | 1.000 |
| 2 full vocabulary reuse | 2131 B | 318 B | **262 B** | 0 B | **262 B** | 1.000 |
| 3 partial vocabulary growth | 2162 B | 332 B | **278 B** | 310 B | **588 B** | 1.000 |

For these controlled fixtures:

- cold total is about 87.7% of verbose typed coordinates;
- fully warm numeric wire is about 12.3% of verbose typed coordinates;
- partial-growth total is about 27.2% of verbose typed coordinates;
- numeric wire is about 81.6–83.7% of the already compact v0.3 packet JSON;
- typed-coordinate round-trip fidelity remains 1.0.

This is a controlled engineering fixture, not a universal compression benchmark.

## CLI

Create baseline + semantic + spectral + numeric profiles:

```bash
isql-core memory-encode --store ./memory --text "..." \
  --semantic-analysis-file analysis.json --numeric-wire
```

Compile a numeric wire without creating a memory record:

```bash
isql-core numeric-wire-compile --store ./memory \
  --semantic-analysis-file analysis.json
```

Decode a standalone numeric wire back to spectral packet metadata:

```bash
isql-core numeric-wire-decode --wire 94040...
```

Decode any stored profile automatically:

```bash
isql-core memory-decode --store ./memory --code ISQL1:MEM:R2:...
```

Compare all profiles:

```bash
isql-core memory-compare --store ./memory \
  --address ISQL1:ADDR:R0:H... --resolution R2 \
  --source-file source.txt --semantic-reference-file analysis.json
```

## Compatibility and invariants

- v0.1/v0.2/v0.3 memory records remain readable.
- `numeric` is additive; previous profiles remain canonical and independently decodable.
- Numeric R1/R2 layer data is exactly one digits-only `wire` field.
- Wire decoding recreates the same spectral registry revision/hash and integer sequence.
- Registry mismatch fails during spectral expansion.
- R4 remains the only layer allowed to declare exact recovery.
- `registry_delta_bytes` is measurement metadata and is intentionally excluded from canonical numeric-wire semantics.

## Non-goals of v0.4

- the shared registry is still a textual dictionary on disk;
- no claim that all ISQL state is now numeric;
- no entropy coding/arithmetic coding;
- no distributed registry synchronization or concurrent writer protocol;
- no cryptographic claim for CRC32;
- no universal compression claim from three fixtures.
