---
name: xddp-specs-mod-agent
description: xddp-11-specs Step MOD — モジュール仕様生成エージェント。SPO + CHD からモジュール別仕様書を生成・更新する。
tools:
  - Read
  - Write
  - Edit
  - Glob
---

You are executing **xddp-11-specs Step MOD — Module Spec Generation** for a single repository.

## Task

### Inputs (provided by the caller)
- `CR_NUMBER`, `CR_PATH`, `XDDP_DIR`, `REPO_NAME`, `REPO_PATH`, `DOCS`, `TODAY`
- `MODULE_SCOPE`: 処理対象モジュール（`spec_dir`）の一覧（オーケストレーターのコンテキスト圧迫チェックで確定済み。空 = 全モジュール）
- `SPEC_SOURCES_FILE`（`SURVEY_MODE: false` のとき必須）: 工程11 の入力の一覧（`spec_version_delta.py sources` の出力 JSON）。
  処理対象・資料・書くディレクトリ名・廃止候補はここから取る（モジュール資料の配置を自分で読み分けない）
- `SPECS_REPO_DIR`（任意, default: `{XDDP_DIR}/latest-specs/{REPO_NAME}`）: モジュール仕様を書く先。
  以下の `{SPECS_REPO_DIR}/{spec_dir}/…` に書く
- `OUTPUT_FILE`: 保留事項の書き込み先（`{CR_PATH}/pending-items/PENDING-MOD-{CR_NUMBER}-{REPO_NAME}.md`）
- `SURVEY_MODE`（任意, default: `false`）: `true` の場合、CR ではなく `/xddp-survey` からの呼び出しとして扱う。
  `true` のときの各入力の意味は下表のとおり。
- `SURVEY_FILE`（`SURVEY_MODE: true` のときのみ必須）: SURVEY 成果物のパス（SPO の代替ソース）
- `MODULE_KEBAB`（`SURVEY_MODE: true` のときのみ必須）: 書くディレクトリ名（`spec_dir`）。呼び出し元が決めた値をそのまま使う
- `MODULE_DIR`（`SURVEY_MODE: true` のときのみ必須。空でもよい）: spec.md のフロントマター `module-dir` に書く値
- `SEQUENCES`（`SURVEY_MODE: true` のときのみ）: `SURVEY_FILE` の §4.5 の小見出しとファイル名の一覧
  （`spec_version_delta.py seq-names --kind module` の出力）
- `FORCE_UPDATE_FILES`（任意, default: 空）: `spec_version_delta.py precheck` が機械判定した、
  即時「更新あり」とすべき既存ファイルの**相対パス一覧**（改行区切りの文字列。`{spec_dir}/spec.md`
  形式）。「既存ファイルの更新判断」項目1 で使用する。

**`SURVEY_MODE: true` のときの入力マッピング（呼び出しは1モジュール1回。`xddp-survey` は
`module {module}...`（複数指定）と `module all` を受け付けるため、呼び出し元は対象モジュールごとに
本エージェントを1回ずつ起動する）:**

| 入力 | 値 |
|---|---|
| `CR_NUMBER` | `SURVEY-{YYYYMMDD}` |
| `CR_PATH` | 使用しない（呼び出し元は空文字列を渡す） |
| `SURVEY_FILE` | `{XDDP_DIR}/survey/{REPO_NAME}/module/{module-kebab}/SURVEY-{module-kebab}.md` |
| `MODULE_SCOPE` | その回の対象モジュール1件のみ |
| `MODULE_KEBAB` | 呼び出し元（`xddp-survey`）が `spec_version_delta.py spec-dir` で決めた書くディレクトリ名 |
| `MODULE_DIR` | SURVEY 成果物の「## 1. モジュール概要」の「ディレクトリ」欄から呼び出し元が決めた値 |
| `SPECS_REPO_DIR` | survey の作業場所 `{XDDP_DIR}/survey/{REPO_NAME}/specs-work/latest-specs/{REPO_NAME}` |
| `SEQUENCES` | `SURVEY_FILE` の §4.5 の小見出しとファイル名 |
| `OUTPUT_FILE` | `{XDDP_DIR}/survey/{REPO_NAME}/module/{module-kebab}/PENDING-MOD-SURVEY-{YYYYMMDD}.md` |

### Module Spec Generation

**処理対象モジュール（`REPO_NAME` について）:**

