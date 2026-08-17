# ISQL-MEM v0.8 Live Results

## Case 1 — identical semantic neighbor

Frozen memory #1 and #2 have different stable source addresses but the same R2 typed spectral coordinate sequence.

- standalone target ISN7: **121 B**
- ISD8 delta: **87 B**
- selected ratio: **71.90%**
- modes: **5 COPY / 0 DELTA / 0 REPLACE**
- registry binding inherited from base
- random-access block 2 exactly matches the corresponding full target slice

## Case 2 — same-registry near neighbor

A new target reorders a small number of already-registered semantic coordinates without adding vocabulary.

- standalone target ISN7: **121 B**
- ISD8 delta: **97 B**
- selected ratio: **80.17%**
- modes: **3 COPY / 2 DELTA / 0 REPLACE**
- registry revision/hash remains identical to the base
- random-access block 1 exactly matches the corresponding full target slice

## Case 3 — registry growth / low locality

Frozen memory #3 changes coordinate structure and advances the registry.

- standalone target ISN7: **126 B**
- candidate ISD8: **168 B**
- locality compiler selection: **native**
- selected bytes: **126 B**

The compiler therefore does not force delta encoding when locality is harmful.

## Partial-decode proof

The test suite includes a frame whose later delta payload is deliberately corrupted while the outer CRC is recomputed. `decode_delta_block(..., block=0)` still succeeds, while full-frame decode fails. This proves the block API does not unpack unrelated target payload blocks.
