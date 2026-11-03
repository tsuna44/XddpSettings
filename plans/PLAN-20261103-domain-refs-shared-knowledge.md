# PLAN-20261103-domain-refs-shared-knowledge

作成日: 2026-11-03  
ステータス: 草案 / **承認待ち** / 承認済み / 実装完了
> 保留: PLAN-20261103-contract-audit の段階3 で書き換える（同プランの 3.3・7. の 3.）。単独で承認・実装しない。

---

## 1. 背景・目的

### 1.1 起きていること

工程2（要求分析）の Step 0 は、既存知識の参照先を `domain_refs.py` で決め、`xddp-analyst-agent` が読む。
code-knowledge の共有の知見（`_structures/`＝構造体依存関係、`_constants/`＝共有定数・列挙値）は、
analyst の Constraint check（今回の要求に関係する制約・暗黙の前提の抽出）の入力になるはずだが、実際には届いていない。

[PLAN-20261102-constraints-module-key](PLAN-20261102-constraints-module-key.md) の実装中（`domain_refs.py` の制約の集め方を直接列挙に変えたとき）に見つけた。

### 1.2 現状（コードで確認した事実）

| 事実 | 場所 |
|---|---|
| `domain_refs.py` は AI_INDEX「## code-knowledge インデックス」のラベル `{repo} 共有構造体`・`{repo} 共有定数` を引き、行があれば `_structures/`・`_constants/` を集める | `xddp-02-analysis/scripts/domain_refs.py` の定数 `CODE_KNOWLEDGE_SPECIAL_DIRS`・関数 `resolve` の「3-2.3: code-knowledge インデックス」 |
| AI_INDEX に書くラベルは `{repo} 構造体関連図`・`{repo} 共有定数`・`{repo} 機能間フロー` | `xddp-close/scripts/promote.py` の関数 `update_ai_index` の「6. code-knowledge インデックス」 |
| 集めるのは**ディレクトリ**のパス（`col.add(special_path, type_name)`。`special_path` は `…/code-knowledge/_structures` 等） | 同「3-2.3」 |
| analyst は `DOMAIN_REF_PATHS` の各絶対パスを Read し、開けなければ飛ばして §0 に失敗を記録する | `agents/xddp-analyst-agent.md` の Process 1. |
| analyst の Constraint check は種別 `制約`・`共有構造体`・`共有定数` の参照先を使う | 同 Process 1. の「Constraint check」 |
| AI_INDEX が無い経路（3-1a）では `_structures/`・`_constants/` を集めない | 同 `resolve` の「3-1a: 索引なし直接列挙」 |
| AI_INDEX を更新するのは `xddp-close` だけ。`_structures/`・`_constants/` は `/xddp-survey` の knowledge 昇格・`/xddp-update-knowledge`（`structure`）でも書かれる | `promote.py`、`xddp-rules/code-knowledge-boundary.md` の宛先ルーティング表・「## overview/ vs _structures/ の役割分担」 |
| `IS_MULTI` のとき `{XKNOW}`（`{DOCS}/cross/knowledge/code-knowledge`）にも `_structures/`・`_constants/` が置かれるが、`domain_refs.py` は cross の code-knowledge を集めない（cross は `lessons-learned.md`・`glossary.md`・インタフェース仕様だけ） | 宛先ルーティング表、`resolve` の「3-2.5」「3-1b」 |
| `domain_refs.py` のテストに `_structures/`・`_constants/` の収集のテストは無い | `xddp-02-analysis/scripts/tests/test_domain_refs.py` |

### 1.3 その結果

1. **`_structures/` は一度も集まらない**（ラベルが `共有構造体` と `構造体関連図` で食い違う）。
2. **`_constants/` はラベルが一致して集まるが、ディレクトリのパスなので analyst が Read できず**、§0 に読み込みの失敗として記録されるだけになる（確認できる範囲の推論。Read ツールにディレクトリのパスを渡した場合の実際の挙動は確認していません）。
3. AI_INDEX が無い場合、またはクローズより後に survey・手での登録で書いた知見は、AI_INDEX に行が無いので集まらない（ADR-0033 の決定 5. で制約について直したのと同じ問題）。
4. マルチリポジトリの cross の共有の知見は集まらない。

