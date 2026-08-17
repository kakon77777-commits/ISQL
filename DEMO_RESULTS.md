# ISQL Core Runtime v0.1 — Live Memory Demo

**Stable address:** `ISQL1:ADDR:R0:H43127207063024224783191743044983672590754433598968256686708319828084954117824`

| Resolution | Exact | Semantic token-Jaccard | Recovered chars |
|---|---:|---:|---:|
| R0 | false | 0.0000 | 0 |
| R1 | false | 0.2619 | 160 |
| R2 | false | 1.0000 | 786 |
| R3 | false | 1.0000 | 786 |
| R4 | true | 1.0000 | 786 |

## Interpretation

- R0 only locates the object and intentionally reconstructs no text.
- R1 is a compact preview/keyword skeleton.
- R2 retains structured sentence heads.
- R3 carries a rich normalized reconstruction but is not certified as byte-exact.
- R4 is the only layer allowed to certify exact recovery when the exact source is present.

This is a deterministic baseline. AI-assisted reconstruction is intentionally not used in this demo.
