# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# XDDP リポジトリ開発ガイドライン

このリポジトリは XDDP（eXtreme Design-Driven Process）を Claude Code で運用するための
スキル・テンプレート・エージェント定義を管理します。

## セットアップ・デプロイ

```bash
# 初回セットアップ（~/.claude/ にコピー）
bash ClaudeCode/setup.sh
```

`setup.sh` の動作：
- `~/.claude/` に該当ファイルがなければコピー
- `ClaudeCode/.claude/` 側が新しければ **自動上書き更新**（mtime 比較）
- `~/.claude/` 側が新しければスキップ

スキル・テンプレートを編集したら `setup.sh` を再実行してデプロイすること。
`~/.claude/` を直接編集すると次回 `setup.sh` 実行時に上書きされるため、必ず `ClaudeCode/.claude/` 側を編集する。

詳細は [README.md](README.md) を参照してください。

## 想定するプロジェクト構成

実際の開発時は以下のディレクトリ構成を想定する。

```
~/workspace/
├── docs/              # 過去の知見・既存ドキュメント（プロジェクト横断）
├── repo-A/            # 母体コード（開発対象リポジトリ）
│   ├── xddp/          # XDDP 成果物（CR フォルダ・latest-specs 等）
│   └── xddp.config.md
└── XddpSettings/      # このリポジトリ（XDDP 設定管理）

~/.claude/             # setup.sh によるインストール先（スキル・コマンド・テンプレート）
```

- `XddpSettings` はスキル・テンプレートの **開発リポジトリ**。編集後に `setup.sh` で `~/.claude/` へ反映する
- `~/.claude/` は `setup.sh` によるインストール先であり、直接編集しない（次回 setup.sh で上書きされる）
- 開発作業は `repo-A` 等の母体リポジトリ上で行う
- `docs/` はプロジェクト横断の知見・既存ドキュメントを蓄積する場所

## ファイル構成

