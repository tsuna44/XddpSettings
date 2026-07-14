# XDDP ツール解析レポート：スキル間不整合・無駄な記述・効率化提案

- **調査日:** 2026-07-14
- **対象:** `ClaudeCode/.claude/` 配下の全スキル（24件）・エージェント（16件）・設定テンプレート・`setup.sh`（合計約14,000行）
- **調査方法:** 全 SKILL.md・主要エージェント定義・設定テンプレートの通読、および grep による参照整合性の機械照合（行番号参照・入力契約・設定キー消費者・デプロイ状態）
- **総評:** xddp.common への共通化、「config を1回読んで配る」設計、ファイル経由ハンドオフなど全体構造は整っている。一方で、**動作に影響する不整合 6件、整合性の問題 4件、大きな効率化余地 5系統** を検出した。

---

## A. 動作に影響するスキル間の不整合（優先度：高）

### A-1. `/xddp.review` に `spec` 引数の入口がなく、xddp.11.specs の案内が機能しない

- `xddp.11.specs/SKILL.md` Step GATE（L358-359 付近）は「`/xddp.review` で `DOCUMENT_TYPE: SPEC` を指定」と案内する。
- しかし `xddp.review/SKILL.md` のマッピングテーブル（L24-32）に `spec` 行がない（`analysis|req|specout|arch|design|test` のみ）。
- `spec` と入力すると「other = ファイルパス扱い」に落ち、ファイル不存在エラーで停止する。
- 1a テーブル（L67-77）には `SPEC`/`PLAN` 行が定義済みなのに、引数解決からの到達経路がない。

**提案:** `xddp.review` の解決テーブルに `spec` 行を追加する（TARGET_FILES の解決方法＝latest-specs 配下のファイル指定 or バッチ指定を定義）。あわせて argument-hint も更新する。

### A-2. setup.sh の削除リストに `skills/xddp.09.specs` がなく、旧スキルが残存デプロイされている

- `setup.sh` の `OLD_XDDP_DIRS` には `skills/xddp.10.specs` はあるが `skills/xddp.09.specs` がない。
- **実機確認済み:** `~/.claude/skills/xddp.09.specs/` が残存しており、`/xddp.09.specs` と `/xddp.11.specs` が同一説明で両方起動可能な状態。
- 誤って旧スキルを起動すると、リナンバー前の旧仕様の工程が走る。

**提案:** `OLD_XDDP_DIRS` に `skills/xddp.09.specs` を追加し、`setup.sh` を再実行する。

### A-3. `/xddp.10.test-run` の `run_number` が常に 1 で、再実行時に TRS が上書きされる

- `xddp.10.test-run/SKILL.md:56` で `run_number = 1` と固定初期化するのみ。既存 `TRS-{CR}-0N.md` から次番号を導出するロジックがない。
- 差し戻し（🔁）→再実行のフローは Step B で明示されているのに、再実行のたびに `TRS-{CR}-01.md` を上書きし実行履歴が消える。
- エージェント側（`agents/xddp-test-runner-agent.md:27`）は `RUN_NUMBER (1, 2, 3, ...)` を想定しており、採番責務が宙に浮いている。
- `TRS-{CR}-0{run_number}` 形式は run 10 で `-010` になり破綻する。

**提案:** Step A 冒頭で `10_test-results/{repo}/TRS-{CR}-*.md` を glob し、最大番号+1 を `run_number` とする。ファイル名はゼロ埋め2桁（`-{run_number:02d}`）と明記する。

### A-4. xddp-reviewer の入力契約に `TARGET_FILES`（複数形）が未定義

- `xddp.11.specs/SKILL.md:304`（Step REV）はバッチレビューで `TARGET_FILES: [...]` を渡す。
- `agents/xddp-reviewer.md` の Input Contract（L268-275）は `TARGET_FILE`（単数）のみ定義。レビューテンプレートも単一ファイル前提。
- 契約外の暗黙動作に依存している。

**提案:** xddp-reviewer の Input Contract に `TARGET_FILES`（optional・SPEC バッチレビュー用）を追加し、複数ファイル時の出力形式（ファイルごとのセクション分け等）を明記する。

