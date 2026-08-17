# ISQL-MEM v0.6 — Physical Digit Carrier Packing

**Runtime:** ISQL Core Runtime v0.6.0  
**Status:** engineering release  
**Date:** 2026-08-17

## 1. Purpose

v0.4 established a canonical digits-only memory wire. v0.5 established a hierarchical registry whose compact structural binary was much smaller than its ASCII decimal wire. v0.6 keeps those canonical wires unchanged and adds a physical transport layer that packs decimal digits into bytes.

The architectural rule is:

$$
\boxed{
\text{canonical numeric wire}
\neq
\text{physical carrier bytes}
}
$$

The numeric sequence remains the stable logical representation. The carrier is a reversible storage/transport encoding.

## 2. Carrier frame

```text
magic        IPC6
version      6
codec        BCD4 or D40
digit_count  canonical unsigned varint
payload      codec-specific packed decimal bytes
crc32        checksum of the original ASCII digit sequence
```

CRC32 detects accidental corruption only. Semantic integrity remains enforced by the inner numeric wire and its registry/revision/hash rules.

## 3. BCD4 baseline

BCD4 stores two decimal digits in one byte. For odd-length inputs the unused low nibble is `0xF`.

Payload density:

$$
2\ \text{digits}/1\ \text{byte}
$$

or about 50% of ASCII digit storage before carrier framing.

## 4. D40 codec

D40 uses the integer inequality:

$$
10^{12}<2^{40}.
$$

Therefore exactly 12 decimal digits can be represented in five bytes:

$$
12\ \text{digits}\rightarrow5\ \text{bytes}.
$$

The payload asymptotically approaches:

$$
\frac{5}{12}\approx41.67\%
$$

of ASCII digit bytes.

The input is processed in bounded 12-digit chunks. v0.6 never converts an arbitrarily long ISQL wire into one unbounded integer. The final partial chunk has a deterministic byte width derived from its decimal digit count, and decoding zero-pads to restore leading zeros exactly.

## 5. Canonicality and fail-closed behavior

The carrier rejects:

- non-ASCII or nondigit input;
- unknown magic/version/codec;
- malformed/noncanonical varints;
- truncated or trailing payload bytes;
- invalid BCD nibbles or odd-length sentinel;
- D40 values outside the allowed decimal range for their block width;
- CRC mismatch.

Required invariant:

$$
\boxed{
\operatorname{unpack}(\operatorname{pack}(w,c))=w
}
$$

for every valid canonical digit wire $w$ and supported codec $c$.

## 6. Compatibility

v0.6 does **not** add a new memory profile. Existing profiles remain:

```text
baseline
semantic
spectral
numeric
```

The `numeric` profile remains canonical. v0.6 has byte-for-byte regression tests for:

- the v0.4 numeric memory wire;
- the v0.5 hierarchical registry numeric delta wire.

## 7. Live measurements

### Memory numeric R2

| ASCII wire | BCD4 carrier | D40 carrier | D40 ratio |
|---:|---:|---:|---:|
| 262 B | 143 B | **122 B** | **46.56%** |
| 262 B | 143 B | **122 B** | **46.56%** |
| 278 B | 151 B | **128 B** | **46.04%** |

The ratio is above the 41.67% payload limit because the frame has a fixed header/checksum cost.

### Hierarchical registry delta

| Case | ASCII numeric wire | Structural binary | BCD4 | D40 | D40 vs structural |
|---|---:|---:|---:|---:|---:|
| Cold | 3515 B | 1452 B | 1770 B | **1477 B** | **+25 B / 1.0172×** |
| Partial growth | 902 B | 368 B | 463 B | **388 B** | **+20 B / 1.0543×** |

This is the principal v0.6 result: packing preserves the canonical decimal wire while recovering almost all of the physical-density loss introduced by ASCII decimal transport.

## 8. Interpretation

v0.5 showed that hierarchical registry organization compressed semantic registry updates, but the ASCII decimal carrier expanded them. v0.6 separates these layers:

$$
\boxed{
\text{semantic structure}
\rightarrow
\text{canonical numeric sequence}
\rightarrow
\text{packed physical carrier}
}
$$

For the cold registry fixture, the packed D40 carrier is only 25 bytes larger than the direct v0.5 structural binary. Thus the cost of retaining the numeric-sequence abstraction becomes small rather than dominant.

This does not mean D40 is globally optimal. It is a deterministic, simple, bounded-chunk reference codec that approaches decimal information density without requiring arithmetic coding or a whole-wire big integer.

## 9. CLI

Pack a numeric wire:

```bash
isql-core carrier-pack --wire 95050... --codec d40 --out registry.ipc6
```

Recover the exact canonical digits:

```bash
isql-core carrier-unpack --file registry.ipc6
```

Inspect physical metadata:

```bash
isql-core carrier-info --file registry.ipc6
```

## 10. Next boundary

After v0.6, the main remaining transport question is no longer whether decimal sequences can be stored efficiently. D40 already brings long wires close to the underlying compact binary size.

The next meaningful research targets are higher-level:

- block-level shared carrier dictionaries;
- relation/coordinate locality and delta coding;
- registry synchronization across agents;
- random-access partial decoding;
- error-resilient framing;
- optional entropy coding above the canonical carrier.

Any such layer must preserve the v0.6 separation between canonical numeric identity and physical transport.
