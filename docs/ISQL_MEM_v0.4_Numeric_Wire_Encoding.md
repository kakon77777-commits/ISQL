# ISQL-MEM v0.4 — Numeric Wire Encoding

## 1. Goal

v0.3 established that verbose semantic coordinates could be compiled into shared-registry-backed integer sequences while preserving typed semantic coordinates exactly. v0.4 removes another representation layer: the sparse integer packet is serialized into a canonical carrier containing ASCII digits only.

The transformation is:

$$
\boxed{
\text{Semantic Coordinates}
\rightarrow
\text{Spectral Registry IDs}
\rightarrow
\text{Sparse Integer Sequence}
\rightarrow
\text{Digits-Only Wire}
}
$$

The objective is not to claim a final universal numeric language. The objective is to establish that a deterministic, self-delimiting, fail-closed numeric runtime carrier can preserve the v0.3 semantic packet exactly.

## 2. Layer separation

The system retains four layers:

$$
\text{Authoring Semantic JSON}
\neq
\text{Spectral Packet}
\neq
\text{Numeric Wire}
\neq
\text{Exact Source}.
$$

The authoring form remains readable and auditable. The spectral packet remains typed and registry-bound. The numeric wire is the compact runtime/transport representation. R4 exact source remains separately governed.

## 3. Wire alphabet

The v0.4 alphabet is:

$$
\Sigma_{wire}=\{0,1,2,3,4,5,6,7,8,9\}.
$$

No punctuation or non-ASCII digit is canonical.

## 4. Self-delimiting unsigned integers

For an unsigned integer $n$, let $d(n)$ be its canonical decimal representation without leading zeroes, except that zero is represented by `0`.

If:

$$
1\le |d(n)|\le9,
$$

the token is:

$$
|d(n)|\Vert d(n).
$$

For longer decimal values, the token begins with `0`, followed by one digit specifying the decimal length of the length field, then the length, then the value.

This gives a deterministic prefix parse without separators.

## 5. Wire structure

Conceptually:

```text
MAGIC
VERSION
REGISTRY_REVISION
REGISTRY_HASH_AS_DECIMAL_INTEGER
SEQUENCE_COUNT
SEQUENCE_ITEM_1
...
SEQUENCE_ITEM_N
CRC32
```

Every variable-width integer is self-delimiting.

The full 256-bit spectral registry hash is preserved. It is converted from hex text into one nonnegative integer for the wire, then reconstructed as exactly 64 lowercase hexadecimal digits during decoding.

## 6. Registry binding

The wire does not reproduce the textual shared dictionary. It binds to:

$$
(\text{registry id},\text{revision},\text{SHA-256 hash}).
$$

The default v0.4 wire profile supports the default ISQL spectral registry ID. A decoder recreates the spectral packet and then the existing v0.3 expansion layer validates the exact revision and hash before resolving integer IDs.

## 7. Relation structural representation

Relations are not serialized as JSON objects. v0.3 already converts them to a counted triple block:

$$
N_{rel},
(s_1,p_1,o_1),
\dots,
(s_k,p_k,o_k).
$$

Subjects and objects reuse the shared atom namespace. v0.4 preserves this compact structural form and serializes the integers directly.

## 8. Integrity

The registry SHA-256 hash protects semantic registry binding. A CRC32 value is appended to detect accidental wire corruption.

CRC32 is explicitly **not** treated as cryptographic authentication or content identity.

## 9. Memory profile

A new profile is additive:

```text
numeric
```

R1/R2 data is exactly:

```json
{"wire":"<ASCII digits only>"}
```

R3 keeps a readable/auditable reconstruction layer plus the wire. R4 preserves the exact-source contract.

## 10. Recovery

For R1/R2:

$$
W
\rightarrow
P
\rightarrow
\mathcal R_v
\rightarrow
C
\rightarrow
\hat x,
$$

where:

- $W$ is numeric wire;
- $P$ is the spectral packet;
- $\mathcal R_v$ is the exact registry revision;
- $C$ is the typed semantic coordinate set;
- $\hat x$ is the realized semantic reconstruction.

Numeric R1/R2 never declares exact recovery.

## 11. Live result

Using the same three fixture family as v0.3:

| Case | Coordinates | Spectral JSON | Numeric wire | Registry delta | Numeric total | Fidelity |
|---|---:|---:|---:|---:|---:|---:|
| cold | 2131 B | 321 B | 262 B | 1607 B | 1869 B | 1.0 |
| warm | 2131 B | 318 B | 262 B | 0 B | 262 B | 1.0 |
| partial growth | 2162 B | 332 B | 278 B | 310 B | 588 B | 1.0 |

The warm case becomes:

$$
\frac{262}{2131}\approx0.1229.
$$

The cold case, including the full first registry growth, becomes:

$$
\frac{1869}{2131}\approx0.8771.
$$

The partial-growth case becomes:

$$
\frac{588}{2162}\approx0.2720.
$$

No typed-coordinate loss was observed in these fixtures.

## 12. Interpretation

v0.4 demonstrates a limited but concrete statement:

$$
\boxed{
\text{A registry-backed semantic coordinate packet can be carried as a deterministic pure-digit sequence.}
}
$$

It does **not** demonstrate that the entire registry is numeric, that natural-language semantics have been completely quantified, or that these ratios generalize to arbitrary corpora.

## 13. Next frontier

The remaining large nonnumeric object is the registry itself. A natural v0.5 direction is therefore:

$$
\boxed{
\text{Registry Compaction / Hierarchical Spectral Dictionary}
}
$$

with possible subproblems:

- hierarchical atom namespaces;
- shared relation templates;
- local dictionary windows;
- delta-coded registry revisions;
- corpus-scale amortization curves;
- cross-model semantic coordinate stability.