### A-5. `/xddp.status` の未定義変数 `REPOS_KEYS`（自己文書化された既知バグ）

- `xddp.status/SKILL.md:115`（Section 5「CR間修正ファイル衝突チェック」）が `REPOS_KEYS` を参照するが、このスキルは config から `XDDP_DIR` しか抽出していない。
- L53 に「既存バグとして存在するがスコープ外」と注記して放置されている。

**提案:** 冒頭の config 読み込みで `REPOS:` → `REPOS_KEYS` も抽出する（1行修正）。注記も削除する。

### A-6. xddp-specout-agent の config 解決がスキル群と不一致

- スキル側（CR Resolution）は `xddp.config.md` を**上方探索**するが、`agents/xddp-specout-agent.md:46` は「current working directory に存在するか」のみを見る。
- サブディレクトリから起動した場合、スキルは設定を読めてもエージェントはデフォルト値（`SPECOUT_MAX_AFFECTED_FILES: 20` 等）で動く可能性がある。
- `SPECOUT_MAX_AFFECTED_FILES`・`SPECOUT_DIAGRAM_LEVEL`・`SPECOUT_SEQUENCE_LEVELS` の3キーだけエージェント側の独自読み込みに依存しており、xddp.common の「1回読んで全て配る」方針と不整合。

**提案:** この3キーを CR Resolution の標準バンドルに追加し、`xddp.04.specout` からエージェント呼び出しパラメータとして渡す。エージェント側の config 読み込みはフォールバックに格下げ（または削除）する。

---

## B. 整合性の問題（優先度：中）

### B-1. カバレッジ基準の記述矛盾

- `MIN_COVERAGE`（デフォルト80%）導入後も、config テンプレート（`xddp.01.init/templates/xddp.config.md` L300-302）は「C0/C1 = カバレッジ **100%**」と定義。
- `agents/xddp-reviewer.md:133` の TSP チェック5も「C0 and C1 100% coverage is achievable」を要求。
- 実際の合格判定（MIN_COVERAGE 以上）と矛盾した基準でレビューされる。

**提案:** TEST_COVERAGE_TARGET の説明を「カバレッジの**種別**（C0=ステートメント / C1=ブランチ）」に改め、閾値は MIN_COVERAGE が担うことを明記。reviewer の TSP チェック5も「MIN_COVERAGE 以上を達成可能か」に修正する。

### B-2. Review Loop の Step 0 が未取得の変数を参照

- `xddp.common/SKILL.md:134-136`：Step 0 が `max_rounds = 0` を判定するが、`max_rounds` を config から読むのは Step 1。手順の順序が逆。

**提案:** Step 0 と Step 1 を入れ替える（config 読み込み → 0 判定）。

### B-3. テンプレートファイル名が工程リナンバー前のまま

| スキル（工程） | 成果物ディレクトリ | テンプレート名（旧番号のまま） |
|---|---|---|
| xddp.09.test（工程9） | `09_test-spec/` | `07_test-specification-template.md` |
| xddp.10.test-run（工程10） | `10_test-results/` | `08_test-results-template.md` |
| xddp.11.specs（工程11） | `latest-specs/` | `09_overview-*` など9ファイル |

動作はするが、「スキル番号＝成果物ディレクトリ番号」という規約（CLAUDE.md ステップ番号体系）に反し混乱の元。

**提案:** テンプレートを `09_`/`10_`/`11_` にリネームし、参照している SKILL.md・エージェント定義を同時更新する。setup.sh の削除リストに旧名を追加する。

### B-4. 未使用の定義・読み込み（デッドコード）

- `xddp.common/SKILL.md` の「## Detect Test Framework」（L334-353）：**どのスキル・エージェントからも参照されていない**（grep で利用箇所ゼロ）。全スキルが毎回 common を読むため純粋なコンテキスト浪費。
- `xddp.07.code/SKILL.md:29` の `Read TEST_FRAMEWORK_REPOS:`：以降一度も使用されない（コーディング工程にテストFWは不要）。
- `xddp.10.test-run/SKILL.md:33` の同読み込み：runner agent へ渡しておらず未使用（使用しているのは xddp.09.test のみ）。
- `xddp.review` の 1a テーブル `SPEC`/`PLAN` 行：引数から到達不能（A-1 の修正とセットで `SPEC` は活かす）。

