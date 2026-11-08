# PLAN-20261105-lessons-backlog

作成日: 2026-11-05（PLAN-20261103-contract-audit の段階3 の P3）  
ステータス: 草案 / 承認待ち / 承認済み / **実装完了**

---

## 1. 背景・目的

### 1.1 起きていること

約束の監査（[docs/xddp-contract-audit-2026-11.md](../docs/xddp-contract-audit-2026-11.md)）は、知見ログ（LL）・改善バックログ（IDEA）・気づき・提案メモの約束（A3）に30件の指摘を挙げ、P3 としてこのプランに割り当てた（報告書の 8.2）。P1（PLAN-20261103-domain-refs-shared-knowledge）の実装の後の状態（c15454f）を見て書く。

食い違いのもとは、次の5つにまとまる。
- **ID が通し番号で、場所をまたいで重なる:** Layer 1（`{XDDP_DIR}/lessons-learned.md`）・update-knowledge（Layer 2 に直接書く）・別のワークスペース・アーカイブの後で、`LL-NNN` を別々に採る。Layer 2（`{DOCS}/{repo}/knowledge/lessons-learned.md`）は ID が同じなら足さないので、後の LL が黙って入らない（A3-1・A3-2・A3-3）。
- **決まった手順で作れる表を LLM が書き、書く側ごとに形が違う:** タグ別インデックス・エントリ一覧・バックログのサマリと一覧を LLM が更新し、区切り・書式・どの表かが決まっていない（A3-15・A3-16・A3-17・A3-18・A3-28）。Layer 2 のヘッダーを書く側が4つあり、1つはヘッダーを書かない（A3-17・A3-24）。
- **気づきの収集の対象が、書く側とずれている:** 書いた節を集めない（cross の TSP・progress.md）、節を集めるが書く側が無い（CODING・VERIFY）、今の CR と関係の無い latest-specs の節を毎回集める、「なし」・HTML コメントを1件と数える（A3-5・A3-6・A3-7・A3-13・A3-14・A3-25・N8）。節の有無の規則の参照先が無い・実際の動作と合わない（A3-26・A3-30）。
- **promote.py の判定と報告が足りない:** LL の `repo` 欄を確かめずにパスにする（A3-9）。cross の置き場所を「今の CR に cross の成果物があるか」で決める（A3-8）。`{DOCS}` の backlog を丸ごと上書きする（A3-4）。共通ファイルの昇格の失敗が Step D・E に出ない（A3-27）。再実行で LL・IDEA が重複したまま昇格する（A3-29）。LL をコードブロックの中の見出しで切る（R2・R3）。
- **読む側が受け取り口を持たない・記述が実物と違う:** analyst・architect・test-writer が `LESSONS_CONTEXT` を受け取る宣言を持たない（A3-10〜A3-12）。テンプレートのパス・管理場所・抽出の観点・読み手の一覧・abort の案内が実物と違う（A3-19〜A3-23）。

### 1.2 割り当てた指摘（P3）

指摘の詳細は、監査の報告書の付録（A3 のやり直し版の「3. 指摘」と、検証者の報告）にある。行番号は監査の対象リビジョン ecb54c4 の値で、今のファイルの行とは違う。

| # | 重大度 | 内容（要約） | 直す節 |
|---|---|---|---|
| A3-1 | 🔴 | Layer 2 の重複判定が ID だけ。update-knowledge が Layer 2 で別に番号を採る | 3.1 |
| A3-2 | 🟡 | Layer 1 の採番の規則が無い（アーカイブの後に重なりうる。インデックスに古い ID が残る） | 3.1・3.2 |
| A3-3 | 🔴 | ワークスペースが別だと番号が独立で、共有の Layer 2 で重なる | 3.1 |
| A3-4 | 🟡 | `improvement-backlog.md` を `{DOCS}` に丸ごと上書きする | 3.5.4 |
| A3-5 | 🔴 | cross の TSP の気づきを集めない | 3.4.1 |
| A3-6 | 🔴 | progress.md の「## 気づき・提案メモ」を集めない | 3.4.1 |
| A3-7 | 🟡 | latest-specs の節を CR で絞らず、全 repo について毎回集める | 3.4.2 |
| A3-8 | 🟡 | multi-repo で cross の成果物の無い CR の `repo: cross` の LL を、黙って Layer 2 に入れない | 3.5.1 |
| A3-9 | 🟡 | LL の `repo` 欄を確かめずにパスにする | 3.5.1 |
| A3-10 | 🟡 | xddp-analyst-agent が `LESSONS_CONTEXT` を Inputs に持たない | 3.7 |
| A3-11 | 🟡 | xddp-architect-agent が同上 | 3.7 |
| A3-12 | 🟡 | xddp-test-writer-agent が同上 | 3.7 |
| A3-13 | 🔵 | analyst の「なし」を未記入と判定しない | 3.4.3 |
| A3-14 | 🔵 | SPO §9 の「なし」の行と HTML コメントを未記入と判定しない | 3.4.3 |
| A3-15 | 🔵 | IDEA のエントリの書式がテンプレートと違う | 3.2.2 |
| A3-16 | 🔵 | Step B の「summary table」がどの表か分からない | 3.2.2 |
| A3-17 | 🔵 | Layer 2 の「エントリ一覧」を誰も更新しない（ヘッダーも書く側で違う） | 3.2.3 |
| A3-18 | 🔵 | update-knowledge の lesson の書式が決まっていない | 3.9 |
| A3-19 | 🔵 | LL テンプレートの「管理場所」が実際のパスと違う | 3.2.1 |
| A3-20 | 🔵 | Step B・C の「create from template」がテンプレートのパスを示さない | 3.8 |
| A3-21 | 🔵 | Step C の抽出の観点が「(same as before …)」で、何から抽出するかも書いていない | 3.8 |
| A3-22 | 🔵 | abort が「update-knowledge 等で backlog に登録」と案内するが、update-knowledge に backlog の種別が無い | 3.11 |
| A3-23 | 🔵 | close のコメントにある Layer 1 の読み手の一覧が足りない | 3.8 |
| A3-24 | 🔵 | `append_breaking_warning` がヘッダーなしで Layer 2 を作る | 3.2.3 |
| A3-25 | 🔵 | CODING・VERIFY の気づき節を集めるが、coder・verifier の出力に節が無い | 3.4.4 |
| A3-26 | 🔵 | SPO §9 のテンプレートは「手で直さない（上書きされる）」と書くが、スクリプトは人の行を残す | 3.4.5 |
| A3-27 | 🟡 | 共通ファイルの昇格の失敗が Step D・E に出ない（AI_INDEX の部分は P1 で直った） | 3.5.3 |
| A3-28 | 🔵 | LL のタグの区切りが決まっておらず、タグ別インデックスから漏れうる | 3.2.1 |
| A3-29 | 🟡 | close の再実行で、重複した LL・IDEA が人が消す前に同じ実行で昇格する | 3.3 |
| A3-30 | 🔵 | latest-specs の「気づきメモポリシー」「Section 3-4」が参照先に無い | 3.4.6 |
| N8 | 🔵 | SPO §9 の「なし」の行が、assemble-spo の再実行で残る | 3.4.5 |
| R2（段階1） | 🟡 | LL の本文のコードブロックの中の `### LL-NNN：` でエントリを切る | 3.6 |
| R3（段階1） | 🟡 | 短いフェンスで長いフェンスが閉じる | 3.6 |
| A5-24（P5 から移す） | 🔵 | cross の rulebook の写しが、今の CR の cross の成果物の有無で決まる | 3.5.2 |
| A5-31（P5 から移す） | 🟡 | `write_output_file` が `affected_repos` だけを出力し、cross・system の失敗が出ない | 3.5.3 |

### 1.3 方針

**人の判断（2026-11-05）:**
1. **LL・IDEA の ID に CR を含める。** `LL-{CR}-{NN}`・`IDEA-{CR}-{NN}`。CR を持たない登録（update-knowledge の lesson）は日付を含める。ID が場所をまたいで重ならないので、採番の規則も重複の判定も単純になる。
2. **A3-4（backlog）だけを P3 で直す。** A5-28（rulebook の丸ごと上書き）は P5 に残す。backlog は IDEA ごとのエントリなので ID で足し込める。rulebook は節の中の行を人も書くので、直し方が違う。
3. **A3-8 と A5-24 を P3 でまとめて直す。** 「cross の知見・rulebook の置き場所は IS_MULTI で決める」を1つの約束にする。
4. **A3-27 と A5-31 を P3 でまとめて直す。** promote.py のすべての失敗（repo・cross・system・共通ファイル）を出力ファイルに出し、Step D・E が失敗として示す。

**このプランの方針:**
5. **決まった手順で作れる表は、スクリプトが作り直す。** LLM はエントリだけを書く（CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。
6. **気づきの収集は、今の CR が書いた・足したものだけにする。** latest-specs は、今の CR が更新したファイルの、`{DOCS}` の承認済みの版に無い項目だけを集める。
7. **書く側と読む側で共有する値は、1つの定義を import する**（3.13）。

### 1.4 目的

- 1.2 の35件を直す。
- 知見ログ・バックログ・気づきの約束を、スクリプトの定義とテストで守る形にする（3.13 の再発防止）。

---

## 2. 変更対象ファイル

