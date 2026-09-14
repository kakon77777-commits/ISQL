# ISQL Dual Addressing Prototype v0.1

**Status:** Internal / Experimental design candidate  
**Date:** 2026-09-14  
**Depends on:** ISQL Meta-Core Internal Research Series Papers 01–07  
**Public status:** NOT Public ISQL 1.0.

---

## 1. Purpose

This document defines the first implementation boundary for the Meta-Core dual-addressing model:

$$
\boxed{
A_S \neq A_I \neq R_P
}
$$

where:

- $A_S$ is a **semantic address / relevance plane**;
- $A_I$ is an **exact identity plane**;
- $R_P$ is a later **physical placement resolver** and is intentionally outside this first prototype.

The prototype must prove one narrow claim:

> a query can be projected into a versioned semantic address, reduced to a finite candidate set, and then return exact immutable state identities without treating semantic similarity as exact equality.

The first runtime loop is:

$$
\boxed{
Q
\rightarrow
A_S(Q)
\rightarrow
\mathcal C
\rightarrow
(E,H)
}
$$

with:

- $E$ = persistent entity identity supplied by the caller/domain;
- $H$ = SHA-256 of exact state bytes;
- $\mathcal C$ = finite read-only candidate set.

No physical storage location is encoded into either semantic address or exact identity.

---

## 2. Existing Core pieces reused

The prototype reuses existing ISQL Core responsibilities instead of inventing a parallel stack.

### Exact address / digest support

`src/isql_core/address.py` already treats 32-byte SHA-256 material as an exact address code.

### Structured semantic output

`src/isql_core/semantics.py` already defines:

- `SemanticAnalysis`;
- `SemanticCoordinateSet`;
- analyzer id / analyzer contract provenance;
- concepts, entities, relations, claims, intent, tags and language.

### Derived locality precedent

`locality.py` and `compact_locality.py` already establish an important governance rule:

$$
\boxed{
\text{Derived Index}
\neq
\text{Canonical Identity Source}
}
$$

The dual-address prototype follows the same rule.

---

## 3. Non-goals

A1/A2 do **not** attempt to provide:

- a universal ontology;
- vector embeddings;
- ANN search;
- a production search engine;
- SEDB persistence;
- physical URL / node / object-store resolution;
- canonical mutation;
- branch-head selection;
- authorization;
- public wire-format changes;
- a claim that lexical atom overlap is complete semantic similarity.

The first resolver is deliberately deterministic and inspectable.

---

## 4. Semantic profile binding

Semantic addresses are meaningful only inside a declared semantic profile.

A profile binding is:

$$
P_S
=
(
\text{analyzer id},
\text{revision},
H(\text{analyzer contract})
)
$$

Two addresses may only be directly compared by the prototype when:

$$
P_S^{(a)}=P_S^{(b)}.
$$

This prevents accidental comparison of coordinates produced under different analyzer contracts.

The profile binding is not an assertion that two AI models have identical latent spaces. It is an explicit declaration of the coordinate contract under which the address was produced.

---

## 5. Semantic address

The prototype semantic address is a normalized structured projection of `SemanticCoordinateSet`.

It contains typed atoms derived from:

- concepts;
- entities;
- relations;
- claims;
- intent;
- tags.

Language is retained as metadata but is not, by itself, sufficient relevance evidence.

The free-form summary is intentionally not indexed in A2. Text tokenization and learned embeddings belong to later replaceable retrieval implementations.

Each semantic string is normalized with a deterministic text rule:

1. Unicode NFKC;
2. whitespace collapse;
3. trim;
4. Unicode case-fold.

Typed atoms remain distinct. For example:

```text
concept:memory
entity:memory
```

are not the same posting.

A relation is preserved as a normalized triple rather than flattened into an untyped sentence.

---

## 6. Exact state identity

For exact bytes $b$:

$$
H(b)=\operatorname{SHA256}(b).
$$

The prototype exact state reference is:

$$
A_I=(E,H(b)).
$$

The stable entity id $E$ is not derived from the state digest.

Therefore:

$$
\boxed{
E \neq H(X_t)
}
$$

and the same entity may legitimately have multiple historical state identities.

The exact reference contains no semantic score and no physical locator.

---

## 7. Derived semantic index

The A2 index is rebuildable derived infrastructure.

Each entry binds:

$$
(E,H)
\leftrightarrow
A_S.
$$

The canonical state bytes remain outside the index.

An in-memory inverted search runtime may map typed semantic atoms to entry ids:

$$
\text{atom}
\rightarrow
\{i_1,i_2,\ldots\}.
$$

The stored index representation does not become a new Public canonical object merely because it is deterministic.

---

## 8. Candidate reduction

Given query address $A_S(Q)$, the resolver first collects the union of postings for matching typed atoms inside the same semantic profile.

Thus:

$$
\mathcal C
\subseteq
\mathcal I
$$

where $\mathcal I$ is the full indexed entry set.

The engineering objective is:

$$
|\mathcal C|\ll|\mathcal I|
$$

for selective queries.

If a query has no searchable semantic atoms, the resolver fails closed rather than pretending that language/profile identity is meaningful relevance.

---

## 9. Deterministic prototype scoring

A2 uses explicit typed-atom weights only as a testable baseline:

