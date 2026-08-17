# ISQL Core Code Base Space v0.2
## 無限光譜量化語言核心碼空間：從單一無限標量到可定址、可恢復、可多解析度運行的結構資訊域

**English Title:** ISQL Core Code Base Space v0.2: A Versioned Structured Code Space for Addressable, Recoverable, and Multi-Resolution Information  
**提出者：** Neo.K（EVEMISSLAB／一言諾科技有限公司）  
**文件類型：** 核心技術規格／架構草案  
**版本：** v0.2  
**日期：** 2026-08-17  
**狀態：** Core Architecture Draft  
**Canonical Source:** UTF-8 Markdown

---

## 摘要

本文重新定義 **ISQL（Infinite Spectral Quantization Language，無限光譜量化語言）** 的工程核心。

早期 ISQL 曾以「單一無限精度浮點數承載高維語義」作為極端壓縮的思想模型；其後 INSL（Infinite Numerical Sequence Language）將此概念修正為**結構化、分層、可擴展的數字序列**，避免單一無限浮點數在實際計算中的精度與結構瓶頸。

本版本進一步提出：

$$
\boxed{
\text{ISQL 的第一優先任務不是先決定用途，而是先建立可計算的 Code Base Space。}
}
$$

也就是先回答：

- 哪些碼是合法的？
- 碼存在於哪個 namespace / domain？
- 碼如何被定址、版本化、組合與解析？
- Address 與 Memory 是否共享同一身份規則？
- 同一資訊是否可以存在多個 resolution？
- AI 解碼器應如何參與語義恢復，但不成為 canonical identity 本身？

因此，本文把 ISQL Core 定義為：

$$
\boxed{
\textbf{ISQL Core}
=
\text{A versioned structured code space for addressable and recoverable information.}
}
$$

新版 ISQL 不要求一開始就決定它最終是：

- Agent memory；
- 內容定址；
- 語義壓縮；
- machine-to-machine protocol；
- AI-native language；
- 多模態資訊表示；
- 或其他未來應用。

這些用途被降為後續 profile。

核心層只建立：

$$
\boxed{
\mathcal C_{\mathrm{ISQL}}
}
$$

——一個版本化、結構化、可多解析度、可由軟體與 AI 共同解碼的資訊碼空間。

---

# 1. 理論沿革：ISQL → INSL → ISQL Core

## 1.1 早期 ISQL：單一無限標量模型

早期 ISQL 的極端構想可以抽象為：

$$
E:
\mathcal I
\rightarrow
\mathbb R_{\infty},
$$

其中：

- $\mathcal I$ 為高維資訊／語義空間；
- $\mathbb R_{\infty}$ 表示理想化的無限精度數值載體。

理想目標是：

$$
x
\rightarrow
z
\rightarrow
x,
$$

即：

$$
D(E(x))=x.
$$

這種模型在哲學上非常簡潔，但具有明顯工程限制：

1. 現實計算系統不存在真正可操作的無限精度單一浮點值；
2. 一個扁平標量難以顯示內部層級；
3. 部分解碼、局部修改、版本管理與錯誤恢復都不自然；
4. 語義與身份容易被混成同一個數字。

---

## 1.2 INSL：從單一標量轉向結構化序列

INSL 的重要修正是：

$$
\boxed{
\text{Single Infinite Scalar}
\rightarrow
\text{Structured Hierarchical Sequence}.
}
$$

資訊不再必須塞進一個理想化單一浮點值，而可以表示成：

$$
s=(s_0,s_1,s_2,\dots,s_n,\dots).
$$

這帶來：

- 分層結構；
- prefix / context；
- 可擴展性；
- 部分解析；
- registry；
- 可組合性；
- 未來保留位。

這個轉向應被保留。

新版 ISQL 不否定 INSL；相反，INSL 提供了新版 ISQL Core 可計算化所需要的結構基礎。

---

## 1.3 新版回歸：重新解釋「光譜」

新版 ISQL 不再把「Spectrum」限定為一條無限實數軸。

本文將光譜重新定義為：

$$
\boxed{
\text{multi-axis}
+
\text{multi-resolution}
+
\text{context-dependent}
+
\text{versioned information coordinates}.
}
$$

因此，資訊表示不再必須是：

$$
z\in\mathbb R.
$$

而可以是：

