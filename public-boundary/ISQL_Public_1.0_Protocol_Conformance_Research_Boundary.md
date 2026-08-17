# ISQL Public 1.0
## Protocol / Conformance / Research Boundary

**Canonical Public Title:** ISQL Public 1.0 — Protocol / Conformance / Research Boundary  
**中文標題：** ISQL 公開版 1.0：協議、相容性測試與研究邊界  
**Status:** Public Core Specification Boundary  
**Date:** 2026-08-17  
**Basis:** ISQL Core Runtime v1.0.0  
**Primary Audience:** third-party implementers, AI/agent runtime developers, auditors, researchers  
**Canonical Source:** UTF-8 Markdown  
**Normative Core:** Identity / Registry Binding / ISN7 / ISD8 / ILI1 / Recovery Boundary / Fail-Closed Conformance  
**Reference Runtime:** Python `isql-core` v1.0.0

---

# 0. 文件定位

本文件不是新的 ISQL 演算法版本，也不是 v1.1。

它的目的，是將目前已完成的 ISQL Core Runtime v1.0.0 從「研究開發成果」整理成一個可以被第三方理解、獨立實作、驗證與批判的**公開穩定邊界**。

本文件回答四個問題：

1. **什麼是 Public ISQL 1.0 的穩定核心？**
2. **一個第三方 implementation 必須做到什麼，才能宣稱 conformance？**
3. **目前 Python Reference Runtime 的哪些行為只是實作選擇，而不是 protocol law？**
4. **哪些區域仍屬研究候選、可替換結構或 Internal / Experimental ISQL 的範圍？**

核心原則：

$$
\boxed{
\text{Specification}
>
\text{Conformance Vectors}
>
\text{Reference Implementation}.
}
$$

Python Reference Runtime 是一個實作。

它不是 ISQL 本身。

---

# 1. Public 與 Experimental 的正式分離

ISQL 從 v1.0 起正式分為兩條治理線：

$$
\boxed{
\begin{array}{ccc}
&&\text{ISQL Meta-Core}\\
&\swarrow&&\searrow\\
\text{Public ISQL}
&&&
\text{Experimental / Internal ISQL}
\end{array}
}
$$

## 1.1 Public ISQL

Public ISQL 追求：

- stable identity；
- canonical encodings；
- deterministic decode；
- independent implementations；
- backward compatibility；
- reproducible test vectors；
- fail-closed behavior；
- explicit versioning；
- externally auditable claims。

Public ISQL 的優先級是：

$$
\boxed{
\text{stability}
>
\text{novelty velocity}.
}
$$

---

## 1.2 Experimental / Internal ISQL

Experimental / Internal ISQL 可以：

- 改變 semantic coordinate topology；
- 改 registry architecture；
- 改 memory organization；
- 改 AI decoder；
- 改 index/search architecture；
- 改 compression；
- 引入新的 frame families；
- 破壞 backward compatibility；
- 進行高風險、高不確定性的表示實驗。

Internal / Experimental 成果不會因「在實驗版有效」就自動成為 Public protocol。

---

## 1.3 Promotion Boundary

任何 Internal / Experimental 特性進入 Public，必須通過：

$$
\boxed{
\text{Research Candidate}
\rightarrow
\text{Independent Validation}
\rightarrow
\text{Specification}
\rightarrow
\text{Conformance Vectors}
\rightarrow
\text{Public Release}.
}
$$

最低要求：

1. canonical behavior 可明確描述；
2. 不依賴單一 model vendor；
3. 可建立 deterministic test vectors；
4. failure modes 可被測試；
5. compatibility impact 被明確列出；
6. 與既有 stable core 的關係被定義；
7. 若破壞 public invariants，必須升 major version。

---

# 2. 規範性關鍵詞

本文件使用以下詞義：

- **MUST**：conforming implementation 必須滿足。
- **MUST NOT**：conforming implementation 禁止執行。
- **SHOULD**：除非有具體且可說明的理由，應遵循。
- **SHOULD NOT**：除非有具體且可說明的理由，不應採用。
- **MAY**：可選功能，不影響核心 conformance。

