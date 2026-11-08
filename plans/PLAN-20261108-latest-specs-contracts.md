# PLAN-20261108-latest-specs-contracts

作成日: 2026-11-08（PLAN-20261103-contract-audit の段階3 の P4）  
ステータス: 草案 / 承認待ち / 承認済み / **実装完了**

---

## 1. 背景・目的

### 1.1 起きていること

約束の監査（[docs/xddp-contract-audit-2026-11.md](../docs/xddp-contract-audit-2026-11.md)）は、仕様・用語・カタログの約束（A4）に46件の指摘を挙げた。そのうち A4-12・A4-13・A4-15 は P1、A4-20 は段階2b の候補なので、残りの43件を P4 としてこのプランに割り当てた（報告書の 8.2）。P1（c15454f）と P3（PLAN-20261105-lessons-backlog。2026-11-08 実装完了・未コミット）の実装の後の状態を見て書く。

食い違いのもとは、次の6つにまとまる。
- **工程11 が工程4a のモジュール資料の置き場所を知らない:** 工程4a は統合パスでは `SPO-{CR}.md` の `## 2.A.` …に、分割パスでは `modules/{名前}-spo.md` という**ファイル**に資料を書く。工程11 の SKILL と mod-agent は `modules/` の**ディレクトリ**だけを資料とみなし、`spec_version_delta.py` は別の名前（ケバブ名）でファイルを引く。そのためモジュール仕様がほぼ作られず、既存のモジュールが毎回廃止候補になる（A4-1〜A4-5）。モジュールの名前と latest-specs のディレクトリ名の対応も、工程5・6・survey・工程11 で決め方が違う（A4-14・A4-16・A4-37）。
- **材料の節の名前が書く側と違う:** structure.md の材料の「クラス図」・architecture.md の材料の別名・deployment.md の材料・SPO §4.3 の `source` 注記・cross SPO §3 の小見出しの意味が、SPO のテンプレートと合わない（A4-6・A4-18・A4-22・A4-32・A4-36・A4-38）。日本語の見出しのファイル名の決め方も無い（A4-23）。
- **latest-specs の変更を LLM が一覧に書き、close がその一覧で `{DOCS}` から書き戻す:** GATE で削除した仕様・一覧に無い人の編集・分割実行の前の回の更新を、close の C0-3 が `{DOCS}` の版で書き戻す（A4-8・A4-9・A4-10）。中止した CR・承認されなかった survey の latest-specs は、後の CR の close で `{DOCS}` に昇格する（A4-43・A4-44）。
- **survey (c) の書く順序と書く先:** 承認の前に latest-specs へ書き、衝突は latest-specs だけで判定し、architecture.md の追記は `{DOCS}` に届かず、レビューの後に書く（A4-11・A4-30・A4-44・A4-45・A4-47）。module-catalog の無い欄を読む（A4-33）。
- **工程11 の廃止候補・分割実行・レビューの入力:** 今の CR が触れていないモジュール・ユースケースを毎回廃止候補にする（A4-4・A4-42）。分割実行の継続の対象が逆で、メモの置き場所・値の形が決まっていない（A4-39・A4-40・A4-41）。SPEC レビューに SPO が渡らない（A4-17）。precheck・compare が比べる範囲と書き換える欄が違う（A4-7・A4-25・A4-46）。
- **記述が実物と違う:** 存在しない節の参照・lint と違うキーの一覧・パスの書き方・説明（A4-19・A4-21・A4-24・A4-26〜A4-29・A4-31・A4-34・A4-35）。

### 1.2 割り当てた指摘（P4）

指摘の詳細は、監査の報告書の付録（A4 のやり直し版の「3. 指摘」と、検証者 V3・V5 の報告）にある。行番号は監査の対象リビジョン ecb54c4 の値で、今のファイルの行とは違う。今のファイルで残っていることは、2026-11-08 にこのプランを書くときに確かめた（A4-9 を除く43件すべて。A4-9 は 3.5 の直し方で、LLM の振る舞いに依存しなくなる）。

| # | 重大度 | 内容（要約） | 直す節 |
|---|---|---|---|
| A4-1 | 🔴 | 工程11 が `modules/` のディレクトリだけをモジュール資料とみなす（工程4a はファイルを書く） | 3.1 |
| A4-2 | 🔴 | 統合パスの §2.A… を工程11 が読まない | 3.1 |
| A4-3 | 🟡 | `SPECOUT_MODULES` を `modules/` のディレクトリ名から取る | 3.1 |
| A4-4 | 🟡 | 廃止モジュールの照合先がディレクトリで、既存のモジュールが毎回廃止候補になる | 3.4 |
| A4-5 | 🔵 | precheck が SPO ファイルをケバブ名で引く | 3.1・3.2 |
| A4-6 | 🟡 | structure.md の材料の見出し「クラス図」が SPO に無い | 3.3 |
| A4-7 | 🔵 | compare が SPO の無いモジュールにも版の下限を当てはめる | 3.2 |
| A4-8 | 🔴 | GATE で削除した仕様を close C0-3 が `{DOCS}` から書き戻す | 3.5 |
| A4-9 | 🟡 | 分割実行の前の回の更新が「更新仕様書ファイル一覧」から外れうる（検証は「判断できず」） | 3.5 |
| A4-10 | 🟡 | GATE で人が直接編集した、一覧に無いファイルが C0-3 で戻る | 3.5 |
| A4-11 | 🟡 | survey (c) の architecture.md の追記が `{DOCS}` に届かず、後の close で上書きされうる | 3.7 |
| A4-14 | 🟡 | 工程5・6 が latest-specs を SPO のモジュール名のまま探す | 3.1 |
| A4-16 | 🟡 | survey の `MODULE_KEBAB` と CR のモジュール名の決め方が違う（catalog で解決したときの規則も無い） | 3.1・3.7 |
| A4-17 | 🟡 | SPEC レビューに SPO が渡らない | 3.9 |
| A4-18 | 🔵 | SPO §4.3 の `source` 注記を書く側がいない | 3.3 |
| A4-19 | 🔵 | 「Section 3-0」「Section 3-4」の参照先が無い | 3.11 |
| A4-21 | 🔵 | module-catalog の入れ子のディレクトリと、specout が照合に使う値（第1要素）が合わない | 3.10 |
| A4-22 | 🔵 | architecture.md の材料の節の別名が SPO と違う | 3.3 |
| A4-23 | 🔵 | 日本語の見出しのケバブ変換が決まっていない | 3.3 |
| A4-24 | 🔵 | 自動修正の対象キーと lint の必須キーが違う | 3.11 |
| A4-25 | 🔵 | compare が §1 の「バージョン」行を書き換えない | 3.2 |
| A4-26 | 🔵 | 設定テンプレートの latest-specs のパスに `{repo}/` が無い | 3.11 |
| A4-27 | 🔵 | 下調べエージェントの `LATEST_SPECS_DIR` の説明に `{XDDP_DIR}/` が無い | 3.11 |
| A4-28 | 🔵 | abort の説明（C3.5/C3.6 で latest-specs へ昇格）が close の動作と違う | 3.11 |
| A4-29 | 🔵 | sync-design の説明（工程11 がコードを参照する）が工程11 の動作と違う | 3.11 |
| A4-30 | 🔵 | code-knowledge-boundary の書き手の欄が survey の実際の書き先と違う | 3.7 |
| A4-31 | 🔵 | glossary をテンプレートから作ると、見本の行が用語数に数えられる | 3.11 |
| A4-32 | 🔵 | overview/deployment.md の材料の節を SPO のどこも書かない | 3.3 |
| A4-33 | 🔵 | survey が module-catalog の無い欄「主要ファイル」を読む | 3.7 |
| A4-34 | 🔵 | module-catalog が無いときの動作の説明がスクリプトと違う | 3.10 |
| A4-35 | 🔵 | ユースケースのシーケンス図から overview のシーケンス図への相対リンクが誤り | 3.11 |
| A4-36 | 🔵 | cross SPO §3 の小見出しはレベルごとなのに、工程11 はフロー名として使う | 3.3 |
| A4-37 | 🔵 | mod-agent が CHD に無い欄「変更対象モジュール名」を探す | 3.1 |
| A4-38 | 🔵 | cross インタフェース仕様の `provider`・`affected-repos` の材料が Step CROSS に書かれていない | 3.3 |
| A4-39 | 🟡 | 分割実行 B の継続で、処理済みのモジュールに限定する（継続の対象が逆） | 3.8 |
| A4-40 | 🔵 | 分割実行メモの置き場所「progress.md §15」が無い | 3.8 |
| A4-41 | 🔵 | `RESUME_UR_LIST` の値が UR かケバブ名かで揺れる | 3.8 |
| A4-42 | 🟡 | 過去の CR のユースケースが毎回廃止候補になる | 3.4 |
| A4-43 | 🟡 | 工程11 の後に中止した CR の latest-specs が、後の CR の close で `{DOCS}` に昇格する。中止した CR は並行 CR 保護で進行中とみなされ続ける | 3.6 |
| A4-44 | 🟡 | survey (c) が承認の前に latest-specs へ書き、却下の扱いが無い | 3.7 |
| A4-45 | 🔵 | survey Step 7 がまだ書いていない architecture.md をレビューの対象に入れる | 3.7 |
| A4-46 | 🔵 | precheck が spec.md の全体と SPO §2 だけを比べる | 3.2 |
| A4-47 | 🟡 | survey の衝突判定は latest-specs だけを見るが、写し先は `{DOCS}` | 3.7 |

### 1.3 方針

1. **工程11 の入力（SPO のどのモジュール資料を、latest-specs のどのディレクトリへ）は、スクリプトの1つの一覧で決める。** LLM は一覧に従って書くだけにする（CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。工程4a の配置の読み方は、書く側の `specout_bfs.py` に置き、工程11・工程5・6・survey は同じ一覧を使う（3.1）。
2. **モジュールの同一性は、モジュールの範囲（`REPO_PATH` 相対のモジュールディレクトリ。1ファイルのモジュールはそのファイルのパス）で決める。** latest-specs の spec.md に `module-dir` を書き、名前の決め方が違っても同じ範囲なら同じ仕様に書く（3.1）。
3. **latest-specs の変更は、工程11 の最初の実行の時点の状態と比べてスクリプトが記録する。** LLM が書く一覧に頼らない。close の C0-3・中止・気づきの収集は、この記録を読む（3.5・3.6）。
4. **廃止候補は、母体から消えたモジュールと、今の CR が取り下げ・廃止を示したユースケースに絞る。** 今の CR が調べていないことを理由には候補にしない（overview の architecture.md の既存の規則と同じ。3.4。7. の 1.）。
5. **survey (c) は、承認の後にだけ latest-specs・`{DOCS}` に書く**（3.7）。

### 1.4 目的

- 1.2 の43件を直す。
- 工程4a → 工程11 → close の受け渡しを、スクリプトの定義とテストで守る形にする（3.13 の再発防止）。

---

## 2. 変更対象ファイル