パスの `CC/` は `ClaudeCode/.claude/` の略。

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `CC/skills/xddp-close/scripts/promote.py` | 修正 | `index` サブコマンドの追加（3.2）。`extract-ll` の振り分け（3.5.1）。Layer 2 の重複判定・内容の違いの報告・ヘッダーと節（3.1・3.2.3）。cross の条件（3.5.2）。出力ファイルと対象の登録（3.5.3）。backlog の足し込み（3.5.4）。フェンス（3.6） |
| `CC/skills/xddp-close/scripts/collect_insights.py` | 修正 | 対象の追加・latest-specs の絞り込み・未記入の判定（3.4） |
| `CC/skills/xddp-common/scripts/docs_layout.py` | 修正 | 気づき・提案メモの見出し・項目の定義・`has_insights` の読み方と期待値の規則の単一定義（3.4.3・3.4.6・3.13） |
| `CC/skills/xddp-common/scripts/artifact_lint.py` | 修正 | `has_insights` と節の有無・期待値の検査（3.4.6） |
| `CC/skills/xddp-04-specout/scripts/specout_bfs.py` | 修正 | §9 の「なし」の行を残さない（3.4.5） |
| `CC/skills/xddp-close/scripts/tests/test_promote.py`・`test_collect_insights.py`、`CC/skills/xddp-common/scripts/tests/test_docs_layout.py`・`test_artifact_lint.py`、`CC/skills/xddp-04-specout/scripts/tests/test_specout_bfs.py` | 修正 | 3.12・3.13 |
| `CC/skills/xddp-close/SKILL.md` | 修正 | Step A〜E（3.3・3.4・3.5・3.8） |
| `CC/skills/xddp-close/templates/lessons-learned-template.md` | 修正 | 管理場所・表の注記（3.2.1） |
| `CC/skills/xddp-close/templates/10_improvement-backlog-template.md` | 修正 | 表の注記・見本のエントリを消す（3.2.2） |
| `CC/skills/xddp-common/procedures/load-lessons-context.md` | 修正 | ID の例（3.1） |
| `CC/skills/xddp-update-knowledge/SKILL.md` | 修正 | lesson の ID・書式・ヘッダー（3.9） |
| `CC/skills/xddp-01-init/SKILL.md` | 修正 | Layer 2 の知見ログを作らない（3.10） |
| `CC/skills/xddp-abort/SKILL.md` | 修正 | 気づきの登録の案内（3.11） |
| `CC/agents/xddp-analyst-agent.md`・`xddp-architect-agent.md`・`xddp-test-writer-agent.md` | 修正 | `LESSONS_CONTEXT` の受け取り口（3.7） |
| `CC/agents/xddp-coder-agent.md`・`xddp-verifier-agent.md` | 修正 | 「気づき・提案メモ」の節（3.4.4） |
| `CC/agents/xddp-close-knowledge-agent.md` | 修正 | 出典の ID の書き方（3.1） |
| `CC/skills/xddp-04-specout/templates/04_specout-summary-template.md` | 修正 | §9 のコメント（3.4.5） |
| `CC/skills/xddp-common/reviewer-checklists/SPEC.md`・`CC/skills/xddp-11-specs/SKILL.md`・`CC/skills/xddp-survey/SKILL.md` | 修正 | 気づきメモの規則の参照先（3.4.6） |
| `CC/skills/xddp-11-specs/templates/11_module-sequence-template.md` | 修正 | 「気づきメモセクションなし」の注記（3.4.6） |
| `test-fixtures/scratch-workspace/**`・`test-fixtures/scratch-workspace-min/seeds/**`・`test-fixtures/scratch-workspace-p4-new-mode/**` の知見ログ・バックログ、同じ fixture の中の LL の参照（`_flows/alert-publish-dispatch-sequence.md`・project-rulebook の出典） | 修正 | ID の形式・Layer 2 の節（3.12） |
| `CLAUDE.md`・`README.md` | 修正 | 3.14 |
| `docs/adr/ADR-0035-lessons-backlog-ids-and-indexes.md` | 追加 | 3.14 |
| `docs/adr/README.md`・`docs/adr/ADR-0013-close-promote-script.md` | 修正 | 3.14 |
| `docs/xddp-contract-audit-2026-11.md` | 修正 | P3 の名前・A5-24・A5-31 の割り当て・同じ型の決定（3.14） |

---

## 3. 変更内容

### 3.1 LL・IDEA の ID（A3-1・A3-2・A3-3）

**変更前:** close Step C は `LL-{NNN}`、Step B は `IDEA-{NNN}` を採る（採番の規則は無い）。update-knowledge は Layer 2 の中で「既存の LL-NNN の次」を採る。promote.py は Layer 2 の本文に `### {ID}：` の文字列があれば足さない。

**変更後:**

| 書く側 | ID | 例 |
|---|---|---|
| close Step C（Layer 1 の LL） | `LL-{CR}-{NN}` | `LL-CR-2026-970-01` |
| close Step B（Layer 1 の IDEA） | `IDEA-{CR}-{NN}` | `IDEA-CR-2026-970-01` |
| update-knowledge の lesson（Layer 2 に直接） | `LL-M{YYYYMMDD}-{NN}` | `LL-M20261105-01` |
| 人が直接書く IDEA（abort の後等） | `IDEA-{CR}-{NN}`（CR があれば）／`IDEA-M{YYYYMMDD}-{NN}` | |

- `{NN}` は、その接頭辞の ID の中の連番（2桁。100 件目からは3桁）。close では 3.3 により今の CR のエントリが無いときだけ足すので、`01` から採る。update-knowledge の番号はスクリプトが決める: `index --layer2-file` の stdout の `next_manual_id`（書くファイルの中の `LL-M{TODAY}-` の番号の最大値 + 1。無ければ `01`）を使う（LLM が数えない。エントリを消した後も既存の ID と重ならない）。
- `index` は、渡したファイルの中で同じ ID のエントリが2つ以上あれば `duplicate_ids` に返す（close Step D・update-knowledge で示す）。
- promote.py の Layer 2 の重複判定は「Layer 2 にある同じ ID のエントリ」とする。Layer 2 の既存のエントリは、本文の文字列の検索ではなく、3.6 の切り分け（フェンスの外の見出し）で取る。
- **エントリの比較の正規化**（`ll_conflicts`・3.5.4 の `backlog_conflicts` で共通。promote.py に1つだけ定義する）: 見出しの行からエントリの終わりまでの各行の末尾の空白を除き、エントリの末尾にある空行と区切りの `---` の行（フェンスの外）をすべて除いてから比べる。Layer 2・`{DOCS}` の backlog にエントリを足すときの区切り（空行 + `---`）も、同じ定義の関数で書く（Layer 1 から写したエントリと、写した先のエントリが、区切りの違いだけで「内容が違う」にならないように）。
- Layer 2 に同じ ID のエントリが1つあり、正規化した本文が違うものは、上書きせず、出力ファイルの新しい節「Layer 2 と内容が違う LL（上書きしていない）」と stdout の `ll_conflicts`（[{id, area}]）に出す。close Step D で示し、どちらを採るかは人が Layer 2 を直して決める（3.3 の作り直しで同じ ID が再び採られた場合に、黙って入らないことを防ぐ）。
- Layer 2 に同じ ID のエントリが2つ以上あるときは、足さず、`ll_conflicts` にも出さず、`duplicate_ids` だけに出す（どちらと比べるかを決めない）。
- `run` は、書いた・表を作り直した Layer 2 と `{DOCS}` の backlog の `duplicate_ids` を、出力ファイルの節「同じ ID が2つ以上あるエントリ」と stdout の `duplicate_ids`（[{id, file}]）に出し、close Step D で示す（別の作業場所から同じ日に登録した手の ID の重なりを、close の中で見つける）。
- ID の正規表現・接頭辞は promote.py に1つだけ定義する（`LL_ENTRY_RE` は形を変えずに使える。`LL-[^\s：]+`）。
- アーカイブ（close Step C の「ファイルサイズポリシー」）の手順から「エントリ一覧の行を消す」「アーカイブにもエントリ一覧を足す」を消し、「エントリを `lessons-learned-archive-{YYYY}.md` に移す。表は次の `promote.py index` が作り直す（移した ID はタグ別インデックスからも消える）」にする（A3-2 のインデックスに古い ID が残る部分）。
- `load-lessons-context.md` の例（`LL-003, LL-005`）を新しい形にする。読み方（`### {id}：`）は変えない。
- `xddp-close-knowledge-agent.md` の `（出典: LL-{NNN}, {CR_NUMBER}）` を `（出典: {LL の ID}）` にする（ID が CR を含むため）。この1行だけを直す（C3.5・C3.6 の他の部分は P5・P2）。
- 古い ID の書き方（`LL-{NNN}`・`IDEA-{NNN}`・`LL-NNN`・`IDEA-00x`）は、実行時ファイルのすべての箇所を新しい形にする。close SKILL.md の Step B・C・D（Step D の案内文の `### LL-{NNN}：{タイトル}` の3か所を含む）、update-knowledge SKILL.md、knowledge agent、`promote.py` のコメント（見出しの崩れた LL の例 `### LL-005: …`）、backlog テンプレートの §5 変更履歴の行（`IDEA-00x追加`）。

**理由:** 人の判断（1.3 の 1.）。CR 番号はワークスペースをまたいで一意（CR のフォルダ名）なので、番号を採るときにほかの場所を見なくてよい。手で登録する ID（`LL-M…`）の番号はスクリプトが最大値から決める（CLAUDE.md「決定的処理はスクリプト」）。別の作業場所から同じ `{DOCS}` に同じ日に登録した場合の重なりは残る（3.13 の 2. の「残る約束」。`index` の `duplicate_ids` で見つかる）。

### 3.2 スクリプトが作り直す表（A3-15・A3-16・A3-17・A3-24・A3-28・A3-19）

**変更前:** close Step B は IDEA を追記した後に「Update summary table」（どの表か書いていない）、Step C は「エントリ一覧に1行追記・`最終更新CR` を更新」とタグ別インデックスの更新を LLM が行う（close SKILL.md の Step B・Step C）。Layer 2 の知見ログのヘッダーは promote.py（`promote_lessons_learned`）・01-init（Step 4.5）・update-knowledge（「create with header if not」）がそれぞれ書き、`append_breaking_warning` はヘッダーを書かない。

**変更後:** promote.py に `index` サブコマンドを足す。

```
promote.py index [--cr CR] [--today YYYY-MM-DD] [--check]
                 [--lessons-file L] [--backlog-file B]
                 [--layer2-file F --area AREA]
```

- 渡したファイルだけを扱う。ファイルが無ければ、Layer 1 の2つは扱わずに件数 0 を返し、Layer 2 はヘッダーだけのファイルを作る（`--check` では作らない）。
- `--check` はファイルを書かず、stdout の件数だけを返す（3.3 の事前確認で使う）。
- 内容が変わらなければ書かない（冪等）。
- stdout に JSON 1行。キー: `cr_ll_count`・`cr_idea_count`（今の CR の ID の見出しの数。3.3）、`cr_ll_ids`・`cr_idea_ids`（その ID の一覧）、`ll_count`・`idea_count`、`unknown_tags`（[{id, tag}]）、`cr_unknown_repo_ideas`（今の CR の IDEA のうち repo が `unknown` の ID）、`bad_ideas`（[{id, reason}]。表の行が足りない・§3 の外にある〔理由 `outside-section`〕等）、`unparsed_ll`（[{id, reason}]。3.6 と同じ理由）、`duplicate_ids`（3.1）、`next_manual_id`（`--layer2-file` のとき。3.1）。
- Layer 1 と backlog のファイルに必要な節（Layer 1 の `## エントリ一覧`・`## タグ別インデックス`・`## 知見詳細`、backlog の `## 1.`・`## 2.`・`## 3.`）が無ければ、exit 1 で stderr にファイルのパスと節の名前を出す（Layer 2 は 3.2.3）。
- 表の列・節の名前・Layer 2 のヘッダーは promote.py に1つだけ定義する。