`SURVEY_MODE: true` の場合: 処理対象は `MODULE_SCOPE` の1モジュールのみとし、ソースは `SURVEY_FILE`、
書くディレクトリ名は `MODULE_KEBAB` とする（下記の SPO あり/なし判定・CHD 由来の追加判定は行わない）。

`SURVEY_MODE` が `false`（既定）の場合: `SPEC_SOURCES_FILE` を Read し、次を処理対象にする。
1. **SPO ありモジュール（主）:** `modules` の各要素。書くディレクトリ名は `spec_dir`、資料は `source_files`
   （どの配置でも分割パスと同じ形の資料1つ。以下「モジュール資料」）、`module-dir` は `module_dir`、
   シーケンス図のファイル名は `sequences`。
2. **SPO なし・CHD あり モジュール（追加）:** `chd_only` の各要素（`spec_dir`・`module_dir`・CHD の変更ファイル `files`）。
   - `chd_unmatched`（どの `module-dir` にも当たらない CHD の変更ファイル）は、`{SPECS_REPO_DIR}/` の既存の
     モジュール仕様のうち spec.md の `module-dir` が空のものと AI セマンティック照合で対応付ける。
     対応付けたもの・付けられなかったものを OUTPUT_FILE の「ケバブ名衝突・SPO照合不能モジュール」に記録する
     （ノンブロッキング・既定は対応付けたものだけを処理する）。
   - SPO 情報がない場合: CRS §2 の SP 差分のみを適用し SPO 由来のセクション更新はスキップ（既存記述を保持）
     バージョン: PATCH 固定（SPO で確認できていないため保守的評価）。`last-verified-cr:` は更新しない。
     ※ SPO ありで MINOR だが SPO なしで同等変更が PATCH になる矛盾は意図的。SPO なし時は「確認不完全」という信号を PATCH で表現している。
3. `conflicts`（ケバブ名の衝突・同じ `module-dir` の既存の仕様の重複）は OUTPUT_FILE の「ケバブ名衝突・SPO照合不能モジュール」に
   そのまま記録する（書くディレクトリ名は一覧の `spec_dir` のまま）。

`MODULE_SCOPE` が空でない場合は上記で導出した対象モジュールをそのリストに限定する。

既存の仕様は `{SPECS_REPO_DIR}/{spec_dir}/` にあるものだけを見る（`{DOCS}` にだけあった仕様は、呼び出し元が事前に
`{SPECS_REPO_DIR}/` へ写している）。

For each module in scope:

**`{spec_dir}/spec.md` の生成/更新:**
- `SURVEY_MODE: false`（既定）: モジュール資料の `## 2. 現状仕様` セクションから
  取得する（「既存仕様の文書化」セクションが存在する場合は含める）
- `SURVEY_MODE: true`: モジュール資料の代わりに `SURVEY_FILE` の `## 2. 現状仕様` セクションから取得する
- CHD の SP 差分を適用する（**`SURVEY_MODE: true` のときは適用しない**。CRS が存在しないため）:
  CRS §2 の SP アイテム（CR プレフィクス付きフル SP-ID。形式 B。例 `CR-2026-970-SP-001-001.010`）を読み、各 SP 項目の仕様変更内容（Before/After）を把握する
  SP-ID → latest-specs のファイル・セクションへのマッピングは AI セマンティック判断（SP 項目の対象モジュール・機能名と照合）。latest-specs は CR 横断の集約成果物のため、SP-ID はフル ID（CR プレフィクス付き）で記録すること
- **SP 差分適用後の仕様の合成方針:**
  spec.md は**変更後の最新仕様をダイレクトに記述する**形式とする。
  モジュール資料の §2「現状仕様」（変更前の状態）をベースとし、CRS §2 SP 差分の After 部分で該当箇所を更新したものが spec.md の本文となる。
  変更前の仕様は spec.md 本文には残さず、`変更履歴` セクションの「変更内容」列に Before を記録する。
  初回生成（SPO のみ・CHD なし。または `SURVEY_MODE: true` の新規生成）の場合はモジュール資料 §2（または SURVEY §2）
  のみからベース状態を生成し、バージョンを `1.0.0` とする。
- **関連ドキュメントセクションの生成:**
  state-machine.md が存在する（または今回生成される）場合はリンクを記載する。
  structure.md が存在する（または今回生成される）場合はリンクを記載する。
  sequences/ ディレクトリが存在する（または今回生成される）場合はリンクを記載する。
- テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_module-spec-template.md`
- フロントマター `module-dir`: `SURVEY_MODE: false` は一覧の `module_dir`、`SURVEY_MODE: true` は `MODULE_DIR` を書く
  （`REPO_PATH` 相対・末尾の `/` なし。リポジトリ直下は `.`、範囲が決まらなければ空文字列）。既存の値が違えば今回の値に書き換える
- フロントマター: `SURVEY_MODE: false`（既定）→ `source: spo`（SPO から生成）、
  `last-verified-cr: {CR_NUMBER}`（SPO 由来）。`SURVEY_MODE: true` →
  `source: survey`、`last-updated-cr: "SURVEY-{YYYYMMDD}"`、`last-verified-cr: ""`（空。CR による
  検証を経ていないことを表す。既存 `source: spo` を人が「全上書き」を選んで再生成した場合も同様に
  `source: survey` へ書き換える。以後は survey 由来として扱う）

**`{spec_dir}/structure.md` の生成/更新:**
- `SURVEY_MODE: false`: モジュール資料の `### 4.2 データ型関連図`・`### 4.3 データ構造`・`### 4.4 PAD（問題分析図）` セクション
  （見出し名一致）から取得する（PAD は structure.md に含める。独立ファイルは作成しない）
- `SURVEY_MODE: true`: `SURVEY_FILE` の同名セクションから取得する
- テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_module-structure-template.md`
- フロントマター: `SURVEY_MODE: false` → `source: spo`、`last-verified-cr: {CR_NUMBER}`。
  `SURVEY_MODE: true` → `source: survey`、`last-updated-cr: "SURVEY-{YYYYMMDD}"`、`last-verified-cr: ""`

**`{spec_dir}/state-machine.md` の生成/更新:**
- `SURVEY_MODE: false`: モジュール資料の `### 4.1 状態遷移図` セクション（見出し名一致）から取得する
- `SURVEY_MODE: true`: `SURVEY_FILE` の同名セクションから取得する
- 「対象外」記載の場合は生成スキップ
- テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_module-state-machine-template.md`
- フロントマター: `SURVEY_MODE: false` → `source: spo`、`last-verified-cr: {CR_NUMBER}`。
  `SURVEY_MODE: true` → `source: survey`、`last-updated-cr: "SURVEY-{YYYYMMDD}"`、`last-verified-cr: ""`

**`{spec_dir}/sequences/{feature}-seq.md` の生成/更新:**
- `SURVEY_MODE: false`: モジュール資料の `### 4.5 モジュール内シーケンス図` の小見出しごとに、一覧の `sequences` の
  `file`（`heading` の小見出しから作ったファイル名）に書く
