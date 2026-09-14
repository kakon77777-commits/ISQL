# ISX1 W3 Independent Conformance Candidate v0.1

**Status:** Internal / Experimental validation evidence  
**Date:** 2026-09-14  
**Depends on:** W2 `ISX1` experimental frame candidate  
**Public status:** NOT Public ISQL conformance.

---

## 1. Purpose

W3 tests whether the `ISX1` experimental byte grammar can be implemented from its declared format rather than by importing the Python reference runtime.

The validation shape is:

$$
\boxed{
\text{Frozen Byte Corpus}
\rightarrow
\begin{cases}
\text{Python reference binding test}\\
\text{Independent Go implementation}
\end{cases}
}
$$

Both implementations must accept the same positive bytes and reject the same invalid bytes.

---

## 2. Frozen vector corpus

Current canonical experimental vector file:

```text
conformance/isx1/experimental_vectors_v0.2.json
```

The compact W3 cross-language corpus contains:

- **6 positive frames**;
- **6 invalid frames**.

Positive coverage includes:

- zero block;
- 65-bit coordinate;
- 254-bit inline-width boundary;
- 255-bit first extended-width boundary;
- 256-bit extended width;
- mixed multi-block payload containing 256-bit and 65-bit blocks.

Invalid coverage includes:

- checksum mismatch;
- wrong magic with recomputed checksum;
- extended encoding for a width below 255;
- nonminimal declared block width;
- nonzero padding bits;
- width 4097 above the experimental runtime cap.

The 4096-bit positive reference-cap boundary remains covered by the W2 Python unit suite. It is deliberately not duplicated as a very large frozen hex fixture in the compact cross-language corpus.

### v0.1 corpus correction

The initial `experimental_vectors_v0.1.json` draft included a manually transferred 4096-bit hex fixture whose checksum did not match the copied bytes. GitHub Actions correctly rejected that single vector in both Python and Go while the direct W2 4096-bit encode/decode test passed.

Rather than silently rewriting that draft, W3 introduced the corrected, compact **v0.2** corpus and moved both conformance bindings to it.

This distinction is intentional:

$$
\boxed{
\text{Reference boundary test}
\neq
\text{Frozen cross-language fixture requirement}
}
$$

---

## 3. Independent Go implementation

Location:

```text
independent/isx1-go/
```

The implementation uses only the Go standard library.

It does **not**:

- import Python;
- execute `native_ext.py`;
- shell out to the Python reference runtime;
- generate expected vectors from the reference implementation during tests;
- import existing ISQL source packages.

The Go implementation independently implements:

- frame header parsing;
- CRC32 verification;
- canonical UVarInt parsing;
- inline and extended width parsing;
- 0..4096-bit block decoding using `math/big`;
- zero-padding checks;
- minimal-width checks;
- canonical block re-encoding;
- canonical full-frame re-encoding;
- positive and invalid vector validation.

---

## 4. Cross-language issue discovered during W3

The first Go draft represented `registry_revision` using `uint64`.

The Python reference grammar uses a canonical UVarInt with its own bounded parser contract and does not define the semantic revision domain as a host-language `uint64` merely because Go provides that type.

W3 therefore changed the independent implementation to use:

```text
*big.Int
```

for registry revision and canonical UVarInt handling.

The governing rule is:

$$
\boxed{
\text{Host Language Integer Type}
\neq
\text{Protocol Integer Domain}
}
$$

Sequence-item count remains intentionally bounded by the runtime limit of 1,000,000 and is converted to a native integer only after that bound is verified.

---

## 5. Python reference binding

W3 adds:

```text
tests/test_isx_conformance_vectors.py
```

This test requires the Python `ISX1` reference decoder to:

- decode every positive v0.2 fixed frame to the declared address, registry binding, resolution, and sequence;
- re-encode to byte-identical output;
- reject every invalid v0.2 fixed frame.

The W3 GitHub Actions workflow additionally runs `tests.test_isx_frame` and the stable `tests.test_native_frame` separation/regression suite.

---

## 6. GitHub Actions validation

Workflow:

```text
.github/workflows/w3-isx1-conformance.yml
```

Jobs:

1. Python 3.11 reference / legacy-separation tests;
2. independent Go 1.23.2 vector tests.

The first workflow run exposed the bad manually transferred v0.1 `width4096` fixture: both jobs failed only on that same checksum mismatch, while all direct W2 4096-bit logic and the remaining Python boundary tests passed.

The v0.2 corpus exists specifically to convert that failure into a versioned conformance-data correction rather than hiding or mutating the original evidence.

---

## 7. What W3 proves

W3 is intended to provide evidence that:

1. the declared `ISX1` byte grammar is implementable outside Python;
2. 65/255/256-bit canonical boundaries do not require a 64-bit host-language scalar representation;
3. the Python reference separately exercises the 4096-bit capability boundary;
4. positive frozen frames have deterministic independent decode/re-encode paths;
5. selected invalid encodings are rejected independently;
6. independent implementation exposes hidden host-language assumptions;
7. conformance-data failures can be distinguished from encoder/decoder algorithm failures.

---

## 8. What W3 does not prove

W3 does not yet prove:

- Public ISQL interoperability;
- completeness of all possible invalid cases;
- security against every parser attack;
- production performance;
- DSR wide-value execution semantics;
- a frozen future Public successor to ISN7.

`ISX1` remains experimental.

---

## 9. Promotion status

The internal evidence progression is:

$$
\boxed{
\text{W1 Architecture Alignment}
\rightarrow
\text{W2 Reference Candidate}
\rightarrow
\text{W3 Frozen Vectors + Independent Decoder}
}
$$

W4 may register `ISX1` as an **experimental native profile** in Origin only as opaque canonical bytes; Origin must not assimilate `ISX1` semantics.

Any future Public promotion remains a separate decision requiring dedicated normative review, compatibility analysis, frozen vectors, and independent implementation evidence.