**理由:** A3-15〜A3-17・A3-24・A3-28。1.3 の 5.（決まった手順で作れる表はスクリプトが作り直す）。

#### 3.2.1 Layer 1 の知見ログ（`--lessons-file`）

- `## 知見詳細` のエントリ（3.6 の切り分け）から、`## エントリ一覧` の表（`ID｜タイトル｜CR｜工程｜タグ`）を作り直す。メタ行の読めないエントリは表に入れず、`unparsed_ll` に返す。
- `## タグ別インデックス` の表を作り直す。行（タグ）は今の表の行をその順に使い、値は該当する ID をカンマ区切り（無ければ `—`）。
- タグは、メタ行の `**タグ：**` 欄を `,`・`、`・空白で分け、`#` で始まる語とする（書き方の区切りがずれても漏れない。A3-28）。表に行の無いタグは行を足さずに `unknown_tags` に返す（タグ一覧に足すかは人が決める。今の方針と同じ）。
- `--cr` があり、今の CR の LL が1件以上あるときだけ `**最終更新CR：**` を `{CR}` にする（今の CR が LL を足さなければ前の値のまま）。
- テンプレート（`lessons-learned-template.md`）:
  - `**管理場所：** プロジェクトルート lessons-learned.md` を `{XDDP_DIR}/lessons-learned.md` にする（A3-19）。
  - エントリ一覧の下の「エントリ追加時は上記テーブルにも1行追記すること」と、タグ別インデックスの「xddp-close Step C が自動更新する」を、「`promote.py index` が `## 知見詳細` から作り直す。手で直さない」にする。
- close Step C の Entry Format のタグ欄を `**タグ：** {#タグ1, #タグ2}`（カンマ区切り）にする。

#### 3.2.2 Layer 1 のバックログ（`--backlog-file`。A3-15・A3-16）

- `## 3. アイデア詳細` の `### IDEA-…：{タイトル}` のエントリの項目の表から、`## 1. サマリ`（ステータスごとの件数と合計）と `## 2. バックログ一覧`（`ID｜タイトル｜カテゴリ｜優先度｜発生源｜ステータス`）を作り直す。5つのステータスに無い値は合計にだけ数え、`bad_ideas`（理由 `status`）に返す。§3 の外（§4 以降等）にある `### IDEA-` の見出しは表に入れず、`bad_ideas`（理由 `outside-section`）に返す（黙って落とさない）。
- `--today` があり、ファイルのほかの部分が変わるときだけ `**最終更新：**` を `{TODAY}` にする（冪等を保つ）。
- IDEA のエントリの書式は、テンプレートの項目の表に `repo` の行を足した形にそろえ、close Step B に定義する（A3-15。今の Step B の太字の行の書式をやめる）。Step B はエントリを `## 3. アイデア詳細` の末尾（次の `## ` の見出しの前）に足す（ファイルの末尾ではない。§3 の後に §4・§5 がある）。

  ```markdown
  ### IDEA-{CR}-{NN}：{タイトル}

  | 項目 | 内容 |
  |------|------|
  | カテゴリ | {カテゴリ} |
  | 優先度 | 高／中／低 |
  | repo | {repo名／cross／全リポジトリ／unknown}（{判定根拠}） |
  | 発生源 | {CR}の{資料名}「気づき・提案メモ」 |
  | ステータス | 🆕 新規 |
  | 対応CR | — |

  **内容：**  
  …（**発生経緯：**・**期待効果：**・**推定影響範囲：**・**CR化の判断メモ：** はテンプレートのとおり）
  ```

- テンプレート（`10_improvement-backlog-template.md`）:
  - §1・§2 の表は見出しの行だけにし、「`promote.py index` が §3 から作り直す。手で直さない」と注記する。
  - 冒頭に、2つのファイルの役割を注記する（3.5.4）:「`{XDDP_DIR}/improvement-backlog.md` は、この作業場所の CR の close が新しい IDEA を書く受け口。close が `{DOCS}/improvement-backlog.md` に足し込む。ステータス・対応CR 等を直すのは `{DOCS}/improvement-backlog.md` の §3 の各アイデアの表（`{XDDP_DIR}` 側を直しても `{DOCS}` には届かない）。取り消すときはエントリを消さず、ステータスを `❌ 却下` にする（消すと次の close で `{XDDP_DIR}` 側から足し込まれる）」。
  - §3 の見本のエントリ（`IDEA-001：{タイトル}`・`IDEA-002`）を消し、「エントリの書式は xddp-close の Step B」と注記する（見本がエントリとして数えられないように）。
  - §5 の変更履歴の見本の行（`IDEA-00x追加`）を `IDEA-{CR}-{NN}追加` にする。
- close Step B の「Update summary table」を消す（A3-16）。

#### 3.2.3 Layer 2 の知見ログ（`--layer2-file`・`--area`。A3-17・A3-24）

- ファイルが無いか空なら、ヘッダー `# 知見ログ: {area}`・1行の説明・`## エントリ一覧` の表を書く。
- ファイルがあり `## エントリ一覧` の節が無ければ（今の promote.py・`append_breaking_warning`・01-init の古いひな形が作ったファイル）、節を足す。位置は、フェンスの外の最初の `### ` 見出し（LL・破壊的変更警告）の前。`### ` 見出しが無ければ末尾。ファイルの先頭に `# ` 見出しが無ければ、ヘッダーの `# 知見ログ: {area}` と説明も先頭に足す。既にある `## エントリ一覧` の節で列が違う（01-init の古いひな形の `ID｜タイトル｜タグ｜CR｜日付` 等）ものは、節の中身を新しい表で置き換える（`{DOCS}` は CR をまたぐ蓄積なので、ファイルを作り直さず、節だけを直す）。
- エントリ（`### LL-…：`）から `## エントリ一覧`（`ID｜タイトル｜CR｜工程｜タグ`。Layer 1 と同じ列）を作り直す。破壊的変更警告（`### 破壊的変更警告（{CR}）`）は表に入れない。
- 書く側はすべてこの定義を使う:
  - `promote_lessons_learned`・`append_breaking_warning`: 書く前にヘッダーを作り（無ければ）、書いた後に表を作り直す（関数を直接呼ぶ）。
  - update-knowledge の lesson: `index --layer2-file` を呼ぶ（3.9）。
  - 01-init は Layer 2 の知見ログを作らない（3.10）。

### 3.3 再実行で重複させない（A3-29）

**変更前:** close の再実行は Step B・C の追記を繰り返す。Step D は「重複した LL は人が消す」と案内するが、同じ実行で extract-ll・promote・knowledge agent まで進む。

**変更後:**
- close Step B の前に `promote.py index --check --cr {CR} --lessons-file {XDDP_DIR}/lessons-learned.md --backlog-file {XDDP_DIR}/improvement-backlog.md` を実行する（ファイルを書かない）。終了コードが 0 以外なら stderr を示して停止する（必要な節が無い。3.2）。
  - `cr_idea_count` が 1 以上なら Step B の追記をしない。
  - `cr_ll_count` が 1 以上なら Step C の追記をしない。
  - どちらも、人に「今の CR の IDEA／LL が既に {n} 件（{cr_idea_ids／cr_ll_ids}）あるので追記しない。作り直すなら、それらを消してから `/xddp-close {CR}` を再実行する。前回の close で `{DOCS}` に昇格済みなら、`{DOCS}` の同じ ID のエントリも消す（消さなければ、作り直したエントリは Layer 2・`{DOCS}` の backlog で『内容が違う』として報告され、上書きされない。3.1・3.5.4）」と示す。
- 数えるのは、フェンスの外の見出し（`#` の数は問わない。見出しの崩れたものも含む）で ID が今の CR の ID に全体で一致するもの（`^LL-{re.escape(CR)}-\d{2,}$`・`^IDEA-{re.escape(CR)}-\d{2,}$`）。前方一致にしない（CR 名は自由形式で、`REQ-1` の close で `LL-REQ-1-2-01`〔CR `REQ-1-2` のエントリ〕を数えないように）。正規表現は 3.1 の ID の定義と同じく promote.py に1つだけ置く。
- Step C の後の `index`（3.8。表の作り直し）は、Step B・C の追記の有無によらず必ず実行し、Step D はその実行の stdout（`unknown_tags` 等）を使う。
- Step D の再実行の案内（「再実行は Step B・C の知見の追記も繰り返すので、重複した LL は人が消す」）を「再実行では、今の CR のエントリが既にあれば Step B・C は追記しない」にする。

**理由:** A3-29。3.1 で今の CR のエントリを ID で見分けられるので、スクリプトで数えられる。重複を人に消させる案内は、同じ実行で昇格する前に人が確認する場所が無いので働かない。

### 3.4 気づきの収集（collect_insights.py ほか）

#### 3.4.1 対象を足す（A3-5・A3-6）

**変更前:** `enumerate_targets`（collect_insights.py）は repo の TSP だけを対象にし、cross の TSP と progress.md を対象にしない。

**変更後:**
- `HAS_CROSS` なら `09_test-spec/cross/TSP-{CR}-cross.md` を足す。
- `{CR_PATH}/progress.md` を足す（「## 気づき・提案メモ」の節）。abort が書く節は、その CR が close に来ないので集まらない（今の方針のまま）。

**理由:** A3-5・A3-6。書いた節が集まらず、知見ログから欠ける。

#### 3.4.2 latest-specs を今の CR が足した項目に絞る（A3-7）

**変更前:** `repos_keys` の全 repo・cross・system の latest-specs の全ファイルの節を、毎回集める。出典の CR は分からない。

**変更後:**
- 走査するのは、次の和集合のファイル:
  - `{CR_PATH}/progress.md` の「## 工程11 更新仕様書ファイル一覧」に載ったファイル。
  - `{XDDP_DIR}/latest-specs/` の `.md` のうち、フロントマターの `last-updated-cr` が今の CR のもの（`docs_layout.last_updated_cr`）。一覧は工程11 の LLM が書き、再実行で上書きされるので、一覧の漏れで黙って集めなくならないように、決定的な手がかりを合わせる。
  - 一覧に無く `last-updated-cr` だけで見つけたファイルは、収集サマリに「工程11 の一覧に無いファイル」として示す。一覧の節が無く `last-updated-cr` でも見つからなければ、latest-specs は走査せず、収集サマリにその旨を書く。
