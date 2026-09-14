# ISQL Meta-Core Internal Architecture v0.1

**Status:** Internal / Experimental architecture alignment  
**Date:** 2026-09-14  
**Scope:** conceptual and governance alignment only; no Public 1.0 canonical bytes are changed by this document.

---

## 1. Purpose

ISQL has evolved beyond the narrow description of an AI-memory format. The current family already separates stable identity, registry binding, machine-native memory, locality, dynamic semantic state, events, branches, native programs, and canonical wrappers.

The internal Meta-Core view therefore treats ISQL as a coordinated family of semantic-state representation, addressing, and runtime architectures rather than one monolithic format.

$$
\boxed{
\text{ISQL Meta-Core}
=
\text{Identity}
+
\text{Semantic State}
+
\text{Addressing}
+
\text{Topology}
+
\text{Transition}
+
\text{Projection}
+
\text{Recoverability}
}
$$

This is an internal research framing. It does not replace the normative Public 1.0 boundary.

---

## 2. Core separation rules

### MC-1 — Semantic object, logical representation, and physical carrier are different layers

$$
\boxed{
\text{Semantic Object}
\neq
\text{Logical Representation}
\neq
\text{Physical Carrier}
}
$$

A host CPU word size is an execution property, not an ontology boundary for ISQL values.

### MC-2 — Meaning, exact identity, and placement are separate

$$
\boxed{
\text{Semantic Address}
\neq
\text{Exact Identity}
\neq
\text{Physical Placement}
}
$$

Semantic addressing reduces a large state space to a relevant candidate domain. Exact identity disambiguates the precise canonical object or state. Physical placement is resolved dynamically and may change without changing identity.

### MC-3 — Mutable entity identity and immutable state identity are separate

For an entity $e$ with state $X_t$:

$$
\boxed{
E(e)
\neq
H(X_t)
}
$$

The same entity may have many exact state identities over time.

### MC-4 — Exact and semantic recovery remain distinct

$$
\boxed{
R_{\mathrm{exact}}
\neq
R_{\mathrm{semantic}}
}
$$

Semantic reconstruction must never be presented as byte-exact recovery.

### MC-5 — A large logical universe only requires a finite active domain per runtime step

$$
\boxed{
D_t
\subset
\mathcal U_t,
\qquad
|D_t|<\infty
}
$$

The engineering objective is to make lookup, materialization, and transition cost depend primarily on the active domain and its dependency closure rather than the total logical universe size.

---

## 3. Width-independent representation

The current Python reference implementation uses:

```text
NATIVE_BLOCK_SIZE = 16
NATIVE_MAX_BIT_WIDTH = 64
```

The current ISN7 block grammar also stores each block width in one byte. These are real and intentional v1.0 implementation / wire constraints. They are not interpreted by the Meta-Core as a universal semantic ceiling.

The internal width model separates:

$$
\boxed{
w_s,
\quad
w_l,
\quad
w_c,
\quad
w_m
}
$$

where:

- $w_s$ — semantic width;
- $w_l$ — logical representation width;
- $w_c$ — carrier width;
- $w_m$ — machine word / execution width.

The conceptual rule is:

$$
\boxed{
w_s
\neq
w_l
\neq
w_c
\neq
w_m
}
$$

This notation means these layers must not be defined as the same thing. They may coincide in a particular implementation.

The current $64$-bit ceiling remains normative for existing Public 1.0 ISN7 bytes until an explicitly versioned successor format is specified and validated.

No existing ISN7 byte grammar may be silently reinterpreted.

---

## 4. Candidate extended-width direction

A future experimental successor may preserve compact inline widths and introduce an explicit extended-width form. One candidate is:

- inline width for $0\le w\le254$;
- `0xFF` as an extension marker;
- canonical shortest-form UVarInt carrying the actual width for $w\ge255$.

Conceptually:

$$
\operatorname{WidthField}(w)
=
\begin{cases}
\operatorname{byte}(w), & 0\le w\le254,\\
\texttt{0xFF}\Vert\operatorname{UVarInt}(w), & w\ge255.
\end{cases}
$$

This is **not** a Public 1.0 amendment and is not yet a frozen wire specification. It is an Internal candidate to be validated in a new, explicit format/profile boundary.

Any such format must preserve:

- minimal-width canonicality;
- canonical zero-block encoding;
- zero padding in unused bits;
- host-endianness independence;
- bounded allocation before payload allocation;
- fail-closed unsupported-width behavior;
- legacy Public 1.0 decoding without byte reinterpretation.

---

## 5. Dual addressing

The internal addressing model uses two address planes plus a placement resolver.

### Semantic address plane

$$
A_S(x)
$$

answers:

> Which state or domain is relevant to the current intent, context, relation, task, or causal neighborhood?

It need not be globally unique.

### Exact identity plane

$$
A_I(x)
$$

answers:

> Which precise canonical object or state is this?

Cryptographic digest profiles are practical identity/binding primitives, but Meta-Core does not define one digest algorithm as eternal ontology.