```text
relation = 9
entity   = 7
concept  = 5
intent   = 4
tag      = 3
claim    = 2
```

For candidate $x$ and query $q$:

$$
\operatorname{coverage}(q,x)
=
\frac{
\sum_{a\in A(q)\cap A(x)}w(a)
}{
\sum_{a\in A(q)}w(a)
}.
$$

This score answers only:

> how much of the declared structured query address is exactly covered by this candidate under the same semantic profile?

It does **not** claim universal semantic distance.

Future vector / graph / learned resolvers may replace this scorer while preserving the same address/identity separation.

---

## 10. Result boundary

Each candidate result must expose at least:

- entity id;
- exact state SHA-256;
- score;
- matched semantic evidence;
- profile binding.

The result must not expose a physical path as identity.

The caller may later pass $(E,H)$ to an exact state resolver or storage adapter.

That future flow is:

$$
Q
\rightarrow
A_S
\rightarrow
\mathcal C
\rightarrow
(E,H)
\rightarrow
R_P
\rightarrow
\text{Fetch}
\rightarrow
\text{Verify}.
$$

A2 stops before $R_P$.

---

## 11. Exact verification

A helper may verify fetched bytes against a candidate exact reference:

$$
\operatorname{Verify}(b,H)
=
[
\operatorname{SHA256}(b)=H
].
$$

A semantic candidate match never allows the verifier to accept different bytes.

Therefore:

$$
\boxed{
\text{Semantic Match}
\neq
\text{Exact Match}
}
$$

---

## 12. Profile isolation

A2 must include a test showing that the same lexical semantic atoms under two different analyzer contracts do not become comparable candidates.

This is required because:

$$
A_S^{(v_1)}(x)
\neq
A_S^{(v_2)}(x)
$$

may be valid even for the same source object.

Cross-profile alignment is a later explicit bridge problem.

---

## 13. Identity independence tests

A2 must prove both directions:

### Same bytes, different semantic address

$$
H(b_1)=H(b_2)
$$

may hold while semantic metadata differs.

Exact identity is not recomputed from semantic metadata.

### Similar semantics, different bytes

$$
A_S(x)\approx A_S(y)
$$

does not imply:

$$
H(x)=H(y).
$$

No semantic deduplication is permitted to impersonate exact content deduplication.

---

## 14. Read-only first

The prototype has no write path.

It may:

- build a derived index;
- project a query;
- return candidates;
- verify exact bytes.

It may not:

- update canonical state;
- change entity head;
- merge branches;
- rewrite semantic metadata in a source reservoir.

This follows the Meta-Core integration principle:

$$
\boxed{
\text{Read-Only First}
>
\text{Canonical Mutation}
}
$$

---

## 15. A1 / A2 split

### A1 — design alignment

Docs only.

- defines the profile/address/identity boundary;
- records non-goals;
- does not modify runtime behavior.

### A2 — deterministic read-only prototype

Adds a replaceable Python reference implementation and focused tests.

Proposed module:

```text
src/isql_core/semantic_addressing.py
```

Proposed API surface:

```text
semantic_address_from_analysis(...)
exact_state_ref(...)
verify_exact_state(...)
build_semantic_address_index(...)
resolve_semantic_candidates(...)
```

These function names are implementation candidates, not Public protocol.

---

## 16. Prototype invariants

### DAP-1 — Semantic / Exact Separation

$$
A_S\neq A_I.
$$

### DAP-2 — Entity / State Separation

$$
E\neq H(X_t).
$$

### DAP-3 — Profile Binding

Semantic comparison requires equal semantic profile binding.

### DAP-4 — Derived Index Non-Authority

The semantic index is rebuildable and is not a canonical state source.

### DAP-5 — No Physical Identity

Physical location is absent from semantic and exact identity objects.

### DAP-6 — Finite Candidate Set

The resolver returns a bounded finite candidate set.

### DAP-7 — Exact Verification

Candidate bytes are accepted only after SHA-256 verification against the exact state identity.

### DAP-8 — Read-Only Prototype

A2 has no canonical mutation authority.

### DAP-9 — Deterministic Baseline

The same index, query address, profile and `top_k` produce the same candidate ordering.

### DAP-10 — Replaceable Retrieval

The baseline lexical/typed-atom scorer is not Meta-Core ontology and may be replaced.

---

## 17. Promotion boundary

A2 success would prove only that dual addressing is implementable as a read-only deterministic prototype over the current Core semantic-analysis structures.

It would not promote semantic addressing to Public ISQL.

A future promotion sequence remains:

$$
\boxed{
\text{Prototype}
\rightarrow
\text{Benchmark / adversarial evaluation}
\rightarrow
\text{independent implementation}
\rightarrow
\text{experimental specification}
\rightarrow
\text{public-candidate review}
}
$$

---

## 18. Next step after A2

If A2 is validated, the next useful step is not write authority.

It is a read-only SEDB adapter:

$$
\boxed{
\text{Semantic Address}
\rightarrow
\text{Candidate }(E,H)
\rightarrow
\text{SEDB Exact Read}
}
$$

That will be the first end-to-end proof of:

$$
\boxed{
\text{ISQL navigates}
,\qquad
\text{SEDB stores}
}
$$