パスの `CC/` は `ClaudeCode/.claude/` の略。

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `CC/skills/xddp-04-specout/scripts/specout_bfs.py` | 修正 | モジュール資料の一覧の関数 `module_docs`（3.1）。統合パスから移した資料の深い見出しのレベル（`_section_to_module_doc`。3.1 (f)）。catalog の見出しの読み方とファイル→モジュールの照合（3.10） |
| `CC/skills/xddp-11-specs/scripts/spec_version_delta.py` | 修正 | `sources`・`spec-dir` サブコマンド（3.1）。precheck・compare の入力・比べる範囲・書き換える欄（3.2）。材料の節の名前（3.3） |
| `CC/skills/xddp-11-specs/scripts/spec_changes.py` | 追加 | `{DOCS}` にだけある既存の仕様の写し（`seed`）・latest-specs の基準の記録（`snapshot`）・変更の記録（`record`）・中止の後片付け（`revert`）（3.5・3.6） |
| `CC/skills/xddp-close/scripts/promote.py` | 修正 | `sync-baseline` サブコマンド（C0-3。C0-4 が読む一覧を JSON で出す）・削除候補に工程11 の削除を足す・削除候補一覧の見出し（3.5） |
| `CC/skills/xddp-close/scripts/collect_insights.py` | 修正 | 工程11 の一覧の見出し・読み方を `docs_layout` から import する（3.5・3.13） |
| `CC/skills/xddp-common/scripts/docs_layout.py` | 修正 | モジュール仕様のディレクトリ名・シーケンス図のファイル名の規則、`module-dir` のキー、工程11 の記録の節の見出しと読み方、進行中の CR の判定 `cr_in_progress`（3.1・3.3・3.4・3.5・3.6・3.13） |
| `CC/skills/xddp-common/scripts/ai_index.py` | 修正 | 用語数で見本の行を数えない（3.11） |
| `CC/skills/xddp-common/scripts/artifact_lint.py` | 修正 | モジュールの spec.md の必須キーに `module-dir`（3.1）。survey の作業場所のパスは今のパスの解釈（`latest-specs` の後を相対パスにする）で読めるので、コードは変えずテストを足す（3.7） |
| 上のスクリプトのテスト（`test_specout_bfs.py`・`test_spec_version_delta.py`・`test_spec_changes.py`〔追加〕・`test_promote.py`・`test_collect_insights.py`・`test_docs_layout.py`・`test_ai_index.py`・`test_artifact_lint.py`） | 修正・追加 | 3.12・3.13 |
| `CC/skills/xddp-11-specs/SKILL.md` | 修正 | Step 0・OV・MOD・CROSS・REV・GATE・DONE（3.1〜3.6・3.8・3.9） |
| `CC/agents/xddp-specs-mod-agent.md` | 修正 | 入力・処理対象・材料の節・ディレクトリ名・廃止候補・survey モードの入力（`MODULE_DIR`・`SPECS_REPO_DIR`）と書き先（3.1・3.3・3.4・3.7） |
| `CC/agents/xddp-specs-uc-agent.md` | 修正 | 命名・バージョンの参照・廃止候補・`RESUME_UR_LIST`・シーケンスの参照・`related-modules` に `spec_dir`（3.1・3.4・3.8・3.11） |
| `CC/agents/xddp-survey-agent.md` | 修正 | module スコープの「ディレクトリ」欄に `MODULE_DIR` を書く（3.1 (e)・3.7） |
| `CC/skills/xddp-11-specs/templates/11_module-spec-template.md`・`11_module-structure-template.md`・`11_overview-architecture-template.md`・`11_overview-deployment-template.md`・`11_system-use-case-sequence-template.md` | 修正 | `module-dir`・節の名前・生成条件・`source:`・参照の書き方（3.1・3.3・3.11） |
| `CC/skills/xddp-close/SKILL.md` | 修正 | Step C0-3・C0-4・D（3.5） |
| `CC/skills/xddp-abort/SKILL.md` | 修正 | latest-specs の後片付け・説明の誤り（3.6・3.11） |
| `CC/skills/xddp-survey/SKILL.md` | 修正 | Step 2・3・4・6・6.5・7・8（3.1・3.7） |
| `CC/skills/xddp-05-arch/SKILL.md`・`CC/skills/xddp-06-design/SKILL.md` | 修正 | Step 0 の latest-specs の探し方（3.1） |
| `CC/skills/xddp-review/SKILL.md` | 修正 | `spec` の参照ファイルに SPO（3.9） |
| `CC/skills/xddp-common/reviewer-checklists/SPEC.md` | 修正 | SPECOUT_MODULES の参照を SPO §8 に（3.9） |
| `CC/skills/xddp-status/SKILL.md` | 修正 | 分割実行メモの表示（3.8） |
| `CC/skills/xddp-01-init/templates/00_progress-management-template.md` | 修正 | 工程11 の削除の記録の節（3.5） |
| `CC/skills/xddp-01-init/templates/xddp.config.md` | 修正 | latest-specs のパス（3.11） |
| `CC/agents/xddp-specout-prelim-agent.md` | 修正 | `LATEST_SPECS_DIR` の説明（3.11） |
| `CC/skills/xddp-04-specout/SKILL.md` | 修正 | module-catalog が無いときの説明（3.10） |
| `CC/skills/xddp-codemap/SKILL.md`・`templates/module-catalog-template.md` | 修正 | ディレクトリの書き方（3.10） |
| `CC/skills/xddp-sync-design/SKILL.md` | 修正 | 工程11 の説明（3.11） |
| `CC/skills/xddp-update-knowledge/SKILL.md` | 修正 | glossary の新規作成で見本の行を置き換える（3.11） |
| `CC/skills/xddp-rules/code-knowledge-boundary.md` | 修正 | architecture.md の書き手（3.7） |
| `test-fixtures/**` の latest-specs・`{DOCS}/*/specs` のモジュールの spec.md | 修正 | `module-dir` を足す（3.12） |
| `test-fixtures/scratch-workspace-min/seeds/phase11-single`・`phase11-multi`・`phaseClose-single` | 修正 | 工程11 のシードに SPO の §2.A…・台帳・`work/module-assignments.json`、close のシードに `.latest-specs-baseline.json`（3.12） |
| `README.md` | 修正 | 3.14 |
| `docs/adr/ADR-0036-latest-specs-inputs-and-change-record.md` | 追加 | 3.14 |
| `docs/adr/README.md` | 修正 | 3.14 |
| `docs/xddp-contract-audit-2026-11.md` | 修正 | 8.2 の P4 の名前（3.14） |

---

## 3. 変更内容

### 3.1 工程11 の入力の一覧（A4-1・A4-2・A4-3・A4-5・A4-14・A4-16・A4-37）

**変更前:**
- 工程11 Step OV は `SPECOUT_MODULES` を `04_specout/{repo}/modules/` の**ディレクトリ名**から取る。mod-agent は `modules/*/` の下に SPO ファイルがあるモジュールだけを「SPO ありモジュール」とし、ディレクトリ名をケバブ化して latest-specs のディレクトリ名にする。統合パス（`SPO-{CR}.md` の `## 2.A.` …）の読み方は無い。
- `spec_version_delta.py precheck` は、latest-specs のディレクトリ名に `-spo.md` を付けて `modules/` の中を探す。
- 工程5・6 Step 0 は、SPO サマリーから読んだモジュール名のまま `latest-specs/{repo}/{mod}/spec.md` を探す。
- survey は `MODULE_KEBAB` を自分の規則（`src/auth` → `src-auth`）で決める。catalog で解決したときの規則は無い。
- mod-agent の「SPO なし・CHD あり」は、CHD に無い欄「変更対象モジュール名」を探し、無ければ AI の照合にする。

**変更後:**

**(a) モジュール資料の一覧（書く側 `specout_bfs.py`）:** 関数 `module_docs(output_dir, cr)` を足す。`04_specout/{repo}/` の配置（`module-documentation.md`「## 配置判定（成長型）」）を読み、モジュールごとに次を返す。
- `name`（台帳のモジュール名）・`module_dir`（`REPO_PATH` 相対のモジュールディレクトリ。台帳と `work/module-assignments.json` の組）
- `layout`: `integrated`（§2.X… の節）／`split`（`modules/{name}-spo.md`）／`index`（索引と `modules/{name}/*-spo.md`）
- 資料の場所（`integrated` は SPO と節の文字、`split` はファイル、`index` は索引とサブモジュール資料のファイル）

台帳に無いモジュール（資料の無いもの）は返さない。配置の判定・節の切り出し・§2.X.n → §2.n の対応は、`assemble-spo` が使っている関数（`_spo_state_paths`・`_module_sections`・`_section_to_module_doc` の対応）をそのまま使う（書く側と読む側で同じ定義）。

**(b) 工程11 の一覧（読む側 `spec_version_delta.py sources`）:** 新しいサブコマンド。
```
spec_version_delta.py sources --spo-dir {CR_PATH}/04_specout/{repo} --cr {CR} \
    --latest-specs {XDDP_DIR}/latest-specs/{repo} [--docs-specs {DOCS}/{repo}/specs] \
    [--repo-path {REPO_PATH} [--exclude PATTERNS] [--include-ext EXTS] [--xddp-dir {XDDP_DIR}]] [--chd FILE ...] \
    [--out-dir DIR [--module-template FILE]] --out OUT_JSON
```
- `specout_bfs.module_docs` を import して呼ぶ（`chd_cochange.py` が `xddp-04-specout/scripts/` を import するのと同じ形）。
- モジュールごとに `spec_dir`（latest-specs のディレクトリ名。(c)）・`module_dir`・`layout`・`source_files`（mod-agent・precheck が読む資料のファイル。どの配置でも1つ）・`sequences`（`### 4.5 モジュール内シーケンス図` の小見出しと、そのファイル名。3.3）・`existing_spec`（latest-specs、無ければ `{DOCS}` の spec.md のパス。無ければ空）を返す。
- **資料の形をそろえる（`--out-dir` を渡したとき）:** 工程11 は `--out-dir {CR_PATH}/04_specout/{repo}/work/spec-sources/` を渡す（CLAUDE.md「ファイルの置き場所」の中間ファイルの位置。`xddp_review_brief.py` がレビューの対象から外す）。
  - `split`: 元のファイル `modules/{name}-spo.md` を `source_files` にする（写さない）。
  - `integrated`: 分割パスと同じ形（`MODULE_TEMPLATE` の §2〜§4）に直した資料 `{name}-spo.md` を `--out-dir` に書き、それを `source_files` にする。変換は `_section_to_module_doc`（(f) の見出しのレベルの修正の後のもの）を使う。テンプレートは `--module-template`（既定は `__file__` から決める `xddp-04-specout/templates/04_specout-module-template.md`）、版・日付は SPO サマリーの値を使う。
  - `index`: 索引とサブモジュール資料を、1つの資料 `{name}-spo.md`（`MODULE_TEMPLATE` の §2〜§4 の形）にまとめて `--out-dir` に書く。サブモジュール資料の §2〜§4 の各節の本文は、同じ節の下に「**{subdir}:**」の行を先に置いて連結する。§4.5 の小見出しは `{subdir}／{元の小見出し}` の名前で、§4.5 の1つ下の深さに並べる。索引の Section 3（サブモジュール間シーケンス図）は §4.5 の小見出し「サブモジュール間」、Section 4（サブモジュール間の関係図）は §4.2 の先頭に置く。
  - 工程11 の LLM・precheck は、どの配置でも同じ形の資料を1つ読む。