- 各ファイルについて、フロントマターの `has_insights` が `false` なら飛ばす（3.4.6。ファイル名での除外〔`schema.md`・`crud.md`・`dfd.md`・`*-seq.md`〕は `docs_layout` の期待値の規則に移す）。
- 節の項目のうち、`{DOCS}` の同じファイル（`latest-specs/{area}/{path}` → `{DOCS}/{area}/specs/{path}`。`docs_layout` の対応で引く）の節に同じ項目があるものを除く。項目は、表の行（`種別`・`内容`・`対応方針` の3つのセル。`#` の列は比べない）と、表の外の空でない行（前後の空白を除いた文字列）。`{DOCS}` にファイルが無ければ全部を今の CR の項目とする。
- **今の CR が昇格済みのファイルは、前回の収集結果を引き継ぐ:** `{DOCS}` の同じファイルのフロントマター `last-updated-cr` が今の CR なら（前回の close が C2 まで進んだ後の再実行）、そのファイルは `{DOCS}` と比べない。代わりに、書き出す前の既存の `--output-file`（前回の `INSIGHTS-{CR}.md`）の `## {出典のパス}` の節を、そのファイルの項目として引き継ぐ。
  - 前回の `INSIGHTS-{CR}.md` があり、そのファイルの節が無ければ、項目は無い（前回も集めなかった）とする。
  - 前回の `INSIGHTS-{CR}.md` が無ければ、そのファイルの項目は集めない。収集サマリに「今の CR が昇格済みで前回の収集結果が無い {m} ファイル（気づきを集められない）」とパスを出す（黙って落とさない）。
  - 引き継ぎの判定は `docs_layout.last_updated_cr` を使う。
- 新しい引数 `--docs`（close Step A で渡す）。
- 収集サマリに「latest-specs: 一覧の {n} ファイルを走査、`{DOCS}` に既にある {k} 件を除外、前回の収集結果から {j} ファイルを引き継ぎ」を足す。

**理由:** A3-7。Step A は Step C0（`{DOCS}` の pull）と C2（昇格）より前に走るので、`{DOCS}` の版は前の承認済みの版で、そこに無い項目が今の CR の工程11 で足した項目になる。書く側（工程11 の agent・survey）を変えずに済む（6. の却下した案）。ただし前回の close が C2 まで進んだ後は `{DOCS}` に今の CR の項目が既にあり、比べるとすべて除かれる。3.3 の案内どおり今の CR の IDEA・LL を消して作り直すと、作り直しの Step B・C が工程11 の気づきを読めず、前回の `INSIGHTS-{CR}.md` も上書きされて失われる。そのため、昇格済みのファイルは前回の収集結果を引き継ぐ（人の判断 2026-11-05。7. の 4.）。

#### 3.4.3 未記入の判定（A3-13・A3-14）

**変更前:** collect_insights.py の未記入の判定は、`>` の引用行・`---`・`{…}` のプレースホルダー行を除いて空かを見る。「なし」の行・HTML コメントは本文として数える。

**変更後:**
- HTML コメント（`<!--` 〜 `-->`。複数行を含む）の中の行は本文とみなさない。
- `>` で始まる引用行（テンプレートの案内文）・`---`・表のヘッダー行と区切り行は項目に数えない（今のまま）。
- 表の外の行が「なし」「（なし）」「(なし)」「特になし」（末尾の `。` は無視）だけなら未記入。
- 表のデータ行のうち、`{…}` のプレースホルダーを含む行と、`内容` のセルが上の「なし」の語の行は、項目に数えない。
- 節の項目が0件なら、その節は集めない。項目があれば、数えない行とコメントを除いた本文を出す。
- 項目の定義（数えない行・「なし」の語・表の行の取り方）は `docs_layout.py` に1つだけ置き、3.4.2 の `{DOCS}` との比較も同じ定義を使う（3.13）。

**理由:** A3-13・A3-14。「なし」だけの節を毎回集めると、Step B・C の LLM が空の項目を読む。

#### 3.4.4 工程7・8 の気づきの置き場所（A3-25）

**変更前:** collect_insights.py は CODING・VERIFY の「気づき・提案メモ」の節を集めるが、coder・verifier の出力の定義にその節が無い。

**変更後:**
- `xddp-coder-agent.md` の Coding Memo の内容に「`## 気づき・提案メモ`（`| # | 種別 | 内容 | 対応方針 |` の表。無ければ「なし」）」を足す。
- `xddp-verifier-agent.md` の Output Format の最後（NG事項一覧の後）に同じ節を足す。cross の VERIFY も同じ agent が書く（07・08 の SKILL の cross の呼び出し）ので、両方に節ができる。10-test-run の b-1 の再検証も同じ agent なので、その出力にも節ができる。

**理由:** A3-25。集める側に合わせて書く側に置き場所を作る（工程7・8 の気づきが集まらない）。

#### 3.4.5 SPO §9（A3-26・N8）

**変更前:** §9 のテンプレートのコメントは「手で直さない（再実行で上書きされる）」だが、`specout_bfs.py` の §9 の作り直しは `[自動転記]` の行と `{内容}` の行だけを除き、人の行を残す。`内容` が「なし」の行も残る。

**変更後:**
- `04_specout-summary-template.md` の §9 のコメント `<!-- 書き手: スクリプト（specout_bfs.py assemble-spo）。手で直さない（再実行で上書きされる） -->` を `<!-- 書き手: 表の [自動転記] で始まる行はスクリプト（specout_bfs.py assemble-spo）が作り直す。それ以外の行は人・AI が書き、再実行でも残る -->` にする。
- `specout_bfs.py` の §9 の作り直しで、残す行から `内容` が `なし` の行を除く（今は `[自動転記]` と `{内容}` だけを除く）。

**理由:** A3-26・N8。コメントがスクリプトの実際の動作（人の行を残す）と違い、「なし」の行が再実行で残って気づきとして集まる。

#### 3.4.6 latest-specs の気づきメモの規則（A3-30）

**変更前:** 11-specs の自動修正・reviewer-checklists/SPEC.md・survey は「Section 3-4 の気づきメモポリシー」を参照するが、参照先に該当する節が無い。collect_insights.py はファイル名（`schema.md`・`crud.md`・`dfd.md`・`*-seq.md`）で除外し、テンプレートのフロントマター `has_insights` を見ない。

**変更後:**
- 規則は、各ファイルのフロントマター `has_insights`（`true`＝「気づき・提案メモ」の節を持つ。工程11 のテンプレートがすでに持つ）とする。
- `has_insights` の期待値は、ファイル名から決める規則として `docs_layout.py` に1つだけ置く（`expected_has_insights(path)`。`schema.md`・`crud.md`・`dfd.md`・`*-seq.md` は `false`、それ以外は `true`。今の collect_insights.py の除外の規則を移す）。
- `docs_layout.py` に、見出しの文字列（`気づき・提案メモ`。番号・見出しの水準・全角空白は問わない）・節を探す関数・`has_insights` の読み方・期待値の規則を置き、`collect_insights.py` と `artifact_lint.py` が import する。
- `artifact_lint.py`（`--doc-type SPEC` でフロントマターがあるとき）: `has_insights: true` で節が無い、または `false` で節がある場合を `frontmatter.insights_mismatch` に出す。`has_insights` の値が期待値と違う場合を `frontmatter.insights_expected_mismatch` に出す（値を書き換えて不一致を消すことを検出する）。
- `reviewer-checklists/SPEC.md` のチェック項目4 を「フロントマター `has_insights` と節の有無の一致・期待値との一致は `LINT_RESULTS.frontmatter.insights_mismatch`・`insights_expected_mismatch` を確認する（機械検査済み・再チェック不要）」にする。自動修正対象カテゴリの「気づきメモセクションの有無」は残す。
- `xddp-11-specs/SKILL.md` の自動修正の「気づきメモセクションの有無（Section 3-4 の気づきメモポリシーとの不整合）」を「（フロントマター `has_insights` と節の有無の不一致。`has_insights` の値は変えず、節を足す・消す。値が期待値と違う〔`insights_expected_mismatch`〕ときだけ値を期待値に直す）」にする。`xddp-survey/SKILL.md` の Step 7 も同じ言い方にする。
- `11_module-sequence-template.md` に、他の `has_insights: false` のテンプレートと同じ注記（「気づきメモは spec.md に記録してください（このファイルには気づきメモセクションなし）」）を足す。

**理由:** A3-30。参照先の無い規則を、ファイルが持つ値と1つの期待値の規則に置き換える。自動修正で `has_insights` を `false` に変えると、そのファイルが気づきの収集（3.4.2）から黙って外れるので、修正の向きを決め、期待値との一致を機械検査する。

### 3.5 promote.py の判定と報告

#### 3.5.1 LL の `repo` 欄の振り分け（A3-9）

**変更前:** `extract-ll` は `repo` 欄を見ずに今の CR の LL をすべて `LL-{CR}.md` に書く。`run` は `repo` 欄の値をそのまま `{DOCS}/{repo}/knowledge/` のパスにし、`unknown` だけを要確認LL一覧に出す。

**変更後:**
- 振り分けを1つの関数にする。`repo` 欄が `REPOS_KEYS` のどれか → その repo、`cross` で IS_MULTI → cross、`unknown` → 理由 `unknown`、それ以外（`全リポジトリ`・IS_MULTI でない `cross`・書き違い）→ 理由 `invalid`。
- `extract-ll` に `--repos-keys`・`--is-multi` を足す。`LL-{CR}.md` には振り分け先のあるエントリだけを書き、振り分け先の無いものを stdout の `unrouted`（[{id, repo, reason}]）に返す。`count` は書いたエントリの数。
- `run` の Layer 2 への振り分けも同じ関数を使い、振り分け先の無いものを出力ファイルの「要確認LL一覧」に理由つきで出す（今は `unknown` だけ）。
- close Step D の「要確認 LL（repo: unknown — 昇格スキップ）」を「要確認 LL（repo 欄が unknown か REPOS に無い値 — 昇格スキップ）」にし、理由を添えて示す。示すのは `run` の出力ファイルの「要確認LL一覧」だけにする（同じ LL を2回示さない）。`extract-ll` の `unrouted` は、`run` が実行されなかった（C2 の前で止まった）ときだけ示す。

**理由:** A3-9。書き違いの repo 名で `{DOCS}` に意図しないディレクトリを作る・存在しない rulebook を knowledge agent に作らせることを防ぐ。