$$
\mathbf z
=
(z_1,z_2,\dots,z_k),
$$

甚至：

$$
\mathbf z^{(r)}
=
(z^{(r)}_1,\dots,z^{(r)}_{k_r}),
$$

其中 $r$ 是 resolution level。

---

# 2. 第一原則：先定義 Code Space，再決定用途

新版 ISQL Core 的中心原則：

$$
\boxed{
\text{Code Space First, Application Later.}
}
$$

因此先建立：

$$
\mathcal C_{\mathrm{ISQL}}
=
\bigcup_{d\in\mathcal D}
\mathcal C_d.
$$

其中：

- $\mathcal D$ 是 domain / namespace 集合；
- $\mathcal C_d$ 是特定 domain 的合法碼空間。

例如：

$$
\mathcal D
=
\{
\mathrm{ADDR},
\mathrm{MEM},
\mathrm{SEM},
\mathrm{EXEC},
\mathrm{STATE},
\mathrm{RESERVED}
\}.
$$

此時 ISQL 不需要立刻回答：

> 「這個 code 到底是記憶還是地址？」

因為：

$$
\boxed{
\text{用途由 domain 決定，而不是由 Core 被迫只選一種用途。}
}
$$

---

# 3. ISQL Kernel

本文定義：

$$
\boxed{
\mathcal K_{\mathrm{ISQL}}
=
(\Sigma,G,\mathcal D,V,E,R).
}
$$

其中：

- $\Sigma$：alphabet；
- $G$：grammar；
- $\mathcal D$：namespace / domain；
- $V$：version；
- $E$：encoding contract；
- $R$：resolution / recovery contract。

這六項構成 ISQL Kernel 的最小結構。

---

# 4. Alphabet

## 4.1 分離 Control 與 Payload Alphabet

初始建議：

$$
\Sigma
=
\Sigma_C
\cup
\Sigma_N.
$$

其中：

$$
\Sigma_C
=
\{A,\dots,Z\},
$$

$$
\Sigma_N
=
\{0,\dots,9\}.
$$

字母主要負責：

- namespace；
- domain；
- control；
- profile；
- version-local opcode。

數字主要負責：

- seed；
- coordinate；
- payload；
- index；
- resolution-specific values。

---

## 4.2 數字永遠先視為字串

例如：

```text
123456789123456789123456789
```

canonical source 是：

$$
\text{UTF-8 decimal digit string},
$$

不是：

$$
1.2345678912345679\times10^{26}.
$$

因此不得因 runtime language 的浮點精度而失去位元。

---

# 5. Grammar

最小 grammar：

```text
CONTROL ::= [A-Z]+
DIGITS  ::= [0-9]+
CODE    ::= CONTROL DIGITS
```

但這只是 surface grammar。

正式 ISQL object 建議表示為：

$$
c=(v,d,p,s),
$$

其中：

- $v$：version；
- $d$：domain；
- $p$：control prefix / profile；
- $s$：main sequence。

例如概念形式：

```text
ISQL1:MEM:XRQ123456789...
```

或：

```text
ISQL1:ADDR:A123456789...
```

真正 wire format 可以之後再決定。

Core 現階段只固定結構，不提前鎖死字串格式。

---

# 6. Domain / Namespace

## 6.1 Address Domain

定義：

$$
A:
\mathcal O
\rightarrow
\mathcal C_{\mathrm{ADDR}}.
$$

其中 $\mathcal O$ 是可定址物件集合。

Address domain 的主要要求：

1. deterministic；
2. stable；
3. version-aware；
4. collision policy 明確；
5. 不因 AI 模型版本改變而改；
6. 可驗證；
7. 最好支援 content-addressing 或 registry identity。

---

## 6.2 Memory Domain

定義：

$$
M:
(\mathcal X,\Gamma,t)
\rightarrow
\mathcal C_{\mathrm{MEM}},
$$

其中：

- $\mathcal X$：experience / information；
- $\Gamma$：context；
- $t$：time / state。

Memory domain 可以允許：

- lossy；
- dynamic；
- adaptive；
- context-sensitive；
- multi-resolution；
- AI-assisted reconstruction。

因此：

$$
\boxed{
\mathcal C_{\mathrm{ADDR}}
\neq
\mathcal C_{\mathrm{MEM}}.
}
$$

