# ISQL Core Experimental ISX1 Extended-Width Frame v0.1

**Status:** Internal / Experimental candidate  
**Date:** 2026-09-14  
**Magic:** `ISX1`  
**Public status:** NOT Public ISQL; NOT an ISN7 amendment; NOT a frozen successor name.

---

## 1. Purpose

`ISX1` is the first isolated engineering proof of the width-independent Meta-Core model.

The stable Public 1.0 `ISN7` format intentionally remains unchanged and retains its current $64$-bit coordinate ceiling. `ISX1` exists beside it so the implementation can test coordinates wider than one machine word without silently changing Public bytes.

The experiment validates the separation:

$$
\boxed{
\text{semantic width}
\neq
\text{logical width}
\neq
\text{carrier width}
\neq
\text{machine word width}
}
$$

The Python reference implementation currently caps this experiment at:

$$
w_{\max}=4096
$$

bits per coordinate as a resource-safety limit. This cap is an implementation capability, not a Meta-Core ontology bound.

---

## 2. Non-goals

`ISX1` does not:

- modify `ISN7`, `ISD8`, or `ILI1`;
- change Public 1.0 decoder behavior;
- claim the future public successor must be named `ISX1` or `ISN8`;
- add CLI/store integration;
- change `MemoryRecord` persistence;
- change locality-delta semantics;
- change DSR;
- change Origin profile registries;
- establish independent interoperability;
- claim production readiness.

W2 is deliberately a small experimental format surface.

---

## 3. Frame overview

The experimental frame preserves the broad machine-native structure used by the v0.7 line while using a distinct magic and width grammar.

```text
magic                4 bytes   "ISX1"
version              1 byte    1
kind                 1 byte    1 = spectral-memory
resolution           1 byte    1=R1, 2=R2
flags                1 byte    MUST be 0
address_digest      32 bytes    raw stable-address SHA-256 digest
registry_revision   UVarInt     canonical shortest form
registry_hash       32 bytes    raw SHA-256
item_count          UVarInt     1..1,000,000
blocks               variable   16 sequence items per block maximum
crc32                4 bytes    big-endian corruption guard
```

`CRC32` remains accidental-corruption detection only. It is not authentication or cryptographic integrity authority.

---

## 4. Sequence blocks

The sequence is divided into blocks of at most:

$$
K=16
$$

items.

For a block:

$$
B=(z_1,z_2,\ldots,z_k)
$$

its canonical width is:

$$
\boxed{
w(B)=\max_i\operatorname{bitlength}(z_i)
}
$$

with:

$$
\operatorname{bitlength}(0)=0.
$$

Every sequence value MUST be a nonnegative integer.

---

## 5. Width header

### 5.1 Inline width

For:

$$
0\le w\le254
$$

encode one byte:

$$
\operatorname{WidthField}(w)=\operatorname{byte}(w).
$$

### 5.2 Extended width

For:

$$
w\ge255
$$

encode:

```text
FF || canonical-UVarInt(w)
```

or:

$$
\boxed{
\operatorname{WidthField}(w)
=
\texttt{0xFF}\Vert\operatorname{UVarInt}(w)
}
$$

The UVarInt MUST use the canonical shortest representation.

An extended width that decodes below $255$ is noncanonical and MUST be rejected.

---

## 6. Experimental implementation cap

The W2 Python implementation defines:

```text
ISX_MAX_BIT_WIDTH = 4096
```

Therefore:

$$
w>4096
$$

MUST fail closed before payload allocation.

A later implementation may declare a different capability, but must not reinterpret an existing canonical object silently.

---

## 7. Bit packing

For block width $w$ and $k$ values, values are concatenated most-significant-bit first:

$$
A
=
z_1 2^{(k-1)w}
+z_2 2^{(k-2)w}
+\cdots
+z_k.
$$

The payload is emitted as a big-endian byte sequence after appending zero padding bits at the least-significant end.

Let:

$$
p=(-kw)\bmod8.
$$

Then:

$$
0\le p\le7.
$$

All $p$ unused padding bits MUST be zero.

Host endianness MUST NOT change canonical bytes.

---

## 8. Zero block

If all values in a block are zero:

$$
B=(0,\ldots,0)
$$

then:

$$
\boxed{w(B)=0}
$$

and no block payload bytes follow the width byte.

Encoding an all-zero block at a wider width is noncanonical.

---