- **`--out-dir` を渡さないとき**（工程5・6）: 資料を書かず、`integrated`・`index` の `source_files` は空にする（工程5・6 は `existing_spec` だけを使う）。
- **`--chd`（SPO の無いモジュール。A4-37）:** CHD の「## 2. 変更対象ファイル一覧」の表を、列の見出しの名前（「ファイルパス」「変更種別」「リポジトリ」）で引く。「リポジトリ」列があれば今の repo の行だけを使う。パスは `specout_bfs._norm_path` と同じ規則で `REPO_PATH` 相対にする。各ファイルを次の順に1つに振り分ける。
  1. SPO の一覧のモジュールの `module_dir` に当たる（ディレクトリ境界で前方一致、またはファイルのパスと一致）→ 振り分けない（SPO のあるモジュールとして扱う）
  2. latest-specs・`{DOCS}` の既存の spec.md の `module-dir` に当たる → 最長のものに割り当て、`chd_only`（`spec_dir` とファイルの一覧）に返す
  3. どれにも当たらない → `chd_unmatched` に返す。mod-agent が、`module-dir` の無い既存の仕様との AI の照合で扱い、照合の結果（当てたもの・当てられなかったもの）を OUTPUT_FILE に記録する
- **`--repo-path`:** 既存のモジュール仕様のうち、`module-dir` が `REPO_PATH` に無いもの、またはその下に工程4a と同じ除外・拡張子の規則（`--exclude`・`--include-ext`。`specout_bfs.list_repo_files` を使う）を適用したファイルが1つも無いものを `missing_module_dirs` に返す（3.4）。ただし、spec.md の `last-updated-cr` が進行中の他の CR（`--xddp-dir` の下の progress.md を `docs_layout.cr_in_progress` で判定。3.6）のものは返さず、`protected_by_concurrent_cr` に返す（その CR がまだ母体に入れていないモジュールでありうるため）。
- **`module_dir` が `.`（リポジトリ直下のファイルのモジュール。工程4a の `module-documentation.md`「## モジュールの決め方」の規則）:** `.` は「ディレクトリを持たないファイル（リポジトリ直下のファイル）」だけを指すものとして扱う。CHD の振り分けの前方一致では、`/` を含まないパスだけが当たる。`missing_module_dirs` では、リポジトリ直下のファイル（規則の適用後）が1つも無いときだけ返す。
- **`conflicts`:** 次を返す。GATE で人に示す。
  - 同じ `spec_dir` に別の `module-dir` のモジュールが当たるもの（ケバブ名の衝突）
  - 同じ `module-dir` を持つ既存のディレクトリが複数あるもの（(c) の `resolve_spec_dir` の選び方で1つを選び、残りを示す）

**(c) latest-specs のディレクトリ名（`docs_layout.py` に1つ定義）:**
- 関数 `module_spec_dir_name(name)`: キャメルケースを区切り、`/`・`_`・空白を `-` に、小文字にし、連続する `-` を1つにする。予約名（`overview`・`cross`・`system`）と一致すれば `mod-` を付ける。
- 関数 `resolve_spec_dir(name, module_dir, roots)`: `roots`（latest-specs、`{DOCS}` の順）の既存の spec.md のフロントマター `module-dir` が `module_dir` と一致するディレクトリがあれば、その名前を使う。先の root にあるものを優先し、同じ root に複数あれば名前の順で最初のものを選んで、残りを重複として返す（`sources` の `conflicts`・`spec-dir` の stderr）。`module_dir` が空か、一致するものが無ければ `module_spec_dir_name(name)`。
- 定数 `MODULE_DIR_KEY = "module-dir"`。

**(d) `module-dir` を書く:** mod-agent は spec.md のフロントマターに `module-dir: "{module_dir}"` を書く（`11_module-spec-template.md` に足す）。値は `REPO_PATH` 相対で末尾の `/` を付けない。リポジトリ直下のファイルのモジュールは `.`（工程11・survey とも同じ値。(b) の `.` の扱い）。工程11 は一覧の `module_dir`、survey は入力 `MODULE_DIR`（(e)）の値を書く。1ファイルのモジュールはそのファイルのパスにする。モジュールの範囲が決まらないとき（survey のファイル名一致で複数のファイルを採用した場合）は空文字列にする（共通の祖先を範囲とみなすと、広すぎる範囲が `resolve_spec_dir`・CHD の振り分け・`missing_module_dirs` に使われ、関係のない既存の仕様と同一とみなされうるため）。`artifact_lint.py` の必須キーに、モジュールの spec.md だけ `module-dir` を足す（値は空でもよい）。

**(e) 呼び出し側:**
- **工程11 Step OV・MOD:** repo ごとに Step OV の冒頭で `sources`（`--out-dir`・`--repo-path`・`--xddp-dir`・`--chd` あり）を1回実行し、`SPEC_SOURCES[{repo}]` とする。`SPECOUT_MODULES` は一覧のモジュールの `spec_dir` にする（A4-3）。Step MOD のモジュール数の合計も一覧から数える。mod-agent には `SPEC_SOURCES_FILE`（JSON のパス）を渡し、mod-agent は処理対象・資料・ディレクトリ名をそこから取る（A4-1・A4-2）。mod-agent の「{module-kebab} の導出ルール」の節は、一覧の `spec_dir` を使う記述に置き換える。「SPO なし・CHD あり」は一覧の `chd_only`・`chd_unmatched` から取る（A4-37）。CHD のパスは、Step REV と同じ「## Discover CHD Files」で取って `--chd` に渡す。
- **`{DOCS}` にだけある既存の仕様:** Step 0 で `spec_changes.py seed` を実行し、latest-specs を更新の前の状態にそろえる（3.5）。mod-agent は latest-specs の既存の仕様を、今までどおり既存として更新する（版・変更履歴を引き継ぐ）。
- **uc-agent:** `SPEC_SOURCES_FILE`（全 repo）を渡す。`related-modules` には、SPO のモジュール名ではなく一覧の `spec_dir` を書く（工程2 の `domain_refs.py` が仕様のディレクトリ名と照合するため）。
- **precheck:** `--spo DIR` を `--sources OUT_JSON` に替え、一覧の `source_files` を読む（A4-5）。
- **工程5・6 Step 0:** 「SPO サマリーからモジュール名を読む」を、`sources`（`--out-dir` なし）の `existing_spec` を `CURRENT_SPECS_REFS` にする形に替える。`existing_spec` が空のモジュールは「現状仕様なし（初回 CR）」と記録する（A4-14）。
- **survey（A4-16）:**
  - **Step 2:** モジュールごとに `MODULE_DIR` を決める。catalog で解決したときは catalog の「ディレクトリ」の値、ディレクトリ一致はそのディレクトリ、ファイル名一致で1件ならそのファイルのパス、複数件なら空（いずれも `REPO_PATH` 相対・末尾の `/` なし）。`MODULE_KEBAB`（SURVEY の置き場所の名前）は `spec_version_delta.py spec-dir --latest-specs … --docs-specs … --name {module名} --module-dir {MODULE_DIR}`（(c) の `resolve_spec_dir` の CLI）で決める。Step 2 の「`MODULE_KEBAB` の導出」の3項と `NORMALIZE()` の「ケバブ化の流用」の記述は、この呼び出しに置き換える（`NORMALIZE()` はファイル名一致の照合にだけ残す）。
  - **Step 4:** survey-agent に `MODULE_DIR` を渡す。survey-agent は module スコープの「## 1. モジュール概要」の「ディレクトリ」欄に `MODULE_DIR` を書く（`.` はそのまま `.`）。`MODULE_DIR` が空（範囲が決まらない）なら、「ディレクトリ」欄には今の規則（`TARGET_FILES` の共通の祖先）で書き、表の直後に決まった文言の注記 `> モジュールの範囲: 未確定（複数のファイルを採用）` を書く（「ディレクトリ」欄は `MODULE_FALLBACK` の決定も読むので、欄の値の形は変えない）。これで SURVEY 成果物が `module-dir` の出どころになる。
  - **Step 6（module・promote のどちらの経路でも）:** `SURVEY_FILE` の「## 1. モジュール概要」の「モジュール名」欄と「ディレクトリ」欄を読む。末尾の `/` を除く。`.` はそのまま `.` にする（工程11 と同じ値）。空・プレースホルダーのまま、または表の直後に上の注記があれば空にする。その値と「モジュール名」で `spec-dir` を実行して `SPEC_DIR` を決める。mod-agent には `MODULE_KEBAB: {SPEC_DIR}` と、新しい入力 `MODULE_DIR`（この値）を渡す。promote の経路は Step 1・2 を飛ばすが、SURVEY 成果物から同じ値を得る。

**(f) 統合パスから移した資料の見出しのレベル（書く側 `specout_bfs.py`）:** `_section_to_module_doc` は、移す節の見出し（`#### 2.A.8.n` → `### 4.n` 等）だけでなく、その下の深い見出し（`#####` 以下）も同じ段数だけ上げる。統合パスのモジュール内シーケンス図（`#### 2.A.8.5`）の小見出しが、直した後も `### 4.5` の1つ下に来る。`assemble-spo` が統合パスから分割パスへ移すときの資料も同じ関数で作るので、同じく直る。

**理由:** 工程4a の配置を工程11 の4か所（SKILL・mod-agent・precheck・レビュー）が別々に読んでいたのが A4-1〜A4-5 のもと。配置を知っている書く側の関数を1つにし、工程11 は一覧だけを見る。資料の形を1つにそろえるので、LLM・precheck は配置を読み分けない。名前の決め方の違い（CR は台帳の名前、survey は引数）は残るが、同じ範囲なら同じ仕様に書くので二重にならない（A4-16）。survey は promote の経路で Step 2 を飛ばすので、`module-dir` の出どころを SURVEY 成果物の欄にして、どちらの経路でも同じ値を読む。見出しのレベルは、読む側で深さを読み替えるより、書く側で正しい形に書くほうが、分割パスの資料と同じ規則で読める。

### 3.2 precheck・compare（A4-5・A4-7・A4-25・A4-46）

**変更前:** precheck は spec.md・structure.md・state-machine.md・sequences の既存のファイルの全体（§1 文書概要・関連ドキュメント・気づき・変更履歴を含む）と SPO の節を比べる。compare はベースラインのすべての `.md` を比べ、フロントマターの `version:` と変更履歴の直近の行だけを書き換える。