這是新版 ISQL Core 的硬分離。

---

## 6.3 Semantic Domain

Semantic domain 保存：

$$
\text{meaning-oriented coordinates}.
$$

它可以接：

- operator；
- ontology；
- embedding；
- logic matrix；
- knowledge graph；
- ISQL spectrum；
- multilingual semantic realization。

但 semantic representation 不應自動成為 address identity。

---

## 6.4 Execution Domain

Execution domain 可接目前的 SES / SPRC：

$$
\mathcal C_{\mathrm{EXEC}}
\supset
\mathrm{SES/SPRC}.
$$

即：

$$
\text{ISQL Core}
\rightarrow
\text{Execution Profile}
\rightarrow
\text{SPR}.
$$

SES / SPRC 可以被視為新版 ISQL Core 的第一個成熟 execution-oriented descendant / profile，而不是 ISQL Core 的全部。

---

## 6.5 State Domain

State domain 表示：

$$
X_t.
$$

例如：

- research state；
- agent state；
- dialogue state；
- world state；
- memory retrieval state。

它與 Memory 不同：

$$
\text{Memory}=\text{retained history},
$$

$$
\text{State}=\text{current operational condition}.
$$

---

# 7. Address Identity 與 Memory Representation 的硬分離

這是新版架構最重要的工程規則之一。

對物件 $x$：

$$
a=A(x),
$$

是 address identity。

而：

$$
m=M(x,\Gamma,t),
$$

是 memory representation。

要求：

$$
\boxed{
a\neq m.
}
$$

即使：

$$
x
$$

的 memory 被重新壓縮、重新摘要、換模型或換 resolution：

$$
M_1(x)\neq M_2(x),
$$

其 identity 仍可保持：

$$
A(x)=\text{constant}.
$$

這延續 INSL 工程化後的重要分層精神。

---

# 8. 多解析度 Memory

同一 memory object：

$$
m
$$

可以具有多層 representation：

$$
M^{(1)}(m),
M^{(2)}(m),
\dots,
M^{(r)}(m).
$$

建議初始 resolution model：

## R0 — Locator

只保存：

- address；
- type；
- minimal routing metadata。

## R1 — Semantic Skeleton

保存：

- 核心主題；
-主要角色；
- 關係；
- 短 semantic coordinates。

## R2 — Structured Memory

保存：

- facts；
- dependencies；
- events；
- causal links；
- uncertainty；
- source refs。

## R3 — Rich Reconstruction Layer

保存接近完整可恢復語義所需的高解析資訊。

## R4 — Exact / Source Layer

必要時連回：

- 原始 UTF-8 source；
- exact binary；
- immutable content object。

因此：

$$
\boxed{
R0<R1<R2<R3<R4.
}
$$

但這個次序表示資訊解析度，不表示價值高低。

---

# 9. Progressive Recall

Memory retrieval 不必一開始載入完整內容。

可以：

$$
R0
\rightarrow
R1
\rightarrow
R2
\rightarrow
R3.
$$

只有當低 resolution 判斷 relevant 時才展開。

因此 context cost 可以近似：

$$
C_{\mathrm{retrieve}}
=
\sum_{r=0}^{r^\ast}
C_r,
$$

而不是每次直接：

$$
C_{\mathrm{full}}.
$$

這可以成為 ISQL Memory Profile 未來的重要用途。

---

# 10. AI Decoder Contract

強 AI 帶來一個早期 ISQL 不具備的工程條件：

$$
\boxed{
\text{Decoder intelligence can participate in reconstruction.}
}
$$

但 AI 不應成為 code identity。

定義：

$$
D_A:
(\mathcal C,\mathcal R,\Gamma)
\rightarrow
\hat x,
$$

其中：

- $A$：AI capability / model；
- $\mathcal C$：ISQL code；
- $\mathcal R$：registry；
- $\Gamma$：context；
- $\hat x$：reconstructed information。

---

# 11. Semantic Recoverability

給定原始資訊：

$$
x,
$$

encode：

$$
c=E(x).
$$

decode：

$$
\hat x=D_A(c,\mathcal R,\Gamma).
$$

定義 reconstruction error：

$$
\epsilon
=
d_{\mathcal I}(x,\hat x).
$$

定義 recoverability：

$$
\boxed{
\operatorname{Rec}_A(c)
=
1-\epsilon.
}
$$

