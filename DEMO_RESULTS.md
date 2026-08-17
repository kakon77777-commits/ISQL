# ISQL-MEM v0.7 Live Results

v0.7 removes decimal text from the canonical memory path.

| Memory | v0.4 ASCII numeric | v0.6 D40 | v0.7 ISN7 native | Native / D40 | Coordinate fidelity |
|---|---:|---:|---:|---:|---:|
| 1 | 262 B | 122 B | **121 B** | 99.18% | 1.0 |
| 2 | 262 B | 122 B | **121 B** | 99.18% | 1.0 |
| 3 | 278 B | 128 B | **126 B** | 98.44% | 1.0 |

The important result is not primarily the small size reduction over D40. The `ISN7` frame is now the direct machine representation:

```text
raw address digest + registry binding + bit-packed spectral integers
```

There is no decimal numeric-wire encode/decode stage in this path.