**変更後:**
- precheck は、既存のファイルのうち SPO から作る節だけを比べる。比べる節は、ファイルの種類（spec.md・structure.md・state-machine.md・sequences）ごとに `spec_version_delta.py` の定数で持つ。どの種類も、テンプレートの文書概要・関連ドキュメント・気づき・変更履歴の節を除いた節とする（spec.md は `## 2. 機能概要`〜`## 6. 制約・前提条件`）。定数の節の名前は、`11_module-*-template.md` の見出しとテストで突き合わせる（3.13。A4-46）。
- compare に `--modules`（一覧の `spec_dir` のうち SPO のあるもの）を足し、その下のファイルだけに下限を当てはめる。「SPO なし・CHD あり」のモジュールは対象外のまま（mod-agent の記述どおり。A4-7）。
- compare は、`## 1. 文書概要` の表の `| バージョン | … |` の行も書き換える（A4-25）。

**理由:** 文書概要・気づき・変更履歴は SPO から作らないので、比べると行数の変化の率が SPO の内容と関係なく変わる。spec.md だけ直すと、同じ型の誤りが他のファイルに残る。compare の下限は SPO で確かめたモジュールに当てる約束（mod-agent の「SPO なし」は PATCH 固定）なので、対象をスクリプトの引数で決める。バージョン行は、フロントマターと本文で版が食い違わないように一緒に書き換える。

### 3.3 材料の節の名前とファイル名（A4-6・A4-18・A4-22・A4-23・A4-32・A4-36・A4-38）

**変更前・変更後:**

| # | 変更前 | 変更後 |
|---|---|---|
| A4-6 | mod-agent・`FILE_TO_SPO_SECTION` は structure.md の材料に `### クラス図` を探す。SPO（モジュールのテンプレート）は `### 4.2 データ型関連図`。structure.md のテンプレートは題名「構造図（クラス図・データ構造）」・`## 2. クラス図`・その注記「SPO §2『現状仕様 → クラス図』」、spec.md のテンプレートの関連ドキュメントの表は「クラス図・データ構造定義」 | 材料の名前を `データ型関連図` にする。structure.md のテンプレートの題名を「構造図（データ型関連図・データ構造）」、`## 2. クラス図` を `## 2. データ型関連図`、注記を「SPO の `### 4.2 データ型関連図` から取得する」にする。spec.md のテンプレートの表も「データ型関連図・データ構造定義」にする（CLAUDE.md「適用ドメインの中立性」の用語） |
| A4-18 | 11-specs SKILL は、data-model.md の `source:` が SPO §4.3 の `source` 注記を引き継ぐと書く（SPO に注記を書く側がいない）。テンプレートの既定は `source: ai-inferred`（AI のマージ・推定を含むことを示し、SPO で確かめたら人が `spo` に変える） | SKILL の「注記を引き継ぐ」を消し、テンプレートの既定 `ai-inferred` のままにする（data-model.md は AI のエンティティ名の正規化を含むマージで作るので、テンプレートの意図が正しい）。テンプレートは変えない |
| A4-22 | architecture.md のテンプレートは材料を「モジュール依存・コンポーネント構成」と書く。SKILL は「`## 2.` または…」 | SKILL・テンプレートとも、SPO サマリーの `## 2. 全体アーキテクチャ図`（見出しの名前で探す。`## 2.A.` …のモジュール資料は含めない）にする |
| A4-23 | シーケンス図のファイル名は「ケバブ変換」とだけ書かれ、日本語の見出しは空になる | `docs_layout.py` に `seq_file_stem(heading)` を置く: 見出しを Unicode の NFC に正規化し、番号を除き、英字を小文字に、空白・`_` を `-` にし、英数字・`-`・かな・漢字以外を除く。空になれば `seq-{見出しの順番}`。既存のファイル名と比べる側（precheck・廃止候補の照合）も、ファイル名を NFC に正規化してから比べる（macOS のファイル名は NFD で返りうるため）。`sources` が `sequences` のファイル名をこの規則で返し、mod-agent・precheck はそれを使う。Step OV（SPO §3 の小見出し）・Step CROSS も同じ関数を使う（`sources` が `overview_sequences` も返す）。順番のフォールバックは見出しを並べ替えると名前が変わる限界があり、ADR-0036 に書く |
| A4-32 | SPO に「ハードウェア構成・デプロイ構成」の節があれば deployment.md を作る（SPO に節が無い）。テンプレートは `source: spo` | 7. の 2. の決定（案A）: 工程11 は deployment.md を作らない。人が書いたものは保持し、昇格する。SKILL の生成の項とテンプレートの生成条件を「人が書くビュー」に書き換える。テンプレートの `source:` を `manual`（use-case の description のテンプレートが使う既存の値）にし、変更履歴の初版の行を「人が作成」にする |
| A4-36 | Step CROSS は cross SPO §3 の小見出しをフロー名としてファイル名にする（小見出しはレベルごと: `### 3.1 {レベル名}レベルのシーケンス図`） | ファイル名は、小見出しのレベル名（「レベルのシーケンス図」の前）を `seq_file_stem` に通したもの（例: `repository-seq.md`）にする。廃止候補の照合も同じ名前で行う |
| A4-38 | Step CROSS は `provider`・`affected-repos` の材料を書かない | 材料は cross SPO §4「共有インタフェース一覧」の提供リポジトリ・消費リポジトリの列とする。SPO に無い新しいインタフェースは cross CHD の「実装依存関係」の表から取る。どちらにも無ければ空にして PENDING に記録する（GATE で人に示す） |

**理由:** 材料の節の名前は、書く側（SPO のテンプレート）が正で、読む側がそれに合わせる（3.13 の 2.）。書く側のいない材料（A4-18・A4-32）は、読む側の記述を消すか、人が書く扱いにする。A4-32 で SPO に節を足さない理由は 7. の 2.。ファイル名の規則は、工程11 の3か所（MOD・OV・CROSS）と precheck が同じ名前を作れるよう、`docs_layout.py` の1つの関数にする。

### 3.4 廃止候補（A4-4・A4-42）

**変更前:**
- mod-agent: latest-specs の既存のモジュールのうち、今の CR の `modules/*/` に無いもの（`source: survey` と並行 CR を除く）を廃止候補にする。GATE で「保持」を選ぶと `status: unverified` を付ける。
- uc-agent: 既存のユースケースのうち、今の CRS に同じケバブ名の UR が無いものを廃止候補にする。「保持」を選ぶと `status: orphaned` を付ける。どちらの値も読む側はいない。
- 一方、Step OV の architecture.md は「今回 specout していないモジュールの情報は保持する」と決めている。

**変更後（7. の 1. の人の決定）:**
- **モジュール:** 廃止候補は `sources` の `missing_module_dirs`（`module-dir` が母体に無い、またはその下に工程4a と同じ除外・拡張子の規則を適用したファイルが1つも無い。3.1 (b)）に限る。スクリプトが決める。今の CR が調べていないモジュールでも、母体から消えていれば候補にする（調べていないことを理由に候補にするのではなく、母体の事実で決める）。今の CR がモジュールのファイルをすべて削除した場合は、工程11 は工程7 の後に実行するので、母体からファイルが消えていてこの条件に入る。CHD の「変更対象ファイル一覧」で判定しない（CHD の表は変えたファイルしか持たず、モジュールの全体を母集合にできない）。`module-dir` が空の仕様は候補にしない（範囲が決まらない）。並行 CR 保護（`last-updated-cr` が進行中の他の CR のものは除く）はスクリプトが行う（3.1 (b) の `protected_by_concurrent_cr`。GATE で「他 CR 進行中 — スキップ」として示す）。mod-agent のモジュールの廃止候補の手順（`modules/*/` との照合・並行 CR 保護・`source: survey` の除外）は、`missing_module_dirs` と `protected_by_concurrent_cr` を OUTPUT_FILE に記録する手順に置き換える。`source: survey` の除外はやめる（候補にする理由が「今の CR が調べていない」から「母体から消えた」に変わり、survey 由来の仕様でも母体から消えていれば廃止を意味するため）。
- **ユースケース:** 廃止候補は (i) 「関連UR」の行がすべて今の CR のもので、その UR が今の CRS に無いもの（工程11 の再実行で UR を取り下げた場合）と、(ii) 今の CRS の UR が既存のユースケースの廃止・置き換えを述べているもの（uc-agent の判断。理由と UR を PENDING に書く）、に限る。過去の CR の UR だけのユースケースは候補にしない。
- GATE で「保持」を選んだときの `status:` の付記をやめる（読む側がいない。人が保持を決めたものは何もしない）。
- GATE の文言「今回 CR の specout 対象に含まれていません（廃止候補）」を、候補にした理由（母体にディレクトリが無い／母体に対象のファイルが無い／UR を取り下げた／UR が廃止を述べる）を示す形に替える。
- architecture.md の「サイレント廃止リスク」の注記はそのまま残す（棚卸しの CR の推奨）。

**理由:** 今の判定では、CR が1つのモジュールだけを直しても、他のすべてのモジュール・過去のユースケースが毎回候補に出る。人が毎回「保持」を選ぶか、誤って削除する（削除は A4-8 で戻るが、3.5 の後は本当に消える）。CLAUDE.md「人の依頼は LLM の関係判断で拒否しない」の向きでも、LLM の判断（ii）で消すのではなく、人に候補として示すだけにする。

### 3.5 latest-specs の変更の記録と close C0-3（A4-8・A4-9・A4-10）

**変更前:**
- 工程11 Step DONE で、LLM が「## 工程11 更新仕様書ファイル一覧」に生成・更新したファイルを書く（既存の節を上書き）。GATE で削除したもの・一覧に無い人の編集は載らない。分割実行で前の回のファイルを載せるかは決まっていない。
- close C0-3 は、一覧に無いファイルを `{DOCS}` から latest-specs に写す（LLM の手順）。C2 の削除候補は、`{DOCS}` にあって latest-specs に無いモジュール・ユースケースのディレクトリだけ。

**変更後:**
- **`{DOCS}` にだけある既存の仕様（`spec_changes.py seed`）:** 工程11 Step 0 で、`snapshot` の前に実行する。今の CR の repo（`AFFECTED_REPOS`）・cross（`HAS_CROSS`）・system について、`{DOCS}` の写しにあって、latest-specs に無く、基準にも無いファイルを latest-specs へ写す（基準にあって今は無いファイルは、今の CR の削除なので写さない。分割実行・C0-4 の B による再実行で、GATE で削除したものを書き戻さないため。基準がまだ無い最初の実行では、この条件は無い）。また、進行中の他の CR（`docs_layout.cr_in_progress`。3.6 の並行 CR 保護と同じ条件）の「## 工程11 削除した仕様書ファイル一覧」にあるものも写さない（その CR の未昇格の削除を戻さない）。基準があれば（再実行）、写したファイルを基準にも写した内容の SHA-256 で足す（今の CR の変更と数えない）。これで mod-agent・uc-agent・Step OV は、`{DOCS}` にだけある仕様も既存として更新し、版・変更履歴を引き継ぐ。
- **基準（`spec_changes.py snapshot`）:** 工程11 Step 0 で、`{CR_PATH}/.latest-specs-baseline.json` が無いときだけ、latest-specs の全ファイルの相対パスと SHA-256 を書く（工程11 の最初の実行の時点の状態）。あれば何もしない（分割実行・C0-4 の B による再実行でも、最初の基準を使う。A4-9）。
- **記録（`spec_changes.py record`）:** 基準と今の latest-specs を比べ、progress.md の次の2つの節を作り直す（`latest-specs/…` のパス）。
  - `## 工程11 更新仕様書ファイル一覧`: 足した・内容が変わったファイル
  - `## 工程11 削除した仕様書ファイル一覧`（新しい節。progress のテンプレートの更新一覧の後に足す）: 基準にあって今は無いファイル
  - どちらの節も、progress.md に無ければ作る（更新一覧は「## 次に実行すべきコマンド」の前、削除一覧は更新一覧の後）。作り直す節なので、無ければ作る（3.8 の分割実行メモと同じ扱い）。