其中距離：

$$
d_{\mathcal I}
$$

必須依 domain 定義。

不同用途不能強迫共用一個「語義距離」。

---

# 12. Decoder Intelligence as a Parameter

同一 code：

$$
c
$$

可能有：

$$
D_{A_1}(c)=\hat x_1,
$$

$$
D_{A_2}(c)=\hat x_2.
$$

如果：

$$
A_2>A_1,
$$

可能觀察到：

$$
d(x,\hat x_2)
<
d(x,\hat x_1).
$$

因此 ISQL 可以研究：

$$
\boxed{
\epsilon
=
\epsilon(k,A,\Gamma,r),
}
$$

其中：

- $k$：code information budget；
- $A$：decoder intelligence；
- $\Gamma$：available context；
- $r$：resolution。

這形成：

$$
\boxed{
\text{Code Length}
\times
\text{Decoder Intelligence}
\times
\text{Context}
\times
\text{Reconstruction Fidelity}.
}
$$

---

# 13. AI-Assisted Compression 的新定義

傳統壓縮關心：

$$
x
\rightarrow
c
\rightarrow
x.
$$

ISQL Memory Profile 可以研究：

$$
x
\rightarrow
c
\rightarrow
\hat x_A.
$$

而：

$$
\hat x_A
$$

不必 byte-identical，但要在指定 semantic contract 下足夠等價。

因此壓縮率不能單獨評估。

需要：

$$
\boxed{
(\text{size},\text{fidelity},\text{decoder},\text{context})
}
$$

四元組。

---

# 14. Exact 與 Semantic Reconstruction 的分離

定義兩種 recovery。

## Exact Recovery

要求：

$$
\hat x=x.
$$

適用：

- 原始 source；
- binary；
- cryptographic identity；
- code；
- legal archival content。

## Semantic Recovery

要求：

$$
d_{\mathcal S}(x,\hat x)\le\tau.
$$

適用：

- memory；
- summary；
- semantic routing；
- AI context；
- approximate conceptual reconstruction。

不得把 semantic equivalence 假裝成 byte-level identity。

---

# 15. Registry Contract

任何 ISQL code 的語義至少綁定：

$$
(\text{Protocol Version},
\text{Registry Version},
\text{Domain},
\text{Code}).
$$

正式 execution / recovery 建議另外保存：

- registry hash；
- encoder version；
- decoder contract；
- model ID；
- resolution；
- context policy。

例如：

```json
{
  "protocol": "ISQL-Core",
  "version": "0.2",
  "domain": "MEM",
  "registry": "ISQL-MEM-1",
  "registry_hash": "...",
  "resolution": "R2",
  "code": "XRQ123456789...",
  "encoder": "isql-mem-encoder/v1",
  "decoder_contract": "semantic-recovery/v1"
}
```

---

# 16. Versioning

Published meaning 不得 silent drift。

版本至少分：

## Protocol Version

定義：

- grammar；
- domain structure；
- canonical serialization。

## Registry Version

定義：

- control codes；
- semantic coordinates；
- field meanings。

## Encoder Version

定義：

$$
E_v.
$$

## Decoder Contract Version

定義：

$$
D_v.
$$

因此：

$$
\boxed{
\text{same code string}
\not\Rightarrow
\text{same meaning without version context}.
}
$$

---

# 17. Code Composition

ISQL code 應支援組合。

定義：

$$
c=c_1\Vert c_2.
$$

但 composition semantics 由 domain 決定。

Address domain 的 concatenation 不必等於 Memory domain 的 concatenation。

因此：

$$
\Vert_{\mathrm{ADDR}}
\neq
\Vert_{\mathrm{MEM}}.
$$

Core 只規定「可組合」，不提前假設所有 domain 使用同一 composition algebra。

---

# 18. Partial Decoding

對：

$$
c=(c_1,\dots,c_n),
$$

decoder 可以只解析：

$$
c_{1:k}.
$$

形成：

$$
D^{(k)}(c).
$$

要求：

$$
k_1<k_2
$$

時，理想上：

$$
\operatorname{Info}(D^{(k_1)}(c))
\subseteq
\operatorname{Info}(D^{(k_2)}(c)).
$$

但這只是 profile-level desirable property，不是所有 ISQL code 的 Core theorem。

---

# 19. Reserved Space