**提案:** 「Detect Test Framework」を削除（将来必要なら復活はプラン経由）。07.code / 10.test-run の未使用 Read 行を削除。

---

## C. 無駄な記述・効率化提案（保守性・コンテキスト効率）

### C-1. ハードコード行番号参照（28箇所）が広範囲に陳腐化【最重要の保守性問題】

他ファイル・自ファイルの行番号を直接記述する箇所が 28箇所あり、照合の結果**多くが既にズレている**：

| 記述箇所 | 主張している行番号 | 実際の行番号 |
|---|---|---|
| `xddp.05.arch/SKILL.md:44,85,102` | ALTERNATIVES_TASK は147行目 | 157行目 |
| `xddp.06.design/SKILL.md:149-151,207-208` | 詳細条件文は148,150,151行 | 156,158,159行 |
| 同上 | 簡略条件文は190,192,193行 | 213,215,216行 |
| `xddp.close/SKILL.md:275` | PULLED_FILES は225行目 | 230行目 |
| `xddp.11.specs/SKILL.md:470` | SPECOUT_MODULES は111行目 | 113行目 |
| `xddp.11.specs/SKILL.md:461-464` | promote-agent 56〜65/72〜78/80〜87行目 | いずれも数行ズレ |
| `xddp.04.specout/SKILL.md:77` | HAS_CROSS 降格は「292 付近」 | 305行目 |

AI が実行時にこれらを信じて誤った行を読む・照合に失敗するリスクがある。`xddp.feedback` の参照（`xddp.common/SKILL.md:67-90` 等）は現時点で正確だが、同じ理由でいずれ壊れる。

**提案:** 行番号参照を全廃し、見出し名・変数名参照に置換する（例：「Step A-cross の `If no inter-repo dependencies found` 行」「`## Discover CHD Files` プロシージャ」）。CLAUDE.md の開発ルールに「SKILL.md/エージェント定義内で行番号による相互参照を禁止する（見出し・変数名で参照する）」を追記する。

### C-2. プランレビュー経緯のメタ注記がプロンプトを肥大化させている

- 特に `xddp.feedback/SKILL.md`（465行）は本文の3〜4割が「プランレビューN回目 指摘#X対応」「初版時点の制約は本改訂で解消された」等の**変更経緯の記録**。指摘番号はレビューファイルを見ないと意味不明で、実行指示としては純粋なノイズ。起動のたびにコンテキストを消費する。
- 同種の長文注記：`xddp.common` Human Review Gate「理由（設計判断の記録）」、`xddp.05.arch`/`xddp.06.design` の `_BASE` 変数注記、`xddp.close` の実装コメント等。

**提案:** 経緯・設計判断は plans/ 配下（承認済みプラン＝ADR相当）に既に残っているため、SKILL.md 側は「なぜそうするか」1行だけ残して削減する。xddp.feedback は 465行 → 250行程度まで圧縮できる見込み。

### C-3. cross レビュー・最終レビューパスのボイラープレート重複

- **cross 成果物レビュー:** `04.specout` Step A2-cross・`05.arch` Step B-cross・`06.design` Step B-cross は「reviewer 呼び出し → 🔴/🟡ならインライン修正 → 再読 → 残存🔴警告 →『サイズが小さく1パスで収束』注記」まで含めてほぼ同一。
  → xddp.common に `## Cross Artifact Review`（パラメータ: DOCUMENT_TYPE / TARGET_FILE / REFERENCE_FILES / OUTPUT_FILE / NEXT_DOCUMENT_TYPE）として抽出可能。
- **「If CHANGED: 最終AIレビュー1回」ブロック**が 02/03/04/05/06/09 の6スキルで重複。Human Review Gate の後続手順として common 化できる（reviewer パラメータを引数で渡す形）。
- `xddp.05.arch` の `ARCH_AGENT_PATHS` は「変更時は grep して3箇所同期させること」という同一警告文が3回コピーされている。共通化すれば警告ごと不要になる。