本文中的中文「必須／不得／應／可」與上述含義對應。

---

# 3. Public 1.0 Stable Core

Public ISQL 1.0 的穩定核心由以下元素構成：

$$
\boxed{
\mathcal P_{1.0}
=
(I,R,N,D,L,E,F)
}
$$

其中：

- $I$：Identity Contract；
- $R$：Registry Binding Contract；
- $N$：ISN7 Native Memory Frame；
- $D$：ISD8 One-Hop Delta Frame；
- $L$：ILI1 Compact Locality Index；
- $E$：Exact / Semantic Recovery Boundary；
- $F$：Fail-Closed / Canonicality Rules。

---

# 4. 不屬於 Stable Core 的內容

以下內容**不是** Public ISQL 1.0 的 canonical meaning：

- Python class layout；
- Python file layout；
- CLI command spelling；
- current semantic analyzer prompt；
- current AI model；
- current heuristic coefficients；
- current benchmark fixtures；
- current test corpus；
- wall-clock performance；
- v0.4 digits-only memory wire；
- v0.5 digits-only registry wire；
- v0.6 BCD4 / D40 carriers；
- human-readable address rendering；
- JSON locality index；
- debug rendering；
- logging format。

它們可以是：

- reference；
- legacy；
- compatibility；
- inspection；
- research；
- implementation-specific。

但不能被第三方誤認為「改了這個就不再是 ISQL」。

---

# 5. Conformance Classes

Public 1.0 定義五種 conformance class。

## C1 — Core Decoder

一個 C1 implementation MUST：

- parse canonical Public 1.0 objects；
- verify integrity bindings；
- reject malformed/noncanonical objects；
- decode ISN7；
- decode ISD8 with correct base；
- decode ILI1；
- distinguish exact from semantic recovery。

---

## C2 — Core Encoder

C2 MUST 包含 C1，並且 MUST：

- 對同一 logical object 產生唯一 canonical bytes；
- 保證：

$$
\boxed{
\operatorname{Encode}(\operatorname{Decode}(b))=b
}
$$

對所有 valid canonical public vectors成立。

---

## C3 — Memory Runtime

C3 MUST 包含 C2，並且 MUST：

- maintain stable source identity；
- bind memory to registry revision/hash；
- construct standalone ISN7；
- construct ISD8 only against standalone ISN7 base；
- select standalone when delta is not smaller。

---

## C4 — Locality Runtime

C4 MUST 包含 C3，並且 MUST：

- load/rebuild a locality index；
- exclude the target itself；
- recall a bounded candidate set；
- perform actual-byte rerank；
- never let heuristic score override actual stored byte cost。

Index algorithm本身可以不同。

---

## C5 — AI Semantic Adapter

C5 是選配。

它 MAY：

- 使用任意 AI model；
- 使用 deterministic model；
- 使用 knowledge graph；
- 使用 logic system；
- 使用 embedding；
- 使用 multimodal model。

但它 MUST：

- expose analyzer/decoder provenance；
- separate semantic reconstruction from exact reconstruction；
- never redefine stable source identity；
- never silently promote AI output to exact source。

---

# 6. Stable Identity Contract

Public 1.0 的 exact source identity 目前綁定 SHA-256 over exact source bytes。

對 source bytes $x$：

$$
\boxed{
A(x)=\operatorname{SHA256}(x).
}
$$

Canonical identity material 是：

$$
256\text{-bit raw digest}.
$$

不是十進位字串。

不是 hex 字串。

不是自然語言檔名。

---

## 6.1 Identity Invariant

任何 semantic re-encoding：

$$
M_1(x),M_2(x),\ldots
$$

不得改變：

$$
A(x).
$$

因此：

$$
\boxed{
\text{Identity}
\neq
\text{Representation}.
}
$$

---

## 6.2 Exact Source Requirement

如果 implementation 宣稱 Exact Recovery，則 MUST 能追溯到 exact source contract。

語義上「看起來一樣」不得被宣稱為 exact recovery。

---