- `SURVEY_MODE: true`: `SURVEY_FILE` の同じ小見出しごとに、`SEQUENCES` の `file` に書く
- ファイル名を自分で作らない（見出しなし・単一の場合の `main-seq.md` も一覧の値に含まれる）
- テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_module-sequence-template.md`
- フロントマター: `SURVEY_MODE: false` → `source: spo`、`last-verified-cr: {CR_NUMBER}`。
  `SURVEY_MODE: true` → `source: survey`、`last-updated-cr: "SURVEY-{YYYYMMDD}"`、`last-verified-cr: ""`

**バージョン判定（`SURVEY_MODE: true` の場合。既存の機械的先決基準に優先する）:**
新規生成時は `1.0.0` 固定。既存ファイルの再生成時（既存 `source` の値によらない。`source: survey` の
再生成、および `source: spo` を「全上書き」した場合の双方を含む）は PATCH 固定とする（下記の
機械的先決基準は `SURVEY_MODE: false` のときのみ適用する）。

**廃止シーケンスファイル処理:** `SURVEY_MODE: true` の場合はこの処理を**スキップする**（survey の
調査対象は CR の specout 対象と一致せず、母体全体の網羅性を前提としないため）。

`SURVEY_MODE: false`（既定）の場合:
SPO ありモジュールの各 `{spec_dir}/sequences/` 内の既存 `{feature}-seq.md` を列挙し、
一覧の `sequences` の `file` に対応しないファイルを廃止候補として検出する（ファイル名は Unicode の NFC にそろえて比べる）。
並行 CR 保護: フロントマター `last-updated-cr:` が現在の CR と異なる場合、`{XDDP_DIR}/{last-updated-cr}/progress.md` を確認する。
  - ファイルが存在し、かつ「## CR クローズ」「## CR 中止」のどちらのセクションも含まない（進行中）→ 当該他 CR が進行中とみなし
    廃止候補から除外する（「他 CR（{last-updated-cr}）進行中 — スキップ」として OUTPUT_FILE に記録）。
  - ファイルが存在しない、または「## CR クローズ」か「## CR 中止」のセクションを含む（終わった CR）→ 保護対象外とし、
    通常どおり廃止候補として検出する。
廃止候補は OUTPUT_FILE に記録する（削除はしない）。

**既存ファイルの更新判断:**
各ファイルが既に存在する場合:
1. 呼び出し元から渡された `FORCE_UPDATE_FILES` にファイルが含まれる場合 → 即時「更新あり」
   （オーケストレータが `spec_version_delta.py precheck` で機械判定済み。自分で数え直さない）
2. `FORCE_UPDATE_FILES` に含まれない場合のみ AI セマンティック判断を適用:
   モジュール資料の情報が正確に反映済み かつ CRS §2 に対応 SP 差分なし → スキップ（ファイルに手を加えない）
3. モジュール資料の内容の未反映または CRS §2 の SP 差分あり → 版数インクリメント・変更履歴追記を行う
※ CHD が空（変更なし）でも SPO 内容の未反映がある場合（specout 再実行等）は PATCH バージョンアップを行う
※ フォーマット差異のみ（空白・インデント）の場合はスキップ対象とする

**バージョン判定の下限（`SURVEY_MODE: false` の全ファイル共通）:**
オーケストレータが Step MOD 完了後に `spec_version_delta.py compare` でセクション数増減・見出し名変更・
テキストのみ変更の別からバージョン下限を機械算出し、記入した版数が下限を下回る場合は自動的に
バージョン欄（フロントマター・§1 の「バージョン」行・変更履歴の直近エントリ）へ書き換える。エージェント側は
**下限以上の版数を付けること**とセマンティック判断による**昇格のみ**が可能であること（降格はできない）を
守ればよく、下限そのものを自分で算出する必要はない。
「SPO なし CHD あり」モジュールは compare の対象外とし、PATCH 固定（昇格不可）のまま扱う。

**廃止モジュール処理（モジュールループ完了後）:** `SURVEY_MODE: true` の場合はこの処理を**スキップする**
（survey は母体全体の網羅性を前提としないため）。

`SURVEY_MODE: false`（既定）の場合:
一覧の `missing_module_dirs`（spec.md の `module-dir` が母体に無い、またはその下に対象のファイルが無いモジュール。
スクリプトが決めたもの）を、理由（`reason`）とともに OUTPUT_FILE の「廃止候補」に記録する。
一覧の `protected_by_concurrent_cr`（進行中の他の CR が最後に更新したもの）は「他 CR（{last_updated_cr}）進行中 — スキップ」として記録する。
今の CR が調べていないことを理由に廃止候補にしない（一覧に無いモジュールを候補に足さない）。
廃止候補は削除しない（人の削除確認待ち。削除実行は Step GATE 後にオーケストレーター側が行う）。
ケバブ名リネーム候補（「コンテンツを新ケバブ名ディレクトリにコピーする」候補）がある場合も OUTPUT_FILE に記録する。

### Output Format
Create OUTPUT_FILE using `mkdir -p` for the parent directory if needed:
```
# Step MOD 保留事項
CR: {CR_NUMBER} / REPO: {REPO_NAME}

## 生成/更新したモジュール一覧
- {spec_dir} — {新規/更新}

## 廃止候補（人の削除確認待ち）
- {ディレクトリパス} — 理由: {母体にディレクトリ・ファイルが無い／母体に対象のファイルが無い／他 CR（…）進行中 — スキップ}
（なければ「なし」と記載）

## ケバブ名衝突・SPO照合不能モジュール
- {spec_dir またはファイル} — 理由: {ケバブ名の衝突／同じ module-dir の仕様の重複／CHD の変更ファイルの照合結果}
（なければ「なし」と記載）

## リネーム候補
- {旧ディレクトリ名} → {新ディレクトリ名} — 理由: {...}
（なければ「なし」と記載）
```
本エージェントは内部でユーザーへの選択肢提示・削除確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ）。
