# ISQL Core Runtime v0.9.0 — Demo Results

## Locality Index / Automatic Base Selection

| Case | Pool | Reranked | Standalone | Selected | Mode | Oracle match |
|---|---:|---:|---:|---:|---|---|
| Frozen identical neighbor | 2 | 2 | 121 B | **87 B** | delta | yes |
| Frozen near neighbor | 3 | 2 | 121 B | **97 B** | delta | yes |
| Frozen low locality | 2 | 2 | **126 B** | **126 B** | native | yes |
| Synthetic 256-base | 256 | **8** | 143 B | **92 B** | delta | yes |

The 256-base run prunes **96.875%** of actual ISD8 evaluations while selecting the same base and same 92-byte result as exhaustive actual-byte search.

## Important negative / cost result

The current locality index is JSON derived speed infrastructure, not a compression representation:

- 256 base frames: **36,595 B** total;
- locality index JSON: **220,384 B**.

This overhead is retained in the release evidence. v0.9 optimizes base-search work, not index storage.

## Decision invariant

The recall heuristic only supplies candidates. Final selection always compares real encoded bytes:

$$
oxed{	ext{heuristic recall}ightarrow	ext{actual ISD8 rerank}ightarrow\min(	ext{ISD8},	ext{ISN7})}
$$