- 工程11 Step DONE は、LLM が一覧を書く代わりに `record` を実行する（GATE の削除・人の編集・前の回の更新が入る。A4-8・A4-9・A4-10）。Step DONE の「system/ ファイルの記録確認（必須チェック）」は消す（スクリプトが全部を記録する）。
- **close C0-3（`promote.py sync-baseline`）:** C0-3 の LLM の手順を、新しいサブコマンドにする。
  1. 先に `spec_changes.py record` を実行する（工程11 の後・close の前の人の編集も入れる）。
  2. `AFFECTED_REPOS`・cross（`HAS_CROSS`）・system について、`{DOCS}` の写しのうち、更新一覧にも削除一覧にも無いファイルを latest-specs へ写す（削除したものを書き戻さない。A4-8）。
  3. 写したファイルは、基準の SHA-256 も写した内容に合わせる（C0-3 で取り込んだものを、次の `record` で今の CR の変更と数えないため）。
  4. stdout に JSON で `protected_files`（更新一覧）・`deleted_files`（削除一覧）・`copied_files` を出す。一覧の読み方は `docs_layout.py` の関数（3.13）。
- **close での失敗の扱い:** `record`・`sync-baseline` が終了コード非0（基準が無い・壊れている等）で終わったら、close SKILL は stderr を示し、`xddp_progress.py close-state --state "⏸ 中断" --detail "Step C0-3: latest-specs の変更の記録に失敗（原因を解消後に /xddp-close {CR} を再実行）"` を記録して停止する（C0-3 の前は `{DOCS}` にも latest-specs にも書いていないので、再実行で続きからできる）。基準が無いのは工程11 を実行していない CR なので、案内に「`/xddp-11-specs {CR}` を先に実行する」を含める。
- **C2 の削除候補:** `promote_specs` は、今のディレクトリの比較に加え、削除一覧のうち `{DOCS}` の写しにあるものを削除候補に足す（ファイル単位。ディレクトリの下がすべて消えたものはディレクトリにまとめる）。cross・overview・モジュールの中のファイルの削除も、Step D で人に示される。`write_output_file` の見出し「## 削除候補一覧（system/use-cases・repo モジュールディレクトリ）」を「## 削除候補一覧（ディレクトリ・ファイル）」にし、各行に種別（ディレクトリ／ファイル）を書く。
- **close Step D:** 「ディレクトリ削除をファイル操作として直接実行する」を、削除候補の種別に従ってディレクトリまたはファイルを削除する記述にする。
- **C0-4:** `PROTECTED_FILES` は、progress.md を LLM が読む代わりに、`sync-baseline` の JSON の `protected_files` を使う（C0-4 の LLM の手順は Python の関数を呼べないので、スクリプトの出力で読み方を1つにする）。あわせて、`deleted_files` のうち `PULLED_FILES` にあるもの（この CR が削除し、他の CR が更新して昇格したファイル）を、Step D の削除候補に「他の CR が更新」の注記を付けて示す。
- **collect_insights.py:** 更新一覧の見出しと読み方を `docs_layout.py` から import する（P3 の 3.4.2 の読み方は変えない）。

**理由:** 一覧を LLM が書くと、削除・人の編集・前の回の更新が漏れても検出できない。基準と比べれば、誰が何をしたかに関係なく変更が分かる。C0-3 も決まった手順なのでスクリプトにする。`seed` は、latest-specs に無いだけで既存の仕様を新規に作り直し、C2 で `{DOCS}` の版と変更履歴を上書きするのを防ぐ（作業場所を新しく作った直後等）。

### 3.6 工程11 の後に中止した CR（A4-43）

**変更前:** abort は latest-specs に触れない。並行 CR 保護（Step OV・mod-agent・uc-agent）は、他の CR の progress.md に「## CR クローズ」が無ければ進行中とみなす。中止した CR には「## CR 中止」しか無い。

**変更後:**
- abort に Step を足す（Step 2 の VCS の案内の後）: `{CR_PATH}/.latest-specs-baseline.json` があれば、`spec_changes.py revert --docs {DOCS} --cr {CR} --dry-run` で、今の CR の latest-specs の変更と、ファイルごとの「戻す／消す／戻せない（理由）」を示し、次を尋ねる。
  > 1. 元に戻す（推奨）: 戻せるファイルだけを `{DOCS}` の内容に戻し、この CR が足したファイルを消す。戻せないファイルは一覧で示し、触らない
  > 2. 残す: 足したファイルは、後の CR の close で `{DOCS}` へ昇格しうる。既存のファイルの変更・削除は、後の CR の close（C0-3）で `{DOCS}` の版に戻る（後の CR も変えたファイルを除く）
- **`revert` の規則（安全な向きのものだけ戻す）:** 基準は SHA-256 しか持たないので、基準の時点の内容には戻せない。他の CR の未昇格の変更を消さないよう、次の条件のものだけを扱い、それ以外は「戻せない」として理由とともに返す。
  - 変更・削除したファイル: 基準の SHA-256 が `{DOCS}` の写しの SHA-256 と一致するとき（基準の時点で、他の CR の未昇格の変更が入っていなかった）だけ、`{DOCS}` の内容に戻す。変更したファイルは、さらに今のフロントマターの `last-updated-cr` が今の CR のときだけ戻す（基準の後に他の CR が上書きしたものを消さない）。
  - 足したファイル（基準に無く今ある）: フロントマターの `last-updated-cr` が今の CR のときだけ消す（基準の後に他の CR・survey (c) が足したものを消さない）。
  - 戻せない理由の例: 「基準の時点で `{DOCS}` と違う（他の CR の未昇格の変更を含みうる）」「`last-updated-cr` が別の CR」「`{DOCS}` に写しが無い」。
- 中止の記録（Step 4）に、選択と、戻した・消した・戻せなかったファイルの一覧を書く。
- 並行 CR 保護の「終わった CR」を「## CR クローズ」または「## CR 中止」を含むものにする。判定は `docs_layout.cr_in_progress(xddp_dir, cr)`（progress.md があり、どちらの節も含まないとき進行中）に1つ定義し、スクリプト（`sources`・`seed`）はそれを使う。LLM の手順の箇所は4か所ある: 11-specs SKILL Step OV（シーケンスの廃止候補）・mod-agent のシーケンスの廃止候補・mod-agent のモジュールの廃止候補・uc-agent。このうち mod-agent のモジュールの廃止候補はスクリプトへ移る（3.4）ので、残りの3か所の条件を同じ文言に直す。

**理由:** 中止した CR の仕様は CR で検証されていないので、`{DOCS}` に入れない。abort は取り消せない操作で、元に戻すのはファイルを消す向きの操作なので、7. の 3.（close では、混ざっても書き戻さない向きの誤りなので許容）と違い、他の CR の変更が混ざりうるファイルは戻さずに人に示す。並行 CR 保護では、中止した CR を進行中とみなし続ける理由が無い。

### 3.7 survey (c)（A4-11・A4-16・A4-30・A4-33・A4-44・A4-45・A4-47）

**変更前:** Step 6 で mod-agent が latest-specs に書き、衝突は latest-specs の `source` だけで判定する。Step 7 はまだ書いていない architecture.md もレビューの対象に入れる。Step 8 の承認の後、① モジュールを latest-specs から `{DOCS}` へ写し、② architecture.md の追記を latest-specs だけに書く。却下の扱いは無い。Step 2 は catalog の無い欄「主要ファイル」を読む。

**変更後:**
- **作業場所:** `{XDDP_DIR}/survey/{REPO_NAME}/specs-work/latest-specs/{REPO_NAME}/`（以下 `WORK_SPECS`）。パスに `latest-specs` の区切りを含めるのは、`artifact_lint.py` の必須キーの判定（`_relative_to_latest_specs` が `latest-specs` の後を相対パスにして、`overview/`・モジュールを見分ける）を、コードを変えずにそのまま効かせるため。`latest-specs` を名前に持たない場所に置くと、`overview/architecture.md` がモジュールの仕様と読まれて `module` が必須キーの欠けと報告され、Step 7 の自動修正（3.11 A4-24 の後は lint の結果のキーを足す）で誤ったキーが `{DOCS}` へ入る。`survey/{REPO_NAME}/**/SURVEY-*.md` の Glob（Step 0.5）とは、ファイル名が重ならない。
- **Step 2:** catalog で解決したときの `TARGET_FILES` は、catalog の「ディレクトリ」の下のファイル（`EXCLUDE_PATTERNS`・`INCLUDE_EXTENSIONS` を適用）とする（A4-33）。`MODULE_DIR`・`MODULE_KEBAB` は 3.1 (e) のとおり（A4-16）。
- **Step 3:** 確認ゲートの表に `MODULE_DIR` を示す。`spec-dir` が同じ `module-dir` の既存のディレクトリの重複を返したら、選んだ名前と残りを注記する。
- **Step 6（作業場所に書く）:** 衝突判定は latest-specs と `{DOCS}/{REPO_NAME}/specs/` の両方の spec.md の `source` を見る。どちらかが `spo` なら一括確認の対象にする（A4-47）。`SPEC_DIR` は 3.1 (e) のとおり SURVEY 成果物から決める。mod-agent の書き先は `WORK_SPECS` にする（mod-agent に入力 `SPECS_REPO_DIR` を足す。既定は `{XDDP_DIR}/latest-specs/{REPO_NAME}`）。mod-agent を起動する前に、`WORK_SPECS/{SPEC_DIR}/` を消し、既存の仕様があれば作業場所へ写し直す（latest-specs を優先、無ければ `{DOCS}`。再生成の PATCH の規則が働くように。前の回の残りを使わない）。
- **Step 6.5（新設。architecture.md の追記も作業場所で）:** 今の Step 8② の追記を、作業場所の `overview/architecture.md` に行う。追記の前に、作業場所の `overview/architecture.md` を毎回 `{DOCS}` の版（無ければテンプレート）で写し直す（却下した前回の追記を残さない）。
- **Step 7:** 作業場所のモジュールと `overview/architecture.md` をレビューの対象にする（A4-45）。
- **Step 8:** 承認されたら、① モジュールを作業場所から latest-specs と `{DOCS}` の両方へ写す。② architecture.md は `{DOCS}` へ作業場所の版を写す。latest-specs の architecture.md は、内容が Step 6.5 のもと（`{DOCS}` の版）と同じなら作業場所の版を写し、違えば（未昇格の CR の変更がある）同じ追記だけを行う（A4-11）。承認されなければ、latest-specs・`{DOCS}` に何も書かない（A4-44）。承認・却下のどちらでも、最後に `WORK_SPECS/{SPEC_DIR}/` と作業場所の `overview/architecture.md` を消す（SURVEY 成果物は残るので、`/xddp-survey {REPO_NAME} promote` の Step 0.5 → Step 4.5 → Step 6 の経路で作り直せる）。
- **code-knowledge-boundary:** `{DOCS}/{repo}/specs/overview/architecture.md` の書き手の欄「xddp-survey（追記のみ）」は、変更後の動作と合うので、追記の先（`{DOCS}` と latest-specs の両方）を書き足す（A4-30）。