# 7. Registry Binding Contract

任何依賴 spectral registry 解讀的 Public canonical memory object MUST 綁定：

$$
\boxed{
(\text{registry revision},\text{registry SHA-256})
}
$$

registry revision 決定語義歷史位置。

registry hash 驗證該 revision 的 canonical content。

wrong revision / wrong hash MUST fail closed。

---

## 7.1 Stable Semantic IDs

已發布的 canonical semantic ID：

- MUST NOT 被重新賦義；
- MUST NOT 被重用；
- MAY 被 deprecated；
- MAY 有 replacement；
- historical decode MUST remain possible。

---

## 7.2 Registry Representation

Canonical semantic registry state 與其 physical transport MUST 分離。

Public 1.0 要求的是：

> 相同 registry revision/hash 必須解出相同 semantic registry state。

目前 hierarchical binary registry implementation 可作 reference path，但其內部 lexeme algorithm 不因此永久成為 Meta-Core law。

---

# 8. ISN7 — Native Standalone Memory Frame

`ISN7` 是 Public 1.0 的 canonical standalone memory frame。

Logical object：

$$
\boxed{
C_{\mathrm{native}}
=
(V,D,R,A,H,\mathbf z).
}
$$

其中：

- $V$：format/version；
- $D$：frame/domain kind；
- $R$：memory resolution；
- $A$：raw 32-byte stable address；
- $H$：registry binding；
- $\mathbf z$：spectral integer coordinates。

---

## 8.1 Required ISN7 Fields

Canonical ISN7 MUST encode：

- magic/version；
- resolution；
- raw 32-byte stable source address；
- registry revision；
- raw 32-byte registry SHA-256；
- coordinate item count；
- coordinate blocks；
- accidental-corruption check。

---

## 8.2 Coordinate Blocks

Current Public 1.0 ISN7 uses blocks of at most 16 non-negative integers.

For a block：

$$
B=(z_1,\ldots,z_n),\qquad n\le16,
$$

minimal bit width：

$$
w=\max_i \operatorname{bitlength}(z_i).
$$

Canonical encoder MUST use the minimal legal $w$。

unused padding bits MUST be zero。

---

## 8.3 Canonicality

The following MUST fail：

- invalid magic；
- unsupported version；
- noncanonical integer encoding；
- impossible width；
- nonzero padding；
- truncation；
- trailing garbage；
- invalid registry binding；
- checksum mismatch。

---

# 9. ISD8 — One-Hop Locality Delta Frame

`ISD8` 是 optional canonical locality representation。

其 base：

$$
\boxed{
\text{MUST be standalone ISN7}.
}
$$

Public 1.0 禁止要求 recursive delta-chain 才能 decode 一筆 memory。

---

## 9.1 One-Hop Invariant

若：

$$
d=\operatorname{ISD8}(b,t),
$$

則 $b$ 必須是 standalone ISN7。

因此 decode depth 有硬上界：

$$
\boxed{
\operatorname{depth}\le1.
}
$$

---

## 9.2 Block Modes

Public ISD8 block 可使用：

- `COPY`
- `DELTA`
- `REPLACE`

Exact equality MUST select COPY。

DELTA MUST be used only when its canonical payload is strictly smaller than REPLACE。

Tie MUST select REPLACE。

---

## 9.3 Base Binding

ISD8 MUST bind：

$$
\operatorname{SHA256}(\text{base ISN7 bytes}).
$$

wrong base MUST fail closed。

---

## 9.4 Storage Decision

A conforming locality runtime MUST NOT store an ISD8 merely because a base exists。

Public rule：

$$
\boxed{
|ISD8|<|ISN7|
}
$$

才允許選 delta。

否則保留 standalone ISN7。

---

# 10. Random-Access Requirement

Public 1.0 支援 block-level partial decode。

A conforming implementation SHOULD 能：

- parse frame metadata；
- identify requested block；
- decode requested block；
- avoid materializing unrelated target blocks。

Full-frame validity 與 partial-access validity必須按 canonical rules 明確處理。

---

