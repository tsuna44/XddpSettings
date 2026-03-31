---
applyTo: "**/変更設計書-*.md"
---

# xddp-tm-generate 実行ガイド

変更設計書（`変更設計書-*.md`）を開いているとき、または `/xddp-tm-generate` を呼び出したときに自動適用される。

## TM自動生成の2つの方法

### 方法1：Copilot Chatで生成（Markdown出力）

```
/xddp-tm-generate #変更設計書-CR-2024-031.md #スペックアウト-CR-2024-031.md
```

Copilot ChatがMarkdown形式のTMを生成する。

### 方法2：Pythonスクリプトで生成（Excel出力）

`03_Skills/Claude-Code/.claude/skills/xddp-tm-generate/tm_generate.py` を使用する。

```bash
# 変更設計書・スペックアウト・変更要求仕様書のパスを指定して実行
python tm_generate.py
```

スクリプト内の以下の変数を編集してから実行する：

```python
DESIGN_DOC  = "変更設計書-CR-YYYY-NNN.md"
SPECOUT_DOC = "スペックアウト-CR-YYYY-NNN.md"
CRS_DOC     = "変更要求仕様書-CRS-YYYY-NNN.md"
OUT_XLSX    = "TM-CR-YYYY-NNN-auto.xlsx"
```

## 出力の確認ポイント

- 全仕様番号に最低1つの●があるか
- スペックアウトの影響確認箇所に○があるか
- 日程・成果物管理カテゴリの仕様は●が空でも正常