**理由:** 承認の前に共有の場所へ書かなければ、却下の後始末が要らない。衝突は写し先の `{DOCS}` でも見る必要がある。作業場所は毎回写し直して最後に消すので、前の回の内容（却下したもの）が後の昇格に混ざらない。

### 3.8 分割実行メモ（A4-39・A4-40・A4-41）

**変更前:** Step DONE は分割実行メモを「progress.md §15」に書く（その節は無い。§15 は更新ファイル一覧も指す）。選択肢 B の継続は「`処理済みモジュール:` に限定する」。UR は `未処理UR:` で継続する。`RESUME_UR_LIST` は初回は「指定 UR」、継続は「URケバブ名一覧」。

**変更後:**
- 置き場所は progress.md の「## 工程11 分割実行メモ」節（無ければ「## 次に実行すべきコマンド」の前に作る）。更新ファイル一覧は 3.5 の節（「§15」の記述を消す。A4-40）。
- 選択肢 B は `未処理モジュール: {repo}: {spec_dir の一覧}` を書き、継続では `MODULE_SCOPE` を未処理モジュールに限定する（`処理済みモジュール:` は書かない。A4-39）。`xddp-status` の表示も `未処理モジュール` にする。
- `RESUME_UR_LIST`・`処理済みUR:`・`未処理UR:` の値は、CRS §2 の UR の ID をそのまま書く（例 `{CR}-UR-001`。A4-41）。

**理由:** 「§15」は無い節で、更新ファイル一覧とも番号が重なるので、見出しの名前で置き場所を決める。継続で要るのは「まだやっていないもの」なので、未処理の側を書く（処理済みを書くと、継続の対象を引き算で求める必要があり、逆に読まれた）。値の形は、UR は CRS の ID、モジュールは一覧の `spec_dir` に固定し、初回と継続で同じ値を使う。

### 3.9 SPEC レビューの参照ファイル（A4-17）

**変更前:** 工程11 Step REV・`/xddp-review … spec` は、SPEC レビューに CRS と CHD だけを渡す。チェックリストは SPO §2 との照合、SPECOUT_MODULES を求める。

**変更後:**
- バッチ1（モジュール仕様）: 対象の repo の `SPEC_SOURCES` の `source_files` を `REFERENCE_FILES` に足す。
- バッチ2（overview）: 対象の repo の `SPO-{CR}.md` を足す。
- バッチ3（cross）: `SPO-{CR}-cross.md` を足す。
- バッチ4（ユースケース）: 全 repo の `SPO-{CR}.md`（§3）を足す。
- `/xddp-review … spec`（「## 1d」）: 対象のファイルの repo について、同じ規則で足す。モジュールは `sources` を、工程11 と同じ `--out-dir {CR_PATH}/04_specout/{repo}/work/spec-sources/` を渡して実行して取る（統合パス・索引のモジュールでも資料が渡るように。同じ位置に同じ入力から作り直すので、内容は工程11 のものと同じ）。
- `SPEC.md` の項目8の SPECOUT_MODULES を「SPO サマリーの §8 調査済みモジュール一覧のモジュール」にする（レビュアーは SPO を読める）。

**理由:** チェックリストは SPO との照合を求めるのに、SPO が渡っていない。バッチごとに、そのバッチの仕様の材料になった SPO だけを渡す（モジュール仕様は形をそろえた資料、overview・ユースケースはサマリー、cross は cross SPO）。全部の SPO を渡すとトークンが増えるだけで、照合の対象は変わらない。

### 3.10 module-catalog（A4-21・A4-34）

**変更前:** catalog の見出し `### {name}/ — …` を `[^\s/]+` で読むので、`src/auth`・`src/db` は同じ `src` になる。確定ファイルのモジュールはパスの第1要素（`_module_dir_for_file`）で、catalog のディレクトリと合わない。ディレクトリを相対・絶対のどちらで書くかは決まっていない。04-specout SKILL は「catalog が空なら優先度差別化なしの通常 BFS」と書くが、スクリプトは近傍優先（`simple`）にする。

**変更後:**
- codemap: 「**ディレクトリ：**」は `REPO_PATH` 相対で書く（テンプレートの注記と Step 1f）。
- `specout_bfs.py`: 見出しは `### ` の後から ` — ` の前の `/` まで（`/` を含む名前）を名前にする。catalog の優先度の計算でファイルのモジュールを決めるときは、catalog のディレクトリにディレクトリ境界で前方一致する最長のものを使う（新しい関数。`_module_dir_for_file` は他の呼び出し元〔`confirmed_modules` 等〕があるので変えない）。
- 04-specout SKILL の説明を、スクリプトの動作（catalog が無いときは確定ファイルの近くのディレクトリを先にし、遠いものは後の波に回す。打ち切りの記録に残る）に合わせる（A4-34）。

**理由:** catalog は入れ子のディレクトリをモジュールとして書けるので、名前とファイルの照合も入れ子を区別する必要がある。`_module_dir_for_file` を直さず新しい関数にする理由は 6.（他の呼び出し元の結果を変えない）。説明はスクリプトの動作が正で、それに合わせる。

### 3.11 記述の食い違い（A4-19・A4-24・A4-26・A4-27・A4-28・A4-29・A4-31・A4-35）

| # | 変更前 | 変更後 |
|---|---|---|
| A4-19 | uc-agent「Section 3-0「共通命名ルール」参照」「機械的先決基準（Section 3-4 参照）」 | 命名は uc-agent に規則を書く（UR タイトルの英訳のケバブ。既存名を優先）。バージョンは同じ節の表を使う（参照を消す） |
| A4-24 | Step REV の自動修正の対象キーを4つ（`version`・`last-updated-cr`・`module`・`repo`）と書く | 「`LINT_RESULTS.frontmatter.missing_keys` に挙がったキー」と書く（必須キーの定義は `artifact_lint.py` の1か所） |
| A4-26 | 設定テンプレート `latest-specs/overview/data-model.md` | `latest-specs/{repo}/overview/data-model.md`（crud も同じ） |
| A4-27 | prelim-agent `LATEST_SPECS_DIR`: `latest-specs/{REPO_NAME}/` | `{XDDP_DIR}/latest-specs/{REPO_NAME}/` |
| A4-28 | abort「Step C3.5/C3.6 等により既に一部成果物が `latest-specs/` へ昇格済み」 | 「…`{DOCS}` へ昇格済み」 |
| A4-29 | sync-design「xddp-11-specs は現状コードと CHD を参照して」 | 「SPO・CHD・CRS を参照して（コードは読まない）」 |
| A4-31 | update-knowledge は glossary をテンプレートから作る（見本の行が残る）。`ai_index.glossary_term_count` は見本の行も数える | update-knowledge: 新規作成では見本の行を登録する用語の行に置き換える。`glossary_term_count`: 正式表記の列がプレースホルダー（`{…}`。`docs_layout` の既存の正規表現）の行を数えない |
| A4-35 | ユースケースのシーケンス図の「実装詳細参照」が `../../{repo}/overview/…` の相対リンク（latest-specs でも `{DOCS}` でも当たらない） | リンクにせず、`{repo}/overview/sequences/{feature}-seq.md`（latest-specs と `{DOCS}/{repo}/specs/` の位置）とパスで書く。uc-agent の「リンク参照を推奨」も「パスで参照」にする |

**理由:** どれも実物（スクリプト・他のスキルの動作・ファイルの位置）と違う記述で、実物を正として記述を合わせる。A4-24 は必須キーの定義を lint の1か所にし、SKILL に写しを持たない。A4-31 は、見本の行を数えないことをスクリプトで守り、新規作成でも見本の行を残さない。A4-35 は、latest-specs と `{DOCS}` で階層が違い、1つの相対リンクでは両方に当たらないのでパスで書く。

### 3.12 テスト・fixture

- `test_specout_bfs.py`: `module_docs` が統合・分割・索引の配置からモジュールを漏れなく返す。`_section_to_module_doc` が深い見出し（統合パスの §2.A.8.5 の `#####` の小見出し）も同じ段数だけ上げる（3.1 (f)）。catalog の入れ子のディレクトリ（`src/auth`・`src/db`）が別のモジュールになり、ファイルが最長一致で当たる。
- `test_spec_version_delta.py`: `sources` の各項目（`spec_dir`・`source_files`・`integrated` と `index` の資料の形・`--out-dir` なしのときの空の `source_files`・`chd_only`・`chd_unmatched`〔3つの振り分け・「リポジトリ」列の有無・パスの正規化〕・`missing_module_dirs`〔ディレクトリが無い・対象のファイルが無い・進行中の他の CR のものは `protected_by_concurrent_cr` に入る〕・`module_dir` が `.` のモジュール〔CHD の振り分けで `/` を含まないパスだけが当たる・`missing_module_dirs`・`resolve_spec_dir`〕・`conflicts`〔ケバブ名の衝突・`module-dir` の重複〕）。precheck が統合パス・索引・`_` を含む名前・日本語のシーケンス見出しで比べられる（A4-5・A4-6・A4-23 の再現の逆）。統合パスで2つ以上のシーケンスの小見出しを別々に比べられる。比べる範囲（spec.md・structure.md・state-machine.md・sequences。A4-46）。compare の `--modules` と §1 の行（A4-7・A4-25）。`spec-dir`（重複のときの選び方と stderr）。
- `test_spec_changes.py`（追加）: `seed` が `{DOCS}` にだけあるファイルを写し、進行中の他の CR の削除一覧にあるものを写さず、基準があれば基準にも足す。基準にあって latest-specs から消したファイル（今の CR の削除）を、再実行の `seed` が写さない。`snapshot` が2回目は書かない。`record` の更新・削除。progress.md に2つの節が無いとき、`record` が決まった位置に作る。`revert` の規則（基準 ≠ `{DOCS}` のファイルを戻さない・`last-updated-cr` が別の CR の変更・追加を戻さない／消さない・条件を満たすものだけを戻す／消す・`--dry-run` は書かない）。
- `test_promote.py`: `sync-baseline` が削除一覧・更新一覧のファイルを写さず、基準を更新し、JSON に `protected_files`・`deleted_files`・`copied_files` を出す。基準が無いと終了コード非0。削除候補にファイル単位の削除が入り、見出しと種別が変わる。
- `test_docs_layout.py`: `module_spec_dir_name`・`resolve_spec_dir`（root の優先順位・重複・`.`）・`seq_file_stem`（NFC・NFD の入力が同じ名前になる）・工程11 の節の読み方・`cr_in_progress`（progress.md が無い・「## CR クローズ」・「## CR 中止」・どちらも無い）。
- `test_ai_index.py`: テンプレートそのままの glossary の用語数が 0。
- `test_artifact_lint.py`: モジュールの spec.md の `module-dir`。survey の作業場所（`…/survey/{repo}/specs-work/latest-specs/{repo}/`）の `overview/architecture.md` が `repo` だけを要求され、モジュールの spec.md が `module`・`repo`・`module-dir` を要求される（3.7）。
- survey の経路は SKILL の手順なので unittest では確かめない。`spec-dir` に SURVEY の「モジュール名」「ディレクトリ」欄の値を渡すと、既存の仕様と同じ `module-dir` のディレクトリ名が返ることを `test_spec_version_delta.py` で確かめる（promote の経路と同じ入力）。
- fixture: `test-fixtures/**` のモジュールの spec.md に `module-dir` を足す（lint の必須キーのため）。値は fixture の母体のディレクトリ。
- smoke のシード（`make smoke-full` の入力）:
  - `phase11-single`・`phase11-multi`: SPO に §2.A…（統合パス）と台帳 `work/documented-files.md`・`work/module-assignments.json` を足す（`sources` がモジュールを返し、工程11 の主な変更を確かめられるように）。
  - `phaseClose-single`: `.latest-specs-baseline.json` を足す（C0-3 の `record`・`sync-baseline` が止まらないように）。中身は空の基準（工程11 の前に latest-specs が空だった状態）にする。latest-specs の `svc-a/mod_a2/` の2ファイルは「この CR が作った」ものとして `record` で更新一覧に入り、C0-3 で `{DOCS}` から書き戻されず（保護）、C2 で昇格する経路を smoke で確かめられる。
  - `phase05`・`phase06` のシードは変えない（latest-specs が無いので、`sources` がモジュールを返しても返さなくても「現状仕様なし」で、今と同じ結果）。