### Physical resolution plane

$$
R_P(A_I(x),C_t)
\rightarrow
\mathcal L_t(x)
$$

returns current usable storage / transport locations under context $C_t$.

Therefore a typical retrieval path is:

$$
\boxed{
Q_t
\rightarrow
A_S
\rightarrow
\mathcal C_t
\rightarrow
A_I
\rightarrow
R_P
\rightarrow
\text{Fetch}
\rightarrow
\text{Verify}
}
$$

---

## 6. State-space runtime boundary

A dynamic state system requires explicit transition semantics:

$$
\boxed{
W_t
\xrightarrow{e_t}
\Delta_t
\xrightarrow{\operatorname{Validate}}
\Delta_t^{valid}
\xrightarrow{\operatorname{Commit}}
W_{t+1}
}
$$

The Meta-Core distinguishes:

- event from state delta;
- candidate transition from committed transition;
- persistent entity identity from exact state identity;
- simulation / planning branches from published branches;
- exact replay from semantic replay.

Version conflict is a semantic precondition failure. It must not be silently repaired unless the relevant runtime explicitly defines merge semantics.

The detailed execution owner for state/event/branch/program semantics is the DSR line, not the Core memory format.

---

## 7. Repository responsibilities

The current internal responsibility split is:

### Origin

$$
\boxed{
\text{Canonical Envelope}
+
\text{Profile Binding}
+
\text{Byte Preservation}
}
$$

Origin should wrap/profile native artifacts without assimilating their semantics.

### Core

$$
\boxed{
\text{Identity}
+
\text{Memory}
+
\text{Registry Binding}
+
\text{Locality}
+
\text{Retrieval}
}
$$

Core is the first implementation owner for experimental width-independent memory representation and semantic/locality retrieval work.

### DSR

$$
\boxed{
\text{State}
+
\text{Event}
+
\text{Branch}
+
\text{Program}
+
\text{Transition}
+
\text{Execution}
}
$$

### SEDB interface

$$
\boxed{
\text{Semantic Navigation}
\leftrightarrow
\text{Persistent Evolving State Reservoir}
}
$$

The integration contract should remain adapter-based rather than merging SEDB into the ISQL Core protocol.

---

## 8. Data-ocean and universe interpretation

The internal integration model is:

$$
\boxed{
\text{ISQL navigates}
,
\qquad
\text{SEDB stores and evolves}
}
$$

For a very large persistent state reservoir $\mathcal D_t$, a task $Q$ should activate only a finite relevant field/state domain:

$$
F_Q\subseteq F_t,
\qquad
D_Q\subseteq\mathcal D_t.
$$

For distributed worlds, the general model is:

$$
\boxed{
\text{One Logical Universe}
+
\text{Many Finite Materialized Domains}
}
$$

A logical universe may be distributed across many physical nodes and storage tiers. Local clients fetch, verify, reconstruct, cache, and simulate only the active domain required by their current context.

This architecture is application/system-level research. It is not a claim that ISQL Core itself is a cloud SDK, database, or world engine.

---

## 9. Public / Internal governance

Public ISQL remains the stable external contract. Internal / Experimental ISQL is the high-velocity research surface.

The promotion path is:

$$
\boxed{
\text{Idea}
\rightarrow
\text{Internal Paper}
\rightarrow
\text{Prototype}
\rightarrow
\text{Validation}
\rightarrow
\text{Experimental Spec}
\rightarrow
\text{Independent Implementation}
\rightarrow
\text{Conformance}
\rightarrow
\text{Public Candidate}
\rightarrow
\text{Public Release}
}
$$

A successful reference implementation is not, by itself, a public protocol.

Any future Public promotion requires an explicit version boundary, golden and invalid vectors, failure semantics, compatibility analysis, and independent implementation evidence.

---

## 10. First engineering proof after this alignment

The recommended first engineering proof is width independence because the current limitation is explicit, local, and testable.

The intended PR sequence is:

1. **W1 — documentation / Meta-Core alignment**: document width independence and the fact that 64-bit is the current reference-format ceiling, with no byte changes;
2. **W2 — Core experimental extended-width candidate**: introduce a new internal format/profile rather than mutating Public ISN7;
3. **W3 — independent decoder and conformance vectors**;
4. **W4 — Origin profile registration** after the Core candidate stabilizes;
5. **W5 — DSR wide-value adoption** only if DSR needs it.

The governing rule is:

$$
\boxed{
\text{Global Architecture}
\rightarrow
\text{Local Surgical Change}
}
$$

---

## 11. Non-goals of this document

This document does not:

- change Public 1.0 ISN7 / ISD8 / ILI1 bytes;
- change the current Python decoder behavior;
- claim an extended-width format is frozen;
- make SEDB part of Public ISQL;
- define a cloud provider;
- claim PB-scale production readiness;
- make world-model output canonical authority;
- merge Origin, Core, DSR, and SEDB into one runtime.

It only establishes the Internal architectural interpretation and the responsibility boundaries for subsequent experimental PRs.