延續 INSL「源點／保留位」精神，新版 ISQL Core 應保留：

$$
\mathcal C_{\mathrm{RESERVED}}.
$$

任何未定義區域：

- 不得被 runtime 自動賦義；
- 不得被 future version 默認當作 legacy code；
- 必須經 registry version 顯式啟用。

這提供未來：

- 非語言資料；
- 多模態；
- sensor space；
- agent-native concepts；
- 尚未存在的 representation。

---

# 20. 與 INSL 的關係

新版建議：

$$
\boxed{
\text{INSL}
=
\text{structured sequence / identity / registry lineage}
}
$$

而：

$$
\boxed{
\text{ISQL Core}
=
\text{generalized addressable and recoverable code-space kernel}.
}
$$

兩者暫時不必強行合併名稱。

可以視為：

```text
ISQL early spectral idea
        ↓
INSL structural correction
        ↓
ISQL Core Code Base Space
        ├─ Address Profile
        ├─ Memory Profile
        ├─ Semantic Profile
        ├─ Execution Profile
        └─ Future Profiles
```

因此新版 ISQL Core 是：

$$
\boxed{
\text{吸收 INSL 工程修正後的 ISQL 第二代核心}.
}
$$

---

# 21. 與 SES / SPRC 的關係

SES / SPRC 已經證明一個小型「語義規則 + 數字 seed + registry + AI rendering」鏈條可以實際運行。

因此可以暫時定義：

$$
\boxed{
\mathrm{SPRC}
\subset
\mathcal C_{\mathrm{EXEC}}.
}
$$

這不代表 SPRC 等於 ISQL。

SPRC 是一個 execution profile / descendant。

它提供：

- versioned semantic rules；
- seed；
- operator program；
- rendering；
- replay。

因此可以作為 ISQL Execution Domain 的第一個真實實驗樣本。

---

# 22. Multilingual Relation

新版 multilingual SPRC 已經提供一個重要實驗：

同一 semantic core：

$$
s
$$

可產生：

$$
R_{\mathrm{en}}(s),
$$

$$
R_{\mathrm{zh-Hant}}(s).
$$

而保持 operator program 不變。

這支持 ISQL Core 採：

$$
\boxed{
\text{language-neutral code}
\rightarrow
\text{language-specific realization}.
}
$$

語言不是 canonical code identity。

---

# 23. Memory Addressing Architecture

若 ISQL 先用於 AI memory，推薦：

```text
Memory Object
├─ Stable Address
│  └─ ISQL-ADDR
├─ Resolution Index
│  ├─ R0 locator
│  ├─ R1 skeleton
│  ├─ R2 structured memory
│  ├─ R3 rich reconstruction
│  └─ R4 exact source reference
├─ Semantic Coordinates
│  └─ ISQL-MEM / ISQL-SEM
├─ Provenance
├─ Registry Version
└─ Decoder Contract
```

因此 address 與 memory content 可以獨立升級。

---

# 24. 最小 Memory Record

```json
{
  "memory_id": "mem:...",
  "address": {
    "domain": "ADDR",
    "code": "..."
  },
  "representations": {
    "R0": "...",
    "R1": "...",
    "R2": "..."
  },
  "semantic_code": {
    "domain": "MEM",
    "code": "..."
  },
  "source_ref": "...",
  "registry": "...",
  "encoder": "...",
  "decoder_contract": "...",
  "provenance": {}
}
```

R4 exact source 可以是外部 immutable artifact，而不必硬塞進 semantic code 本身。

---

# 25. Retrieval

Memory retrieval 可以拆成：

$$
\operatorname{Route}
\rightarrow
\operatorname{Rank}
\rightarrow
\operatorname{Expand}.
$$

第一階段只用：

$$
R0/R1
$$

進行候選檢索。

只有命中才載入：

$$
R2/R3.
$$

最後必要時才追：

$$
R4.
$$

因此 ISQL Memory 不只是「壓縮」，也可以成為：

$$
\boxed{
\text{progressive semantic retrieval architecture}.
}
$$

---

# 26. Code Base Space 的數學抽象

定義：

$$
\mathcal C
=
\coprod_{d\in\mathcal D}
\mathcal C_d.
$$

使用 disjoint union 是因為：

同一 surface sequence 在不同 domain 中不應被視為同一 semantic object。