### 3.13 再発防止（PLAN-20261103-contract-audit 3.3）

**1. 書く側→読む側のテスト:**
- `assemble-spo` が書いた統合パス・分割パス・索引の SPO を、そのまま `sources` に通し、台帳のすべてのモジュールが `source_files` を持つ（A4-1・A4-2）。統合パスで2つ以上のシーケンスの小見出しを持つモジュールの `sequences` が小見出しごとに分かれる（3.1 (f)）。
- `MODULE_TEMPLATE`（`04_specout-module-template.md`）の見出しを読み、`FILE_TO_SPO_SECTION`・シーケンスの親見出しのすべての名前がテンプレートにある（A4-6 の型）。`11_module-*-template.md` の見出しを読み、precheck の比べる節（ファイルの種類ごと）がテンプレートにある（A4-46）。
- `spec_changes.py record` が書いた progress.md を、`promote.py sync-baseline`（C0-4 が使う JSON の `protected_files`・`deleted_files`）・`collect_insights.py` に通す。
- progress のテンプレート（`00_progress-management-template.md`）の「## 工程11 更新仕様書ファイル一覧」「## 工程11 削除した仕様書ファイル一覧」の見出しが、`docs_layout.py` の定数と一致する。
- `glossary-template.md` をそのまま `glossary_term_count` に通して 0（A4-31）。
- `module-catalog-template.md` の書式で書いた入れ子の catalog を `_parse_module_catalog` に通す（A4-21）。
- `11_*-template.md` のフロントマターが、そのパスの lint の必須キーをすべて持つ（A4-24 の型。`module-dir` を足し忘れない）。

**2. 共有の値の単一定義（`docs_layout.py`）:** latest-specs のモジュールのディレクトリ名の規則・`module-dir` のキー・シーケンス図のファイル名の規則・工程11 の2つの節の見出しと読み方。モジュール資料の配置の読み方は `specout_bfs.module_docs`（書く側）。
- 単一定義にしないもの: SPO の節の名前（`データ型関連図` 等）は、テンプレートが正で、スクリプトの定数をテストでテンプレートと突き合わせる（テンプレートは LLM が読むので Python の定数にできない）。

**3. refcheck の検査:** 足さない。今回の約束はテンプレートとスクリプトの間のもので、1. のテストで守れる。

### 3.14 ドキュメント・ADR

- README: 「決定的処理スクリプト」の表（`spec_version_delta.py` の `sources`・`spec-dir`、`spec_changes.py`〔追加。`seed`・`snapshot`・`record`・`revert`〕、`promote.py` の `sync-baseline`、`docs_layout.py` の役割）。`/xddp-11-specs`・`/xddp-survey`・`/xddp-abort` の説明（latest-specs の変更の記録・survey (c) の作業場所・中止の後片付け）。「ファイル構成」の図に survey の作業場所（`{XDDP_DIR}/survey/{repo}/specs-work/`）を足す。
- ADR-0036（追加）: 工程11 の入力の一覧（書く側の関数・資料の形をそろえる・`module-dir` による同一性）と、latest-specs の変更の記録（基準との比較・`seed`・C0-3 のスクリプト化・abort の `revert` を安全な向きに限る理由）を決めた理由と、却下した案（6.）。7. の 3. の許容と、`seq_file_stem` の順番のフォールバックの限界も書く。
- `docs/adr/README.md` に ADR-0036 を足す。
- 監査の報告書の 8.2: P4 の名前を `PLAN-20261108-latest-specs-contracts` にする。

---

## 4. 影響範囲

- **影響するスキル・コマンド:** `/xddp-11-specs`（全 Step）、`/xddp-close`（C0-3・C0-4・C2 の削除候補）、`/xddp-survey`（Step 2〜4・6〜8）、`/xddp-abort`（latest-specs の後片付け）、`/xddp-05-arch`・`/xddp-06-design`（Step 0）、`/xddp-review … spec`、`/xddp-status`（分割実行メモ）、`/xddp-codemap`（ディレクトリの書き方）、`/xddp-04-specout`（catalog の優先度だけ）、`/xddp-update-knowledge`（glossary の新規作成）。
- **影響する工程:** 工程11・close・工程5・6（Step 0）・工程4a（catalog の優先度）・随時実行（survey・abort・review・codemap）。
- **後方互換性:** 考慮しない（CLAUDE.md「後方互換性ポリシー」）。旧い形の CR・仕様を見分ける処理・移行の手順は足さない。`spec_changes.py record`・`promote.py sync-baseline` は基準が無ければ終了コード非0で止まる（通常の入力の検査。close での扱いは 3.5）。`module-dir` が空・無い仕様は、3.1 (c) の名前の規則で引き当て、廃止候補にはしない（3.4）。
- **書く側の出力の変化（デグレードの確認）:** `_section_to_module_doc` の見出しのレベルの修正（3.1 (f)）で、`assemble-spo` が統合パスから分割パスへ移すときの資料の深い見出しが1段上がる。分割パスのモジュール資料（prelim agent が書くもの）と同じ形になる向きの変化で、読む側（document agent・precheck・工程11）は分割パスの形を前提にしている。`test_specout_bfs.py` の既存のテストの期待値で、深い見出しを含むものは直す。
- **survey-agent の「ディレクトリ」欄:** `MODULE_DIR` を書くようになり、1ファイルのモジュールではファイルのパスになる。この欄を読む `MODULE_FALLBACK` の決定（`knowledge_place.py place`）は、ファイルのパスも対象として受け付ける（docstring の入力例 `src/db.go:45`）。
- **トークン:** 工程11 の LLM が配置の読み分け・一覧の作成・ケバブ化をしなくなる分だけ減る。SPEC レビューの参照ファイルに SPO が増える（3.9）分だけ増える。
- **他のプランとの関係:**
  - P2（code-knowledge の書く側）: `specout_bfs.py` を P4（catalog の優先度・`module_docs`）と P2（`confirmed_modules`）が直す。P4 は `_module_dir_for_file` を変えない（3.10）。`xddp-survey/SKILL.md` は P4（Step 2〜4・6〜8）と P2（§2.6 の昇格）が直す。P2 は P4 の実装の後の状態を見て書く。
  - P5（project-rulebook）: `xddp-close/SKILL.md` を P5（A5-1 の順序）も直す。`promote.py` は P4（`sync-baseline`・削除候補）と P5（rulebook の写し）が直す。P5 は P4 の実装の後の状態を見て書く。
  - P1・P3: 実装の後の状態を見て書いた。P3 の `collect_insights.py` の latest-specs の絞り込み（工程11 の一覧との和集合）は、一覧の作り方が変わるだけで読み方は変えない。
  - 段階2b の候補（A4-20〔cross CHD の「影響リポジトリ」列〕）と、報告書の 3. の段階2b に置いたもの（`SPECOUT_DIAGRAM_LEVEL` の節番号）は、このプランで触らない。

---

## 5. 確認項目

- [x] 1.2 の43件それぞれに、直した箇所とテストがある（スクリプトで直したものは unittest がある。SKILL・agent・テンプレートの記述だけを直したもの〔A4-18・A4-19・A4-22・A4-24・A4-26〜A4-30・A4-35・A4-37〜A4-45 の記述部分等〕は unittest が無く、下の同期の確認〔実行時ファイルの検索〕と refcheck で確かめた）
- [x] `make test` が緑（refcheck 検査F: 実行時ファイルにプランの参照・履歴を書いていない）
- [x] 3.13 の書く側→読む側のテストが、実物のテンプレートと `assemble-spo` の出力を読んでいる
- [x] スキルの同期（11-specs SKILL・mod-agent・uc-agent・survey・05・06・review・close・abort・status が、`sources` の一覧・`spec_dir`・工程11 の2つの節を同じ名前で使う。「`modules/` 配下のディレクトリ名」「progress.md §15」「Section 3-」「処理済みモジュール」が実行時ファイルに残っていない）
- [x] 並行 CR 保護の「終わった CR」の条件が、LLM の手順の3か所（11-specs SKILL Step OV・mod-agent のシーケンスの廃止候補・uc-agent）と `docs_layout.cr_in_progress`（`sources`・`seed` が使う）で同じ。mod-agent のモジュールの廃止候補の手順が `missing_module_dirs`・`protected_by_concurrent_cr` の記録に置き換わっている
- [x] `module-dir` の値が、工程11（一覧の `module_dir`）・survey（module・promote の両方の経路で SURVEY の「ディレクトリ」欄と範囲未確定の注記）のどちらでも、`REPO_PATH` 相対・末尾の `/` なしで書かれる。リポジトリ直下は両方とも `.`、範囲が決まらないものは空
- [x] abort の `revert` が、他の CR の変更が混ざりうるファイルを戻さず・消さずに一覧で示す
- [x] 中間ファイル（`spec-sources/`）が `04_specout/{repo}/work/` の下にあり、レビューブリーフの対象から外れる
- [x] smoke のシード（`phase11-*`・`phaseClose-single`）を直した（smoke の実行はユーザー）
- [x] CLAUDE.md・README・ADR が実装と一致する
- [x] 特定ドメイン（Web・業務・組み込み）への偏りがないか（CLAUDE.md「適用ドメインの中立性」参照。structure.md の節の名前・deployment.md の扱い）
- [x] 監査の報告書の 8.2 の表を直した

