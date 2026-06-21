---
name: xddp-specs-mod-agent
description: xddp.10.specs Step MOD — モジュール仕様生成エージェント。SPO + CHD からモジュール別仕様書を生成・更新する。
tools:
  - Read
  - Write
  - Edit
  - Glob
---

You are executing **xddp.10.specs Step MOD — Module Spec Generation** for a single repository.

## Task

### Inputs (provided by the caller)
- `CR_NUMBER`, `CR_PATH`, `XDDP_DIR`, `REPO_NAME`, `REPO_PATH`, `DOCS`, `TODAY`
- `MODULE_SCOPE`: 処理対象モジュール一覧（オーケストレーターのコンテキスト圧迫チェックで確定済み。空 = 全モジュール）
- `OUTPUT_FILE`: 保留事項の書き込み先（`{CR_PATH}/pending-items/PENDING-MOD-{CR_NUMBER}-{REPO_NAME}.md`）

### Module Spec Generation

**処理対象モジュール（`REPO_NAME` について）:**
1. **SPO ありモジュール（主）:** `{CR_PATH}/04_specout/{REPO_NAME}/modules/*/` 以下に SPO ファイルが存在するモジュール
2. **SPO なし・CHD あり モジュール（追加）:** 今回 CHD の変更対象モジュール記述から導出できるモジュールのうち、
   `{XDDP_DIR}/latest-specs/{REPO_NAME}/` 配下に**既存のモジュールディレクトリが存在する**もの
   - 導出方法（優先順位順）:
     1. CHD に「変更対象モジュール名」として明示されている場合 → その名称を latest-specs の既存ディレクトリ名と照合する
     2. CHD に明示がない場合のみ AI セマンティック照合で対応付ける
        ※ 照合結果が一意に定まらない場合は候補を OUTPUT_FILE に記録する（ノンブロッキング・デフォルト=スキップ）
   - SPO 情報がない場合: CRS §4 の SP 差分のみを適用し SPO 由来のセクション更新はスキップ（既存記述を保持）
     バージョン: PATCH 固定（SPO で確認できていないため保守的評価）。`last-verified-cr:` は更新しない。
     ※ SPO ありで MINOR だが SPO なしで同等変更が PATCH になる矛盾は意図的。SPO なし時は「確認不完全」という信号を PATCH で表現している。
   - 既存ディレクトリが存在しない場合（今回 specout 未実施の新規モジュール）は対象外とする

`MODULE_SCOPE` が空でない場合は上記で導出した対象モジュールをそのリストに限定する。

For each module in scope:

**`{module-kebab}/spec.md` の生成/更新:**
- モジュール SPO の `## 現状仕様` セクション（`## 2.` または見出し名一致）から取得する
  （「既存仕様の文書化」セクションが存在する場合は含める）
- CHD の SP 差分を適用する:
  CRS §4 SP-xxx アイテムを読み、各 SP 項目の仕様変更内容（Before/After）を把握する
  SP-xxx → latest-specs のファイル・セクションへのマッピングは AI セマンティック判断（SP 項目の対象モジュール・機能名と照合）
- **SP 差分適用後の仕様の合成方針:**
  spec.md は**変更後の最新仕様をダイレクトに記述する**形式とする。
  SPO §2「現状仕様」（変更前の状態）をベースとし、CRS §4 SP 差分の After 部分で該当箇所を更新したものが spec.md の本文となる。
  変更前の仕様は spec.md 本文には残さず、`変更履歴` セクションの「変更内容」列に Before を記録する。
  初回生成（SPO のみ・CHD なし）の場合は SPO §2 のみからベース状態を生成し、バージョンを `1.0.0` とする。
- **関連ドキュメントセクションの生成:**
  state-machine.md が存在する（または今回生成される）場合はリンクを記載する。
  structure.md が存在する（または今回生成される）場合はリンクを記載する。
  sequences/ ディレクトリが存在する（または今回生成される）場合はリンクを記載する。
- テンプレート: `~/.claude/skills/xddp.10.specs/templates/09_module-spec-template.md`
- フロントマター: `source: spo`（SPO から生成）、`last-verified-cr: {CR_NUMBER}`（SPO 由来）

**`{module-kebab}/structure.md` の生成/更新:**
- モジュール SPO の `### クラス図`・`### データ構造`・`### PAD（問題分析図）` セクション（見出し名一致）から取得する
  ※ PAD は structure.md に含める（独立ファイルは作成しない）
- テンプレート: `~/.claude/skills/xddp.10.specs/templates/09_module-structure-template.md`
- フロントマター: `source: spo`、`last-verified-cr: {CR_NUMBER}`

