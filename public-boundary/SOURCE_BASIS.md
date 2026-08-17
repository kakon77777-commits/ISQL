# Source Basis

The Public 1.0 boundary was derived from the current ISQL Core Runtime v1.0.0 release and its documented lineage.

Primary basis:

- `README.md` from ISQL Core Runtime v1.0.0
- `docs/ISQL_Core_v1.0_Compact_Machine_Native_Locality_Index.md`
- `docs/ISQL_MEM_v0.7_Machine_Native_Canonical_Representation.md`
- `docs/ISQL_MEM_v0.8_Locality_Delta_and_Random_Access.md`
- `docs/ISQL_MEM_v0.5_Hierarchical_Spectral_Registry_Compaction.md`
- current v1.0 tests and validation evidence

This boundary document intentionally separates:
- protocol-level invariants already supported by the v1.0 runtime;
- current reference-implementation choices;
- historical compatibility transports;
- research/internal candidates.

It does not claim that a second independent implementation has already proven interoperability.