**実装メモ（2026-11-08）:**
- `sources` は Step OV の冒頭ではなく Step 0 で実行した（3.1 (e)）。Step UC の uc-agent も一覧（`related-modules` の `spec_dir`・シーケンス図のファイル名）を使い、Step UC は Step OV より前に動くため。CHD の取得（「## Discover CHD Files」）も Step 0 に移し、Step REV はそれを使う。
- survey (c) の Step 6 で mod-agent に渡すシーケンス図のファイル名を作るため、`seq-names` に `--kind module`（モジュール資料・SURVEY の §4.5）を足した（mod-agent は Bash を持たないので、SKILL が出して `SEQUENCES` で渡す）。
- `seq_file_stem` は、空白・`_` に加えて `/`・`／` も `-` にする（索引の配置の小見出し `{subdir}／{元の小見出し}` が `sub送信` のようにつながるのを避けるため）。ADR-0036 は規則の詳細を持たず、`docs_layout.py` の docstring に書いた。
- `module_docs` の `module_dir` は台帳の組から取る（台帳のモジュールの組は台帳が正なので、`module-assignments.json` は読まない。資料のあるモジュールは台帳にある）。
- `promote.py` の削除候補は `{"path", "kind"}` の形にした（JSON の `deletion_candidates` も同じ）。
- fixture: `scratch-workspace` のモジュールの spec.md の `module-dir` は、各ファイルの §1 の「主要ファイル」の値（1ファイルのモジュール）。主要ファイルの無いスタブは空。`scratch-workspace-min` の seed の `mod_a2/spec.md`（3つ）はフロントマターを持たないので変えていない（lint の対象外）。
- smoke のシード: `phase11-*` の台帳のモジュールディレクトリは `src`（§8 の「ディレクトリ」列と同じ）。seed の README に追加の内容を書いた。
- `make test` は緑（refcheck の警告2件はこのプランの前からある `invoke-reviewer.md` のもの）。`make smoke-full` は実行していない（ユーザーが実施）。

---

## 6. 却下した案

- **mod-agent に統合パスの読み方（§2.A.n → §2.n の対応表）を教える:** LLM が2つの形を読み分ける必要があり、precheck にも別の読み方が要る。スクリプトが分割パスと同じ形に直して渡す（3.1 (b)）。
- **工程11 が `SPO-{CR}.md` §8 の表からモジュールを取る:** §8 も `assemble-spo` が書くが、表のセルの書式（リンク・注記）を読み直すことになる。台帳と配置から直接取る関数のほうが、書く側と同じ定義を使える。
- **latest-specs のディレクトリ名をモジュール名だけで決める（`module-dir` を持たない）:** 工程4a の名前は CR ごとに台帳で決まり、survey は引数で決まるので、同じコードの仕様が二重にできうる（A4-16）。
- **工程11 の LLM に「一覧を累積する」「削除も書く」と指示を足すだけ（A4-8〜A4-10）:** 書き漏らしを検出できない。GATE の後の人の編集も捕まらない。
- **C2 を一覧のファイルだけ写す形にする:** 一覧に無い人の編集が昇格しない（A4-10 の裏返し）。C0-3 で書き戻さないほうが、今の C2（丸ごと写す）と組み合わせて単純。
- **基準として latest-specs の丸ごとの写しを CR に置く:** 量が大きく、CR フォルダを走査するレビューブリーフに混ざる。元に戻す内容は `{DOCS}` にある（3.6）。
- **`_module_dir_for_file` を最長一致に直して catalog の照合に使う:** 他の呼び出し元（`confirmed_modules` 等。P2 の範囲）の結果も変わる。catalog の照合だけ別の関数にする。
- **survey (c) で latest-specs に書いてから、却下されたら消す:** 消す手順を漏らすと残り、既存の版を上書きした後は戻せない。作業場所に書く（3.7）。
- **SPO サマリーに「ハードウェア構成・デプロイ構成」の節を足す（A4-32 の案B）:** 人の判断（7. の 2.）で採らない。材料は全体の設定ファイルで、今の工程4a（CR に関係するモジュールの調査・ソースを読まない document agent）の範囲に合わない。
- **モジュールの廃止候補に「CHD の変更対象ファイル一覧で、`module-dir` の下のファイルがすべて削除」を足す:** CHD の表は変えたファイルしか持たないので、1ファイルを削除しただけでモジュール全体が候補になる。工程11 は工程7 の後なので、母体のファイルで判定すれば足りる（3.4）。
- **abort の `revert` で、`{DOCS}` に写しのあるファイルをすべて `{DOCS}` の内容に戻し、`{DOCS}` に無いファイルをすべて消す:** 同じ作業場所の他の CR の未昇格の変更・追加を消しうる。abort は取り消せないので、混ざりうるものは戻さず人に示す（3.6）。
- **survey の作業場所を `latest-specs` を含まないパスにし、`artifact_lint.py` のパスの解釈を直す:** lint に survey の作業場所の知識が入り、パスの解釈が2通りになる。`latest-specs` の区切りを含むパスにすれば、今の解釈のまま効く（3.7）。
- **`sources` の中間ファイルを `{CR_PATH}/pending-items/` に置く:** CLAUDE.md「ファイルの置き場所」の中間ファイルの位置から外れ、工程11 GATE のレビューブリーフに混ざる（3.1 (b)）。
- **`sources` が `{DOCS}` にだけある既存の仕様を mod-agent に `existing_spec` として渡し、mod-agent が `{DOCS}` から読んで更新する:** mod-agent・uc-agent・Step OV のそれぞれに「既存の仕様を2か所から探す」読み方が要る。先に latest-specs へ写せば、既存の読み方のまま版・変更履歴を引き継げる（3.5 の `seed`）。
- **モジュールの廃止候補の確かめる範囲を、今の CR のモジュール（SPO のあるもの・CHD だけで当たるもの）に限る:** CR の外でコードが消えたモジュールの仕様が、棚卸しの CR まで残る。確かめるのはディレクトリ・ファイルの有無だけで、候補はコードが消えたときにしか出ないので、範囲を限る必要が無い（人の判断。7. の 1.）。
- **廃止候補の判定は今のまま（今の CR が調べていないものをすべて候補）にし、ディレクトリの照合だけ直す:** 人の判断（7. の 1.）と逆。候補が毎回全モジュールになり、人が「保持」を選び続けるか、誤って削除する。

---

## 7. 未決事項（人の判断 2026-11-08 で決着）

1. **廃止候補の範囲（3.4。A4-4・A4-42）:** 今の CR が調べていないモジュール・ユースケースを、廃止候補にするか。
   - 推奨: しない（3.4 の (i)・(ii) に絞る）。理由: Step OV の architecture.md は「specout していないモジュールの情報は保持する」と決めており、同じ規則にそろう。今の判定では、候補が毎回すべての既存のモジュール・過去のユースケースになる。
   - しない場合の欠点: 母体にディレクトリ・ファイルを残したまま機能をやめたモジュール等は、候補に出ない（今の architecture.md の「サイレント廃止リスク」と同じ。棚卸しの CR で扱う）。
   - あわせて、「保持」を選んだときの `status: unverified`・`status: orphaned` の付記をやめてよいか（読む側がいない）。
   - **決定（2026-11-08・人）:** 今の CR が調べていないモジュール・ユースケースは候補にしない（3.4 の (i)・(ii) に絞る）。「保持」を選んだときの `status:` の付記もやめる。
   - 補足（AI レビュー 1回目・2回目の後）: モジュールの (ii)（CHD で全ファイルを削除）は、CHD の表が変えたファイルしか持たず母集合にならないので、(i) を「母体にディレクトリが無い、または対象のファイルが無い」に広げて1つにした（3.4）。
   - **再確認の決定（2026-11-08・人）:** 3.4 は、今の CR が調べていないモジュールでも、母体から消えていれば候補にする（進行中の他の CR が最後に更新したものは除く）。確かめるのはスクリプトによるディレクトリ・ファイルの有無だけで、LLM がソースを読む母体調査はしない。候補にする理由は「調べていない」ではなく「母体から消えた」という事実なので、決定の意図（毎回すべての既存のモジュールが候補に出るのをやめる）に合う。見る範囲を今の CR のモジュールに限る案（CR の外でコードが消えた仕様は棚卸しの CR まで残る）は採らない。`source: survey` の仕様を廃止候補の判定から除外する規則もやめる（母体から消えていれば survey 由来でも廃止を意味するため）。
2. **deployment.md（3.3。A4-32）:** SPO にハードウェア構成・デプロイ構成の節が無い。
   - 案A（推奨）: 工程11 は作らない。人が書いたものは保持・昇格する。理由: 工程4a の書く側（prelim・document agent・`assemble-spo`）を変えずに済み、このプランの範囲（約束の食い違いを直す）に収まる。
   - 案B: SPO サマリーに任意の節「ハードウェア構成・デプロイ構成」を足し、document agent が書く。組み込みでは工程11 が自動でビューを作れるが、工程4a の変更（テンプレート・agent・レビュー）が要るので、別のプランにする。
   - 確認できる根拠はありませんが、組み込みでは配置・メモリマップを人が持っていることが多いと考え、案A でも人が書けば失われない。
   - 補足（2026-11-08 の検討）: SPO は母体の今の状態を書く資料なので、案B の材料は CRS ではなくコード（構成ファイル・リンカスクリプト・タスク生成の呼び出し等）になる。SPO を仕上げる document agent はソースコードを読まず、下調べは CR に関係するモジュールだけを調べるので、全体の設定は今の工程4a の範囲に入らない。自動で作る仕組みが要るなら、CR に依存しない調査（`/xddp-survey` に構成の調査のスコープを足す等。案C）を別のプランにする。
   - **決定（2026-11-08・人）:** 案A。
3. **同じ作業場所の他の CR の変更（3.5）:** 基準との比較は、工程11 の後に同じ作業場所で他の CR（工程11・survey (c)）が latest-specs を変えると、それも今の CR の変更として記録する（C0-3 で書き戻さず、C2 で昇格する。削除なら Step D の削除候補に出る）。
   - 推奨: 許容する。工程11 は CR ごとに逐次実行する（工程11 の SKILL の既存の注意）。混ざっても、書き戻さない（新しい側を残す）向きの誤りで、削除は人が Step D で確かめる。ADR-0036 に書く。
   - **決定（2026-11-08・人）:** 許容する。
   - 補足（AI レビュー 1回目の後）: この許容は close（書き戻さない向きの誤り）についてのもの。abort の `revert` は消す向きの操作なので、混ざりうるファイルは戻さずに人に示す（3.6）。

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20261108-latest-specs-contracts-review.md](review/PLAN-20261108-latest-specs-contracts-review.md)

---

## 9. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | ユーザー（会話で承認） |
| 承認日 | 2026-11-08 |
| 備考 | |