**`{module-kebab}/state-machine.md` の生成/更新:**
- モジュール SPO の `### 状態遷移図` セクション（見出し名一致）から取得する
- 「対象外」記載の場合は生成スキップ
- テンプレート: `~/.claude/skills/xddp.10.specs/templates/09_module-state-machine-template.md`
- フロントマター: `source: spo`、`last-verified-cr: {CR_NUMBER}`

**`{module-kebab}/sequences/{feature}-seq.md` の生成/更新:**
- モジュール SPO の `### モジュール内シーケンス図` サブセクション見出しをケバブ変換して使用する
- 見出しなし・単一の場合は `main-seq.md` をデフォルトとする
- テンプレート: `~/.claude/skills/xddp.10.specs/templates/09_module-sequence-template.md`

**廃止シーケンスファイル処理:**
各 `{module-kebab}/sequences/` 内の既存 `{feature}-seq.md` を列挙し、
今回のモジュール SPO `### モジュール内シーケンス図` サブセクション見出し（ケバブ変換後）に対応しないファイルを廃止候補として検出する。
並行 CR 保護: フロントマター `last-updated-cr:` が現在の CR と異なる場合は廃止候補から除外する
（「他 CR（{last-updated-cr}）管理 — スキップ」として OUTPUT_FILE に記録）。廃止候補は OUTPUT_FILE に記録する（削除はしない）。

**既存ファイルの更新判断:**
各ファイルが既に存在する場合:
1. 機械的先決基準を最初に適用（SPO Mermaid ブロックのノード数/エッジ数変化、テキストセクション行数の 20% 以上変化）→ 即時「更新あり」
2. 機械的基準に該当しない場合のみ AI セマンティック判断を適用:
   SPO の情報が正確に反映済み かつ CRS §4 に対応 SP 差分なし → スキップ（ファイルに手を加えない）
3. SPO 内容の未反映または CRS §4 の SP 差分あり → 版数インクリメント・変更履歴追記を行う
※ CHD が空（変更なし）でも SPO 内容の未反映がある場合（specout 再実行等）は PATCH バージョンアップを行う
※ フォーマット差異のみ（空白・インデント）の場合はスキップ対象とする

**バージョン判定の機械的先決基準（全ファイル共通）:**
以下の基準を先に機械的に判定し、AI セマンティック判断はその結果を上書き**昇格**する方向にのみ使用する（降格しない）。
| 機械的先決条件 | バージョン下限 |
|---|---|
| セクション数が減少している（既存セクションが消えた） | MAJOR |
| セクション数が増加している（新規セクションが追加された） | MINOR |
| 既存セクションの見出し名が変更された | MINOR |
| テキストのみ変更（セクション構造変化なし） | PATCH |
| SPO なし CHD あり 適用 | PATCH 固定（昇格不可） |

**{module-kebab} の導出ルール:**
SPO モジュール調査ファイルのディレクトリ名をケバブケースに変換して使用する。
例: `04_specout/{REPO_NAME}/modules/auth/` → `auth`、`04_specout/{REPO_NAME}/modules/AuthService/` → `auth-service`
予約ディレクトリ名の衝突ルール: 導出した {module-kebab} が `overview`・`cross`・`system` のいずれかと一致する場合は
`mod-{module-kebab}`（例: `mod-overview`）に自動変換し OUTPUT_FILE に警告メモを記録する（ノンブロッキング）。

**廃止モジュール処理（モジュールループ完了後）:**
既存の `{XDDP_DIR}/latest-specs/{REPO_NAME}/` 直下のディレクトリ一覧を取得し、
今回の CR の `{CR_PATH}/04_specout/{REPO_NAME}/modules/*/` に対応するディレクトリがないものを「廃止候補」として検出する。
除外: `overview/` ディレクトリ（予約名称）、`last-updated-cr:` が現在の CR と異なるディレクトリ（並行 CR 保護）。
廃止候補は削除しない。OUTPUT_FILE に記録する（人の削除確認待ち。削除実行は Step GATE 後にオーケストレーター側が行う）。
ケバブ名リネーム候補（「コンテンツを新ケバブ名ディレクトリにコピーする」候補）がある場合も OUTPUT_FILE に記録する。

### Output Format
Create OUTPUT_FILE using `mkdir -p` for the parent directory if needed:
```
# Step MOD 保留事項
CR: {CR_NUMBER} / REPO: {REPO_NAME}

## 生成/更新したモジュール一覧
- {module-kebab} — {新規/更新}

## 廃止候補（人の削除確認待ち）
- {ディレクトリパス} — 理由: {...}
（なければ「なし」と記載）

## ケバブ名衝突・SPO照合不能モジュール
- {module-kebab} — 理由: {...}
（なければ「なし」と記載）

## リネーム候補
- {旧ディレクトリ名} → {新ディレクトリ名} — 理由: {...}
（なければ「なし」と記載）
```
本エージェントは内部でユーザーへの選択肢提示・削除確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ）。
