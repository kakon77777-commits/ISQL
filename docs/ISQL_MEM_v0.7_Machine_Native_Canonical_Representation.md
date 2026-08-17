# ISQL-MEM v0.7 — Machine-Native Canonical Representation

## Purpose

v0.7 removes a mistaken engineering constraint from the ISQL mainline: **canonical memory does not need to be directly readable by humans**.

ISQL is intended primarily for AI/agent memory, addressing, retrieval, and machine-to-machine use. Human-readable decimal strings are therefore inspection/export representations, analogous to disassembly or debug dumps, not the memory object itself.

## Canonical distinction

$$
\boxed{\operatorname{DebugRender}(C)\neq C}
$$

The v0.7 canonical machine-memory object is:

$$
\boxed{C_{\mathrm{native}}=(V,D,R,A,H,\mathbf z)}
$$

where $A$ is the raw 256-bit stable source address, $H$ is the raw 256-bit registry hash, and $\mathbf z$ is the integer spectral-coordinate sequence.

## Native frame

The binary `ISN7` frame contains:

- version and frame kind;
- R1/R2 resolution;
- raw 32-byte stable address digest;
- spectral registry revision;
- raw 32-byte registry SHA-256;
- spectral sequence item count;
- 16-value block bit-packed coordinates;
- CRC32 accidental-corruption check.

The spectral sequence is never rendered as decimal during canonical encode/decode.

## Bit packing

Each block of at most 16 integers computes:

$$
w=\max_i \operatorname{bitlength}(z_i).
$$

The block stores $w$ once, then stores each coordinate using exactly $w$ bits. Zero-only blocks use $w=0$. Unused pad bits must be zero, so encodings are canonical rather than merely decodable.

## Address identity

Previous textual addresses encode the SHA-256 digest as a decimal string. v0.7 provides a compatibility bridge but native frames store the original 32-byte digest directly.

Thus:

$$
\text{decimal address} = \text{debug/compatibility view},
$$

while:

$$
\text{raw digest} = \text{native identity material}.
$$

## Registry

The v0.5 hierarchical structural registry frame was already binary. v0.7 treats the structural binary path as the machine-native registry path. Numeric registry rendering and D40 packing remain compatible historical transports but are no longer required by the native execution path.

## Compatibility

v0.7 does not delete or rewrite:

- v0.4 digits-only numeric memory wire;
- v0.5 numeric registry wire;
- v0.6 BCD4/D40 physical carriers.

They remain useful for experiments, interchange, debugging, and legacy replay.

## Live result

Frozen R2 fixtures:

| memory | ASCII numeric | v0.6 D40 | v0.7 native | coordinate fidelity |
|---|---:|---:|---:|---:|
| 1 | 262 B | 122 B | **121 B** | 1.0 |
| 2 | 262 B | 122 B | **121 B** | 1.0 |
| 3 | 278 B | 128 B | **126 B** | 1.0 |

The primary result is architectural rather than merely a 1–2 byte size win: **the canonical path no longer contains decimal text at all**.

## New canonical pipeline

```text
source / event
→ stable raw address digest
→ semantic coordinates
→ spectral registry IDs
→ integer spectral sequence
→ ISN7 machine-native bitstream
```

Human inspection is external:

```text
ISN7 frame
→ native-debug / inspector
→ optional text view
```

That text is never hashed or replayed as the canonical memory object.
