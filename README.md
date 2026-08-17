# ISQL Core Runtime v0.1

First executable implementation of the `ISQL Core Code Base Space v0.2` architecture.

## Implemented domains

- `ISQL-ADDR`: deterministic model-independent content address.
- `ISQL-MEM`: multi-resolution `R0`–`R4` text memory representation.
- `SEM`, `STATE`, `EXEC`: registered namespaces for later profiles.
- `RESERVED`: parseable but deliberately non-executable.

## Canonical wire object

```text
ISQL1:MEM:R2:XRQ123456789
```

A code is structurally:

$$
(protocol, version, domain, resolution, control, payload).
$$

Arbitrary-length payload digits remain UTF-8 digit strings and are never coerced to floating point.

## Address versus memory

$$
\boxed{\text{Address identity} \neq \text{Memory representation}}
$$

`ISQL-ADDR` is SHA-256 based and deterministic. `ISQL-MEM` can change representation metadata/resolution without changing the source address.

## Memory resolution

- `R0`: locator only.
- `R1`: semantic skeleton / preview / keywords.
- `R2`: structured sentence heads + keywords.
- `R3`: rich normalized reconstruction + metadata.
- `R4`: exact-source recovery layer / source reference.

## Decoder contract

The deterministic decoder is built in. `CallableAIDecoder` is an adapter for later AI reconstruction; it records `decoder_id` and `decoder_contract` and is never allowed to change canonical address identity or claim exact recovery.

## CLI

```bash
isql-core registry-info
isql-core parse ISQL1:MEM:R2:X123
isql-core address --text "hello"
isql-core memory-encode --store ./memory --text "Alpha beta. Alpha gamma."
isql-core memory-decode --store ./memory --code ISQL1:MEM:R4:M...
isql-core recoverability --store ./memory --code ISQL1:MEM:R1:M... --source-text "..."
```

## Status

This is a kernel/prototype implementation. It does not claim a complete semantic ontology, globally optimal compression, or lossless AI reconstruction.
