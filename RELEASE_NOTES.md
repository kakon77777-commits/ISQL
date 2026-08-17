# Release Notes — ISQL Core Runtime v0.2.0 / ISQL-MEM v0.2

## Added

- `isql.memory-record/v0.2` profile-aware schema.
- v0.1 record migration to `baseline` profile.
- `SemanticCoordinateSet`, `SemanticRelation`, `SemanticAnalysis`.
- `CallableSemanticAnalyzer` adapter for external/AI semantic analysis.
- AI-assisted `semantic` R0–R4 memory variant.
- `SemanticCoordinateDecoder`.
- coordinate fidelity metrics separated from token overlap.
- profile comparison with serialized layer size.
- CLI: `--semantic-analysis-json`, `--semantic-analysis-file`, `memory-profiles`, `memory-compare`.
- auto-selection of baseline vs semantic decoder in `memory-decode` and `recoverability`.

## Preserved

- exact-source SHA-256 address identity.
- v0.1 baseline MEM code generation.
- R4 exact recovery contract.
- standard-library-only runtime.

## Measured limitation

The first semantic JSON representation is larger than the deterministic baseline at R1/R2 in the bundled live experiment. This release therefore demonstrates semantic-coordinate structure and comparison methodology, not superior compression.