## 9. Minimal-width canonicality

A decoder MUST reject any block whose declared width exceeds the actual maximum decoded value width.

For decoded values $B$:

$$
\boxed{
w_{declared}
=
\max_i\operatorname{bitlength}(z_i)
}
$$

must hold.

The W2 implementation additionally re-encodes each decoded block and requires byte equality with the original block encoding.

---

## 10. Frame canonicality

After decoding a complete frame, the implementation reconstructs the `ISXSpectralFrame` and requires:

$$
\boxed{
\operatorname{Encode}(\operatorname{Decode}(b))=b
}
$$

Any mismatch fails closed.

This catches alternative encodings that may decode to the same mathematical values.

---

## 11. Random access

`ISX1` keeps block-level indexability.

The experimental index records:

- block index;
- item start;
- item count;
- encoded offset;
- encoded length;
- width-header length;
- logical bit width.

Because extended width headers are variable length, encoded block length is:

$$
L_B
=
L_{width}
+
\left\lceil\frac{kw}{8}\right\rceil.
$$

Random-access decoding therefore uses the parsed block index rather than assuming a one-byte width field.

---

## 12. Public format separation

The two families are deliberately disjoint:

```text
Public 1.0:  ISN7 ...
Experimental: ISX1 ...
```

Required behavior:

$$
\boxed{
\operatorname{Decode}_{ISN7}(ISX1)=\text{reject}
}
$$

and:

$$
\boxed{
\operatorname{Decode}_{ISX1}(ISN7)=\text{reject}.
}
$$

A coordinate whose bit length is $65$ MUST continue to be rejected by the stable `ISN7` encoder while the experimental `ISX1` encoder may represent it.

This is the central compatibility proof of W2.

---

## 13. Width boundary matrix

The W2 test surface includes:

$$
w\in
\{
0,
1,
7,
8,
9,
63,
64,
65,
127,
128,
129,
254,
255,
256,
257,
511,
512,
1024,
4096
\}.
$$

Special transition checks cover:

- $254$: one-byte inline header;
- $255$: extended marker + two-byte UVarInt;
- $256$: extended marker + two-byte UVarInt.

The test suite also includes:

- zero-block canonicality;
- mixed-width multi-block random access;
- noncanonical extended width below $255$;
- nonminimal block width;
- nonzero padding bits;
- checksum corruption;
- truncation;
- runtime-cap overflow;
- invalid random-access ranges;
- `ISN7` / `ISX1` mutual rejection.

---

## 14. Why 4096 bits

The value $4096$ is not a theoretical optimum.

It is a conservative experimental safety cap large enough to test:

- 128-bit values;
- 256-bit values;
- 512-bit values;
- 1024-bit values;
- multiword values well beyond common SIMD widths;

without allowing a malicious width field to request arbitrary-size per-block allocation.

A future capability model may expose:

$$
\mathcal C_{width}=[0,w_{max}]
$$

per implementation.

---

## 15. Why no CLI in W2

W2 intentionally exposes only a Python module/API surface.

Adding CLI commands or persistence integration would expand the responsibility boundary and make it harder to determine whether failures come from:

- width grammar;
- frame canonicality;
- CLI parsing;
- storage behavior;
- legacy dispatch.

The current goal is only to prove the isolated binary representation.

---

## 16. W3 gate

W2 is not sufficient for public promotion.

The next stage should freeze an experimental vector corpus containing positive and invalid `ISX1` cases, then implement an independent decoder without importing Python runtime behavior.

The target progression is:

$$
\boxed{
\text{W2 Reference Candidate}
\rightarrow
\text{W3 Vectors + Independent Decoder}
\rightarrow
\text{Conformance Review}
}
$$

Only after that should an Origin profile-registration PR be considered.

---

## 17. Relationship to the Meta-Core papers

This experiment is the first implementation proof of the series claim:

$$
\boxed{
\text{Machine-Native}
\neq
\text{Single-Register-Native}
}
$$

A $256$-bit or $1024$-bit canonical value can be represented and reconstructed on a $64$-bit host through multiword / arbitrary-precision execution without changing the semantic value.

`ISX1` is therefore a test of architecture, not merely a larger integer field.

---

## 18. Status statement

At W2, `ISX1` must be described only as:

> an isolated Internal / Experimental extended-width reference candidate.

It is not Public ISQL, it does not replace ISN7, and its magic/version may still change before any future protocol promotion.
