# ISQL-MEM v0.6 Live Results — Physical Digit Carrier Packing

The v0.6 experiment reuses canonical numeric wires produced by the unchanged v0.4/v0.5 encoders. No semantic coordinates, memory codes, spectral packets, or hierarchical registry IDs were regenerated under a new meaning.

## Memory numeric R2 carriers

| Memory | Canonical ASCII wire | BCD4 carrier | D40 carrier | D40 / ASCII |
|---|---:|---:|---:|---:|
| 1 | 262 B | 143 B | **122 B** | **46.56%** |
| 2 | 262 B | 143 B | **122 B** | **46.56%** |
| 3 | 278 B | 151 B | **128 B** | **46.04%** |

All unpack exactly to the original digits-only wire.

## Hierarchical registry delta carriers

| Registry update | ASCII numeric wire | Direct structural binary | BCD4 carrier | D40 carrier | D40 vs structural |
|---|---:|---:|---:|---:|---:|
| Cold bootstrap | 3515 B | 1452 B | 1770 B | **1477 B** | **+25 B / 1.0172×** |
| Partial growth | 902 B | 368 B | 463 B | **388 B** | **+20 B / 1.0543×** |

The warm identical-vocabulary case requires no registry update, so the transport cost remains 0 B by policy rather than transmitting a packed no-op delta.

## Interpretation

v0.5 demonstrated that the registry's hierarchical structural representation was compact but the ASCII decimal wire was physically expensive. v0.6 keeps the decimal sequence as the canonical form while storing/transmitting it with bounded decimal packing.

For the cold registry fixture:

$$
3515\ \text{ASCII bytes}
\rightarrow
1477\ \text{D40 carrier bytes}
$$

while the direct structural binary is 1452 B. The price of preserving the canonical numeric-sequence layer is therefore only 25 B in this fixture.

D40 does not claim universal optimality. Its full-block density is fixed at:

$$
12\ \text{digits}/5\ \text{bytes}.
$$

This controlled result shows that a canonical numeric ISQL wire does not require paying one physical byte per decimal digit.