| パス | 説明 |
|---|---|
| `ClaudeCode/setup.sh` | セットアップスクリプト |
| `ClaudeCode/.claude/skills/` | スキルファイル（`skills/<skill-name>/SKILL.md` 形式でXDDPフェーズ実行ロジックを格納）。スキル名がそのままスラッシュコマンド名になる |
| `ClaudeCode/.claude/skills/xddp-common/SKILL.md` | スキル共通ロジック（CR 解決等）。`user-invocable: false`。変更時は全スキルの動作確認が必要 |
| `ClaudeCode/.claude/agents/` | サブエージェント定義 |
| `ClaudeCode/.claude/skills/<skill-name>/templates/` | 各スキル専用テンプレート（スキルから直接参照される） |
| `ClaudeCode/.claude/skills/xddp-common/templates/` | 複数スキルで共有するテンプレート（project-rulebook-*.md 等） |
| `ClaudeCode/.claude/skills/xddp-common/procedures/` | 全スキルから参照される共通プロシージャの遅延ロード用ファイル群（1ファイル1プロシージャ・フロントマターなし）。`xddp-common/SKILL.md` の「## Procedures Index」が索引を持つ。波紋調査の判定エンジンの決定・照合・波ループ・件数一致検証・手で復旧する手順・初回以外の調査の実行・調査ごとの出力・資料の記載量・SPO の仕上げ（`ripple-*.md`・`specout-doc-levels.md`・`specout-finish.md`）は、`xddp-04-specout`・`xddp-investigate`・`xddp-05-arch` が共有する。単一スキル専用の `skills/<skill-name>/*.md` とは異なり、複数スキルから参照される。ファイル集合と索引の整合は `tools/harness/refcheck.py` 検査G が機械検査する。設計根拠は [docs/adr/ADR-0016-common-procedures-split.md](docs/adr/ADR-0016-common-procedures-split.md) を参照 |
| `ClaudeCode/.claude/skills/xddp-common/reviewer-checklists/` | `xddp-reviewer` エージェントが `DOCUMENT_TYPE` に応じて実行時に 1 ファイルだけ Read する遅延ロード用チェックリスト（`{DOCUMENT_TYPE}.md`。ペルソナ・主チェックリスト・次工程受け取り可否観点を同梱。SKILL.md なし・フロントマターなし）。ファイル集合の整合は `tools/harness/refcheck.py` 検査E が機械検査する。設計根拠は [docs/adr/ADR-0014-reviewer-checklist-lazy-load.md](docs/adr/ADR-0014-reviewer-checklist-lazy-load.md) を参照 |
| `ClaudeCode/.claude/skills/xddp-templates/` | スキル開発用メタファイル（xddp.skill-template.md 等。SKILL.mdなし） |
| `ClaudeCode/.claude/skills/xddp-rules/` | XDDP規約・ルール文書（SKILL.mdなし。スキルから直接参照される） |
| `ClaudeCode/.claude/skills/<skill-name>/*.md`（SKILL.md以外の低頻度参照ファイル） | 当該スキル専用の低頻度手順を切り出す参照ファイル（例: `xddp-04-specout/module-documentation.md`＝下調べエージェント `xddp-specout-prelim-agent`（下調べ・追加下調べ）と `xddp-specout-document-agent`（SPO の LLM が書く欄）が共有するモジュール文書化手順〔観察・累積観察メモ・記載要件・必須図・成長型の配置判定・§8 の書き方・資料の状態・モジュールの決め方〕。設計根拠は [docs/adr/ADR-0018-specout-prelim-phase.md](docs/adr/ADR-0018-specout-prelim-phase.md) と [docs/adr/ADR-0023-specout-two-layer-output.md](docs/adr/ADR-0023-specout-two-layer-output.md)）。フロントマターなし（`xddp-rules/*.md` と同じく `# 見出し` + blockquote でスコープを明示）。SKILL.md 本体または当該スキルが起動するエージェントから Read される。xddp-commonとは異なり単一スキル専用であり、他スキルから参照しないこと |
| `ClaudeCode/.claude/skills/xddp-survey/` | CR 非依存の母体調査スキル。`{XDDP_DIR}/survey/` に調査結果（SURVEY-*.md）を出力し、人の選択で knowledge / specs へ昇格する |
| `ClaudeCode/.claude/skills/xddp-investigate/` | CR の母体調査に波紋調査を足す・採用する・取り消す・取り除き、人の依頼でファイル・モジュールを調べて資料にするスキル（`ripple`／`adopt`／`unadopt`／`remove`／`list`／`finish`／`document`／`suggest`）。工程4a の後でも、工程5以降でも実行できる。調査は `04_specout/{repo}/ripple/{名前}/` に1回＝1フォルダで置き、採用した調査だけが SPO の波紋調査の欄に入る。採用・取り消しを決めるのは人。`document`（依頼調査）は下調べのエージェント（`PRELIM_MODE: requested`）が資料を書き、台帳の工程は `依頼調査`。依頼するかは人が決め、`suggest` は候補を示すだけ。設計根拠は [docs/adr/ADR-0025-specout-ripple-runs.md](docs/adr/ADR-0025-specout-ripple-runs.md)・[docs/adr/ADR-0026-specout-requested-docs.md](docs/adr/ADR-0026-specout-requested-docs.md) |
| `ClaudeCode/.claude/skills/xddp-md2excel/scripts/` | `xddp-md2excel` スキルが実行するPythonスクリプト（`crs_md2excel.py`） |
| `ClaudeCode/.claude/skills/xddp-02-analysis/scripts/` | `xddp-02-analysis` Step 0 専用の決定的処理スクリプト（`domain_refs.py`＝既存知識の参照先解決。AI_INDEX.md 実在時はテーブル照合（ユースケース一覧・モジュール別最新仕様・code-knowledge インデックス）、不在時はディレクトリ直接列挙（3-1a）で代替し、`{DOCS}` 側ディレクトリ自体が不在の場合のみ `latest-specs/` へフォールバックする。名称照合の正規化（区切り文字・拡張子除去＋完全一致優先／3文字以上の部分一致フォールバック）・区切り文字ガード・`DOMAIN_REF_MODE`（none/degraded/normal）判定を一括担当。意味判定（変更要求書からのキーワード抽出）は呼び出し元 SKILL.md が `--keywords-file` として渡す） |
| `ClaudeCode/.claude/skills/xddp-11-specs/scripts/` | `xddp-11-specs` Step MOD 専用の決定的処理スクリプト（`spec_version_delta.py`＝`precheck`（既存 latest-specs ファイルと今回 SPO の対応セクションを比較し、Mermaid ノード/エッジ数変化〔無条件発火〕・テキスト行数変化率〔既定20%〕から即時更新要否を機械判定し `FORCE_UPDATE_FILES` を出力）／`compare`（退避済みベースラインと生成後ファイルを比較し、セクション数増減・見出し名変更・テキストのみ変更の別からファイル別バージョン下限を機械算出し、下限を下回るフロントマター `version:` と変更履歴直近エントリを自動的に書き換える）の2サブコマンド。`xddp-specs-mod-agent` はこの機械判定済み `FORCE_UPDATE_FILES` を受け取り、数え直さず意味判断（どのセクションが対応するか）にのみ専念する） |
| `ClaudeCode/.claude/skills/xddp-common/scripts/` | 全スキル共通の決定的処理スクリプト（`xddp_progress.py`＝progress.md更新（`ARTIFACT_LINK` の書式検証を含む）、`xddp_config.py`＝`xddp.config.md` パース→CRに依存しない標準設定バンドルのJSON出力（`## Load Config` から呼ばれる。`load --list-keys` で出力キー名・既定値・消費者の一覧を取得可能）、`xddp_gate_snapshot.py`＝Human Review Gate の CHANGED 機械判定、`artifact_lint.py`＝フロントマター・Mermaid・テーブル検査＋SPO 機械検査（`--doc-type SPO` 時：F1〜F4＝funcmap の SP 網羅・直接呼び出し元数と機械算出値 `SPO-{CR}-funcmap-counts.md` の一致〔counts に行が無い識別子の `—`（未測定）は免除〕・`確認要` 残存なし・影響種別と §5.1 の一致〔§5.1 に行が無く、counts にも行が無い識別子の両列 `—`、または counts の値が 0 の識別子の `0` と `—` は免除。counts のファイルがある場合のみ〕〔cross/ は対象外・採用した波紋調査が無い SPO（SPO と同じディレクトリの `ripple/runs.json` に `"adopted": true` の調査が無い。ファイルが無い・読めない場合を含む）は F4 の対象外・funcmap／CRS／counts 不在時は縮退〕、S1〜S5＝§4.1・§4.2・§5.5〜§5.7 の存在と記入。`LINT_RESULTS` の `spo` カテゴリとして `xddp-reviewer` に渡す。SPO レビューの LLM のチェックは L1 影響範囲の十分性・L2 設計への申し送りの2項目のみ）＋CRS構造チェック（`--doc-type CRS` 時：理由必須・ID一意・仕様グループ配下SP存在・グループ名`＜＞`・「等」等の曖昧表現・SP本文重複・否定表現候補・分割軸列挙値・要求3階層兆候・H7見出し不在・CRプレフィクス欠落ID検出（L13 fail-loud）の L1〜L13。ID形式は形式B（CR名前空間先頭。例 `CR-2026-970-UR-001`／`CR-2026-970-SR-001-001`／`CR-2026-970-SP-001-001.010`）。見出し体系は USDM Canonical：カテゴリ=H3 ＜＞・UR=H4・要求グループ=H5 ＜＞・SR=H6・仕様グループ=太字行・SP=リスト項目）＋ANA §0 degraded mode 注記チェック（`--doc-type ANA` 時：§0テーブルの出典ファイルに `latest-specs/` 由来の参照があれば注記の有無を検査。A1）、`xddp_review_brief.py`＝Human Review Gate のレビューブリーフ生成：不確実性マーカー集約・前工程差分・推奨レビュー順序（`{工程}/{repo}/work/` 配下・波紋調査ごとの `{工程}/{repo}/ripple/{調査}/work/` 配下・取り除いた調査の `{工程}/{repo}/ripple/_removed/` 配下の中間ファイルと、CR 直下の計測ファイル `.phase-metrics-*.json`・`metrics.jsonl` は対象外。中間ファイルは差分件数のみ表示。中間ファイルを出す工程は `{工程}/{repo}/work/`（CR_PATH 相対の第3要素）または `{工程}/{repo}/ripple/{調査}/work/`（第5要素）に置くこと。これ以外の深さの `work/` は除外されない）、`xddp_vcs.py`＝VCS 抽象層スクリプト（detect / branch / commit / revert / status。VCS 種別ごとの関数群＋ディスパッチ構成）、`xddp_metrics.py`＝工程別テレメトリ CLI（`phase-start`／`record`。`## Snapshot Phase Baseline`〜`## Progress Update`（完了時）間の壁時計所要時間と、`## Review Loop` のレビューラウンド数・収束可否、`## Invoke Reviewer` 呼び出し1回あたりの `reviewer_call` イベント（`--reference-file` から算出する `reference_bytes`／`reference_file_count`／`reference_unmeasured_count`）を `{CR_PATH}/metrics.jsonl` へ1行1イベントで追記する。実LLMトークン数はライブ実行中のスキルからは取得不可能なため対象外＝ `tools/harness/smoke_full.py` の校正ラン専用））、`crs_ur_scope.py`＝CRS Markdown から指定 UR の見出しサブツリー（USDM Canonical: UR=H4）＋文書概要（Section 1）＋トレーサビリティマトリクス該当行（Section 3.1）を抽出する決定的スクリプト（`xddp-06-design` Step B・`xddp-feedback` Step 1-code-d の CHD レビュー時に CRS 全文の代わりに参照させ、レビュアーへの入力サイズを UR 単位に絞り込む）、`xddp_verify_tools.py`＝lint/build/typecheckコマンドを REPO を cwd として実行し、終了コードで PASS/FAIL を判定して結果レポート（Markdown）を生成する（工程8実ツール実行。`xddp-common/SKILL.md`「## Run Verification Tools」から呼ばれる。設計根拠は [docs/adr/ADR-0015-verify-real-tool-execution.md](docs/adr/ADR-0015-verify-real-tool-execution.md)）、`crs_model.py`＝CRS Markdown 共通パーサ（カテゴリ・要求グループ・分割軸・仕様グループ・UR/SR の懸念・検討事項・1階層パターン（UR→仕様グループ→SP、SR なし）を保持する。`xddp-md2excel`・`xddp-crs-view` から `sys.path` 経由で共有利用される）） |
| `ClaudeCode/.claude/skills/xddp-04-specout/scripts/` | specout 専用の決定的処理スクリプト（`specout_bfs.py`＝BFS 帳簿エンジン。visited/frontier管理・検索（既定 `auto`＝識別子索引 `index`。起動のたびにリポジトリ全体の識別子と `root.field` の索引を作り、索引で引けないシンボル〔`Foo::bar`・`$var`・ファイルパス等〕は rg があれば rg・無ければ grep に委譲。`grep`/`rg` を明示すると索引を使わない〔`root.field` シンボルは `root.field` / `root->field` に一致するパターンで検索する〕）・コマンドID採番・HIGH/MEDIUM交差・ケースA/B/C分岐・判定先の振り分け（C / C++ / Python のヒットはスライス用チャンク `wave-{N}-hits-chunk-S.json`〔常に1件〕、それ以外の言語のヒットだけを LLM 用チャンクへ。0件可）・高ノイズ判定（前倒し縮退＝代表行のみ分類。LLM 分類に回るヒットだけに適用し、`SPECOUT_MAX_FILES_PER_MODULE` 超過HIGHシンボルを対象に等価性を保ちつつLLM分類量を削減）・検索の後の1波の予算（`hit-budget`。関数シンボル→値シンボル、各々ヒットの少ない順に採る）と LLM 分類の上限（`llm-budget`）・打ち切り記録（state の `truncated` から discovery-log の「## 打ち切り記録」を作り直す）・探索の起点の波（`wave_origin`）から数える波数上限での自動完了（一時停止しない。`wave-limit` の打ち切り記録を残して complete）・`extend`（波数上限の引き上げ。`wave-limit` で打ち切ったエントリを frontier に戻す。状態によらず上限を更新）・`switch-engine`（tree-sitter を使えなくなったときの規則判定への切り替え）・要約の拡大による関数シンボルの再訪（dedup の鍵に要約の正規形を含める）・シードの直接参照ファイル数（`seed_direct_files`。Step C5 の規模の判定と、Step A-Document の CR 分割の警告・追加下調べの対象に使う）とファイル別のシードのヒット行数（`seed_direct_hits`。`commit-wave` が伝播しない判定以外のシードのヒット行を数えて足し込み、`import` で初期化する。追加下調べの対象を採る順に使う）・`search` の終了コード 6（シード要約の取り込みが済んでいない）・`merge-frontier` の `--summaries-file`／`--as-seed-globals`・catalog不在時の簡易module-priority（近傍HIGH/遠方LOW）・保守的ヒットフィルタ（`SPECOUT_HIT_FILTER`。行コメント除外は拡張子で言語別解決）＋分類済みロケーションdedup・未ヒット投入シンボル検出（Wave 0 は初期シンボル全件、Wave 1 以降は `entry_point_symbols` との積集合のみを対象とする。生ヒット0件／フィルタ後0件を区別し、ENTRY_POINTS 由来か否かを併記して discovery-log の「## 未ヒット投入シンボル（Wave N）」へ波ごとに `_upsert_section` で冪等に upsert し、`search` の stdout へ `zero_hit_symbols`／`zero_after_filter_symbols`／`wave0_seed_count` として返す。非ブロッキング）・ヒット過多の投入シンボル検出（未ヒット検出と同じ対象集合のうち、多数のファイル〔`SPECOUT_MAX_FILES_PER_MODULE` 超〕にヒットしたシンボル〔LLM 分類に回るヒットは代表行に縮退される〕を discovery-log の「## ヒット過多の投入シンボル（Wave N）」へ波ごとに upsert し、`search` の stdout へ`noisy_seed_symbols`／`all_seeds_noisy` として返す。非ブロッキング）・予算で打ち切った投入シンボル検出（「## 予算で打ち切った投入シンボル（Wave N）」・`budget_truncated_seed_symbols`／`all_seeds_budget_truncated`。非ブロッキング）・投入シンボルが0件（1波もコミットしていない状態で frontier が空）のときは `search` が終了コード 4 で終了・由来テーブル「## 投入シンボルの由来」の書き込み（全9行は `init --seed-candidates` が候補表から決定的に書く。`init --symbols` で始めた調査は ENTRY_POINTS 行に `--entry-point-symbols` を書く）・per-wave metrics（metrics.jsonl）・discovery-log/状態ファイル書き出しを一括担当。エントリ表記 `symbol[FILE:filepath]`（static・無名名前空間・そのファイルで定義したマクロ等、そのファイルの中でしか参照できない名前。そのファイルの中だけを検索する種別 `FILE` のコマンドで、`[MEDIUM:…]` とは別のエントリ〔確信度 HIGH・交差ルール・ケースA/B/C の対象外〕）・エントリ表記 `symbol[CLASS:ClassName]`（ClassName は名前空間をまたいで同じ名前のクラスがあれば `ns::ClassName`。C++ のメソッド・メンバー変数。C++ として解析するファイルだけを素の名前で検索し、判定でクラスを絞る。同じ素の名前のエントリの検索は1回にまとめ、ヒット行をエントリごとに複製する。種別 `CLASS`、確信度 HIGH・交差ルール・ケースA/B/C の対象外。要約と種類の表は `summary_key`〔`[CLASS:…]` はエントリ文字列、それ以外は素名〕を鍵にする。人が候補表・`/xddp-investigate` でシードに指定できる。設計根拠は [docs/adr/ADR-0022-specout-cpp-class-identity.md](docs/adr/ADR-0022-specout-cpp-class-identity.md)）・同一性の印（state の `entry_identity`〔`resolved`／`name-only`〕・`confirmed_files` の `identity`・ヒット表と確定ファイル一覧の「同一性」列・材料の `同一性:`・`status --brief` の `name_only_file_count`。`init --entry-identity`〔クロスリポジトリ伝播の調査は `name-only`〕。設計根拠は [docs/adr/ADR-0021-specout-symbol-identity.md](docs/adr/ADR-0021-specout-symbol-identity.md)）。`known_symbols` の素名正規化配布・チャンク分割出力（`search --hits-dir`/`--chunk-size`）・`status --brief`（`max_wave_depth`・`truncated_wave_limit_count`・`slice_engine`・`seed_direct_file_count`・`seed_budget_truncated_count` を含む）・`commit-wave --unsupported-patterns` も担う（波内 classification のチャンク並列化。ADR-0010）。discovery-log の種別・派生元・判定の値は英語のコード（`seed(X)`・`HIGH-compound`・`✅ excluded(…)` 等）で書き、冒頭の「## 凡例」で説明する（判定エンジン・予算・打ち切り記録・自動完了の設計根拠は [docs/adr/ADR-0019-specout-static-slicer.md](docs/adr/ADR-0019-specout-static-slicer.md)）。調査の記録のサブコマンド（`run-add`＝`ripple/runs.json` に調査を加え `ripple/{名前}/` を作る〔名前は `^[a-z0-9][a-z0-9-]{0,39}$`。`initial`＝工程4a・`cross-*`＝クロスリポジトリ伝播・`arch-*`＝方式検討エージェント・他＝人の由来だけが使える。approach・reason・seeds・entry_identity は `--meta-file`〕／`run-adopt`・`run-unadopt`＝採用・取り消し〔冪等。`complete` の調査だけを採用できる。stdout の `changed`〕／`run-remove`＝取り除き〔採用を取り消し、`ripple/_removed/{名前}-{日時}/` へ退避。クロスリポジトリ伝播の調査なら伝播の記録の組を `deferred` に戻す〕／`run-list`＝調査ごとの状態〔`in-progress`・`complete`・`not-started`・`missing`〕と採用した調査の合算の件数／`finish-record`・`finish-needed`＝SPO の仕上げの開始・成功と採用した調査の集合・台帳と依頼調査の記録の SHA-256 の記録・照合〔`work/specout-finish.json`。台帳か依頼調査の記録が変わっていれば `reason_code` `docs-changed`〕。`--repo-dir` を受け付けるサブコマンドは、採用した調査の状態ファイルが無い・壊れている・`repo_path`/`cr`/`repo` が食い違う場合 exit 1。合算は確定ファイルの和集合〔波は最小・同一性は resolved 優先・確信度は高い方〕・シードの直接参照の和集合〔ヒット行数は最大〕・打ち切りの連結。設計根拠は [docs/adr/ADR-0025-specout-ripple-runs.md](docs/adr/ADR-0025-specout-ripple-runs.md)）、`ripple-digest`＝調査1つの LLM 向けの上限つきの要約 `ripple-digest.md`（名前・由来・理由・シード・確定ファイル数・波数・予算・打ち切り・「資料」列の時点と、SPO §5.0 と同じ列・並び・上限の機能一覧。方式検討エージェントが読む）、`ripple-summary`＝波紋調査の結果を機能（モジュール）単位に要約するサブコマンド（`--path` は調査1つ、`--repo-dir` は採用した調査の合算〔全量に「届いた調査」列〕。人向けの全量 `{OUT}/ripple-summary.md`〔全モジュールの表・調査の打ち切り・下調べに無いシードの直接参照・grep 未対応パターン・モジュールごとのファイル一覧。上限なし。LLM には渡さない〕と、`assemble-spo` の入力 `work/ripple-summary.json`〔モジュールごとの確定ファイル数・名前の一致のみの数・到達波・シードの直接参照数・資料の有無と、`seed_direct_file_count`・`direct_modules`・`prelim_gap_files`・`gap_reviewed_files`〕を書く。`prelim_gap_files`＝シードの直接参照のうち台帳にも追加下調べの判断の記録 `work/prelim-gap-reviewed.md` にも無いファイル〔理由 `over-limit`＝追加下調べの累計の上限を超えた／`not-written`＝追加下調べの対象だが資料が無い・未実施〕。どのモジュールにも属さない確定ファイルがあれば exit 1）、`ripple-trace`＝discovery-log と `work/ripple-summary.json` から、人向けのモジュール単位の伝播グラフ `ripple-graph.md`（Mermaid。描くモジュールは60個・辺は400本まで、全量は表。実線＝送り手の行と受け手の行がともに resolved の伝播を含む）と関数単位の階層表 `ripple-tree.md`（各関数1回・他の派生元つき）を書く（LLM には渡さない。設計根拠は [docs/adr/ADR-0024-specout-ripple-trace.md](docs/adr/ADR-0024-specout-ripple-trace.md)）、`verify-sweep`＝検証スイープ（全シンボルの再検索と、波紋調査の帳簿〔確定ファイル `confirmed_files`・判定で関係なしとしたファイル `false_positive_files`〕との突き合わせ。資料にしたかは問わない）のサブコマンド（未記録ヒットありは終了コード 7。`specout_verify_counts.py` の件数不一致〔終了コード 3〕とは別。SKILL は人の承認を待たず、stdout を `work/verify-sweep.json` に保存して SPO §9 に転記する）、`assemble-spo`＝配置判定と SPO の組み立てのサブコマンド（`--layout-only --only seed-direct --max-files N`＝台帳と追加下調べの対象で成長型の配置判定・統合→分割の移し替え・サブディレクトリ分割を行い、追加下調べの書き先 `file_outputs` を返す。指定なし＝配置判定は台帳のファイルだけで行い〔資料の無いモジュールに `modules/` を作らない〕、統合パスの追加下調べの下書き `work/module-drafts/` の差し込み〔差し込み後に削除〕・資料のある各モジュール資料の「波紋調査の結果」節〔最大30行。再実行で節ごと置き換え〕・SPO サマリーのスクリプトが書く欄〔§1・§1.x 調査の打ち切り・§5.0 波紋調査の要約（1モジュール1行・最大30行）・§5.1・§5.2 と §5.5（資料のあるモジュールのファイルだけ）・§8・§9（追加下調べでも資料にできなかったシードの直接参照・採用した各調査の検証スイープの未記録ファイルと未実施）〕・SPO とモジュール資料の版の確定〔変更者 `specout_bfs.py assemble-spo`〕を書き、`--metrics` 指定時は `metrics.jsonl` へ `specout_doc_summary` を1行追記する。`--repo-dir`（必須）の採用した調査の合算で組み立て〔`--repo-path`・`--repo` 必須。合算の要約は `{repo-dir}/work/ripple-summary.json`。§1.x は採用した調査ごとの1行、§9 は採用した各調査の `work/verify-sweep.json`（無ければ「検証スイープ未実施」）〕、採用した調査が0件なら台帳だけから組み立てる〔`work/no-ripple.json` の有無で「波紋調査を行っていない」「採用した波紋調査が無い」を書き分ける〕。`--crs-file`・`--entry-points` から、document agent に渡す ENTRY_POINTS `doc_entry_points`〔人の指定（今回の指定と `work/doc-entry-points.json` の累積。書き戻すのは人の指定だけ）と採用した調査のシード（`initial` は state の `entry_point_symbols`、それ以外は `runs.json` の `seeds`）の和集合〕と入力の指紋 `inputs_fingerprint`〔台帳・合算の `ripple-summary.json`・初回の調査を作らない印の有無・CRS の内容・`doc_entry_points` の SHA-256〕・前回の成功時との比較 `inputs_changed` を返す〔指紋は保存しない〕。引数の組み合わせの誤りは終了コード 2）、`commit-assemble-inputs`＝document agent の成功（返答 `OK:` で lint が停止しなかった場合）の後に SKILL が実行し、`assemble-spo` が返した指紋を `work/assemble-inputs.json` に保存するサブコマンド（入力が変わらない再実行では document agent を起動せず、SPO の LLM が書く欄を保持する。指紋は依頼調査の記録 `work/doc-request-log.md` も含む）、依頼調査（`/xddp-investigate document`・`suggest`）のサブコマンド（`doc-request`＝人が名指しした対象〔ファイル・ディレクトリ・モジュール名〕を資料にするファイルへ展開し、モジュール単位・1回 `SPECOUT_MAX_AFFECTED_FILES` ファイルまでのバッチを決めて JSON に書く〔`--append-file` は資料のあるファイルへの追記。`pattern_overridden`＝名指しした対象が除外パターンに一致したため除外パターンを適用しなかったファイル・`concerns`＝名前の一致のみ／追加下調べが関係なしと判断・`already_documented`〔`appended_on`〕・`over_soft_limit` を返す。`module-assignments.json` は書かない。SPO の仕上げが途中なら exit 1〕／`doc-suggest`＝資料の無いモジュールの候補〔採用した調査の合算からメモリ上で算出。シードの直接参照で資料の無いファイルを持つものが先、名前の一致のみが全部のものは最後〕／`assemble-spo --layout-only --only requested --files-file`＝依頼調査の書き先の決定／`doc-append-check`＝追記の写し `work/doc-append-backup/` と検査〔`snapshot`（前回の写しが残っていれば exit 4）／`verify`（追記の節 `### 2.7`・`### 2.X.10` と変更履歴の表の外が変わっていれば、または `--restore` なら、書き先・観察メモ・台帳を元に戻して exit 3）／`restore`／`discard`〕／`doc-request-record`＝依頼調査の記録 `work/doc-request-log.md` への追記〔スクリプトだけが書く〕。`assemble-spo --exclude` は台帳の工程 `依頼調査` の行のうち除外パターンに一致するファイル〔名指しで調べたテストコード等。`pattern_override_files`〕を §5.5・影響の一覧〔§1 の検出モジュール数・採用0件の §5.0・§5.1〕から外して §8 に注記し、CRS との関係を `確認できず` とした依頼調査の行も同じく影響の一覧から外して §8 に注記する〔「資料あり」の判定は変えない〕。統合パスの下書き `work/module-drafts/` は抜き出し元の節の SHA-256 を `.source-sha256.json` に記録し、抜き出しの後に §2.A… が変わっていれば差し込み・移し替えを exit 1 で止める〔移し替えは下書きから資料を作る〕）、`doc-targets --auto-assign`＝どのモジュールにも属さないファイルを親ディレクトリへ機械的に割り当て `work/module-assignments.json` に追記する（`--repo-dir` では自動の割り当て〔`"auto": true`〕をいったん外してから採用した調査の合算で割り当て直す。調査ごとの出力は調査のディレクトリの写しに書き、repo の割り当ては SPO の仕上げだけが書く。名前の衝突は exit 1 で fail-loud。設計根拠は [docs/adr/ADR-0020-specout-doc-digest-and-review.md](docs/adr/ADR-0020-specout-doc-digest-and-review.md)。波紋調査の結果の2層化〔SPO 内の上限つきの要約と人向けの全量〕・追加下調べ・波紋調査なしの経路の設計根拠は [docs/adr/ADR-0023-specout-two-layer-output.md](docs/adr/ADR-0023-specout-two-layer-output.md)）。LLMはhits行の意味判定のみ実施、`funcmap-counts`＝discovery-log.md の Wave 0 ブロックから初期シンボル別の直接呼び出し元数（ユニークファイル数。伝播種別が `false-positive` の行を除く）を機械的に算出し `SPO-{CR}-funcmap-counts.md` へ書き出すサブコマンド（xddp-specout-document-agent の funcmap 生成・reviewer-checklists/SPO.md チェック項目4の突合を、LLM による手集計から機械算出値の転記・突合へ置換する。書式解析失敗時は exit 1 で fail-loud し、呼び出し側は discovery-log.md 参照へフォールバックする）、`write-seed-candidates`＝discovery-setup が渡した由来別のシンボルと根拠の JSON（`work/seed-input.json`）から、シード候補表（`work/seed-candidates.md`）の「## 候補」等を決定的に書く（採否は常に ☑。同一シンボルは `ENTRY_POINTS ＞ CRS SP項目 ＞ 下調べ ＞ 母体コードから補完 ＞ 継承展開` で1行に畳む。新規作成は一時ファイル経由で、書式検証に失敗したら `--out` を作らず、`--stale-ref` より新しい既存の候補表は上書きしない。`--append` は人が編集済みの既存行を変えずに足りない行だけを追記し、採否 ☐ の ENTRY_POINTS を `excluded_entry_points` として返す。同じ入力の `unsupported_patterns` から grep 未対応パターンの記録（`work/seed-unsupported.json`。`--unsupported-out`）も書く（`location` の全角 `（` 以降は `note` へ分け、`(pattern, location)` で重複を除いて注記を連結する。`--append` は既存の要素を変えずに足りない要素だけを追加する。書き出しは検証をすべて済ませた後で、exit 1 ではどちらのファイルも変更しない）。入力の不正は exit 1 で stderr に原因ファイルのパスを出す）、`seed-preview`＝シード候補表（`work/seed-candidates.md`。discovery-setup エージェントが書き、Step A-Seed で人が採否を編集しうる）の採用シンボルを `search` と同じバックエンド・フィルタで試算し「ヒット（ファイル数）」「警告」（未ヒット／フィルタ後0件／ヒット過多／予算超過〔`--wave-hit-budget` を超える。ヒット過多と独立に判定し、両方なら `予算超過・ヒット過多`〕）列と、表の直前の採用シンボルの合計ヒット数の注記行（予算超過なら分割実行の案内。`--slice-engine slice` ではシードが書くグローバルを含まない旨を添える）を書き換えるサブコマンド（状態ファイルは作らない。`--ledger` 指定時は文書化済みファイル台帳の工程 `下調べ` の行からモジュール数・ファイル数を数え、台帳の整合を検査する。候補表・台帳の書式不正は exit 1 で stderr に原因ファイルのパスを出す）、`init --seed-candidates`＝候補表の採用行から初期シンボル・`entry_point_symbols`（由来 `ENTRY_POINTS`／`人が追加`）と由来テーブル全9行を作る（`--symbols`／`--entry-point-symbols` とは排他。`init` は Step A-Seed で SKILL が実行する）、`init --unsupported-patterns`＝discovery-setup が見つけた grep 未対応パターン（`work/seed-unsupported.json`）の記録、`doc-targets`＝`bfs-state.json` と文書化済みファイル台帳（`work/documented-files.md`。工程は `下調べ`／`追加下調べ`／`依頼調査`〔`依頼調査` は追加下調べの累計の上限に数えない〕）の集合演算で、台帳に無い確定ファイル（`doc_targets`。`--only seed-direct --max-files N --gap-reviewed work/prelim-gap-reviewed.md` では追加下調べの対象＝シードの直接参照のうち台帳にも判断の記録にも無いファイルに絞り、repo ごとの累計の上限 N〔`SPECOUT_MAX_AFFECTED_FILES`〕から台帳の工程 `追加下調べ` の行数と判断の記録の行数を引いた件数まで、同一性 `resolved` → シードのヒット行数〔`seed_direct_hits`〕の多い順 → パスの順に採り、残りを `over_limit_files` に返す）・`documented_confirmed`・`unconfirmed_documented`・モジュールの割り当て（台帳と `work/module-assignments.json` のモジュールディレクトリへのディレクトリ境界での最長前方一致。一致しないものは `unassigned`）・`module_file_counts`・`current_layout` を返し、`--memo` 指定時は累積観察メモ（`work/observation-memo.md`）から台帳に無い行を除去する（台帳・観察メモ・判断の記録の不整合は exit 1、`module-assignments.json` の不正は exit 5、引数の組み合わせの誤りは exit 2）、`prelim-metrics`＝下調べの効果測定値（`prelim_summary`。`prelim_file_count`・シード候補の採否・`human_added_count`／`human_removed_count`・`bfs_only_file_count`・`prelim_only_file_count`・`adopted_over_budget_count`・`adopted_total_hits` 等）を初回の波紋調査完了時に1回だけ `metrics.jsonl` へ追記する、`specout_slice.py`＝ヒットの判定エンジン（`probe`＝tree-sitter を使えるかの確認、`seed-summary`＝シード関数の副作用の要約〔戻り値・出力引数・書くグローバル・その他の副作用・クロージャ〕、`classify`＝スライス用チャンクの判定。state の `slice_engine` が `slice` なら tree-sitter による関数内の完全スライス〔影響が関数の外へ出る経路を求め、呼び出し元・グローバル変数の読み手〔`root.field`〕・関数の外の値〔マクロ名・初期化した変数名・代入先〕を次の波のシンボルにする〕、`rule` なら標準ライブラリのみの規則判定〔コメント・文字列・goto のラベル名・プロトタイプ宣言の引数名を偽陽性とし、ヒット行を含む関数を追う〕。リンケージによる名前の解決〔static・`extern`・ヘッダ。書き込み先は書き込んだ関数のファイルから見える宣言で解決し、内部リンケージは `name[FILE:path]`、見える宣言の無い名前は呼び出し元へ伝播する〕・呼び出し先の要約は呼び出し元のファイルから呼べる定義だけで作る・変数のシンボルのヒット側の除外〔`member-name`・`shadowed-local`・`param-name`・`other-static`・`other-class`。`false-positive` にする〕・同一性の印〔classification の `identity`・`next_symbol_kinds`・`name_only_symbols`〕・C++ のクラス単位の同一性〔メソッド・メンバー変数を `name[CLASS:X]` で送り〔メンバー変数はヒットした関数の中の直接の書き込みからだけ。`this` を省いたメソッドの呼び出しも呼び出し元の `out(this)` にする〕、ヒットの受け手のクラスを修飾・`this`・宣言の型〔型の別名を解決〕から決める。兄弟・無関係のクラス・リポジトリの外の型〔`std::` 等〕の受け手と、メソッドのエントリの変数・引数の名前の出現は `other-class`、基底クラスの virtual は動的ディスパッチとして関係あり、決められなければ `name-only`。呼び出し先の要約はクラスごと。名前空間・列挙・`::` で修飾した出現と、自由関数の宣言・メソッドでない関数の中の修飾なしの出現はメソッドではない（`other-class`）。受け手の式の型〔範囲 for の要素・`auto` の初期化子・戻り値・メンバーの連鎖。ローカル変数は出現から見える宣言〕を求める。同じ名前空間の同名クラスはまとめ、名前空間をまたいで同じ名前のクラスの鍵は `名前空間::名前`（名前空間に属さないものは `::名前`）。構文解析の誤りの中の出現は決めず、誤りのあるファイルでは名前空間の入れ子に頼る規則を使わない。設計根拠は [docs/adr/ADR-0022-specout-cpp-class-identity.md](docs/adr/ADR-0022-specout-cpp-class-identity.md)・[docs/adr/ADR-0028-specout-cpp-receiver-resolution.md](docs/adr/ADR-0028-specout-cpp-receiver-resolution.md)〕。関数ポインタ経由の呼び出し・デストラクタ・演算子オーバーロードは grep 未対応パターンとして返す。C/C++ の前処理（判定エンジンが `slice` のとき、リポジトリのオブジェクト形式のマクロのうち、宣言を飾るマクロ・名前空間マクロを同じ行の中で置き換え、空の定義を持つ構造を開く側・閉じる側の組〔`export {`／`}`・`try`／`catch (…) {…}` 等。両方の空の定義と空でない定義がそれぞれ同じファイルの同じ条件コンパイルの枝にあるもの〕を空にする。プリプロセッサ指令の行・コメント・文字列の中は対象外。マクロの表は `specout_macros.py` が作り、置き換えた数は `init` が state の `preprocess` と discovery-log の「## 探索設定」に書く。置き換えたマクロ自体へのヒットは `file-scope`〔`neutralized-macro`〕。文のループマクロの書き換えは引数が1行に収まるものに限り、コンストラクタ等を書き換えない）。構文解析の誤りで言語の予約語が含む関数・次の波のシンボルになった箇所は送らず、grep 未対応パターン `parse-artifact` として返す。終了コード 5＝state が `slice` なのに tree-sitter を import できない。tree-sitter は遅延 import し、`--help`・`probe`・`rule` は標準ライブラリのみで動く）、`specout_log_values.py`＝discovery-log の英語の値（伝播種別・派生元・実行コマンドの種別・件数一致検証の判定・同名 MEDIUM 重複ログのケースと処置・打ち切り記録の理由）の定数と判定の文字列の書式関数（`specout_bfs.py` と `specout_verify_counts.py` が共有する。サブコマンドなし）、`specout_macros.py`＝C/C++ のマクロの事前走査と種類の判定（宣言を飾るマクロ・名前空間マクロ・空にする組）・置き換え・コメントと文字列とプリプロセッサ指令の字句の走査・C/C++ の拡張子と言語の対応 `C_CXX_EXT_LANG` とファイルの言語を決める `c_cxx_lang`（`specout_slice.py` の `EXT_LANG`・`specout_bfs.py` の `CPP_SOURCE_EXTS` をここから作る。`specout_slice.py` と `specout_bfs.py` が共有する。サブコマンドなし・標準ライブラリのみ）、`specout_verify_counts.py`＝discovery-log件数一致検証（生=記録+dedup除外+フィルタ除外+noise-collapse除外で照合する独立回帰チェック。「フィルタ除外」は保守的フィルタと1波の予算による除外の合計。`commit-wave` の自己検証がスクリプトのメモリ上のデータを突き合わせるのに対し、本スクリプトは書き出されたログのテキストを突き合わせるため、ログ書き出し自体の欠陥を検出できる。波紋調査ごとに `--wave all --strict` で全波が自動検証され（共通プロシージャ「## Ripple Count Check」）、不一致時は exit 3 で同プロシージャの「### 不一致の扱い」へ振り分けられる。終了コードは 0=成功 / 1=検証の実行エラー / 2=使用法エラー（argparse 既定）/ 3=件数不一致）、`merge_classification.py`＝チャンク並列 classification の検証・結合（line_id 欠落/重複/未知値検出・grep未対応パターン集約・チャンク mtime 収集による再利用波検出。ADR-0010）） |
| `ClaudeCode/.claude/skills/xddp-06-design/scripts/` | 変更設計書フェーズ専用の決定的処理スクリプト（`chd_sp_coverage.py`＝CRS×CHD SPカバレッジ照合） |
| `ClaudeCode/.claude/skills/xddp-close/scripts/` | `xddp-close` スキルが実行するPythonスクリプト（`promote.py`＝latest-specs→DOCS_DIR の成果物昇格コピー・削除伝播検出・AI_INDEX.md 全7セクションupsert・lessons-learned/CRS/TSP/TRS/project-rulebook/improvement-backlogの昇格・cross破壊的変更検出を一括担当。決定的処理のみでLLM意味判定を含まない、`collect_insights.py`＝全成果物からの「気づき・提案メモ」節の決定的抽出（列挙・除外・切り出し・集約）。出力は `{CR_PATH}/pending-items/INSIGHTS-{CR}.md`） |
| `ClaudeCode/.claude/skills/xddp-excel2md/scripts/` | `xddp-excel2md` スキルが実行するPythonスクリプト（`excel_dump.py`＝Excel全セルのタブ区切りダンプ） |
| `ClaudeCode/.claude/skills/xddp-crs-view/scripts/` | `xddp-crs-view` スキルが実行するPythonスクリプト（`crs_view.py`＝`crs_model.py` を用いて CRS Markdown を HTML ビューア／CLI ツリーへレンダリングする。標準ライブラリのみに依存し `openpyxl` を必要としない） |
| `docs/` | このリポジトリ自体の要求書 |
| `docs/adr/` | XddpSettings リポジトリ自身（XDDPツールのスキル・エージェント定義）の設計判断記録（ADR）。開発リポジトリ限定の参考資料であり、`setup.sh` によるデプロイ対象（`~/.claude/`）には含まれない |
| `tools/harness/` | ツール自身を検証する開発時メタツール（`refcheck.py`＝L1/L3 静的参照整合、`run_all.py`＝`make test` の実体、`smoke_full.py`＝L4/L5 full-run スモーク）。`setup.sh` のデプロイ対象（`~/.claude/`）には含めない |