#### 3.5.2 cross の置き場所は IS_MULTI で決める（A3-8・A5-24）

**変更前:** `repo: cross` の LL と `project-rulebook-cross.md` の写しは、HAS_CROSS（今の CR に cross の成果物があるか）が偽なら行わない（LL は黙って捨てる）。`run` は `--is-multi` を受け取るが使わない。

**変更後:**
- `repo: cross` の LL は、IS_MULTI なら `{DOCS}/cross/knowledge/lessons-learned.md` に書く（今は HAS_CROSS が偽なら黙って捨てる）。
- `project-rulebook-cross.md` の写し（C6）は IS_MULTI で行う（今は HAS_CROSS）。knowledge agent・fill-rulebook は cross の成果物によらず cross の rulebook を更新するため。
- 今の CR の cross の成果物から写すもの（仕様・CRS・TSP・TRS・破壊的変更の警告）は HAS_CROSS のまま。
- `run` は今も `--is-multi` を受け取るが使っていないので、それを使う。
- close Step D の「cross: `project-rulebook-cross.md` を…昇格」の行の条件を IS_MULTI にし、成功・失敗は 3.5.3 の結果で書き分ける。

**理由:** A3-8・A5-24。人の判断（1.3 の 3.）。cross の知見・rulebook は CR をまたいで蓄積するもので、今の CR が cross の成果物を作ったかとは関係しない。

#### 3.5.3 失敗をすべて出す（A3-27・A5-31）

**変更前:** `write_output_file` は「リポジトリ別処理結果一覧」に `affected_repos` だけを出す。`repo_results` の `cross`・`system` のキーと `global_errors`（共通ファイルの失敗）は出力ファイルに出ず、close Step D・E の `FAILED_REPOS` にも入らない。`repo_results` の `cross` のキーは、成功では `promote_specs` だけが作る（他の関数は失敗時にしか作らない）。

**変更後:**
- 処理する対象（affected の各 repo、IS_MULTI なら `cross`、`latest-specs/system` があれば `system`、`共通ファイル`）を処理の前に `repo_results` に登録し（`setdefault`）、各対象を「成功／失敗／対象外」の3つで書き分ける（どの処理も行わなかった対象は「対象外」）。成功しても行が無い、ということを無くす。
- `write_output_file` の「リポジトリ別処理結果一覧」に、`affected_repos` に続けて `repo_results` のほかのキー（`cross`・`system`）を出す。`global_errors` は「共通ファイル（`{DOCS}` 直下）」の1行として成功・失敗を出す。見出しは「処理結果一覧（repo・cross・system・共通ファイル）」にする。
- stdout の JSON に `failed`（失敗した対象の名前の一覧。`共通ファイル` を含む）を足す。
- close Step D の `FAILED_REPOS` を `FAILED_TARGETS`（出力ファイルの処理結果一覧で「失敗」の対象。cross・system・共通ファイルを含む）にする。Step D の各行の書き分けと、Step E のステータス（「⚠️ 完了・クローズ済み（{FAILED_TARGETS} の昇格が未完了…）」）も同じ一覧を使う。
- 出力ファイルの内容の説明（close の「`promote.py` は以下を OUTPUT_FILE に書き込む」）も直す。

**理由:** A3-27・A5-31。人の判断（1.3 の 4.）。cross・system・共通ファイルの昇格の失敗が人に示されず、CR が「完了」として閉じる。

#### 3.5.4 `{DOCS}` の backlog に足し込む（A3-4）

**変更前:** `shutil.copy2` で `{XDDP_DIR}/improvement-backlog.md` を `{DOCS}/improvement-backlog.md` に上書きする。

**変更後:**
- **2つのファイルの役割を決める:** `{DOCS}/improvement-backlog.md` を「正」とする（ステータス・対応CR 等を直すのはこちら）。`{XDDP_DIR}/improvement-backlog.md` は、この作業場所の CR の close が新しい IDEA を書く受け口で、`{DOCS}` に足し込んだ後のステータスは追わない。テンプレートの冒頭（3.2.2）・close Step D・README に書く。
- `{DOCS}` に無ければ、今までどおり写す。
- あれば、Layer 1 の IDEA のうち `{DOCS}` に同じ ID が無いものを `{DOCS}` の `## 3. アイデア詳細` の末尾（次の `## ` の見出しの前）に足し、`{DOCS}` の §1・§2 を 3.2.2 で作り直す。
- 同じ ID が `{DOCS}` にあるものは、何もしない（`{DOCS}` が正なので、ステータスの違い等は比べない）。ただし今の CR の ID（`IDEA-{CR}-{NN}`。3.3 と同じ全体一致）で、close が書き人が直さない部分が違うものは、出力ファイルの新しい節「`{DOCS}` と内容が違う今の CR の IDEA（上書きしていない）」と stdout の `backlog_conflicts` に出す（3.3 の作り直しで同じ ID が再び採られた場合）。close Step D でも示し、どちらを採るかは人が `{DOCS}` を直して決める。前の CR の ID は比べないので、`{DOCS}` でステータスを直したことで報告が毎回出続けることはない。
  - 比べる部分: 見出し（タイトル）、項目の表の `カテゴリ`・`repo`・`発生源` の行、`**内容：**`・`**発生経緯：**`・`**期待効果：**`・`**推定影響範囲：**` の本文（3.1 の正規化をする）。
  - 比べない部分（人が `{DOCS}` で直す）: 項目の表の `優先度`・`ステータス`・`対応CR` の行と、`**CR化の判断メモ：**` の本文。今の CR の close の再実行の前に人が `{DOCS}` でステータスを `❌ 却下` にしても、報告されない。
  - 比べる・比べない部分の定義は promote.py に1つだけ置く。
- `{DOCS}` の backlog に必要な節（3.2 の backlog の `## 1.`・`## 2.`・`## 3.`）が無いときは、足し込まず、`{DOCS}` の backlog を変えずに「共通ファイル」の失敗（3.5.3）とし、出力ファイルにファイルのパスと無い節の名前を出す（close Step D・E が失敗として示す。人が節を直して `/xddp-close {CR}` を再実行する）。
- Layer 1 から消した IDEA は `{DOCS}` からは消えない。Step D に「IDEA を取り消す・ステータスを変えるなら `{DOCS}/improvement-backlog.md` を直す」を添える。
- 取り消しは、`{DOCS}` でエントリを消さず、ステータスを `❌ 却下` にする（テンプレートのステータスにある）。`{DOCS}` でエントリを消すと、Layer 1 に残っている同じ ID が次の close で足し込まれて戻るため。テンプレートの冒頭の注記（3.2.2）・Step D・README に書く。

**理由:** A3-4。ID が CR を含む（3.1）ので、別の作業場所の IDEA と重ならず、足し込むだけで両方が残る。正を1つに決めないと、どちらで直しても他方と食い違い、「内容が違う」の報告が毎回出続けて本当の競合が埋もれる。`{DOCS}` は作業場所をまたいで共有するので、ステータスの正にする。今の CR の IDEA は close が書いた直後なので、違えば作り直しによるもので、黙って捨てずに示す。

### 3.6 LL の切り分けのコードブロック（R2・R3）

**変更前:** `_split_ll_blocks` は `### LL-…：` の見出しを先に判定してフェンスの状態を消すので、コードブロックの中の見出しでエントリを切る。`_Fence` は長さを問わず同じ文字の行で閉じるので、短いフェンスで長いフェンスが閉じる。

**変更後:**
- `_split_ll_blocks`・`_window_has_meta` は、フェンスの中かを先に見て、フェンスの中の行は見出しとして扱わない（今は `### LL-…：` を先に判定し、フェンスの状態を消す）。
- `_Fence` は、開いたときと同じ文字で、長さが開いたフェンス以上の行（後ろの空白は可）でだけ閉じる。
- フェンスがファイルの終わりまで閉じないときは、そのフェンスを開いた行のエントリを `unparsed`（理由 `unclosed-fence`）として返し、そのフェンスの中の見出しでは今までどおりエントリを切る（閉じ忘れで後のエントリを全部飲み込まないように）。
- close Step D の「見出し・CR 欄を読めない LL」の理由に「`unclosed-fence` なら『コードブロックが閉じていない』」を足す。
- `extract-ll`・`run`・`index`（3.2・3.3）・Layer 2 の重複判定（3.1）は、すべてこの切り分けを使う。

**理由:** R2・R3。CommonMark 仕様の「4.5 Fenced code blocks」の規則（閉じるフェンスは開いたフェンスと同じ文字で、長さが開いたフェンス以上）に合わせる。

### 3.7 `LESSONS_CONTEXT` の受け取り口（A3-10・A3-11・A3-12）

**変更前:** 02・05・09 の SKILL は Step A0 で `LESSONS_CONTEXT` を作って analyst・architect・test-writer に渡すが、3つの agent の Inputs に `LESSONS_CONTEXT` が無い（designer だけが持つ）。

**変更後:** designer（`xddp-designer-agent.md`）にそろえ、Inputs に `LESSONS_CONTEXT` (optional) と使い方を足す。呼び出し側（02・05・09 の SKILL）は今も初回の生成のときだけ渡している（修正のラウンドでは渡さない）ので、呼び出し側は変えない。

| agent | 呼び出し側の TARGET_TAGS | 使い方 |
|---|---|---|
| analyst | `#要求分析` `#仕様定義` `#見落とし` | 分析の前に読み、§3（曖昧性・不明点）・§4（見落とし・抜け漏れ）を挙げるときの観点にする。反映した項目に LL の ID を添える |
| architect | `#方式検討` `#設計` `#リスク` `#依存関係` | 各案のリスク・懸念の評価（comparison の懸念事項と対策）に使う。反映した項目に LL の ID を添える |
| test-writer | `#テスト` `#不具合` `#テスト観点` `#見落とし` | テストの観点・TC を足すときに使う。反映した TC・観点に LL の ID を添える |

**理由:** A3-10〜A3-12。渡しているのに受け取り口が無く、使い方が決まっていない。

### 3.8 close SKILL.md の記述（A3-16・A3-20・A3-21・A3-23）

**変更前:** Step B・C は「create from template」とだけ書きテンプレートのパスが無い。Step C の抽出の観点は「(same as before …)」。Layer 1・Layer 2 のコメントの読み手の一覧が足りない。Step B の「Update summary table」がどの表か分からない。