# 11. ILI1 — Compact Machine-Native Locality Index

`ILI1` 是 Public 1.0 的 derived machine-native locality index。

它不是 memory identity。

它不是 source truth。

它可以刪除並重建。

---

## 11.1 ILI1 MUST Preserve

ILI1 MUST bind/index enough metadata to support：

- base frame identity；
- source address；
- resolution；
- registry binding；
- coordinate block signatures/statistics；
- deterministic entry order；
- canonical binary round-trip。

---

## 11.2 ILI1 Canonicality

For valid canonical bytes：

$$
\boxed{
\operatorname{Encode}(\operatorname{Decode}(b))=b.
}
$$

Malformed：

- magic；
- version；
- varint；
- table ref；
- UTF-8 ref；
- truncation；
- trailing bytes；
- CRC

MUST fail closed。

---

# 12. Locality Search Semantics

ILI1 的**索引格式**是 Public stable。

但 locality search heuristic 不完全是 Public law。

Implementation MAY 使用：

- exact block postings；
- sorted sums；
- LSH；
- ANN；
- learned retrieval；
- graph index；
- tree index；
- custom hardware search。

只要最終遵守以下規則。

---

## 12.1 Recall ≠ Decision

Public invariant：

$$
\boxed{
\text{Recall Score}
\neq
\text{Final Storage Decision}.
}
$$

heuristic 只負責候選召回。

最終候選 MUST 根據實際 canonical bytes 評估。

---

## 12.2 Actual-Byte Rerank

給 recalled bases：

$$
B=\{b_1,\ldots,b_k\},
$$

runtime MUST evaluate canonical delta cost：

$$
d_i=
|\operatorname{ISD8}(b_i,t)|.
$$

最後：

$$
b^\ast=\arg\min_i d_i.
$$

只有：

$$
d_{b^\ast}<|ISN7(t)|
$$

才選 delta。

---

# 13. Exact Recovery 與 Semantic Recovery

Public ISQL 明確區分兩種成功。

## 13.1 Exact Recovery

要求：

$$
\boxed{
\hat x=x
}
$$

byte-for-byte。

---

## 13.2 Semantic Recovery

要求：

$$
d_{\mathcal S}(x,\hat x)\le\tau.
$$

其中 metric 與 threshold 由 profile / benchmark 定義。

---

## 13.3 禁止混淆

一個 AI decoder 即使輸出：

> 與原文含義完全相同的句子

也不得自動宣稱 Exact Recovery。

---

# 14. AI Decoder Contract

Public 1.0 不規定 AI vendor。

Decoder：

$$
D_A:
(C,\mathcal R,\Gamma)
\rightarrow
\hat x.
$$

其中 $A$ 是 decoder implementation/capability。

AI decoder MUST record至少：

- decoder ID；
- decoder contract/version；
- registry binding；
- source memory ID/address；
- requested resolution；
- semantic/exact mode；
- relevant provenance。

---

# 15. Semantic Analyzer Boundary

目前 semantic coordinates 可以由 AI 產生。

但 Public 1.0 不規定：

- prompt；
- model；
- embedding；
- ontology generation strategy；
- number of semantic concepts；
- language；
- vendor。

Stable requirement只有：

> analyzer output 必須可被其 declared semantic profile/registry deterministic interpret。

因此：

$$
\boxed{
\text{AI Analyzer}
=
\text{replaceable adapter}.
}
$$

---

# 16. Reference Implementation 的地位

Python `isql-core` v1.0.0 是：

$$
\boxed{
\text{Reference Implementation}.
}
$$

不是：

$$
\boxed{
\text{Normative Definition}.
}
$$

若 Python behavior 與正式 specification / golden vector 衝突：

1. specification / approved errata 優先；
2. golden conformance vector 次之；
3. Python runtime 必須修正。

不得因 reference implementation bug 而自動改寫 protocol meaning。

---

# 17. Golden Conformance Vectors

Public ISQL 必須建立獨立的 golden vectors。

建議目錄：