即：

$$
(d_1,s)
\neq
(d_2,s)
$$

若：

$$
d_1\neq d_2.
$$

每個 domain：

$$
\mathcal C_d
$$

可以擁有自己的：

- grammar；
- equivalence relation；
- composition；
- decoder；
- resolution order。

---

# 27. Equivalence

Core 不定義全域唯一 equivalence。

每個 domain 定義：

$$
\sim_d.
$$

Address：

$$
c_1\sim_{\mathrm{ADDR}}c_2
$$

可能要求完全相同 identity。

Memory：

$$
c_1\sim_{\mathrm{MEM}}c_2
$$

可以表示 semantic equivalence。

因此：

$$
\boxed{
\sim_{\mathrm{ADDR}}
\neq
\sim_{\mathrm{MEM}}.
}
$$

---

# 28. ISQL Base-Space Invariants

新版 Core 建議至少固定以下 invariants。

## I1 — Domain Explicitness

任何 canonical code 必須能確定 domain。

## I2 — Version Explicitness

正式 archive / transport 必須可定位 protocol + registry version。

## I3 — No Float Collapse

任意長 sequence 不得被默認轉成有限浮點。

## I4 — Identity / Representation Separation

Address identity 不等同 semantic representation。

## I5 — Exact / Semantic Recovery Separation

exact recovery 與 semantic recovery 不混為同一種成功。

## I6 — Decoder Disclosure

AI-assisted decode 必須記錄 decoder/model contract。

## I7 — Reserved Means Undefined

保留區不得被 silent inference。

## I8 — Progressive Resolution Is Explicit

每個 resolution 的資訊契約必須明確。

## I9 — Unknown Code Fails Closed

未知 domain / registry code 不自行猜 canonical meaning。

## I10 — Source Preservation

若任務要求 exact reconstruction，必須保留可追溯 exact source。

---

# 29. 第一階段實作目標

ISQL Core v0.2 暫時只要求建立：

1. Core grammar；
2. domain registry；
3. version model；
4. Address Profile；
5. Memory Profile；
6. resolution hierarchy；
7. encode/decode interface；
8. AI decoder contract；
9. recoverability test harness；
10. canonical trace / provenance。

先不實作：

- 全球 semantic coordinate ontology；
- 完整自然語言壓縮器；
- 真正無限 sequence；
- 全多模態；
- cryptographic protocol；
- public distributed registry。

---

# 30. 第一批實驗

## Experiment A — Exact Address Stability

同一 object：

$$
x
$$

跨模型、跨時間 encode address：

$$
A_1(x),A_2(x),\dots
$$

要求：

$$
A_i(x)=A_j(x).
$$

---

## Experiment B — Memory Resolution

對同一 source：

$$
x,
$$

建立：

$$
M^{(1)}(x),M^{(2)}(x),M^{(3)}(x).
$$

測：

$$
\epsilon_r
=
d(x,D_A(M^{(r)}(x))).
$$

---

## Experiment C — Decoder Capability Axis

固定 code：

$$
c,
$$

測：

$$
D_{A_1}(c),
D_{A_2}(c),
\dots
$$

觀察：

$$
\epsilon(A).
$$

---

## Experiment D — Context Axis

固定：

$$
(c,A),
$$

改變 context：

$$
\Gamma_1,\Gamma_2,\dots
$$

測：

$$
\epsilon(\Gamma).
$$

---

## Experiment E — Cross-Model Recoverability

同一 semantic memory code：

$$
c
$$

交給不同模型。

研究：

$$
d(
D_{A_i}(c),
D_{A_j}(c)
).
$$

這才是「AI 不用特意解釋也能理解 ISQL」可以被正式驗證的版本。

---

# 31. 成功條件

ISQL Core v0.2 的成功，不是：

> 壓縮率比 ZIP 高。

也不是：

> 一串數字可以神奇代表所有知識。

成功條件是：

$$
\boxed{
\text{建立一個穩定、可版本化、可測量恢復品質的資訊碼空間。}
}
$$

其上層應能自然容納：

- address；
- memory；
- semantic code；
- execution code；
- AI reconstruction。

---

# 32. 核心公式

新版 ISQL 可以濃縮成：

$$
\boxed{
\mathcal C_{\mathrm{ISQL}}
=
\coprod_{d\in\mathcal D}
\mathcal C_d.
}
$$