**変更後:**
- Step A: `collect_insights.py` に `--docs {DOCS}` を渡す（3.4.2）。
- Step B:
  - 3.3 の `index --check` を先に実行し（0 以外なら停止）、`cr_idea_count` が 1 以上なら追記しない。
  - IDEA を `## 3. アイデア詳細` の末尾（次の `## ` の見出しの前）に足す（3.2.2）。
  - 「If not exists, create from template」を `~/.claude/skills/xddp-close/templates/10_improvement-backlog-template.md` から作る、にする（`{YYYY-MM-DD}` は `{TODAY}` に置き換え、他の `{…}` は残す）（A3-20）。
  - ID・書式は 3.1・3.2.2。「Update summary table」を消す。`repo` の判定の規則は今のまま。
- Step C:
  - 「create from template」を `~/.claude/skills/xddp-close/templates/lessons-learned-template.md` から作る、にする（A3-20）。
  - 「Knowledge Extraction Perspectives」の `(same as before — …)` を次にする（A3-21）: 「Step A の `INSIGHTS-{CR}.md` の項目から、後の CR で同じ判断・作業をするときに役立つものを LL にする。観点は、要求分析・方式検討と設計・実装とテスト・進め方。タグはタグ一覧から選ぶ」。
  - ID・タグの区切りは 3.1・3.2.1。`cr_ll_count` が 1 以上なら追記しない（3.3）。
  - 「append one row to the エントリ一覧 table and update 最終更新CR」と「タグ別インデックスの更新」の手順を消し、その位置ではなく「ファイルサイズポリシー（アーカイブ提案）」の後、「Final VCS commit」の前に `promote.py index --cr {CR} --today {TODAY} --lessons-file … --backlog-file …` を実行する、にする（アーカイブの提案で人が移したエントリも表に反映し、書き換えた Layer 1 を同じコミットに含める）。この `index` は Step B・C の追記の有無によらず必ず実行する（3.3）。その stdout の `unknown_tags`・`cr_unknown_repo_ideas`・`bad_ideas`・`unparsed_ll`・`duplicate_ids` を Step D で示す。終了コードが 0 以外なら stderr を示して停止する。
  - アーカイブの手順は 3.1。
  - Layer 1 のコメントの読み手を「xddp-02-analysis・05-arch・06-design・09-test の Step A0（`load-lessons-context.md`）」にする。Layer 2 のコメントの読み手は「xddp-02-analysis の Step 0（`domain_refs.py`）」とする（A3-23。Step A0 は Layer 1 だけを読む）。
- Step C2〜C7: `extract-ll` に `--repos-keys`・`--is-multi` を渡す（3.5.1。`unrouted` は C2 の `run` が実行されなかったときだけ Step D で示す）。出力ファイルの説明を 3.1（`ll_conflicts`）・3.5.3・3.5.4 に合わせる。
- Step D: 3.1（`ll_conflicts`・`duplicate_ids`〔Step C の `index` と `run` の両方〕）・3.3・3.5（要確認LL は `run` の一覧・`backlog_conflicts`・backlog の正は `{DOCS}`）・3.6 の表示を足す・直す。「要確認 IDEA」は `cr_unknown_repo_ideas` から示す。案内文の `### LL-{NNN}：{タイトル}`（3か所）を `### LL-{CR}-{NN}：{タイトル}` にする（3.1）。
- Step E: `FAILED_TARGETS` を使う（3.5.3）。

**理由:** A3-16・A3-20・A3-21・A3-23。LLM が手順を推測しなくてよいように、パス・観点・読み手を実物に合わせて書く。

### 3.9 update-knowledge の lesson（A3-18）

**変更前:** lesson の書き込みは「Ensure file exists (create with header if not)」「Read existing LL-NNN; assign next NNN. Append new entry at end.」だけで、ヘッダー・エントリの書式・番号の採り方を LLM が決める（update-knowledge SKILL.md の書き込みの節の **lesson:**）。

**変更後:**
- 入力の例のタグを `#リスク, #見落とし, #コーディング`（カンマ区切り）にする。
- 書き込みの手順を次にする:
  1. `promote.py index --today {TODAY} --layer2-file {TARGET_FILE} --area {repo}` を実行する（ファイルが無ければヘッダーを作る。`## エントリ一覧` が無ければ足す。3.2.3）。終了コードが 0 以外なら stderr を示して停止する。
  2. ID は stdout の `next_manual_id`（`LL-M{TODAY の YYYYMMDD}-{NN}`。3.1）を使う。
  3. エントリは close の Step C の Entry Format（`**CR：** —` ／ **工程：** … ／ **repo：** {repo} ／ **タグ：** …）で、`**出典：**` の行を足して末尾に書く。
  4. もう一度 `index --layer2-file` を実行する（エントリ一覧を作り直す）。stdout の `duplicate_ids`・`unparsed_ll`・`unknown_tags` が空でなければ人に示す。
- 「Ensure file exists (create with header if not)」「Read existing LL-NNN; assign next NNN」を消す。

**理由:** A3-18。書式・ヘッダー・番号を LLM に任せず、close と同じ定義とスクリプトに寄せる。

### 3.10 01-init（A3-17・A3-24 の書く側を1つにする）

**変更前:** 01-init の Step 4.5 が Layer 2 の知見ログを、独自のひな形（列 `ID｜タイトル｜タグ｜CR｜日付` とプレースホルダーの行）で作る。

**変更後:**
- Step 4.5 の 3.・4. から `{DOCS}/{repo}/knowledge/lessons-learned.md` を消し、「Initial file contents」の Layer 2 の知見ログのひな形を消す。Layer 2 は書く側（promote.py・update-knowledge）が 3.2.3 のヘッダーで作る。既に古いひな形で作られたファイルは、次に書く側が 3.2.3 の規則で節を直す。
- Layer 2 を読む `domain_refs.py` は、ファイルがあるときだけ集める（今のまま）。

**理由:** A3-17・A3-24。ヘッダーの定義を promote.py の1か所にする（6. の却下した案）。

### 3.11 abort（A3-22）

**変更前:** Step 3 の括弧の文が「update-knowledge 等で backlog に登録」と案内するが、update-knowledge に backlog の種別が無い。

**変更後:** Step 3 の括弧の文（AI 向けの注記で、人には表示されない）を消し、次の案内を「If はい」の追記の後の **Tell the user** のブロックとして置く（人が読む案内にする）。案内の中のコマンドは他の SKILL と同じ `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py …` の形で書く。冒頭の「reuse …」の変数の列挙に `DOCS` を足す（close と同じく CR Resolution の値を使う）。案内の文:
「progress.md に書いた気づきは昇格しない。残すなら、IDEA は人が `{XDDP_DIR}/improvement-backlog.md` の `## 3. アイデア詳細` の末尾に `IDEA-{CR}-{NN}` で書き（書式は xddp-close の Step B。次の close で `{DOCS}` に足し込まれる）、LL は `/xddp-update-knowledge {repo} lesson` で登録する。cross の LL は update-knowledge で登録できないので、人が `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py index --today {TODAY} --layer2-file {DOCS}/cross/knowledge/lessons-learned.md --area cross` を実行して ID（stdout の `next_manual_id`）を得て、そのファイルの末尾に書き（書式は xddp-close の Step C）、同じコマンドをもう一度実行して表を作り直す。`{XDDP_DIR}/improvement-backlog.md` が無ければ、`~/.claude/skills/xddp-close/templates/10_improvement-backlog-template.md` を写して作る（`{YYYY-MM-DD}` は今日の日付に置き換え、他の `{…}` は残す。3.8 の Step B と同じ）。」
（cross の行は IS_MULTI のときだけ示す。backlog のファイルが無い場合の文は、ファイルが無いときだけ示す。abort が値を知っている `{XDDP_DIR}`・`{DOCS}`・`{TODAY}`・`{CR}` は値に置き換えて示す〔例: `IDEA-CR-2026-970-{NN}`〕。人が埋める欄の `{NN}`〔`01` からの連番〕・`{repo}`〔REPOS のキー〕は置き換えず、そのまま示す）
今の文の「自動昇格しない理由は…」（実行に不要な設計根拠。CLAUDE.md「実行時ファイルへの設計根拠・履歴の混入禁止」）は消す。

**理由:** A3-22。存在しない手段を案内しない。IDEA は Layer 1 に書けば 3.5.4 で `{DOCS}` に足し込まれる（`{DOCS}` に無い ID なので、今の CR の ID でなくても足される）。

### 3.12 テスト・fixture

- `test_promote.py`:
  - ID: `LL-{CR}-{NN}` と `LL-M…` が Layer 2 で重ならず両方入る。同じ ID は足さない。同じ ID で内容が違うものは上書きせず `ll_conflicts` に出る。同じ Layer 1 で `run` を2回実行しても、2回目の `ll_conflicts`・`backlog_conflicts` が空（区切りの `---`・空行の違いを内容の違いとしない）。Layer 2 に同じ ID が2つあれば、足さず `ll_conflicts` にも出さず、`run` の `duplicate_ids` に出る。本文に `### {ID}：` の文字列があるだけ（コードブロックの中）では「既にある」としない。
  - `index`: Layer 1 の2つの表とタグの区切り（カンマ・`、`・空白）・`unknown_tags`・`最終更新CR`（今の CR の LL が無ければ変えない）。backlog の §1・§2・未知のステータス・§3 の外の IDEA（`outside-section`）・`cr_unknown_repo_ideas`。Layer 2 のヘッダーの作成と表、`## エントリ一覧` の無い既存の Layer 2（ヘッダーだけ・破壊的変更警告だけ・01-init の古いひな形）に節を足す位置。`next_manual_id`（エントリを消した後も最大値 + 1）・`duplicate_ids`。冪等（2回目は書かない）。`--check` は書かない。Layer 1・backlog で節の無いファイルは exit 1。
  - `cr_ll_count`・`cr_idea_count`（見出しの崩れたもの・フェンスの中のもの・CR 名が別の CR 名の接頭辞のとき〔`REQ-1` と `REQ-1-2`〕に他の CR のエントリを数えない）。
  - 振り分け: `全リポジトリ`・IS_MULTI でない `cross`・`unknown` が `unrouted`／要確認LL に理由つきで出る。IS_MULTI で HAS_CROSS でない CR の `repo: cross` が cross の Layer 2 に入る。cross の rulebook が IS_MULTI で写る。
  - 出力ファイル: cross・system・共通ファイルの失敗が処理結果一覧と `failed` に出る。IS_MULTI で HAS_CROSS でない CR の cross の昇格の成功が「成功」の行として出る。処理しなかった対象が「対象外」として出る。
  - backlog: `{DOCS}` に無い IDEA を §3 の末尾に足す。前の CR の ID でステータスの違うものは比べず報告しない。今の CR の ID で内容の違うものは上書きせず `backlog_conflicts` に出す。今の CR の ID で `{DOCS}` の `優先度`・`ステータス`・`対応CR`・CR化の判断メモだけが違うものは報告しない。`{DOCS}` の backlog に必要な節が無ければ、足し込まず共通ファイルの失敗になる（ファイルは変わらない）。既存のテスト `test_backlog_overwrite_not_append`（丸ごと上書きを前提にしたテスト）は、これらの足し込みのテストに置き換える。
  - `append_breaking_warning` がファイルの無いときにヘッダーを書く。
  - R2・R3: 段階1 の報告書の再現の入力で、エントリが切れない。閉じないフェンスは `unclosed-fence`。