### 1.4 目的

`_structures/`・`_constants/` の知見を、AI_INDEX の有無・ラベルによらず、analyst が Read できるファイル単位で工程2 の参照先に入れる。
制約（ADR-0033）と同じく、code-knowledge の直接列挙で集める（決定的な処理なのでスクリプトで行う）。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/skills/xddp-02-analysis/scripts/domain_refs.py` | 修正 | `_structures/`・`_constants/` を AI_INDEX のラベルではなく直接列挙し、配下の `.md` ファイルを1件ずつ参照先にする。`IS_MULTI` では cross も集める（3.1） |
| `ClaudeCode/.claude/skills/xddp-02-analysis/scripts/tests/test_domain_refs.py` | 修正 | 収集のテストを足す（3.1） |
| `CLAUDE.md` | 修正 | `domain_refs.py` の説明を直す（3.2） |
| `docs/adr/ADR-0033-constraints-module-key.md` | 修正 | Consequences に、共有の知見も同じ理由で直接列挙にした旨を1段落足す（3.3） |

`agents/xddp-analyst-agent.md`・`xddp-02-analysis/SKILL.md` は変えない（種別 `共有構造体`・`共有定数` の名前と、参照先を Read する手順はそのまま）。

---

## 3. 変更内容

### 3.1 `domain_refs.py`（修正）

**変更前:**
- 「3-2.3」で、AI_INDEX のラベル `{repo} 共有構造体`・`{repo} 共有定数` の行があれば、`{DOCS}/{repo}/knowledge/code-knowledge/{_structures|_constants}` のディレクトリを種別 `共有構造体`・`共有定数` で集める。
- 「3-1a」では集めない。cross は集めない。

**変更後:**
- 「3-2.3」の `_structures`・`_constants` のラベル照合を削除する（「3-2.3」は AI_INDEX の「code-knowledge インデックス」の表の形の検査〔`ai_index_malformed_sections`〕だけを残すか、節ごと削除する。どちらにするかは実装時に決める。表の形の検査を残す場合も、収集には使わない）。
- AI_INDEX の有無によらず（制約の直接列挙と同じ位置で）、affected repos ごとに次を集める:
  - `{DOCS}/{repo}/knowledge/code-knowledge/_structures/` の直下の `*.md` → 種別 `共有構造体`
  - `{DOCS}/{repo}/knowledge/code-knowledge/_constants/` の直下の `*.md` → 種別 `共有定数`
  - 並びはファイル名の順。ディレクトリが無ければ何もしない。
- `IS_MULTI` のときは `{DOCS}/cross/knowledge/code-knowledge/_structures/`・`_constants/` も同じく集める。
- キーワードでは絞らない（未決事項 1.）。
- 定数 `CODE_KNOWLEDGE_SPECIAL_DIRS` は種別名の対応（`_structures`→`共有構造体`、`_constants`→`共有定数`）として残し、ラベルの意味（「promote.py と同一の対応」というコメント）を削る。
- 出力の形（`domain_ref_paths`・種別名）は変えない。`stats["docs_sourced"]` はファイルごとに数える（`add_docs` を使う）。

**テスト:**
- AI_INDEX があっても無くても、`_structures/` と `_constants/` の `.md` がファイル単位で、種別 `共有構造体`・`共有定数` で集まる。
- AI_INDEX の「code-knowledge インデックス」に `{repo} 構造体関連図` の行があっても無くても結果が同じ。
- ディレクトリ自体のパスは参照先に入らない。`.md` 以外のファイルは入らない。
- `IS_MULTI` で cross の `_structures/`・`_constants/` が集まり、`IS_MULTI` でなければ集まらない。
- `_flows/` は集まらない（未決事項 2.）。
- 既存のテストがそのまま通る。

**理由:** ラベルの食い違いを直すだけでは、ディレクトリのパスを Read できない問題・AI_INDEX に行の無い知見が見えない問題が残るため。
制約と同じく直接列挙にすれば、ラベルの対応を2つのスクリプトで揃える必要がなくなる。

### 3.2 `CLAUDE.md`（修正）

**変更前:** ファイル構成の表の `xddp-02-analysis/scripts/` の説明「AI_INDEX.md 実在時はテーブル照合（ユースケース一覧・モジュール別最新仕様・code-knowledge インデックスの `_structures`・`_constants`）」。

**変更後:** 「AI_INDEX.md 実在時はテーブル照合（ユースケース一覧・モジュール別最新仕様）」にし、制約の直接列挙の文に「共有の知見（`_structures/`・`_constants/` の `.md`。`IS_MULTI` では cross も）も AI_INDEX の有無によらず直接列挙で集める」を足す。

### 3.3 `ADR-0033`（修正）

Consequences に1段落足す: 「工程2 は `_structures/`・`_constants/` も同じ理由で直接列挙し、ファイル単位で渡す（AI_INDEX のラベル照合は `promote.py` と `domain_refs.py` でラベルが食い違い `_structures` を集めず、渡していたのも Read できないディレクトリのパスだった）。」

---

## 4. 影響範囲

- 影響するスキル・コマンド: `/xddp-02-analysis`（Step 0 の参照先）。`domain_refs.py` を呼ぶのは工程2 だけ。
- 影響する工程: 工程2（ANA §0 の参照先に共有構造体・共有定数のファイルが入る）。
- トークン: analyst が読むファイルが、`_structures/`・`_constants/` の `.md` の数だけ増える（今は実質0件）。件数はドメインの数（`{DOMAIN}-relations.md`・`{DOMAIN}-constants.md`）に比例する。
- 後方互換性: 考慮しない。出力の形は変えない。
- デグレードのリスク: `_constants/` を参照先に入れていた（Read できないディレクトリとして）場合、§0 の読み込みの失敗の記録が無くなる（意図した変化）。

---

## 5. 確認項目

- [ ] `make test`（refcheck・全 unittest）が緑
- [ ] `domain_refs.py` のテスト（3.1 の各場合）
- [ ] fixture（`test-fixtures/` に `_structures/`・`_constants/` を持つ `baseline_docs` があればそれ、無ければテストの一時ディレクトリ）で、`DOMAIN_REF_PATHS` に `.md` のファイルが種別付きで入る
- [ ] CLAUDE.md・ADR-0033 の記述と整合
- [ ] 実行時ファイルに設計根拠・プランへの参照を書いていない（スクリプトの docstring・コメントを含め、refcheck 検査F の対象外でも書かない）
- [ ] 特定ドメインへの偏りがない（ディレクトリの列挙だけで、ドメインに依存する記述は無い）

---

## 6. 却下した案

- **`CODE_KNOWLEDGE_SPECIAL_DIRS` のラベルを `構造体関連図` に直すだけ:** ディレクトリのパスを渡していて analyst が Read できない問題、AI_INDEX に行の無い知見（survey・手での登録の直後、AI_INDEX が無い場合）が見えない問題が残る。ラベルを2つのスクリプトで揃え続ける必要もある。
- **ディレクトリのパスを渡したまま、analyst に配下を Glob させる:** 決定的な列挙を LLM に任せることになる（CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。

---

## 7. 未決事項（レビューで確認したい点）

1. **キーワードで絞るか:** ファイル名の `{DOMAIN}` にキーワードを `resolve_matches` で当てて絞る案もある。ただし `{DOMAIN}` はクローズで暫定に付けた名前（推定できなければ `shared`）が多く、照合の当たりにくさは確認できていない。
   本プランは絞らない（全件）とする。件数が問題になったら、`stats` に件数を出して計測してから決める。
2. **`_flows/`（機能間フロー・DFD・callgraph）を集めるか:** 今の analyst の Constraint check の種別に `_flows` は無く、工程2 で使う根拠を確認できていない。本プランでは集めない。