### アーキテクチャパターン：スキル → エージェント

- **skills/**: フェーズ実行の全ロジックを持つ。スキル名（例: `xddp-02-analysis`）がそのままスラッシュコマンド（`/xddp-02-analysis`）になる
- **agents/**: スキルから自動呼び出されるサブエージェント定義。人が直接呼ぶことはない

### project-rulebook.md の位置付け

`/xddp-01-init` 実行時に以下の3種類のステアリングファイルが生成される。

| ファイル | テンプレート | 説明 |
|---|---|---|
| `{XDDP_DIR}/project-rulebook.md` | `project-rulebook-template.md` | プロジェクト全体の共通規約・ADR・ドメイン制約 |
| `{XDDP_DIR}/project-rulebook-{repo}.md` | `project-rulebook-repo-template.md` | リポジトリ固有の命名規約・コーディングパターン。REPOS: が2エントリ以上の場合のみ生成（シングルリポジトリ時は省略） |
| `{XDDP_DIR}/project-rulebook-cross.md` | `project-rulebook-cross-template.md` | リポジトリ間インタフェース規約・APIバージョニング。REPOS: ≥2 の場合のみ生成 |

各ファイルは工程5（実装方式検討）・工程6a（変更設計書作成）で `RULEBOOK_CONTEXT` として読み込まれる。
ファイルが存在しない場合や未記入でもXDDPプロセスは動作するが、工程4（specout）開始前に記入することで工程5・6の成果物品質が向上する。
`xddp.config.md` の `REPOS:` キー名と `project-rulebook-{repo}.md` のファイル名は一致させること。
`cross` はシステム予約名称であり `REPOS:` のキーとして使用してはならない。
（理由: REPOS: エントリが 2 つ以上ある場合、システムがリポジトリ間インタフェースを管理するための
仮想リポジトリとして `cross/` ディレクトリおよび関連成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）を
自動生成するため予約されている）

### xddp.config.md の位置付け

`/xddp-01-init` 実行時にテンプレート（`~/.claude/skills/xddp-01-init/templates/xddp.config.md`）から**ワークスペースルート**へコピー生成される。
XDDP コマンドはワークスペースルートで実行し、`xddp.config.md` もワークスペースルートに1つだけ置く（マルチリポジトリ構成でも共通）。

```
workspace/          ← xddp コマンドをここで実行
  xddp.config.md   ← このファイル
  xddp/            ← XDDP_DIR（デフォルト）
  baseline_docs/   ← DOCS_DIR（デフォルト）
  repo-A/
  repo-B/
```

`XDDP_DIR` 設定で XDDP 成果物（CR フォルダ・latest-specs・project-rulebook.md 等）の配置先をワークスペースルートからの相対パスで指定する（デフォルト: `xddp`）。
`{XDDP_DIR}/` 直下の `latest-specs` と `survey` はシステム予約ディレクトリ名であり、CR フォルダ名として使用してはならない。
（理由: CR 番号の自動解決は `{XDDP_DIR}/` 直下のディレクトリを列挙して行うため、
同名の CR を作成すると解決が失敗する。`survey` は `/xddp-survey` が調査結果を出力するディレクトリ）
`DOCS_DIR` 設定で中央知識ハブのパスをワークスペースルートからの相対パスで指定する（デフォルト: `baseline_docs`）。
`SPECOUT_MAX_FILES_PER_MODULE` 設定で1モジュール内の波及ファイル数の上限を指定する（デフォルト: `10`）。超過時はサブディレクトリ単位でモジュールファイルを分割出力する（サブディレクトリがない場合は分割しない）。SPO の配置（統合パス／分割パス／サブディレクトリ分割）は文書化済みファイル台帳の件数で判定する成長型で、下調べ時点の配置から、追加下調べ時に閾値を超えた単位だけを分割へ移す（逆方向には戻さない。SPO の仕上げの最終の組み立ては台帳のファイルだけで判定し、波紋調査で届いただけのファイルは数えない）。この閾値を超える HIGH シンボル（1エントリの異なるファイル数が超過）は `cmd_search` 時点で前倒し縮退（PLAN-20260806 Phase 2A）され、LLM 分類対象をファイルパス昇順の代表サブセット（各ファイル最大1行・上限件数）に絞る（前倒し縮退と高ノイズによる波及停止は LLM 分類に回るヒットだけに適用する。スライス判定・規則判定のヒットは1波の予算が代わりを担う）。縮退後も全ファイルは confirmed_files に網羅され（代表行以外は判定しないため、`false-positive` だけのファイルも含む。縮退しないシンボルでは `false-positive` だけのファイルは確定しない）、次波への伝播抑止は現行と等価に保たれる（fixture で保証）。設計根拠は [docs/adr/ADR-0009-specout-hit-reduction.md](docs/adr/ADR-0009-specout-hit-reduction.md) を参照。
`SPECOUT_HIT_FILTER` 設定で Discovery BFS の保守的ヒット事前フィルタを指定する（デフォルト: `conservative`。`off` で無効化）。`conservative` は「行全体が行コメント」のヒット（コメントマーカーは拡張子で言語別に解決し、C/C++ の `#define`/`#include`/`#ifdef` は除外しない）と過去波で分類済みの同一ロケーション（同一スコープ種別）の再出現を、LLM 意味判定へ渡す前に除外してトークンを削減する。除外・dedup 行は discovery-log.md の「## フィルタ除外一覧」に全件記録され、件数一致検証は「生=記録+dedup除外+フィルタ除外+noise-collapse除外」で照合する（漏れの監査が可能）。「フィルタ除外」には1波の予算（`hit-budget` / `llm-budget`）で除いた件数も含み、予算で除いた行は「## フィルタ除外一覧」ではなく「## 打ち切り記録」にシンボル単位で記録される。
`SPECOUT_CROSS_PROPAGATE` 設定で、Step A-cross（クロスリポジトリ SPO 統合）が識別した「あるリポジトリが
提供し別のリポジトリが消費するシンボル」について、消費リポジトリ側に1ラウンドだけ新しい波紋調査
（`cross-{提供 repo}-{n}`。`/xddp-04-specout` が作り、完了したら採用する）を自動実行するかどうかを指定する（デフォルト: `true`。
マルチリポジトリ CR のみ意味を持つ）。連鎖的な追跡（A→B→C→…）は CR 単位で意図的に行わない——
`/xddp-04-specout {CR}` の再実行時も、過去に追加探索したリポジトリを提供元とする新規の共有インタフェースは
`cross/work/cross-propagation-log.json` に基づき自動の追加探索対象から除外される。詳細は
`xddp.config.md` テンプレートの「### クロスリポジトリ伝播探索」節を参照。
`SPECOUT_SEED_GATE` 設定で、工程4a 初回実行時（初回の波紋調査 `ripple/initial/` も `work/no-ripple.json` も無い repo）の波紋調査の前に、シード候補表と repo ごとの波紋調査の要否を人が確認するか（Step A-Seed）を指定する（デフォルト: `true`）。`true` は候補表（下調べ〔Step A-Prelim。`xddp-specout-prelim-agent`〕の候補 ∪ CRS のコード表記 ∪ ENTRY_POINTS。`seed-preview` によるヒット数試算付き）を提示し、人が採用・除外・追加を確定するまで待つ。波紋調査は既定で行い、「`{repo}`: 波紋調査なし」と指示した repo は波紋調査を行わず下調べ資料で工程4a を完了する（印 `work/no-ripple.json` を書き、再実行でも Step A-Document だけを行う。工程4b へ進める。影響範囲は下調べで読んだ範囲に限られる）。「中断する」を選ぶと波紋調査を始めずに ⏸ 中断で終了し（CR 単位。工程4b へ進まない）、再実行で Step A-Seed から再開する。`false` は提示のみで全 repo の波紋調査へ進む（波紋調査なし・中断は選べない）が、採用0件または採用した全候補がヒット過多か予算超過の repo がある場合は設定によらず確認する。CR 単位の上書き引数はない。`metrics.jsonl` の `prelim_summary`（`prelim-metrics`）で `human_added_count`・`human_removed_count`・`bfs_only_file_count` が継続して小さい場合に `false` を検討できる。下調べ・シード確認・成長型の資料配置の設計根拠は [docs/adr/ADR-0018-specout-prelim-phase.md](docs/adr/ADR-0018-specout-prelim-phase.md)、下調べを母体調査の本体とし波紋調査を repo ごとに選べるようにした設計根拠は [docs/adr/ADR-0023-specout-two-layer-output.md](docs/adr/ADR-0023-specout-two-layer-output.md) を参照。
`SPECOUT_CLASSIFY_CHUNK_SIZE` 設定で波内 classification（LLM 分類に回るヒット＝C / C++ / Python 以外の言語のヒットだけ）のチャンク分割サイズを指定する（デフォルト: `40`）。`0` で分割を無効化し常に単一チャンク（並列化前と同一の分類）に戻す。波のヒット数がこの値以下なら分割しない。`SPECOUT_CLASSIFY_PARALLEL` 設定で classifier サブエージェントの同時起動数上限を指定する（デフォルト: `4`。対象波の全リポジトリのチャンクを合算した値。超過分はバッチに分けて順次起動する）。1波のヒット数が多い場合の壁時計レイテンシ短縮が目的で、トークン総量はほぼ不変（並列化は時間短縮であってトークン削減ではない）。波ループの実行主体を `xddp-04-specout/SKILL.md`（オーケストレータ）へ移設し、判定ルールを新設エージェント `xddp-specout-classifier-agent` へ逐語移設した設計判断・チャンク結合スクリプト `merge_classification.py` の役割は [docs/adr/ADR-0010-specout-parallel-classification.md](docs/adr/ADR-0010-specout-parallel-classification.md) を参照。
`SPECOUT_EXCLUDE_PATTERNS` 設定で Discovery BFS から除外するディレクトリ・ファイルパターンをカンマ区切りで指定する（デフォルト: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`）。書き方の意味は検索ツール（index / grep / rg）によらず同じ: `/` で終わり途中に `/` を含まない（`tests/`）＝パスのどの階層でもその名前のディレクトリの配下、`/` で終わり途中に `/` を含む（`lib/legacy/`）＝リポジトリのルートからのパスがそのディレクトリの配下、`/` で終わらない（`*.pb.c`・`gen/*.c`）＝`/` を含まなければファイル名、含めばルートからのパスに対する glob。一致するファイルが無いエントリは discovery-log の「## 探索設定」に警告が残る。スペックアウトはプロダクションコードだけを対象にする（テストコードは調べない。SPO §5.5 はプロダクションコードの構造から観察したテスト可能性だけを書く）。除外パターンは調査と結果の量を抑えるための既定である。依頼調査（`/xddp-investigate document`）で人が名指しした対象は、除外パターンに一致しても調べる（名指しした対象そのものが一致したパターンだけを外し、配下の他のパターンと、名指しした対象より下の階層で初めて一致するファイルには今までどおり適用する）。
`SPECOUT_INCLUDE_EXTENSIONS` 設定で Discovery BFS の検索対象拡張子をカンマ区切りで指定する（デフォルト: 空 = 全ファイル）。
`SPECOUT_MAX_WAVE_DEPTH` 設定で Discovery BFS で調べる波の数を指定する（デフォルト: `6`。探索の起点の波から数え、初回は第0〜5波）。上限に達したら一時停止せず、残りのシンボルを「## 打ち切り記録」（理由 `wave-limit`）に残して自動完了する。上げて `/xddp-04-specout {CR}` を再実行すると、探索中・完了済みのどちらの repo にも新しい上限が反映され（`specout_bfs.py extend`）、打ち切ったところから探索を続ける。下げた場合はその CR の探索で使っている値のまま続ける。シンボルを足して調べる場合は `/xddp-investigate {CR} ripple --adopt {シンボル}` で新しい調査を作る（新しい調査は第0波から上限の波数まで調べる）。
`SPECOUT_MAX_AFFECTED_FILES` 設定で変更の中心として扱うファイル数の目安を指定する（デフォルト: `20`）。Step A-Document（SPO の仕上げ）で、シードが直接参照するファイルの数（`seed_direct_file_count`）がこの値を超えたら CR の分割を推奨する警告を出す（処理は止めない）。また、シードが直接参照するのに下調べの台帳に無いファイルを自動で追加下調べ（`xddp-specout-prelim-agent` を `PRELIM_MODE: additional` で repo ごとに1回起動）するのは、repo ごとの累計でこの件数まで（台帳の工程 `追加下調べ` の行と、追加下調べが関係なしと判断した `work/prelim-gap-reviewed.md` の行を数える。再実行しても、この値を上げない限り累計を超えて追加下調べしない）とし、超えた分と追加下調べでも資料にできなかった分は SPO §5.0 の ⚠️ と §9 で知らせる。件数はシードの呼び出し元の数に比例する。依頼調査（`/xddp-investigate document`）では、展開後のファイル数がこの値を超えたら人に確認し、エージェントを1回この件数までに分けて起動する（累計の上限にはしない）。資料を書く LLM は下調べ・追加下調べ・依頼調査だけで、波紋調査の結果はスクリプトが SPO §5.0（最大30行）・モジュール資料の「波紋調査の結果」（最大30行）・人向けの全量 `ripple-summary.md`（上限なし）に反映する（行数の上限はスクリプトの定数で設定キーはない）。設計根拠は [docs/adr/ADR-0023-specout-two-layer-output.md](docs/adr/ADR-0023-specout-two-layer-output.md) を参照。
`SPECOUT_WAVE_HIT_BUDGET` 設定で1波で処理するヒットの予算（dedup・フィルタの後の件数）を指定する（デフォルト: `10000`。`0` で無制限）。超えた場合は関数シンボル → 値シンボル、各々ヒットの少ない順に予算に収まるシンボルを採り、残りを「## 打ち切り記録」（理由 `hit-budget`）に残す（`/xddp-investigate {CR} ripple --adopt {シンボル}` で新しい調査として追える）。判定エンジン・検索ツールによらず同じ値。`SPECOUT_LLM_HIT_BUDGET` 設定で1波で LLM 分類に回すヒットの上限を指定する（デフォルト: `160`〔暫定。`SPECOUT_CLASSIFY_CHUNK_SIZE` × `SPECOUT_CLASSIFY_PARALLEL` の1バッチ分〕。`0` で無制限。超えた分は理由 `llm-budget`）。
`SPECOUT_SLICE` 設定で判定エンジンを指定する（デフォルト: `auto`）。`auto`＝tree-sitter があればスライス判定（`specout_slice.py`。完全スライス・computed）、無ければ規則判定（標準ライブラリのみ。discovery-log に警告を残す）。`off`＝常に規則判定。どちらも C / C++ / Python のヒットに LLM を使わず、それ以外の言語のヒットだけが `xddp-specout-classifier-agent` に回る。`SPECOUT_SLICE_IGNORE_CALLS` はスライス判定で影響なしとみなす呼び出しの正規表現（関数名に完全一致。例: ログ出力・メモリ確保・assert。デフォルト: 空）、`SPECOUT_SLICE_H_AS` は `.h` の解析言語（`auto`/`c`/`cpp`。`auto` は C++ のソースがあれば `cpp`。デフォルト: `auto`）、`SPECOUT_SLICE_PYTHON_BIN` は `specout_slice.py` を実行する Python（tree-sitter を入れた Python。デフォルト: 空＝自動検出。`pip install -r ~/.claude/skills/xddp-04-specout/scripts/requirements-slice.txt`）。予算と判定エンジンの設定は探索の開始時（`init`）の値で調査ごとの state に固定され、CR の途中で変えても反映されない（新しく作る調査には反映される。工程4a の初回の調査に反映するには `specout_bfs.py run-remove --run initial` で取り除いて最初から探索する。例外: tree-sitter を使えなくなった場合は、再実行時に人が選べば `switch-engine` で規則判定に切り替えて続けられる）。設計根拠は [docs/adr/ADR-0019-specout-static-slicer.md](docs/adr/ADR-0019-specout-static-slicer.md) を参照。
`SPECOUT_BACKEND` 設定で Discovery BFS の参照解決バックエンドを指定する（デフォルト: `auto`）。`auto`＝`index`（識別子索引。索引で引けないシンボルは rg・無ければ grep）、`grep`/`rg`＝明示指定（従来の挙動）、`ctags`/`global`/`lsp`＝静的解析バックエンド（段階2以降で実装予定・未実装時は grep へフォールバックし discovery-log と bfs-state.json に警告を記録）。マルチリポジトリでは `SPECOUT_BACKEND.{repo}` 形式で REPOS エントリ単位に上書きできる（未指定はグローバル値を継承）。`SPECOUT_BACKEND_BIN` は静的バックエンドの外部バイナリパス用に予約（段階2以降）。参照解決を差し替え可能にする設計判断は [docs/adr/ADR-0008-specout-backend-abstraction.md](docs/adr/ADR-0008-specout-backend-abstraction.md) を参照。
`REPOS:` マッピングでリポジトリ名とパスを定義する。エントリが1つの場合はシングルリポジトリ、2つ以上の場合はマルチリポジトリとして扱われ、cross/ 成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）が生成される。
`cross` はシステム予約名称であり `REPOS:` のキーとして使用してはならない。
（理由: REPOS: エントリが 2 つ以上ある場合、システムがリポジトリ間インタフェースを管理するための
仮想リポジトリとして `cross/` ディレクトリおよび関連成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）を
自動生成するため予約されている）
`DEVELOPMENT_MODE` 設定で開発モードを指定する（デフォルト: `change`）。
`change`: 既存コードへの変更（通常の CR）。工程4（スペックアウト）を実行する。
`new`: 新規開発（母体コードが存在しない状態からの開発）。工程4（4a・4b）をスキップする。
  また CRS・CHD・TSP の成果物文法が新規開発向けに切り替わる: CRS の仕様（SP）は
  Before/After 対比ではなく単一の「仕様」記述になり、CHD の Before 設計・回帰確認項目、
  TSP の回帰テストは「新規コンポーネント間の依存整合性」の確認に置き換わる
  （既存動作が存在しないため）。

`CR_PROFILE` 設定で CR 規模に応じた工程テーラリングを指定する（デフォルト: `full`）。
`full`: 標準の 12 工程を実行する。
`quick`: 工程2+3を統合・工程4を簡略化（探索深さは full と同一。SPO 文書の記載量のみ削減）・工程5は
  per-repo の方式比較を省略する軽量パス（マルチリポジトリで cross SPO がある場合、工程5では
  リポジトリ間インタフェース契約として cross DSN のみ生成し CRS へフィードバックする。単一リポジトリ
  または cross SPO がない場合は工程5全体をスキップする）。
  AI レビューは各工程1ラウンドに制限され、レビュアーの合格基準も quick 用（網羅性のみ緩和）に切り替わる。
  `latest-specs/` 更新・project-rulebook 抽出・`xddp-close` による昇格は quick でも省略しない。
  個別の CR では `/xddp-01-init` の `--profile` 引数で上書き可能。工程途中での切替は `/xddp-set-profile` を使用する。
  適用基準例：変更ファイル数5以下・単一機能・外部I/F変更なし・既存テスト修正のみ。

`MIN_COVERAGE` 設定でテストカバレッジの合格閾値（%）を指定する（デフォルト: `80`）。この値以上で自動合格、未満の場合は人が承認するかテストを追加するかを選択する。100 に設定すると旧動作（100% 強制）に戻る。
廃止: `REPO_NAME` と `MULTI_REPO` は使用しない（旧設定キー）。
`FIX_STRATEGY` 設定で工程種別ごとの AI レビュー修正方針を指定する（デフォルト: PLAN=`ideal`、その他=`balanced`）。
`ideal`（本来あるべき姿を優先）/ `balanced`（複数案は人に確認、AI エージェントでは `ideal` と同等）/ `efficiency`（最小インパクト優先）。`REVIEW_MAX_ROUNDS` と同形式の種別ごとの dict で指定する。
`MD2EXCEL_PYTHON_BIN` 設定で `crs_md2excel.py`（CRS→Excel変換）・`xddp-excel2md/SKILL.md`（Excel→Markdown変換）実行用の Python インタプリタパスを指定する（デフォルト: 空＝`command -v python3 || command -v python` で自動検出）。両者とも `openpyxl`（非標準ライブラリ）に依存するため、デフォルトの `python3` に `openpyxl` が無い環境向けの設定。`specout_slice.py` のスライス判定（tree-sitter）は `SPECOUT_SLICE_PYTHON_BIN` を使う。他の決定的処理スクリプトは標準ライブラリのみで動作する。

`VCS_TYPE`（default: `auto`）, `VCS_BRANCH_PREFIX`（default: `feature/`）,
`VCS_BASE_BRANCH`（default: `auto`。新規作業ブランチの起点 ref。`auto` はリモート既定ブランチ／
`main`／`master`の順で実行時に解決する）,
`VCS_AUTO_BRANCH`（default: `true`）, `VCS_COMMIT_ON_STEP`（default: `7,10`）
（`xddp-07-code`/`xddp-08-verify`/`xddp-10-test-run`/`xddp-close` で使用。現状 Git のみブランチ作成・
コミット・巻き戻しを実行し、Git 以外の VCS（Subversion 等）は `none` と同様に全操作を no-op とする。
内部は VCS 種別ごとの関数群＋ディスパッチにより、将来他 VCS を関数群の追加だけで拡張できる設計。
設計根拠は [docs/adr/ADR-0011-vcs-abstraction.md](docs/adr/ADR-0011-vcs-abstraction.md) を参照）

`VERIFY_LINT_COMMAND`／`VERIFY_BUILD_COMMAND`／`VERIFY_TYPECHECK_COMMAND`（いずれも default: 空文字列
＝未設定＝実行しない）で工程8（静的検証）が実行する lint・ビルド・型検査コマンドを指定する。
`REPOS:` が複数エントリの場合は `VERIFY_LINT_COMMAND.{repo}` 等（`SPECOUT_BACKEND.{repo}` と同型の
ドット接尾辞キー）でリポジトリ単位に上書きできる（未指定はグローバル値を継承）。
`VERIFY_TOOL_TIMEOUT_SEC`（default: `600`）は各コマンドに個別に適用されるタイムアウト秒数
（3コマンド合計の共有バジェットではない）。`xddp-07-code`（Step B）・`xddp-08-verify`（Step A）・
`xddp-10-test-run`（b-1 実装バグ再検証）が `xddp_verify_tools.py` を実行し、終了コードで
PASS/FAIL を決定的に判定する（cross/ 検証は対象外）。設計根拠は
[docs/adr/ADR-0015-verify-real-tool-execution.md](docs/adr/ADR-0015-verify-real-tool-execution.md) を参照。

## 開発ルール

### 決定的処理はスクリプト・意味判定はLLM

決定的処理（帳簿管理・件数照合・状態更新・機械検査等）は Python スクリプトに実装し、LLM は意味判定
（言語知識を要する分類・レビュー）に専念させる。新規に決定的処理を追加する際は、まず
`crs_md2excel.py`（`xddp-md2excel/scripts/`）や `xddp_progress.py`・`artifact_lint.py`（`xddp-common/scripts/`）
等の既存スクリプトを先例として参照すること。

### 人の依頼は LLM の関係判断で拒否しない

人が明示的に依頼した調査・資料化・追記は、LLM が変更要求（CRS 等）との関係を確かめられなくても
拒否・スキップしない。スキル・エージェント・スクリプトを設計するときは次を守ること。

- LLM の判断は「確認できず」として記録するだけにし、「関係なし」「影響なし」と断定させない（成果物にもそう書かせない）。
- 追記するか等の要否は LLM に判断させず、人に尋ねる。
- LLM の判断で扱いを変えたもの（影響の一覧から外した等）は、人が見直せる形で残す（台帳・成果物の注記等）。
- 人の依頼が無い自動の経路（例: 工程4a の追加下調べ）で LLM が対象を絞り込むのは構わない。ただし人が依頼すれば、その絞り込みより依頼を優先する。
  量を抑えるための既定の絞り込み（例: 除外パターンでプロダクションコードに限る）も、人が名指しした対象そのものには適用しない
  （ディレクトリを名指しした場合、その配下の量を抑える既定の絞り込みは効かせてよい。配下も知りたければ人がそこを名指しする）。
- 拒否はしないが、LLM の確認で依頼と食い違う点があれば、根拠を添えて質問・助言する（決めるのは人）。根拠を挙げられない推測は伝えない。

理由: LLM の判断は複雑なパターン以外では信頼できるが、調べきれていないだけで実は関係がある場合がある。
人がわざわざ依頼したものは関係する可能性がある。

### 変更前の計画・合意（必須）

`ClaudeCode/.claude/` 以下のファイル（skills / agents）を変更する前に、以下の手順を必ず守ること。

1. `plans/_template.md` をコピーして `plans/PLAN-YYYYMMDD-{description}.md` を作成する（ファイル名は英語のみ・日本語不可）
2. 変更内容・対象ファイル・Before/After・影響範囲を記載する
3. プランの AI レビューを実施し、結果を `plans/review/PLAN-YYYYMMDD-{description}-review.md` に保存する
4. 人がプランとレビュー結果を確認・修正し、ステータスを「承認済み」に更新する
5. 承認を確認してから実装（ファイル編集）を開始する

**Claude はプランファイルの承認確認前に `ClaudeCode/.claude/` 以下を編集してはならない。**

### 実装後の関連ドキュメント更新（必須）

`ClaudeCode/.claude/` 以下のファイルを変更した後、以下のドキュメントを必ず確認し、内容が古くなっていれば更新すること。

| 変更内容 | 更新が必要なドキュメント |
|---|---|
| スキルの動作・手順を変更 | `README.md` のフェーズ説明テーブル |
| コマンドの引数・出力を変更 | `README.md` の使い方セクション |
| テンプレートの構造を変更 | `README.md` のプロジェクト固有ファイル一覧、`CLAUDE.md` の該当説明 |
| `xddp.config.md` テンプレートに設定キーを追加・削除 | `CLAUDE.md` の「xddp.config.md の位置付け」節、`README.md` |
| 任意の変更 | 承認済みプランファイルのステータスを「実装完了」に更新 |

### ツール修正後のハーネス実行（必須）

`ClaudeCode/.claude/` 配下（skills / agents）を変更したら、最低限 `make test`（L1〜L3・**0トークン**・
数秒。`refcheck` ＋全 unittest）を実行し緑を確認する。スキルの分岐・手順など**挙動に関わる変更**の
場合は、該当工程を `make smoke-full PHASE=NN`（隔離HOME・予算ガード）で検証してからプランのステータスを
「実装完了」にする。`make smoke-full`（L4/L5）は `claude` CLI とトークン予算を要するが、
2026-07-26 に校正済み・有効化済みであり、成果物の構造的健全性を advisory チェックとして検証する。
詳細は [README.md](README.md) の「開発時テストハーネス（make）」節を参照。

### 新規スキル作成のルール

xddp スキルを新規作成する際は、必ず以下を守ること:

1. `ClaudeCode/.claude/skills/xddp-templates/xddp.skill-template.md` をひな形として使用する
2. `ClaudeCode/.claude/skills/<skill-name>/SKILL.md` として作成する（ハイフン区切りディレクトリ名を
   使用する。小文字・数字・ハイフンのみ使用可——ドット・大文字・空白は不可。Anthropic Agent Skills
   仕様が `name:` に課す許可文字集合と同一であり、ディレクトリ名と `name:` を完全一致させるため）
3. フロントマターに `name:` を追加する。値はディレクトリ名と完全一致させること
   （例: ディレクトリ `xddp-12-newphase` なら `name: xddp-12-newphase`）
4. 引数セクションの直後に以下の CR 解決行を含めること:
   `Read \`~/.claude/skills/xddp-common/SKILL.md\`, apply "## CR Resolution" with $ARGUMENTS → let \`CR\`, \`REST_ARGS\`.`
5. CR を使わないスキル（xddp-fill-rulebook、xddp-plan-review 等）はこの限りではない
6. `user-invocable: false` をフロントマターに追加することで「ユーザーが直接起動するスキルではない」役割を表現できる（xddp-common が使用）

### 新規エージェント作成のルール

xddp サブエージェント（`ClaudeCode/.claude/agents/*.md`）を新規作成する際、および既存エージェントの
`tools:` を変更する際は、必ず以下を守ること:

1. **`tools:` には Process に明示された手順が実際に必要とするツールのみを列挙する（最小権限原則）。**
   特に `Bash` は任意コマンド実行（書き込み・削除・ネットワークアクセスまで可能）で事故半径が最大の
   権限であるため、Process 内に外部コマンド実行を伴う具体的な手順がある場合のみ付与する。「念のため」
   「将来使うかもしれない」という理由での付与は禁止する。
2. `Grep`/`Glob` は読み取り系で事故半径が小さいため、Process に明示手順がなくても記述外の補助参照
   （関連実装の周辺確認等）のために保持してよい。
3. `Edit` は生成物（`OUTPUT_FILE`）の部分修正に使われうるため、Process 手順が「Write」のみでも
   保持してよい。
4. 既存エージェントの `tools:` を見直す場合も同じ基準を適用し、Process 全文を通読したうえで
   不要な権限がないか確認する。

### ファイル生成の承認

skills, agents, template のファイルを作成するときに write 確認を人にせず、書き込みます。

### 相互参照のルール

`ClaudeCode/.claude/skills/` `ClaudeCode/.claude/agents/` 配下のファイルで他ファイル・自ファイルの
内容を参照する際、行番号（`SKILL.md:123` `L123-145` `123行目` 等）を使用してはならない。
編集のたびに行番号がずれ、AIが実行時に誤った行を読む・照合に失敗するリスクがあるため、
見出し名（`## Step A` 等）・変数名（`ALTERNATIVES_TASK` 等）・番号付きセクションラベル
（`1. **「ユースケース一覧」セクション**` 等、当該ファイルが既に持つ安定した参照アンカー）で参照すること。

### 実行時ファイルへの設計根拠・履歴の混入禁止

`ClaudeCode/.claude/skills/` `ClaudeCode/.claude/agents/` 配下の `.md` には、
**「今何をすべきか」のみを書く**。以下は書いてはならない。

- プランへの参照（`PLAN-YYYYMMDD-*`）
- 変更履歴・削除された旧手順の説明（「旧 Step A にあった〜は削除した」「従来は〜だった」）
- 手順の実行に不要な設計根拠

理由: 実行時に不要な情報がトークンを消費するだけでなく、LLM が「今の手順」と
「過去の経緯」を区別できず、廃止済み手順を復活させるリスクを生む。
設計根拠は `docs/adr/`、変更経緯は `plans/` に記録する。
`tools/harness/refcheck.py` 検査F が機械検査する（`templates/`・`scripts/`・
`xddp-plan-review` は除外）。

### 適用ドメインの中立性（必須）

**XDDPツールはすべてのソフトウェア開発ドメインを対象とする汎用ツールである。**
Webシステム・業務システム・組み込み・制御システム・科学技術計算・ゲーム開発など、
特定のドメインを前提とした記述をしてはならない。

#### チェックリスト：変更前に必ず確認すること

**用語・表現の偏りチェック：**

| 偏った表現（NG） | ドメイン中立な表現（OK） | 理由 |
|---|---|---|
| API・APIシグネチャ | インタフェース（API・関数シグネチャ・プロトコル・バスI/F等） | APIはWeb/サービス間通信を想起させる |
| マイグレーション・初期データ | 移行手順・初期状態定義 | マイグレーションはRDB前提の用語 |
| クラス図（必須） | データ型関連図（OOP言語の場合） | C言語等の手続き型にクラスは存在しない |
| ER図 | データモデル（ER図/データ構造定義） | ER図はRDB前提 |
| CRUD | データアクセスマトリクス（CRUD/Read-Write/Set-Clear等） | CRUDはDB操作の用語 |
| DBスキーマ変更がある場合 | データ構造・インタフェース変更がある場合 | DBを持たないシステムでも構造変更は発生する |

**成果物・セクションの網羅性チェック：**

- 新しいセクション・成果物を追加するとき、**すべてのドメインで意味を持つか** を確認すること
  - 例：「グローバル変数一覧」は組み込み・業務・Webいずれにも適用できる → OK
  - 例：「ER図（必須）」はRDBを持たないシステムには適用できない → 条件付きまたは代替表現が必要
- 条件付きセクションの条件文がドメイン固有になっていないか確認すること
  - NG例：「RDBを持つ場合は必須」→ OK例：「永続化ストア（DB・ファイル・フラッシュ等）がある場合」

**図種別の適用条件チェック：**

- classDiagram：OOP言語（Java・C++・Python等）の場合のみ必須。C言語では構造体関係図として使用可
- stateDiagram：状態管理がある場合のみ（全ドメインで適用可）
- sequenceDiagram：呼び出しフローがある場合のみ（全ドメインで適用可）
- erDiagram：RDB（リレーショナルDB）がある場合のみ
- タイミング図：リアルタイム・組み込み系では重要度が高い（オプション扱いにしない）

#### 書き方の原則

ドメイン固有の例示が必要な場合は、以下のいずれかで対処する。

1. **複数ドメインの例を並べる：** `（例：DB書き込み/レジスタ書き込み/ファイルI/O）`
2. **プレースホルダーで抽象化：** `{モジュール名}` `{インタフェース名}` `{永続化先}`
3. **条件分岐で説明：** `RDB: ～／組み込み: ～／業務システム: ～`

### 後方互換性ポリシー

このツールは現在開発中であり、ドラスティックな変更が入る場合がある。
**後方互換性は保証しない。**
既存の CR・成果物が新しいフォーマット・仕様に追従できない場合は、再実行・再生成を求めることを許容する。
プラン作成・変更実装において、後方互換性を考慮する必要はない。

### ステップ番号体系

スキルファイル番号は「担当する工程の先頭番号」であり、成果物ディレクトリ番号
（`{CR_PATH}/01_requirements/` 〜 `10_test-results/`）とも一致する。
複数の細分工程を担当するスキルは、工程をサブ番号（4a/4b 等）で表す。
スキル番号に欠番はない（工程10 = テスト実行系は xddp-10-test-run が担当）。

| スキル | 実行する工程（progress.md番号） | 主な成果物ディレクトリ |
|--------|-------------------------------|---|
| xddp-01-init | 工程1（要求書作成） | 01_requirements/ |
| xddp-02-analysis | 工程2（要求分析・整理） | 02_analysis/ |
| xddp-03-req | 工程3（変更要求仕様書作成） | 03_change-requirements/ |
| xddp-04-specout | 工程4（4a スペックアウト + 4b CRS更新） | 04_specout/ |
| xddp-05-arch | 工程5（実装方式検討） | 05_architecture/ |
| xddp-06-design | 工程6（6a 変更設計書作成 + 6b CRSフィードバック・TM生成） | 06_design/ |
| xddp-07-code | 工程7（コーディング）+ 工程8（静的検証）※工程8は xddp-08-verify でも単体実行可 | 07_coding/, 08_code-review/ |
| xddp-08-verify | 工程8（静的検証）— 人が手動実行する場合（xddp-07-code の自動検証と同一内容） | 08_code-review/ |
| xddp-09-test | 工程9（テスト設計） | 09_test-spec/ |
| xddp-10-test-run | 工程10（10a テスト実行 + 10b 不具合修正 + 10c 不具合フィードバック） | 10_test-results/ |
| xddp-11-specs | 工程11（最新仕様書作成） | latest-specs/（CR外） |
| xddp-close | CR クローズ（気づき集約・知見ログ更新） | —（CR外・随時実行） |
| xddp-abort | CR 中止（気づき記録・VCS 後片付け案内・progress.md への終端状態記録） | —（CR外・随時実行。CR を再開しない前提の終端操作。`xddp-close` の「一時中断」とは異なる） |
| xddp-update-knowledge | 工程対象外・随時実行 | —（CR外・随時実行） |
| xddp-review | 単体AIレビュー（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-plan-review | プランAIレビュー→修正ループ（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-revise | 人レビュー指摘の反映（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-feedback | arch/design/test/code の内容をCRSへ反映（工程対象外・随時実行） | —（CR外・随時実行。CRS・design/code時はTMも更新。codeは事前にCHDも直接更新） |
| xddp-status | 進捗確認（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-set-profile | CR_PROFILE の切替（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-excel2md | USDM形式Excel → Markdown変換（工程対象外） | —（CR外・随時実行） |
| xddp-md2excel | CRS Markdown → USDM形式Excel生成（工程対象外） | —（CR外・随時実行） |
| xddp-crs-view | CRS を階層的に閲覧できる HTML ビューア／CLIツリーを生成する（工程対象外・随時実行。Excel を要さない） | —（CR外・随時実行） |
| xddp-sync-design | コード→DSN再生成・リビジョン追加（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-codemap | モジュールカタログ生成・更新（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-survey | 工程対象外・随時実行 | `{XDDP_DIR}/survey/`（CR外・随時実行。人の選択で knowledge／latest-specs へ昇格） |
| xddp-investigate | 工程対象外・随時実行（下調べの完了後） | `04_specout/{repo}/ripple/{調査}/`（波紋調査の追加・採用・取り消し・取り除き。採用が変わると SPO を仕上げ直す）、モジュール資料・台帳（依頼調査。人の依頼による資料の追加） |
