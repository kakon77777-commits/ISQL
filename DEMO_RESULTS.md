# ISQL Core Runtime v1.0.0 — Live Results

## 256-base exhaustive-oracle fixture

- standalone target: **143 B**;
- v0.9-style JSON locality index: **219,185 B**;
- v1.0 `ILI1`: **37,421 B**;
- compact index / JSON ratio: **17.07%**;
- metadata probe set: **64/256 = 25%**;
- actual ISD8 reranks: **8**;
- selected base: `base-good.isql7`;
- selected frame: **92 B**;
- exhaustive 256-base oracle: same base, same **92 B** result.

## 4096-base structural scale fixture

- entries: **4096**;
- compact `ILI1`: **598,061 B**;
- mean: **146.01 B/indexed base**;
- metadata probe set: **64/4096 = 1.5625%**;
- actual ISD8 reranks: **8**;
- selected base: `base-good.isql7`;
- selected frame: **92 B** from 143 B standalone.

No wall-clock claim is made. The benchmark records structural index size and candidate/rerank counts only.

Full machine-readable evidence: `validation/v10/v10_live_summary.json`.