```text
conformance/
├─ address/
├─ registry/
├─ isn7/
├─ isd8/
├─ ili1/
├─ recovery/
├─ compatibility/
└─ invalid/
```

每個 vector SHOULD 保存：

```json
{
  "vector_id": "isql-public-1.0/isn7/000001",
  "class": "ISN7",
  "spec_version": "ISQL-PUBLIC-1.0",
  "input": {},
  "expected": {},
  "canonical_sha256": "...",
  "valid": true
}
```

Binary canonical object SHOULD 另存 binary file，而不是 base64 塞進 JSON 成為 canonical source。

---

# 18. Required Positive Vectors

Public 1.0 conformance suite至少應包含：

## Address

- empty bytes；
- ASCII；
- UTF-8 multilingual；
- binary bytes；
- source with leading zero hash material case。

## Registry

- revision 1；
- append-only revision；
- deprecated entry；
- hash binding。

## ISN7

- zero block；
- partial final block；
- multiple blocks；
- maximum tested coordinate；
- R1；
- R2；
- multilingual semantic source。

## ISD8

- COPY-only；
- DELTA；
- REPLACE；
- mixed modes；
- inherited registry；
- registry override；
- standalone fallback。

## ILI1

- one entry；
- multiple registry bindings；
- duplicate registry table dedup；
- deterministic rebuild；
- target exclusion；
- actual-byte rerank。

---

# 19. Required Invalid Vectors

至少：

- bad magic；
- unsupported version；
- truncated varint；
- noncanonical varint；
- invalid bit width；
- nonzero padding；
- trailing bytes；
- checksum mismatch；
- registry hash mismatch；
- wrong ISD8 base；
- recursive/non-standalone delta base attempt；
- invalid ILI1 registry table reference；
- invalid UTF-8 ref；
- malformed block directory；
- count mismatch；
- source-address mismatch。

Invalid vector MUST have deterministic failure class/code where practical。

---

# 20. Conformance Result

第三方 implementation MAY 宣稱：

```text
ISQL Public 1.0 C1 Conformant
ISQL Public 1.0 C2 Conformant
...
ISQL Public 1.0 C5 Conformant
```

但必須：

1. 指出 conformance suite version；
2. 公開 pass/fail summary；
3. 指出 unsupported optional features；
4. 不得用「大致 compatible」替代 canonical vector failures。

---

# 21. Compatibility Policy

Public 1.x 遵循：

$$
\boxed{
\text{additive by default}.
}
$$

Minor release MAY：

- 新增 optional frame；
- 新增 optional decoder contract；
- 新增 conformance vectors；
- 新增 metadata；
- 新增 index/search strategy；
- 新增 profile。

Minor release MUST NOT：

- silent reinterpret existing canonical bytes；
- reassign stable semantic IDs；
- change exact source identity meaning；
- make valid old ISN7/ISD8 decode into different logical object。

---

# 22. Major-Version Boundary

以下變更 SHOULD 觸發 Public 2.0：

- identity algorithm change；
- ISN7 canonical semantic reinterpretation；
- ISD8 recursive-chain requirement；
- registry binding meaning change；
- stable ID reassignment；
- exact/semantic recovery boundary removal；
- incompatible ILI1 logical interpretation。

---

# 23. Legacy / Compatibility Formats

以下格式繼續保留，但 Public 1.0 不把它們列為主 canonical runtime path：

- v0.4 ASCII numeric memory wire；
- v0.5 numeric registry wire；
- v0.6 BCD4；
- v0.6 D40；
- decimal address rendering；
- v0.9 JSON locality index。

它們 MAY 用於：

- historical replay；
- debugging；
- protocol study；
- compatibility；
- educational inspection。

---

# 24. Machine-Native First Principle

Public ISQL 1.0 的正式原則：

$$
\boxed{
\text{Machine-readable}
>
\text{Human-readable}.
}
$$

更精確地說：

$$
\boxed{
\text{human readability is not a canonical requirement}.
}
$$

Human inspectors MAY render binary objects into：

- JSON；
- decimal；
- tables；
- natural language；
- diagrams。

但：