### C-4. CR非依存スキルの config 読み込みロジック重複

- `xddp.status` / `xddp.codemap` / `xddp.update-knowledge` / `xddp.fill-rulebook` がそれぞれ「xddp.config.md を上方探索してキー抽出」を微妙に異なる文言で再実装。
- xddp.common に CR 解決を含まない `## Load Config` を切り出せば統一でき、A-5（status の REPOS_KEYS バグ）も構造的に解消する。
- なお `xddp.plan-review/SKILL.md:39` だけ「cwd 直下のみ・上方探索しない」。意図的（ツール開発リポジトリでの実行想定）なら理由を1行明記すべき。

### C-5. その他の小さな無駄

- `xddp.status` のセクション番号が物理順と不一致（1→2→3→2.4→2.5→4→4.5→5）で、それを説明する「今後の編集者向け注意」注記まで付いている。リナンバーすれば注記ごと消せる。
- `xddp.01.init` は Step 1 が欠番（0 → 0.5 → 2）。
- `xddp.excel2md/SKILL.md:23` の Excel 読み込みが「python3 -c "import openpyxl; ..." or similar」と場当たり的。md2excel は `crs_md2excel.py` でフォーマットを一元化しているのに、逆変換だけ AI 任せで精度がセッション依存。対になる `crs_excel2md.py` のスクリプト化を推奨（USDM 構造は固定のため機械変換可能）。
- `agents/xddp-reviewer.md:157` の「### SPEC」チェックリストだけ「## Output Format」見出しの下に紛れ込んでおり、他のチェックリスト群（## Review Checklists by Document Type）から分離している。移動すべき。
- `xddp.common` Review Loop の `FIX_STRATEGY` が「Input パラメータ（default: balanced）」と「step 1 で config から自動読み込み」の両方で説明されており、どちらが正か曖昧（自動読み込みに一本化推奨）。
- `xddp.08.verify` Step 0 の Else 分岐は `IMPL_ORDER = REPOS_KEYS` だが、`xddp.07.code` は `AFFECTED_REPOS` を使う。現状は等価（FILTER_BY_SPO=false のため）だが表記を揃えるべき。
- `xddp.07.code` Step A-Pre の「Already loaded in Step 0. `CODING_RULES` and `RULEBOOK_CONTEXT` (shared) are available.」は誤り。Step 0 で読むのは CODING_RULES のみで、RULEBOOK_CONTEXT は Step A のループ内でロードされる。Step B 内にも per-repo のロード指示がなく、Step A の残存値に暗黙依存している。

---

## 推奨する対応順序

| 優先度 | 項目 | 内容 |
|---|---|---|
| 1（即修正・バグ） | A-2 | setup.sh に `skills/xddp.09.specs` 追加＋再実行 |
| 1 | A-5 | xddp.status で `REPOS:` を抽出（1行） |
| 1 | A-3 | run_number の採番ロジック追加 |
| 1 | A-1 | xddp.review に `spec` 引数追加 |
| 2（契約の明文化） | A-4 | reviewer に TARGET_FILES 定義 |
| 2 | A-6 | specout 設定3キーをスキルから渡す |
| 2 | B-1 | カバレッジ表記を MIN_COVERAGE 基準に統一 |
| 2 | B-2 | Review Loop Step 0/1 の順序修正 |
| 3（保守性・効果大） | C-1 | 行番号参照の全廃 → 見出し参照化（28箇所） |
| 3 | C-2 | 経緯メタ注記の削減（特に xddp.feedback） |
| 4（リファクタ） | C-3 | cross レビュー・最終レビューの common 化 |
| 4 | C-4 | CR非依存 config 読み込みの common 化 |
| 4 | B-3 | テンプレートのリネーム（07/08/09 → 09/10/11） |
| 4 | B-4 | デッドコード削除（Detect Test Framework 等） |
| 4 | C-5 | 小規模修正一式 |

> **注:** CLAUDE.md の開発ルールに従い、実装前に `plans/PLAN-YYYYMMDD-{description}.md` を作成し、`/xddp.plan-review` による AI レビューと人の承認を経ること。
