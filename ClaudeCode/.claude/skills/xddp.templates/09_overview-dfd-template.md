---
version: "1.0.0"
last-updated-cr: "{CR}"
last-verified-cr: "{CR}"
source: spo
repo: "{repo}"
---

# データフロー図 — {repo}

**リポジトリ:** {repo}  
**最終更新CR:** {CR}  

> 気づきメモは `architecture.md` に記録してください（このファイルには気づきメモセクションなし）。
> **生成条件:** SPO §4.2 DFD から生成する（常に必須）。

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| 対象リポジトリ | {repo} |
| DFD種別 | コンポーネント間データフロー |

---

## 2. データフロー図（DFD）

> コンポーネント間のデータフローの全体像を示す。
> SPO サマリー「データフロー図（DFD）」セクションから取得する。
> プロセスノード・データストアノード・外部エンティティを区別して描く。

```mermaid
graph LR
    subgraph External
        {ExternalSystem}["{外部システム名}"]
    end
    subgraph {repo}
        {ProcessA}("{プロセスA}")
        {ProcessB}("{プロセスB}")
        {DataStore}[("{データストア}")]
    end
    {ExternalSystem} -->|"{入力データ}"| {ProcessA}
    {ProcessA} -->|"{変換後データ}"| {ProcessB}
    {ProcessB} -->|"{書き込み}"| {DataStore}
```

---

## 3. データフロー説明

| データフロー | 送信元 | 受信先 | データ内容 | 説明 |
|---|---|---|---|---|
| {フロー名} | {送信元} | {受信先} | {データの内容・型} | {説明} |

---

## 4. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | {CR} | {YYYY-MM-DD} | 初版作成（SPO §4.2 から生成） |