$$
\boxed{
\operatorname{DebugRender}(C)\neq C.
}
$$

---

# 25. Security Boundary

Public 1.0 不宣稱：

- encryption；
- authenticated encryption；
- post-quantum security；
- secrecy；
- adversarial tamper resistance。

CRC32 只代表 accidental corruption detection。

SHA-256 在目前 Public 1.0 用作：

- content identity；
- registry binding；
- frame/base binding。

若應用需要 cryptographic authentication，必須由上層 security profile 提供。

---

# 26. Resource-Safety Requirement

Conforming decoder MUST 對 hostile/untrusted bytes 採 fail-closed 與 bounded resource policy。

至少 SHOULD 有：

- maximum frame size；
- maximum coordinate count；
- maximum registry entries；
- maximum block count；
- maximum nesting/dependency depth；
- maximum allocation budget。

Public ISD8 的 one-hop rule同時也是 resource-safety invariant。

---

# 27. Benchmark Boundary

目前 v1.0 的 controlled fixtures可以證明：

- canonical round-trip；
- controlled compaction；
- locality behavior；
- bounded candidate rerank；
- compatibility。

但不得被誇大為：

$$
\boxed{
\text{universal semantic compression superiority}.
}
$$

Public benchmark 必須擴大到：

- natural language；
- conversation memory；
- research notes；
- code；
- structured facts；
- agent trajectories；
- multilingual；
- high-locality；
- low-locality；
- adversarial；
- random/incompressible controls。

---

# 28. Public Benchmark Metrics

至少報：

$$
\boxed{
(
B_s,
B_r,
B_m,
B_i,
C_{\mathrm{cold}},
C_{\mathrm{warm}},
F_s,
F_e,
Q_r
)
}
$$

其中：

- $B_s$：source bytes；
- $B_r$：registry bytes；
- $B_m$：memory bytes；
- $B_i$：index bytes；
- $C_{\mathrm{cold}}$：cold-start cost；
- $C_{\mathrm{warm}}$：warm/amortized cost；
- $F_s$：semantic fidelity；
- $F_e$：exact fidelity；
- $Q_r$：retrieval quality。

---

# 29. Cross-Model Benchmark

AI-native memory 的公開測試 SHOULD 包含：

$$
D_{A_1}(C),
D_{A_2}(C),
\ldots,
D_{A_n}(C).
$$

研究：

$$
d(D_{A_i}(C),D_{A_j}(C)).
$$

但 model variation不應改變：

- source identity；
- canonical frame；
- registry interpretation。

---

# 30. Machine-Readable Public Boundary

Public release SHOULD 同時發布 machine-readable boundary manifest。

每個 component 至少標：

- identifier；
- status；
- normative level；
- compatibility class；
- replacement policy；
- public/internal ownership。

例如：

```json
{
  "component": "ISN7",
  "status": "public-stable",
  "normative": true,
  "wire_frozen": true,
  "replacement_requires_major": true
}
```

---

# 31. Public 1.0 Component Classification

## Public Stable

- exact source identity contract；
- stable semantic ID rule；
- registry revision/hash binding；
- ISN7 logical/wire canonicality；
- ISD8 one-hop semantics/wire canonicality；
- ILI1 logical/wire canonicality；
- exact vs semantic recovery split；
- fail-closed rules；
- actual-byte final locality selection principle。

## Public Replaceable / Algorithmic

- locality recall heuristic；
- candidate probe strategy；
- semantic analyzer；
- AI decoder model；
- semantic distance metric；
- benchmark implementation；
- index in-memory data structure；
- storage backend。

## Legacy / Experimental Compatibility

- digits-only memory wire；
- digits-only registry wire；
- BCD4；
- D40；
- decimal address view；
- JSON locality index。

## Research / Internal Candidate

- new ontology topologies；
- learned coordinate systems；
- recursive or graph delta models；
- alternative identities；
- adaptive registries；
- new machine-native frames；
- neural compression；
- self-modifying semantic coordinate spaces。

---

# 32. Independent Implementation Principle

一個第三方 implementation 不需要：