Encoding：

$$
E_{d,v,r}:
(\mathcal I,\Gamma)
\rightarrow
\mathcal C_d^{(r)}.
$$

Decoding：

$$
D_{A,d,v,r}:
(\mathcal C_d^{(r)},\mathcal R,\Gamma)
\rightarrow
\hat{\mathcal I}.
$$

Recovery error：

$$
\epsilon
=
d_d(x,\hat x).
$$

因此：

$$
\boxed{
\epsilon
=
f(
\text{code budget},
\text{resolution},
\text{decoder intelligence},
\text{context},
\text{domain}
).
}
$$

這是新版 ISQL 的主要可實驗形式。

---

# 33. 核心設計原則

本文將新版 ISQL 壓縮成十條原則：

1. **Code space first.**
2. **Application later.**
3. **Address is not memory.**
4. **Memory is not exact source.**
5. **Digits are sequences, not floats.**
6. **Spectrum is multi-axis and multi-resolution.**
7. **AI is a decoder parameter, not canonical identity.**
8. **Version and domain are part of meaning.**
9. **Unknown codes fail closed.**
10. **Exact source remains recoverable when exactness is required.**

---

# 34. 結論

早期 ISQL 的核心直覺並沒有必要被放棄。

真正需要放棄的是：

$$
\boxed{
\text{「所有資訊都必須被塞進單一無限精度浮點數」}
}
$$

這個過強工程假設。

INSL 已經完成第一輪結構修正：

$$
\text{single scalar}
\rightarrow
\text{structured sequence}.
$$

而現在，隨著強 AI 可以實際參與：

- semantic reconstruction；
- cross-language realization；
- context completion；
- semantic routing；
- state interpretation；
- code-driven execution；

ISQL 可以進行第二次工程化。

新版核心不再是：

$$
\text{一個神奇的無限數字}.
$$

而是：

$$
\boxed{
\text{一個版本化、分域、多解析度、可被軟體與 AI 恢復的 Code Base Space}.
}
$$

因此：

$$
\boxed{
\textbf{ISQL Core}
=
\text{Structured Code Space}
+
\text{Domain Semantics}
+
\text{Resolution}
+
\text{Recovery Contract}.
}
$$

未來它可以成為 memory。

也可以成為 address。

也可以成為 semantic representation。

也可以承載 SES / SPRC 類 execution code。

但這些都不必在今天被強迫選成唯一用途。

真正應先完成的是：

$$
\boxed{
\mathcal C_{\mathrm{ISQL}}.
}
$$

只要底層 Code Base Space 足夠清楚，之後的用途可以一層一層長出來。

---

# 附錄 A：暫定 Profile

```text
ISQL-ADDR
    Stable Address / Identity

ISQL-MEM
    Multi-resolution AI Memory

ISQL-SEM
    Semantic Coordinates

ISQL-STATE
    Dynamic State Representation

ISQL-EXEC
    Executable Semantic Code

ISQL-RESERVED
    Future / Undefined Domains
```

---

# 附錄 B：與目前專案的映射

```text
ISQL Core Code Base Space
├─ ISQL-ADDR
│  └─ 可接 INSL / content identity
├─ ISQL-MEM
│  └─ AI memory / progressive recall
├─ ISQL-SEM
│  └─ semantic spectrum / multilingual meaning
├─ ISQL-STATE
│  └─ agent / research / dialogue state
├─ ISQL-EXEC
│  └─ SES / SPRC
└─ ISQL-RESERVED
   └─ future domains
```

---

# 附錄 C：下一步實作順序

建議：

```text
Phase 1
ISQL Core grammar + domain registry

Phase 2
ISQL-ADDR minimal profile

Phase 3
ISQL-MEM multi-resolution profile

Phase 4
AI decoder / recoverability harness

Phase 5
Cross-model experiments

Phase 6
Semantic / execution integration
```

先不要做完整「無限語義宇宙」。

先把最小的：

$$
\boxed{
\text{Encode}
\rightarrow
\text{Address}
\rightarrow
\text{Store}
\rightarrow
\text{Retrieve}
\rightarrow
\text{Decode}
\rightarrow
\text{Measure Error}
}
$$

跑起來。

這會是新版 ISQL 從理論重新回到可實驗工程的第一步。