- `test_collect_insights.py`: cross の TSP・progress.md を集める。latest-specs は一覧のファイルと `last-updated-cr` が今の CR のファイルの和集合だけ（一覧に無いものは収集サマリに出る）・`has_insights: false` を飛ばす・`{DOCS}` にある項目を除く・どちらでも見つからなければ走査しない。`{DOCS}` の `last-updated-cr` が今の CR のファイルは、前回の `INSIGHTS-{CR}.md` の項目を引き継ぐ（1回目の収集 → `{DOCS}` に昇格した状態で2回目の収集をして、latest-specs の項目が1回目と同じ）。前回の `INSIGHTS-{CR}.md` が無ければ、収集サマリにそのファイルが出る。「なし」・HTML コメント・`>` の案内文だけの節・SPO §9 の「なし」の行を集めない。
- `test_docs_layout.py`・`test_artifact_lint.py`: 節の検出・項目の定義・`expected_has_insights`・`insights_mismatch`・`insights_expected_mismatch`。
- `test_specout_bfs.py`: §9 の「なし」の行が再実行で残らない。
- fixture: `test-fixtures/scratch-workspace/` の `xddp/lessons-learned.md`・`xddp/improvement-backlog.md`・`baseline_docs/*/knowledge/lessons-learned.md`・`baseline_docs/improvement-backlog.md`、`test-fixtures/scratch-workspace-min/seeds/*/baseline_docs/svc-a/knowledge/lessons-learned.md`、`test-fixtures/scratch-workspace-p4-new-mode/baseline_docs/widget-svc/knowledge/lessons-learned.md`（01-init の古いひな形）の LL・IDEA の ID を新しい形にし、表を `promote.py index` で作り直す。fixture の中で Layer 1・Layer 2 の LL を指す参照も、同じエントリの新しい ID にする（参照先が無くならないように）: `test-fixtures/scratch-workspace/baseline_docs/cross/knowledge/code-knowledge/_flows/alert-publish-dispatch-sequence.md` の「（LL-003 参照）」、project-rulebook の出典（`test-fixtures/scratch-workspace/baseline_docs/notify-svc/project-rulebook.md`・`test-fixtures/scratch-workspace/xddp/project-rulebook-notify-svc.md`・`test-fixtures/scratch-workspace/xddp/project-rulebook-cross.md` の `（出典: LL-…, CR-…）` は 3.1 の新しい書き方 `（出典: {LL の ID}）` に。同じファイルの見出しのコメント・変更履歴の LL の ID も新しい ID に）。直さないのは `pending-items/` の中だけ（CR の作業中の中間ファイルで、close が毎回作り直す）。

### 3.13 再発防止（PLAN-20261103-contract-audit 3.3）

1. **書く側→読む側のテスト:**
   - 実物のテンプレート（`lessons-learned-template.md`・`10_improvement-backlog-template.md`）から作った Layer 1 に、close Step B・C の書式のエントリを（IDEA は §3 の末尾に）足し、`index`・`extract-ll`・`run` に通す。テンプレートの節の名前とスクリプトの定義がずれたら落ちる。Layer 1 のエントリが `load-lessons-context.md` の読み方（タグ別インデックスの行 → `### {id}：`）で引けること（Layer 1 の読み手は 02・05・06・09 の Step A0）と、`run` で書いた Layer 2 のエントリが `domain_refs.py` に集まること（Layer 2 の読み手は 02 の Step 0）を、それぞれ確かめる。
   - 工程11 の全テンプレートについて、`has_insights` と「気づき・提案メモ」の節の有無が一致し、`has_insights` が `docs_layout.expected_has_insights`（テンプレートが作るファイルの名前で引く）と一致することを確かめる。
   - CR の fixture（ANA・CRS・SPO・TSP〔repo・cross〕・CODING・VERIFY〔repo・cross〕・TRS・progress.md・latest-specs）で `collect_insights.collect` を通し、各成果物の節が集まることを確かめる。
2. **共有の値の単一定義:**
   - 気づき・提案メモの見出しと節の検出・項目の定義（3.4.3）・`has_insights` の読み方と期待値の規則は `docs_layout.py` に置き、`collect_insights.py` と `artifact_lint.py` が import する。
   - LL・IDEA の ID の形（今の CR の ID の全体一致・手で登録する ID の採番を含む）・Layer 1・Layer 2・backlog の節と表の列・Layer 2 のヘッダー・`repo` 欄の振り分けは `promote.py` に置く。表を書くのは `promote.py` だけで、SKILL.md・テンプレートは「スクリプトが作り直す」とだけ書く。
   - **残る約束（このプランでは守れない）:**
     - エントリそのもの（LL の見出しとメタ行、IDEA の項目の表）は LLM・人が書く。書式は close の Step B・C に1つだけ定義し、update-knowledge・abort はそこを指す。崩れたエントリは `extract-ll`・`index` が `unparsed_ll`・`bad_ideas` で返し、close の Step D で人に示す（黙って落とさない）。
     - 手で登録する ID（`LL-M{YYYYMMDD}-{NN}`・`IDEA-M{YYYYMMDD}-{NN}`）は、別の作業場所から同じ `{DOCS}` のファイルに同じ日に登録すると重なりうる。`{DOCS}` を pull して取り込んだ後、close の `run`（そのファイルに書いたか表を作り直したとき）または update-knowledge の `index` が `duplicate_ids` で返し、人に示す（3.1）。close がそのファイルに触れない間は見つからない。
     - IDEA のステータス等は `{DOCS}` で直し、取り消しはステータスを `❌ 却下` にする（3.5.4）。`{XDDP_DIR}` 側で直しても届かないこと・`{DOCS}` でエントリを消すと戻ることは、テンプレートの注記と Step D で示すだけで、スクリプトでは検出しない。
3. **refcheck の検査は足さない。** 理由: 表とヘッダーの定義はスクリプトに寄せ、テンプレートとの一致は 1. のテストで守る。2. の「残る約束」は実行時に人に示される。

### 3.14 ドキュメント・ADR

- `CLAUDE.md` のファイル構成の表の `xddp-close/scripts/` の行: `promote.py` に `index`（Layer 1・Layer 2・backlog の表を作り直す・今の CR のエントリを数える）・`extract-ll` の振り分け（`unrouted`）・backlog の足し込み・cross の条件を、`collect_insights.py` に対象（cross の TSP・progress.md）・latest-specs の絞り込み（工程11 の一覧・`has_insights`・`{DOCS}` に無い項目）・`--docs` を足す。`xddp-common/scripts/` の `docs_layout.py` の説明に気づき・提案メモの見出しと `has_insights` を足し、`artifact_lint.py` の説明に `insights_mismatch` を足す。
- `README.md`: `/xddp-close` の行・`promote.py` の行・プロジェクト固有ファイルの表の `improvement-backlog.md`（`IDEA-{CR}-{NN}`）・`lessons-learned.md`（`LL-{CR}-{NN}`）の説明を直す。update-knowledge の lesson の ID（`LL-M{YYYYMMDD}-{NN}`）と、バックログ・知見ログの表はスクリプトが作り直すので手で直さないこと、`{DOCS}` の backlog が正（ステータス等は `{DOCS}` で直す。取り消しはエントリを消さずステータスを `❌ 却下` にする。消すと次の close で `{XDDP_DIR}` 側から足し込まれて戻る）で、close は `{DOCS}` に無い IDEA を足し込み、作り直した今の CR の IDEA・LL の内容の違いは人が直すことを書く（実例を1つ載せる）。
- `docs/adr/ADR-0035-lessons-backlog-ids-and-indexes.md`（追加）: 1.3 の方針（ID に CR を含める・表はスクリプトが作り直す・`{DOCS}` の backlog は足し込みで、ステータス等の正は `{DOCS}`・気づきの収集は今の CR が足したもの〔昇格済みのファイルは前回の収集結果を引き継ぐ〕・cross の置き場所は IS_MULTI）と理由、却下した案（6.）、残る制約（7. の 1. の並行 CR の項目の混入は運用で避ける。7. の 3. の全 repo に当てはまる LL の置き場所は別のプラン）。
- `docs/adr/ADR-0013-close-promote-script.md`: `index` サブコマンドと backlog の足し込みを ADR-0035 で足した旨を追記する。
- `docs/adr/README.md`: ADR-0035 の行を足す。
- `docs/xddp-contract-audit-2026-11.md` の 8.2: P3 のプラン名を `PLAN-20261105-lessons-backlog` にする。A5-24・A5-31 を P3 に移し（P3 の件数 31 → 33、P5 の件数 33 → 31）、「同じ型で、まとめて直すかを決めるもの」に人の判断（2026-11-05。1.3 の 2.〜4.）を書く。8.3 の P3 の名前も直す。

---

## 4. 影響範囲