- import Python package；
- reproduce Python classes；
- copy current CLI；
- use same storage directory；
- use same AI model；
- use same locality heuristic。

它只需要對 normative vectors 產生相同 canonical logical result / bytes。

因此：

$$
\boxed{
\text{Implementation Diversity}
\land
\text{Protocol Equivalence}
}
$$

是 Public ISQL 的目標。

---

# 33. Language Independence

ISQL Public Core 不以英文或中文作 canonical semantic truth。

Natural language只存在於：

- source；
- analyzer input/output；
- debug rendering；
- semantic gloss；
- documentation。

Core identity/frame 是 machine-native。

因此未來：

$$
R_{\mathrm{en}},
R_{\mathrm{zh-Hant}},
R_{\mathrm{ja}},
\ldots
$$

不應改變同一 stable semantic coordinate object 的底層 identity。

---

# 34. Relationship to SPRC / SES

SPRC / SES 可以視為 Execution-oriented profile / sibling system。

Public ISQL Core 不要求：

- SPRC；
- persona；
- prompt rendering；
- natural-language surface generation。

未來可建立：

$$
\mathrm{ISQL\text{-}EXEC}
$$

把 SPRC 類執行碼映射進 ISQL domain，但這不是 Public 1.0 的 mandatory core。

---

# 35. Relationship to INSL

INSL 歷史上提供：

- structured sequence；
- context-dependent classification；
- expandable registry；
- reserved/future space。

Public ISQL 1.0 保留這些工程精神，但 canonical mainline已演化為 machine-native code space。

因此不再要求：

> ISQL 必須是一串人類可以直接閱讀的十進位數字。

---

# 36. Research Claims Boundary

Public 1.0 可以聲稱：

- 已建立 coherent experimental AI-native memory stack；
- stable addressing implemented；
- semantic/spectral coordinates implemented；
- machine-native standalone/delta/index formats implemented；
- deterministic conformance behavior可建立；
- controlled locality/compaction experiments存在。

Public 1.0 不應聲稱：

- universal compression optimum；
- AGI-native universal language已完成；
- lossless semantic reconstruction for arbitrary information；
- globally optimal semantic ontology；
- production cryptographic protocol；
- universal ANN superiority；
- human language已被取代。

---

# 37. Public v1.x 的工作方向

v1.x SHOULD 優先：

1. Conformance Suite；
2. Golden Vectors；
3. second-language implementation；
4. benchmark expansion；
5. fuzz/property testing；
6. spec errata；
7. security/resource limits；
8. model-neutral semantic adapter contract。

不應優先：

> 每一版都新增一個新的 frame magic。

---

# 38. Internal / Experimental 的工作方向

Internal line 可以研究：

- AI-native ontology；
- dynamic coordinate spaces；
- continuous/discrete hybrid spectrum；
- higher-order memory topology；
- learned registries；
- graph/delta structures；
- cross-model semantic repair；
- self-compressing memories；
- AI-to-AI protocol；
- alternate addressing；
- non-text/multimodal states。

Internal 不承諾 Public 1.x compatibility。

---

# 39. 雙架構 Invariant Comparison

當另一套 ISQL-like architecture 可供比較時，不應先問：

> 哪套比較強？

而應先求：

$$
\boxed{
\mathcal I_{\cap}
=
\operatorname{Invariant}(I_A)
\cap
\operatorname{Invariant}(I_B).
}
$$

特別觀察是否共同出現：

- stable identity；
- registry；
- version；
- resolution；
- semantic coordinate；
- machine-native carrier；
- decoder contract；
- provenance；
- recovery boundary；
- locality/retrieval abstraction。

共同 invariant 是未來 ISQL Meta-Core 的優先候選。

---

# 40. ISQL Meta-Core 暫定邊界

目前 Public 1.0 尚不足以宣稱完整 Meta-Core。

但可提出暫定候選：

$$
\boxed{
\mathcal M_{\mathrm{ISQL}}
=
(
\text{Identity},
\text{Coordinates},
\text{Registry},
\text{Version},
\text{Recovery},
\text{Machine Carrier}
)
}
$$

