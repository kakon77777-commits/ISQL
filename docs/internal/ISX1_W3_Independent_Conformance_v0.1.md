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

Both implementations are expected to accept the same positive bytes and reject the same invalid bytes.

---

## 2. Frozen vector corpus

Canonical experimental vector file:

```text
conformance/isx1/experimental_vectors_v0.1.json
```

The corpus contains:

- **8 positive frames**;
- **10 invalid frames**.

Positive coverage includes:

- zero block;
- 64-bit coordinate;
- 65-bit coordinate;
- 254-bit inline-width boundary;
- 255-bit first extended-width boundary;
- 256-bit extended width;
- mixed multi-block random-access-shaped payload;
- 4096-bit experimental-cap boundary.

Invalid coverage includes:

- checksum mismatch;
- wrong magic with recomputed checksum;
- unsupported version with recomputed checksum;
- extended encoding for a width below 255;
- overlong width UVarInt;
- nonminimal declared block width;
- nonzero padding bits;
- width 4097 above the reference capability cap;
- truncated extended-width header;
- trailing bytes with recomputed checksum.

The vectors are fixed bytes. Implementations do not generate expected bytes during the test.

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
- generate expected vectors from the reference implementation;
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

## 4. Independent execution evidence

The independent module was formatted and tested in an isolated local environment using:

```text
go version go1.23.2 linux/amd64
```

Commands:

```text
gofmt -w isx1/decoder.go isx1/decoder_test.go
go test ./...
```

Observed result:

```text
ok   isql-isx1-independent/isx1   0.002s
```

The command was rerun after the registry-revision type correction and remained passing.

This is an observed local validation result, not a universal performance claim.

---

## 5. Cross-language issue discovered during W3

The first Go draft represented `registry_revision` using `uint64`.

The Python reference grammar, however, uses a canonical UVarInt with a ten-byte parser limit and does not define the semantic revision value itself as a 64-bit integer.

Therefore a Go `uint64` representation would have silently narrowed the accepted logical revision domain.

W3 corrected this by using:

```text
*big.Int
```

for registry revision and canonical UVarInt processing.

This is exactly the kind of issue the independent-implementation gate is intended to reveal:

$$
\boxed{
\text{Host Language Integer Type}
\neq
\text{Protocol Integer Domain}
}
$$

The sequence-item count remains intentionally bounded by the protocol/runtime limit of 1,000,000 and is converted to a native integer only after that bound is verified.

---

## 6. Python reference binding

W3 adds:

```text
tests/test_isx_conformance_vectors.py
```

This test requires the Python `ISX1` reference decoder to:

- decode every positive fixed frame to the declared address, registry binding, resolution, and sequence;
- re-encode to byte-identical output;
- reject every invalid fixed frame.

The repository currently has no GitHub Actions workflow. This connector session did not execute the complete Python repository test suite, so W3 does not claim a fresh full-suite Python PASS result here.

The independent Go vector suite **was** executed successfully as recorded above.

---

## 7. What W3 proves

W3 provides evidence that:

1. the declared `ISX1` byte grammar is implementable outside Python;
2. 65/255/256/4096-bit boundaries do not require a 64-bit host-language scalar representation;
3. positive frames have a deterministic independent decode/re-encode path;
4. the selected invalid encodings can be rejected independently;
5. independent implementation can expose hidden host-language assumptions.

---

## 8. What W3 does not prove

W3 does not yet prove:

- Public ISQL interoperability;
- completeness of all possible invalid cases;
- security of the format against every parser attack;
- production performance;
- compatibility with Origin;
- DSR wide-value execution semantics;
- a frozen future public successor to ISN7.

`ISX1` remains experimental.

---

## 9. Promotion status

The internal evidence progression is now:

$$
\boxed{
\text{W1 Architecture Alignment}
\rightarrow
\text{W2 Reference Candidate}
\rightarrow
\text{W3 Frozen Vectors + Independent Decoder}
}
$$

The next repository step may register `ISX1` as an **experimental native profile** in Origin, but Origin must continue to treat the payload as opaque canonical bytes and must not assimilate `ISX1` semantics.

Any future Public promotion remains a separate decision and requires a dedicated normative protocol review.