- **影響するスキル・コマンド:** `/xddp-close`（Step A〜E）、`/xddp-update-knowledge`（lesson）、`/xddp-01-init`（Step 4.5）、`/xddp-abort`（Step 3）、`/xddp-02-analysis`・`/xddp-05-arch`・`/xddp-09-test`（agent の受け取り口だけ。呼び出し側は変えない）、`/xddp-07-code`・`/xddp-08-verify`・`/xddp-10-test-run`（b-1 の再検証。verifier の出力に節が1つ増える）、`/xddp-04-specout`（§9 のコメントと「なし」の行）、`/xddp-11-specs`・`/xddp-survey`（レビューの自動修正の言い方）、AI レビュー（SPEC）。
- **影響する工程:** close・工程2・5・7・8・9・10（b-1 の再検証）・4a（§9 だけ）・11（レビューだけ）。
- **後方互換性:** 考慮しない（CLAUDE.md「後方互換性ポリシー」）。既存の Layer 1・Layer 2 の `LL-NNN`・`IDEA-NNN` は移し替えない。切り分けの正規表現は ID の形を問わないので読めるが、`cr_ll_count`・`cr_idea_count` は新しい形の ID だけを数える。既存の `{DOCS}/improvement-backlog.md` の §1・§2 は、次の close で 3.2.2 のとおり作り直される。既存の Layer 2 で `## エントリ一覧` を持たないもの・古い列のものは、次に書く側が 3.2.3 のとおり節を足す・直す（エントリはそのまま）。
- **トークン:** close Step B・C で LLM が表を書かなくなる分だけ減る。工程7・8 の出力に表が1つ増える。
- **他のプランとの関係:**
  - P4（latest-specs）: `xddp-11-specs/SKILL.md`・`reviewer-checklists/SPEC.md`・`xddp-survey/SKILL.md` を P3 も1か所ずつ直す。P4 は P3 の実装の後の状態を見て書く。
  - P2（code-knowledge の書く側）: `xddp-update-knowledge/SKILL.md` の lesson の部分と、`xddp-close-knowledge-agent.md` の出典の1行を P3 が直す。P2 は P3 の実装の後の状態を見て書く。
  - P5（project-rulebook）: A5-24・A5-31 を P3 に移した。`promote_rulebooks` の cross の条件と `write_output_file` は P3 の後の状態を見て書く。A5-28（rulebook の丸ごと上書き）は P5 に残る。3.5.4 の backlog の足し込みとは別の直し方になる。
  - 全 repo に当てはまる LL の置き場所（7. の 3.）: 別のプランにする。このプランの 3.5.1 の振り分け（`全リポジトリ` は `invalid`）は、そのプランで値を足すときに直す。
  - PLAN-20260730-specout-recall-crosscheck: 監査のプラン 3.3 により、A3 の指摘を割り当てた修正プラン（このプラン）の実装の後に、メインのセッションが今の close Step A（3.4 の後の `collect_insights.py`）に合わせて書き換える。このプランでは触らない。

---

## 5. 確認項目

- [x] 1.2 の35件それぞれに、直した箇所とテストがある
- [x] `make test` が緑（refcheck 検査F: 実行時ファイルにプランの参照・履歴を書いていない）
- [x] 3.13 の書く側→読む側のテストが、実物のテンプレートを読んでいる
- [x] close Step B・C・D・E・update-knowledge・abort の手順が 3.1〜3.3 と矛盾しない（ID・書式・`index` の呼び方）
- [x] スキルの同期（close・update-knowledge・abort・01-init・agent の記述が同じ ID と書式を使う。実行時ファイルに古い ID の書き方〔`LL-{NNN}`・`IDEA-{NNN}`・`LL-NNN`〕が残っていない）
- [x] backlog の正が `{DOCS}` であること・取り消しはステータスを `❌ 却下` にすること（エントリを消さない）が、テンプレートの注記・close Step D・README で一致する
- [x] CLAUDE.md・README・ADR が実装と一致する
- [x] 特定ドメイン（Web・業務・組み込み）への偏りがないか（CLAUDE.md「適用ドメインの中立性」参照）
- [x] 監査の報告書の 8.2 の表を直した

**実装メモ（2026-11-08）:**
- CLAUDE.md は前回のスリム化（675d129）でスクリプトごとの表を持たなくなっていたので、3.14 の CLAUDE.md の項目は README の「決定的処理スクリプト」の表（`promote.py`・`collect_insights.py`・`docs_layout.py`・`artifact_lint.py` の行）で直した。CLAUDE.md は変えていない。
- 3.2.3 の `## エントリ一覧` を足す位置: 最初の `### ` 見出しの直前が `## ` の見出し（間は空行だけ）なら、その `## ` の見出しの前に足す（fixture の svc-a の `## 知見詳細` の下に入って節の並びが崩れたため）。テストのケース `detail-section` を足した。
- Layer 2 の `unknown_tags` は、LL テンプレートのタグ別インデックスの行のタグと比べる（Layer 2 はタグの表を持たないため）。
- SPO の既存のテスト `test_no_ripple_sections` は §9 に `[自動転記]` の文字列が無いことを見ていたが、3.4.5 のコメントがその語を含むので、表の行（`| [自動転記]`）だけを見るように直した。
- fixture の `scratch-workspace/baseline_docs/notify-svc/knowledge/lessons-learned.md` の `### LL-{破壊的変更警告}：…`（このプランの前からある書き方）は、人の指示（2026-11-08）で、device-svc・cross と同じ今の破壊的変更警告の形 `### 破壊的変更警告（CR-2026-900）` に直した。
- fixture の seed（`scratch-workspace-min/seeds/*/svc-a`）の LL はメタ行を持たなかったので、人の指示（2026-11-08）で、ID を `LL-M20260807-01`（seed の作成日）にし、update-knowledge の lesson の書式（メタ行・発生状況・学んだこと・次回への適用・出典）に直した。エントリ一覧に入る。

---

## 6. 却下した案

- **ID は通し番号のまま、Layer 2 の重複判定を (ID, CR) にする:** 人の判断で採らない（1.3 の 1.）。別の作業場所の同じ ID が Layer 2 に並び、アーカイブの後の採番に Layer 1・アーカイブ・Layer 2 の最大値を見る規則が要る。
- **latest-specs の気づきの表に CR の列を足す:** 工程11 の agent（mod・uc）・工程11 の SKILL・survey のすべてが列を書く必要があり、書き忘れを検出できない。`{DOCS}` との比較（3.4.2）は書く側を変えずに済む。
- **latest-specs を工程11 の一覧のファイルだけに絞る（比較しない）:** architecture.md のように毎回更新するファイルでは、前の CR の項目が毎回集まる。
- **`{DOCS}` の backlog で、内容の違う IDEA を Layer 1 の内容で上書きする:** 別の作業場所や人が `{DOCS}` で直したステータスを黙って戻す。
- **`{DOCS}` の backlog で、すべての ID の内容の違いを報告する:** `{DOCS}` でステータスを直すと Layer 1 は元のままなので、同じ報告が以後の close で毎回出続け、本当の競合が埋もれる。今の CR の ID だけを比べる（3.5.4）。
- **`{DOCS}` の内容で Layer 1 の IDEA を揃える（逆向きの同期）:** Layer 1 を書き換える手順が増え、Layer 1 を正と誤解させる。Layer 1 は受け口と決めて、ステータスを追わない。
- **latest-specs を `last-updated-cr` だけで選ぶ（工程11 の一覧を使わない）:** `last-updated-cr` を書かないファイル・人が直したファイルを取りこぼしうる。一覧との和集合にする（3.4.2）。
- **C2 の後の再実行で latest-specs の気づきが集まらないことを、3.3 の案内に書くだけにする:** 3.3 の作り直しの経路で工程11 の気づきを取りこぼし、前回の `INSIGHTS-{CR}.md` も上書きされる。人の判断（2026-11-05）で、前回の収集結果を引き継ぐ案（3.4.2）を採る。
- **`has_insights` と節の不一致の自動修正を LLM に任せる（向きを決めない）:** `has_insights` を `false` に変えて不一致を消すと、そのファイルが気づきの収集から黙って外れる（3.4.6）。
- **タグ別インデックスは LLM のまま、区切りだけ決める:** 決まった手順で作れる表なので、CLAUDE.md の開発ルールによりスクリプトにする。アーカイブの後の古い ID も、作り直しで消える。
- **progress.md の「## 気づき・提案メモ」の節をテンプレートから消す:** 人が CR の途中で書く置き場所として使われうる。abort も書く。集めるほうを足す。
- **01-init が Layer 2 を 3.2.3 と同じヘッダーで作る:** ヘッダーの定義が SKILL.md とスクリプトの2か所になる（A3-17・A3-24 のもと）。

---

## 7. 未決事項（人の判断 2026-11-05 で決着）

1. 3.4.2 の比較は、Step A の時点の `{DOCS}`（pull の前）を使う。別の作業場所が同じファイルを先に昇格させていても、今の CR が足した項目はそこに無いので集まる。逆に、今の作業場所で close していない別の CR（同じ `{XDDP_DIR}`）が同じ latest-specs のファイルに足した項目は、今の CR の項目として集まりうる。工程11 の一覧に載ったファイルに限ることで範囲は狭まるが、無くはならない。
   - **判断: 許容する。** 同じ latest-specs のファイルを並行する CR で更新しないことは運用で守る。混ざっても、多く集める側の誤り（取りこぼしではない）。ADR-0035 に書く。
2. 3.3 で、前回の close が Step B の途中で止まり IDEA が一部だけ書かれた場合、再実行は追記しない（人に件数と ID の一覧を示す）。足りない分は人が書くか、今の CR の IDEA を消して再実行する。
   - **判断: この扱いでよい。**
3. 3.5.1 で、`extract-ll` が `unknown`・`invalid` の LL を `LL-{CR}.md` に書かなくなる。knowledge agent は今も `unknown` を使わないが、`invalid`（`全リポジトリ`・書き違いの repo 名・単一リポジトリの `cross`）の LL では、今は存在しない `project-rulebook-{repo}.md`・`project-rulebook-cross.md` を「create if absent」で作りうる。変更後は作らなくなる（意図した変化）。振り分け先の無い LL は Layer 1 に残り、close Step D の要確認LL で人に示され、`repo` 欄を直して再実行すれば昇格する（情報は失わない）。
   - **判断: この扱いでよい。**
   - **別のプランにする穴（このプランでは直さない）:** close Step C の LL の `repo` 欄に許す値は `{repo名}`・`cross`・`unknown` だけで（`全リポジトリ` は IDEA だけ）、進め方の知見のように全 repo に当てはまる LL の昇格先（Layer 2）が無い。`unknown` にすると同じ作業場所の Step A0（Layer 1）では使われるが、ほかの作業場所には届かない。P3 の前からある穴で、置き場所（例: `{DOCS}` 直下の共通の知見ログ）と読み手を決める別のプランにする。
4. 前回の close が Step C2 まで進んだ後の再実行では、`{DOCS}` に今の CR の latest-specs の項目が既にあるので、比べるとすべて除かれる。3.3 の作り直しの経路では、工程11 の気づきが作り直しに入らない。
   - **判断: 前回の収集結果を引き継ぐ（3.4.2）。**

---

## 8. レビュー

AIレビュー結果: [plans/review/PLAN-20261105-lessons-backlog-review.md](review/PLAN-20261105-lessons-backlog-review.md)

---

## 9. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