Locality / delta / index 是否屬 Meta-Core，仍需另一套架構與更多 workload 比較。

---

# 41. Conformance Suite Versioning

Protocol version與 conformance-suite version分離。

例如：

```text
Protocol: ISQL-PUBLIC-1.0
Conformance: ISQL-CONFORMANCE-1.0.3
```

新增 invalid vector MAY 只升 conformance patch。

改 protocol meaning 必須按 protocol versioning 處理。

---

# 42. Errata Policy

若 Public spec 有錯：

- MUST 發布 errata；
- MUST 指出受影響 vector；
- MUST 指出是否改 canonical bytes；
- 若 canonical bytes meaning 改變，應按 major-version policy處理。

不能只更新 Python code 然後默認 spec 已變。

---

# 43. Public Release Artifact Set

正式 Public 1.0 release 建議包含：

```text
ISQL_PUBLIC_SPEC.md
PUBLIC_BOUNDARY.json
CONFORMANCE/
REFERENCE_RUNTIME/
GOLDEN_VECTORS/
INVALID_VECTORS/
BENCHMARK_PROTOCOL.md
SECURITY_CONSIDERATIONS.md
CHANGELOG.md
CHECKSUMS.sha256
```

---

# 44. Public 1.0 Acceptance Gate

Public protocol package完整發布前至少要求：

- [ ] Stable-core specification complete
- [ ] Boundary manifest complete
- [ ] Positive golden vectors
- [ ] Invalid vectors
- [ ] Python reference runtime passes all vectors
- [ ] Second independent decoder implementation passes core vectors
- [ ] All public binary formats canonical round-trip
- [ ] Compatibility vectors for ISN7 / ISD8 / ILI1
- [ ] Resource-limit policy documented
- [ ] Security non-claims documented
- [ ] Benchmark protocol separated from benchmark results
- [ ] Reference implementation explicitly non-normative

在第二獨立 implementation 尚未完成前：

$$
\boxed{
\text{Public 1.0 protocol boundary can be specified,}
}
$$

但：

$$
\boxed{
\text{cross-implementation interoperability is not yet independently proven.}
}
$$

這個差異必須公開寫明。

---

# 45. Public 1.0 的核心治理原則

最終壓縮成十二條：

1. **Specification outranks implementation.**
2. **Canonical bytes must have one meaning.**
3. **Identity is separate from representation.**
4. **Registry meaning is version/hash bound.**
5. **Human readability is optional.**
6. **AI model choice is replaceable.**
7. **Exact recovery is not semantic recovery.**
8. **Delta depth is bounded.**
9. **Heuristic recall never decides storage alone.**
10. **Derived indexes are rebuildable.**
11. **Public stability outranks research velocity.**
12. **Experimental success requires promotion before becoming public law.**

---

# 46. 結論

ISQL Core Runtime v1.0.0 已經形成第一套一致的 experimental AI-native memory stack：

$$
\boxed{
\text{Source}
\rightarrow
\text{Stable Identity}
\rightarrow
\text{Semantic/Spectral Coordinates}
\rightarrow
\text{Registry Binding}
\rightarrow
\text{ISN7}
\rightarrow
\text{ISD8}
\rightarrow
\text{ILI1}.
}
$$

但 Public ISQL 1.0 的真正意義，不是：

> 「我們已經寫到 v1.0，所以這些 Python code 就是標準。」

而是：

$$
\boxed{
\text{我們現在開始把可替換的研究實作，
和不可被靜默破壞的公開語義邊界分開。}
}
$$

從這一步開始，Public ISQL 的主要問題不再只是：

> 還可以怎麼壓？

而是：

> 第三方能不能在完全不依賴原作者 Python 實作的情況下，
> 讀同一個 object、拒絕同一個 invalid object、
> 重建同一個 identity，並得到同一個 canonical meaning？

只有當答案可以由獨立 implementation 重現時，

Public ISQL 才真正從：

$$
\text{research runtime}
$$

跨進：

$$
\boxed{
\text{protocol}.
}
$$
