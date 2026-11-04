# 約束の監査の報告書（PLAN-20261103-contract-audit 段階2a）

作成日: 2026-11-03（更新: 2026-11-04。A3・A4・A5 の監査のやり直しとその検証を反映）

**状態:** 監査・検証・統合が終わった。A3・A4・A5 は、人の判断でやり直した。人の判断を待っているのは次の3つ（10.）。
1. やり直しの後の抜き取り確認で、また漏れがあった。A3・A4・A5 の監査をもう一度やり直すか
2. 段階2b を行うか
3. 段階3 の割り当て（案）

- **対象リビジョン:** ecb54c4（`audit/contract-audit-2026-11` の、段階2a を始めた時点の HEAD）。`ClaudeCode/`・`tools/` は fbf3956 と同一（`git diff --stat fbf3956 ecb54c4 -- ClaudeCode tools` の出力が空）。
- **読んだ場所:** 監査者・検証者は、セッションのスクラッチのディレクトリに作った worktree（`git worktree add --detach … ecb54c4`）だけを読んだ。この worktree は、最初の統合の後に削除し、やり直しのために同じリビジョンで作り直した。検証者5体は、どれも終わった時点で worktree の `git status --short` が空であることを報告した。
- **行番号:** ecb54c4 の値。パスの `CC/` は `ClaudeCode/.claude/` の略。
- **段階1 の報告書:** [review-fbf3956-2026-11.md](review-fbf3956-2026-11.md)
- **付録（原文）:**
  - 監査者の報告（A1・A2 は1回だけ。A3・A4・A5 はやり直し版が最新）:
    - [A1](contract-audit-2026-11/A1-audit.md)・[A2](contract-audit-2026-11/A2-audit.md)
    - A3: [やり直し版](contract-audit-2026-11/A3-audit-redo.md)（[前回](contract-audit-2026-11/A3-audit.md)）
    - A4: [やり直し版](contract-audit-2026-11/A4-audit-redo.md)（[前回](contract-audit-2026-11/A4-audit.md)）
    - A5: [やり直し版](contract-audit-2026-11/A5-audit-redo.md)（[前回](contract-audit-2026-11/A5-audit.md)）
  - 検証者の報告:
    - 最初の監査の検証: [V1](contract-audit-2026-11/V1-verify.md)・[V2](contract-audit-2026-11/V2-verify.md)・[V3](contract-audit-2026-11/V3-verify.md)
    - やり直しの検証: [V4](contract-audit-2026-11/V4-verify.md)・[V5](contract-audit-2026-11/V5-verify.md)
  - 渡した指示:
    - [監査者](contract-audit-2026-11/instructions-auditor.md)（A1・A3・A4・A5 の最初の監査で渡した版）
    - [やり直しの追加の指示](contract-audit-2026-11/instructions-auditor-redo.md)
    - [検証者](contract-audit-2026-11/instructions-verifier.md)
    - A2 に渡した指示は、A2 の監査者を起動したときの依頼文で、ファイルにはしていない（9. の「A2 の後に直した点」との差分）。

**指摘ごとの詳細の置き場所（プラン 3.2.5 の「指摘ごと」）:**
- 約束／書く側／読む側／食い違い／起きること／修正案: 各監査者の報告（付録）の「3. 指摘」。A3・A4・A5 は、やり直し版の報告に、前回からの指摘も含めて全部ある。
- 検証の判定・確度・根拠（再現の手順を含む）: 各検証者の報告（付録）の「1. 指摘の検証の表」。A1〜A3-23・A4-1〜A4-31・A5-1〜A5-28 は V1〜V3、やり直しで足した指摘は V4・V5 が検証した。
- 統合で変えた点（重複・否定・重大度・段階2b への移動）: 2.
- この報告書の 1. は、統合した後の結果。

---

## 1. 指摘の一覧（統合後）

### 1.1 件数

| | 🔴 | 🟡 | 🔵 | 計 |
|---|---|---|---|---|
| A1 code-knowledge（段階1 の R1・R4 を含む） | 1 | 6 | 12 | 19 |
| A2 AI_INDEX.md | 0 | 7 | 2 | 9 |
| A3 知見ログ・バックログ | 4 | 10 | 16 | 30 |
| A4 仕様・用語・カタログ | 3 | 17 | 26 | 46 |
| A5 project-rulebook | 0 | 13 | 20 | 33 |
| 監査者の担当外・検証者が新たに見つけたもの（3.） | 0 | 0 | 4 | 4 |
| **計** | **8** | **53** | **80** | **141** |

**重大度の凡例:**
- 🔴 知見・成果物が黙って失われる／誤った内容が下流に渡る
- 🟡 人が気付ける形で失われる・限定的な条件でだけ起きる
- 🔵 記述の不整合（動作への影響は無い）

重大度は、検証者の案を採った。監査者の案と違うものは 2.3 に書いた。他の指摘に統合したもの（2.1）、検証で否定したもの（2.2）、段階2b の候補に移したもの（6.）は、件数に入れていない。

**確度の凡例:**
- ✅ 確かめた（両側を読んで確認した。「再現」は、検証者がスクリプト・git を実行して再現した）
- 🔶 推論（LLM の振る舞い・運用に依存する）
- ⬜ 未確認

**検証の判定:**
- 確認: 食い違いがあり、起きることも監査者の記述のとおり
- 一部確認: 食い違いはあるが、起きること・条件・範囲が監査者の記述と違う
- 判断できず: LLM の振る舞い等に依存して確かめられない
- 否定: 食い違いではない

### 1.2 🔴（8件）

| # | 領域 | 内容 | 確度 | 検証 |
|---|---|---|---|---|
| A1-1 | A1 | survey の knowledge への昇格で、§2.6 の全項目が同じ出典 `SURVEY-{TODAY}` を持つので、同じ置き場所の制約が互いに置き換わり、最後の1件しか残らない（CC/agents/xddp-survey-promote-agent.md:59-60,63） | ✅ | 確認 |
| A3-1 | A3 | Layer 2 の LL の重複判定が ID だけ（CC/skills/xddp-close/scripts/promote.py:904-908）。update-knowledge の lesson は Layer 2 で別に番号を採る（CC/skills/xddp-update-knowledge/SKILL.md:206-209）。同じ ID になった Layer 1 の LL は Layer 2 に入らず、どこにも示されない | ✅ 再現（前提の書式は 🔶） | 確認 |
| A3-3 | A3 | ワークスペースごとに Layer 1 の LL を LL-001 から採番すると、共有の `{DOCS}` の Layer 2 で番号が重なり、後からクローズした側の LL が入らない | 仕組みは ✅・運用は 🔶 | 確認（条件つき） |
| A3-5 | A3 | cross の TSP（`09_test-spec/cross/TSP-{CR}-cross.md`）の「気づき・提案メモ」を、`collect_insights.py`（:170-171）が集めない | ✅ 再現 | 確認 |
| A3-6 | A3 | progress.md の「## 気づき・提案メモ」（テンプレートは「バックログの入力として活用する」と書く）を `collect_insights.py` が集めない。人が書いた場合に失われる | ✅ 再現 | 確認 |
| A4-1 | A4 | 工程11（CC/agents/xddp-specs-mod-agent.md:49,161）は `04_specout/{repo}/modules/` の**ディレクトリ**だけをモジュール資料とみなす。工程4a は、分割パスでは `modules/{名前}-spo.md` という**ファイル**を書く（CC/skills/xddp-04-specout/module-documentation.md:268-270）。同じ工程11 の `spec_version_delta.py:181-183` は、ファイルのほうを前提にしている | ✅ | 確認 |
| A4-2 | A4 | 統合パス（`SPO-{CR}.md` の §2.A…）のモジュール資料を工程11 が読まない（統合パスの読み方が書かれていない）。文書化したファイルが10件以下の CR では、モジュール仕様が作られない | ✅ | 確認 |
| A4-8 | A4 | 工程11 の Step GATE で人が削除したモジュール・ユースケースを、close の Step C0-3 が `{DOCS}` から latest-specs に書き戻す。そのため C2 の削除候補にもならない（CC/skills/xddp-11-specs/SKILL.md:512-514 → CC/skills/xddp-close/SKILL.md:211-216 → promote.py:297-301,317-322） | ✅ | 確認 |

### 1.3 🟡（53件）

| # | 領域 | 内容 | 確度 | 検証 |
|---|---|---|---|---|
| A1-2 | A1 | update-knowledge の constraint: 同じ出典の別の制約を置き換え、プレビューにもそれを示さない | ✅ | 確認 |
| A1-3 | A1 | close の SPO §5.6・LL 由来の制約に upsert の鍵が無い（鍵を定めているのは TRS だけ） | 鍵が無いことは ✅・置き換わるかは 🔶 | 確認 |
| A1-4 | A1 | TRS の NG の upsert の鍵 `CR-{CR} / NG-{NNN}` に実行回が入っていない。回ごとに NG を振り直すと置き換わる（repo は置き場所で分かれるので問題ない） | 🔶 | 一部確認 |
| A1-7 | A1 | `domain_refs.py:308-311` が、`DOMAIN_REF_PATHS` に `_structures`・`_constants` の**ディレクトリ**を入れる。analyst はファイルを Read する前提 | ✅ 再現 | 確認 |
| A1-8 | A1 | `_structures`・`_constants` だけを AI_INDEX のラベル経由で集める。AI_INDEX が無い場合・クローズ直後・survey や手での登録の後は、工程2 に届かない（A2-10 を統合） | ✅ 再現 | 確認 |
| R1 | A1 | 予約名（`_structures` 等）と同じ名前のディレクトリにある対象の制約は、置き場所がその予約名になり、`list_places` がそれを除くので読まれない（段階1） | ✅ 再現 | 確認 |
| A2-1 | A2 | code-knowledge インデックスの `_structures` のラベルが、書く側は `構造体関連図`（promote.py:601）、読む側は `共有構造体`（domain_refs.py:35-38）で食い違う | ✅ 再現 | 確認 |
| A2-2 | A2 | クロスインタフェース一覧の「⚠️ 破壊的変更あり」が付かない（CHD の生の名前と、ケバブ形式のディレクトリ名を比べている）。付いた場合も、キー列が変わって行が増える | (a)(c) は ✅ 再現・(b) は 🔶 | 確認 |
| A2-4 | A2 | 過去の DSN／CHD を AI_INDEX から引く読む側（工程5・6）に、書く側が無い | ✅ | 確認 |
| A2-5 | A2 | TSP／TRS の表のキーが repo だけで、過去の CR の一覧にならない | ✅（影響は 🔶） | 確認 |
| A2-7 | A2 | 「最終更新CR」を、今の CR が触っていない行にも付ける。11-specs が引用する promote.py の文は実在しない | ✅ | 確認 |
| A2-8 | A2 | 先行更新のモジュール名（SPO のディレクトリ名）と、latest-specs のケバブ名がずれうる | 🔶 | 判断できず |
| A2-11 | A2 | 11-specs がコミットせずに AI_INDEX を書き換えると、close C0-2 の `git pull` が止まる（失敗時の扱いが無い）。また `git diff --name-only` は git のリポジトリのルートからの相対パスを返すので、`AI_INDEX.md` との照合（C0-4 の PROTECTED_FILES の照合も）が一致しない | git の振る舞いは ✅ 再現・LLM の扱いは 🔶 | 確認 |
| A3-2 | A3 | Layer 1 の LL の採番の規則が無い（アーカイブの後に番号が重なりうる） | ✅／🔶 | 確認 |
| A3-4 | A3 | `improvement-backlog.md` を `{DOCS}` に丸ごと上書きする（A5-28 と同じ型） | ✅（運用は 🔶） | 確認 |
| A3-7 | A3 | `collect_insights.py` が、`repos_keys` の全 repo・cross・system の latest-specs を毎回走査する。そのため、前の CR・survey の気づきが、出典の CR の分からない形で集まる（V2 の N2 を含む） | ✅ 再現 | 確認 |
| A3-8 | A3 | multi-repo で cross の成果物の無い CR の `repo: cross` の LL を、Layer 2 に入れず、示しもしない（A5-24 と同じ型） | ✅ 再現 | 確認 |
| A3-9 | A3 | LL の `repo` 欄を検証せずにパスにする（`全リポジトリ` という名前のディレクトリができる） | ✅ 再現 | 確認 |
| A3-10 | A3 | xddp-analyst-agent が `LESSONS_CONTEXT` を Inputs に持たない | 宣言が無いことは ✅・使われないかは 🔶 | 確認 |
| A3-11 | A3 | xddp-architect-agent が `LESSONS_CONTEXT` を Inputs に持たない | 同上 | 確認 |
| A3-12 | A3 | xddp-test-writer-agent が `LESSONS_CONTEXT` を Inputs に持たない | 同上 | 確認 |
| A3-27 | A3 | 共通ファイルの昇格エラー（C7 の backlog・AI_INDEX の更新・C6 の共通 rulebook）が、出力ファイルの「共通ファイルの昇格エラー」にだけ出て、close の Step D・Step E に出ない（✅ で完了する）。A3 のやり直しの担当外1 を統合 | ✅ 再現（Step D で LLM が示すかは 🔶） | 確認 |
| A3-29 | A3 | close の再実行で Step B・C の追記が繰り返され、重複した LL・IDEA が、人が消す前に同じ実行で昇格する（再実行の案内は5か所。V4） | 順序は ✅・LLM は 🔶 | 確認（条件は監査者の記述より広い） |
| A4-3 | A4 | `SPECOUT_MODULES` を `modules/` のディレクトリ名から取る（統合パスでは空になる） | ✅ | 確認 |
| A4-4 | A4 | 工程11 の廃止モジュールの判定の照合先がディレクトリなので、既存のモジュールが毎回廃止候補になる | ✅ | 確認 |
| A4-6 | A4 | structure.md の材料の見出し `クラス図` が SPO に無い（SPO は `### 4.2 データ型関連図`） | ✅ 再現 | 確認 |
| A4-9 | A4 | 工程11 を分割して実行すると、前の回の更新が「更新仕様書ファイル一覧」から外れ、C0-3 で上書きされうる | 🔶 | 判断できず |
| A4-10 | A4 | GATE で人が直接編集した、一覧に無いファイルが、C0-3 で `{DOCS}` の前の版に戻る | ✅ | 確認 |
| A4-11 | A4 | survey の (c) で architecture.md に追記した内容が `{DOCS}` に届かず、後の CR の C0-3 で上書きされうる | ✅ | 確認 |
| A4-12 | A4 | AI_INDEX が無いとき、`domain_refs.py:354-359` は cross のインタフェース仕様を誤ったパスで探す | ✅ | 確認 |
| A4-13 | A4 | 01-init が `{DOCS}/{repo}/specs/` を必ず作るので、`domain_refs.py` の latest-specs へのフォールバック（a）は働かない。11-specs の先行更新の目的と案内（close の前でも次の CR の工程2 が参照できる）も成り立たない（A2-3 を統合） | ✅ 再現 | 確認 |
| A4-14 | A4 | 工程5・6 が latest-specs を探すとき、SPO のモジュール名をそのまま使う（ケバブ名とずれる） | 🔶 | 確認 |
| A4-15 | A4 | ユースケースの `related-modules` の値が、latest-specs のディレクトリ名とずれうる | 🔶 | 確認 |
| A4-16 | A4 | survey の `MODULE_KEBAB` と CR のモジュール名の決め方が違い、同じコードの仕様が二重にできうる。catalog から解決したときの規則も書かれていない（やり直しで補足） | 🔶 | 一部確認（補足は確認） |
| A4-17 | A4 | SPEC レビューに SPO が渡らない（チェックリストは SPO との照合を求める） | ✅ | 確認 |
| A4-39 | A4 | 工程11 の分割実行 B の継続で、`処理済みモジュール:` に限定して継続する（UR は未処理の一覧で継続する）。継続の対象が逆なので、残りのモジュールの仕様が作られないまま完了しうる | 文面は ✅・LLM が逆に読むかは 🔶 | 確認 |
| A4-42 | A4 | ユースケースの description.md には複数の CR の UR が蓄積するのに、今回の CRS に同じ UR が無ければ廃止候補にするので、過去の CR のユースケースが毎回廃止候補になる | ✅ | 確認 |
| A4-43 | A4 | 工程11 の後・close の前に `/xddp-abort` した CR の latest-specs が残り、後の CR の close で `{DOCS}` に昇格する。並行 CR 保護は「## CR クローズ」の有無で判定するので、中止した CR は進行中とみなされ続ける | ✅ | 確認 |
| A4-44 | A4 | survey の (c) は、人の承認の前に latest-specs へ書き、承認されなかったときの扱いが無い。後の CR の close で `{DOCS}` に昇格しうる | 🔶 | 確認 |
| A4-47 | A4 | survey の衝突判定は latest-specs だけを見るが、写し先は `{DOCS}`。作業場所の latest-specs にモジュールが無く、`{DOCS}` に `source: spo` の版があると、確認なしに上書きする | 文面は ✅・条件は 🔶 | 一部確認 |
| A5-1 | A5 | close で C3.5 の rulebook の upsert が、C6 の `{DOCS}` への写し（promote.py run）の後に行われる | ✅ | 確認 |
| A5-2 | A5 | シングルリポジトリでも C3.5 が `project-rulebook-{repo}.md` を作る。init・fill-rulebook はそのファイルが無い前提で動く | ✅ | 確認 |
| A5-3 | A5 | 最初の CR では、init が §7 の初期行に {CR} を入れるので、02 Step B3 が「抽出済み」と判定してスキップする | ✅ | 確認 |
| A5-4 | A5 | fill-rulebook が、repo 別ファイルの §2 の判定に §3 のプレースホルダーを使っている | 対応のずれは ✅・上書きが起きるかは 🔶 | 確認 |
| A5-6 | A5 | fill-rulebook の「§5 (ADR)」の規則が、共通ファイルでは §5 禁止事項に当たる | ✅／🔶 | 確認 |
| A5-7 | A5 | fill-rulebook に §6 の規則が2つあり、repo 別の §6 禁止事項にモジュール構成を書く | ✅／🔶 | 確認 |
| A5-8 | A5 | fill-rulebook が §4 を「スペックアウトで記入」の注記で置き換えるが、工程4 は rulebook を書かない。repo 別の §4 も同じで、C3.5 の upsert 先のサブセクションも消える（やり直しで追記） | ✅／🔶 | 確認 |
| A5-9 | A5 | fill-rulebook の「§1 / §2 Cross-repo overview」が、cross の §2 API バージョニング規約に当たる | ✅／🔶 | 確認 |
| A5-10 | A5 | fill-rulebook に、cross §3〜§6 用のドラフト規則が無い | ✅／🔶 | 確認 |
| A5-12 | A5 | C3.5 で cross に追記する節が決まっていない | 🔶 | 確認 |
| A5-18 | A5 | 02 Step B3 の「repo 別は C3.5 で行う」に、受け渡しの仕組みが無い。シングル構成でも注記する（やり直しで追記） | 🔶 | 確認 |
| A5-28 | A5 | `{DOCS}` の rulebook を、競合を検出せずに丸ごと上書きする（A3-4 と同じ型） | 🔶 | 確認 |
| A5-31 | A5 | `write_output_file`（promote.py:1111）は `affected_repos` だけを出力する。そのため cross（C2・C4・C5・C6・C2 の破壊的変更の警告）と system（C2）の失敗が出力ファイルにも Step D にも出ず、「昇格」と報告される（A5 のやり直しの担当外3 と、V4 の N3 を統合） | ✅ 再現（:1212 の警告は読んで確認） | 確認（範囲は監査者の記述より広い） |

### 1.4 🔵（80件）

| # | 領域 | 内容 | 確度 | 検証 |
|---|---|---|---|---|
| A1-5 | A1 | 出典の `CR-{CR_NUMBER}` で、CR フォルダ名が `CR-` で始まると接頭辞が二重になる | 🔶 | 確認 |
| A1-6 | A1 | 「対象」を書くよう指示しているのに、constraints テンプレートの2つの節に `**対象:**` 欄が無い | 文面は ✅・影響は 🔶 | 一部確認 |
| A1-9 | A1 | SPO §4.5 の `定義モジュール` と、`_constants` テンプレートの `定義場所` の列が合わない | ✅ | 確認 |
| A1-10 | A1 | 「## 昇格見送り一覧」を close の Step D で示さない | ✅ | 確認 |
| A1-11 | A1 | `_domain名要確認一覧` から、cross の `_constants`・`_structures` が漏れうる | ✅ | 一部確認 |
| A1-12 | A1 | update-knowledge の callgraph で、入力させた「フロー名」をファイル名に使わない | ✅ | 確認 |
| A1-13 | A1 | update-knowledge が flow・callgraph のパスを自分で定義している（単一情報源の規則に反する） | ✅ | 確認 |
| A1-14 | A1 | survey が昇格先のパスを自分で定義している | ✅ | 確認 |
| A1-15 | A1 | survey の「topic では §2.6 の昇格は発生しない」という記述が誤り | ✅ | 確認 |
| A1-16 | A1 | `specout_bfs.py status` の `confirmed_modules`（第1階層）を読むのがテストだけ | ✅ | 確認 |
| A1-17 | A1 | ヒアドキュメントに人の入力をそのまま JSON 文字列として埋め込むので、`\` で exit 2 になるか、`\n` 等で黙って `no-path` になる | ✅ 再現（LLM がエスケープするかは 🔶） | 確認 |
| R4 | A1 | ワークスペースの外の絶対パスの `status` が `not-found` になる（段階1） | ✅ 再現 | 確認 |
| A2-6 | A2 | AI_INDEX「共通知識」の列が init と promote で違い、repo 別・cross の rulebook があると共通の rulebook の行が消える（A5 の担当外を統合。V1 は 🟡、V3 は 🔵。共通知識の節を読むスクリプトは無く、写しは残るので 🔵 とした） | ✅ 再現 | 一部確認 |
| A2-9 | A2 | AI_INDEX のひな形・説明の不整合（ひな形が3つある・プレースホルダー行・知識参照ガイドの参照先・`state` 列・`related-modules: []`・セルの `|`）。A2 は前の版の指示で監査したため、6件が1つの指摘にまとまっている | ✅（一部 再現） | 確認 |
| A3-13 | A3 | analyst の「なし」を、`collect_insights.py` が未記入と判定しない | ✅ 再現 | 確認 |
| A3-14 | A3 | SPO §9 の「なし」の行と、テンプレートのままの §9 を、未記入と判定しない | ✅ 再現 | 確認 |
| A3-15 | A3 | IDEA のエントリの書式が、テンプレートと違う | ✅ | 確認 |
| A3-16 | A3 | close Step B の「summary table」がどの表を指すか分からない | ✅ | 確認 |
| A3-17 | A3 | Layer 2 の「エントリ一覧」の表を誰も更新しない | ✅ | 確認 |
| A3-18 | A3 | update-knowledge の lesson のエントリの書式が決まっていない | 🔶 | 確認 |
| A3-19 | A3 | LL テンプレートの「管理場所」が、実際のパスと違う | ✅ | 確認 |
| A3-20 | A3 | close Step B・C の「create from template」が、テンプレートのパスを示さない | ✅ | 確認 |
| A3-21 | A3 | close Step C の抽出の観点が「same as before」で、何から抽出するかが書かれていない | ✅ | 一部確認 |
| A3-22 | A3 | abort が「update-knowledge 等で backlog に登録」と案内するが、update-knowledge に backlog の種別が無い | ✅ | 確認 |
| A3-23 | A3 | close のコメントにある Layer 1 の読み手の一覧が足りない | ✅ | 確認 |
| A3-24 | A3 | `append_breaking_warning` がファイルの無いときにヘッダーなしで Layer 2 を作り、後の LL もヘッダーを足さない（cross で起きる。codemap を init より先に実行すると repo でも起きうる。V2 の N3 を統合） | ✅ 再現 | 確認 |
| A3-25 | A3 | `collect_insights.py` は CODING・VERIFY の「気づき・提案メモ」を集めるが、coder・verifier の出力にその節が無い（工程7・8 の気づきの置き場所が無い） | ✅ | 確認 |
| A3-26 | A3 | SPO §9 のテンプレートのコメントは「手で直さない（再実行で上書きされる）」と書くが、スクリプトは人が書いた行を残す | ✅ | 確認 |
| A3-28 | A3 | LL のタグの区切りが Entry Format で決まっておらず、タグ別インデックスから漏れうる（監査者は 🟡。V4 は、監査者が挙げた空白区切りの書く側はエントリの書式ではなく、同じ手順に「カンマ区切り」と書いてあるとして 🔵） | ✅／🔶 | 一部確認 |
| A3-30 | A3 | latest-specs の「気づきメモポリシー」「Section 3-4」が、参照先に無い | ✅ | 確認 |
| A4-5 | A4 | precheck が SPO ファイルをケバブ名で引くので、`_`・大文字のモジュールでは見つからない | ✅ 再現 | 確認 |
| A4-7 | A4 | compare が、SPO の無いモジュールにも版の下限を当てはめる | ✅ | 確認 |
| A4-18 | A4 | SPO §4.3 の `source` 注記を書く側がいない | ✅ | 確認 |
| A4-19 | A4 | 「Section 3-0」「Section 3-4」を参照しているが、その節が無い（uc-agent:29,76・11-specs:374。V4 の N2 は同じもの） | ✅ | 確認 |
| A4-21 | A4 | module-catalog のディレクトリ（入れ子）と、specout が照合に使う値（第1要素）の形が合わない。見出しの正規表現は `src/auth`・`src/db` を同じ `src` にする（やり直しで補足） | ✅ 再現 | 確認 |
| A4-22 | A4 | architecture.md の材料にする SPO の節の名前が、テンプレートの別名と違う | ✅ | 一部確認 |
| A4-23 | A4 | 日本語の見出しのケバブ変換が決まっていない（precheck が判定を飛ばす） | ✅ 再現 | 確認 |
| A4-24 | A4 | 工程11 の自動修正の対象キーと、lint の必須キーが違う | ✅ | 確認 |
| A4-25 | A4 | compare が、§1 の「バージョン」行を書き換えない | ✅ | 確認 |
| A4-26 | A4 | 設定テンプレートの latest-specs のパスに `{repo}/` が無い | ✅ | 確認 |
| A4-27 | A4 | 下調べエージェントの `LATEST_SPECS_DIR` の説明に `{XDDP_DIR}/` が無い | ✅ | 確認 |
| A4-28 | A4 | abort の説明が、close の動作と違う | ✅ | 確認 |
| A4-29 | A4 | sync-design の説明が、工程11 の動作と違う | ✅ | 確認 |
| A4-30 | A4 | code-knowledge-boundary の書き手の欄が、survey の実際の書き先と違う | ✅ | 確認 |
| A4-31 | A4 | glossary をテンプレートから作ると、見本の行が用語数に数えられる | ✅ 再現 | 確認 |
| A4-32 | A4 | overview/deployment.md の材料の節を、SPO のどこも書かない | ✅ | 確認 |
| A4-33 | A4 | survey が module-catalog の「主要ファイル」欄を読むことになっているが、その欄が無い | 🔶 | 確認 |
| A4-34 | A4 | module-catalog が無いときの動作の説明（優先度の差なし）が、スクリプト（近傍優先 `simple`）と違う | ✅ | 確認 |
| A4-35 | A4 | ユースケースのシーケンス図から overview のシーケンス図へのリンクの相対パスが誤っている | ✅ | 確認 |
| A4-36 | A4 | cross SPO §3 の小見出しはレベルごとなのに、工程11 はそれをフローの名前として使う | 🔶 | 確認 |
| A4-37 | A4 | mod-agent が CHD の「変更対象モジュール名」を探すが、CHD にその欄が無い | ✅ | 確認 |
| A4-38 | A4 | cross インタフェース仕様の `provider`・`affected-repos` の材料の取り方が Step CROSS に書かれていない（cross SPO §4 に列があるので、材料が無いのは SPO に無い新しいインタフェースだけ） | 🔶 | 一部確認 |
| A4-40 | A4 | 分割実行メモの置き場所「progress.md §15」が存在しない（§15 は別の節を指す箇所もある） | ✅ | 確認 |
| A4-41 | A4 | `RESUME_UR_LIST` の値が、UR かケバブ名かで揺れる | 🔶 | 確認 |
| A4-45 | A4 | survey Step 7 が、Step 8② でまだ書いていない architecture.md をレビューの対象に入れる（時期。前回の N4） | ✅ | 確認 |
| A4-46 | A4 | precheck が spec.md の全体と SPO §2 だけを比べるので、行数の変化率が大きく出る（前回の N5） | ✅ 再現 | 確認 |
| A5-5 | A5 | fill-rulebook の repo 別ファイルの §6 の行に、テンプレートに無いプレースホルダーがある | ✅ | 確認 |
| A5-11 | A5 | fill-rulebook がテンプレートから作るとき、日付と CR のプレースホルダーを置き換えない | ✅ | 確認 |
| A5-13 | A5 | C3.5 の宛先の表の Section 5 の名前が、テンプレートと違う | ✅ | 確認 |
| A5-14 | A5 | C3.5 の宛先の表の Section 4 の名前が、テンプレートと違う（同じエージェントの中でも食い違う） | ✅ | 確認 |
| A5-15 | A5 | C3.5 の Section 4 のテーマ見出しの例が、テンプレートの見出しと一致しない | 🔶 | 確認 |
| A5-16 | A5 | C3.5 がテンプレートからファイルを作るときの、テンプレートと置き換えが決まっていない | ✅ | 確認 |
| A5-17 | A5 | LL のタグ `#レビュー` が、C3.5 の宛先の表に無い | ✅ | 確認 |
| A5-19 | A5 | 02 Step B3 の「既存のコードブロックの末尾」で、どのブロックかが決まらない | ✅ | 確認 |
| A5-20 | A5 | 禁止事項の行の書式が、書く側どうしで違う | ✅ | 確認 |
| A5-21 | A5 | init の `{CR}` の置き換えで、cross テンプレート §6 の一般的な手順の文に CR 番号が入る | ✅（すべての出現を置き換えるかは 🔶） | 確認 |
| A5-22 | A5 | init の置き換えで、ADR の書式のコメントに日付と CR が入る | 同上 | 確認 |
| A5-23 | A5 | load-domain-constraints の「未記入」の判定が、テンプレートの §1.6 の行の形に合わない | 🔶 | 確認 |
| A5-24 | A5 | cross の rulebook の写しが、今の CR の cross の成果物の有無で決まる（A3-8 と同じ型） | ✅ | 確認 |
| A5-25 | A5 | close Step D が、写していない rulebook も「昇格」と報告する | ✅ | 確認 |
| A5-26 | A5 | cross テンプレート §6 が、存在しない形のパスを指す（「移行ガイド」の節は存在する） | ✅ | 一部確認 |
| A5-27 | A5 | README の §1.5 の説明が、テンプレートと合わない | ✅ | 確認 |
| A5-29 | A5 | fill-rulebook が使う `{REPO_PATH}` が、どこにも定義されていない（前回の N2。V4 は、LLM が `xddp.config.md` の `REPOS:` を拾える余地があるとして 🔵） | ✅／🔶 | 確認 |
| A5-30 | A5 | load-steering-context の `INCLUDE_CROSS` を使う呼び出し元が無く、cross の rulebook が工程7〜10 の cross の検証・テスト設計に届かない | ✅ | 確認 |
| A5-32 | A5 | fill-rulebook の cross §1 の `upstream-repos`/`downstream-repos` が、どこにも定義されていない | 🔶 | 確認 |
| A5-33 | A5 | designer・architect の修正・追加の呼び出し（05:279,331,444、06:251,303,358,377,467）が `RULEBOOK_CONTEXT` を渡さない（06:358 は V4 が追加） | 渡さないことは ✅・影響は 🔶 | 確認 |
| N1 | A2 | survey が AI_INDEX に書く最終更新CR `SURVEY-{TODAY}` が、アーカイブ候補の正規表現に一致しない（V1） | ✅ | — |
| N6 | A2 | AI_INDEX の知識参照ガイドの早見表が、rulebook の場所として `{XDDP_DIR}/…` だけを指す（`{DOCS}` の写しを示さない）。A5 のやり直しの担当外2 | ✅ | V4 確認 |
| N7 | A2 | 破壊的変更の印を付けた行が、AI_INDEX のクロスインタフェース一覧に重複して残る（印が出るようになってから起きる。A2-2 の修正と関係）（V5） | ✅ 再現 | — |
| N8 | A3 | SPO §9 の「なし」の行が、assemble-spo の再実行で残る（自動の注記と並ぶ）（V4） | ✅ | — |

---

## 2. 統合で変えた点

### 2.1 重複の統合

| 統合したもの | 残したもの | 理由 |
|---|---|---|
| A1 の担当外（構造体のラベル） | A2-1 | 同じ食い違い（V1） |
| A4 の担当外 #1（breaking の印）とその補足（印の付いた値をパスに使う。V5 は一部確認） | A2-2 | 同じ食い違い（V3・V5） |
| A4 の担当外 #2（先行更新の行の集合） | A2-7 | 同じ食い違い（V3） |
| A5 の担当外（共通知識） | A2-6 | 同じ食い違い（V3） |
| A2-10（`_structures`・`_constants` は AI_INDEX 経由でしか読まれない。時期） | A1-8 | 同じ食い違い（V1）。書かれるもの（code-knowledge の読み方）の領域 A1 に寄せた |
| A2-3（先行更新の目的が達成されない） | A4-13 | 同じ原因（init が `{DOCS}/{repo}/specs/` を作るので、latest-specs へのフォールバックが働かない。V3）。latest-specs の読み方の領域 A4 に寄せた |
| V1 の新たな気付き1（工程11 は `modules/` をディレクトリとして読む） | A4-1・A4-3・A4-4 | 同じ食い違い |
| V1 の新たな気付き2（C0-4 の PROTECTED_FILES の照合） | A2-11 | 同じ原因（git が返すパスの基準） |
| V2 の N2（`repos_keys` の全 repo を走査） | A3-7 | V2 が「A3-7 に含めてよい」とし、A3 のやり直しでも含めた |
| V2 の N1（fill-rulebook の `{REPO_PATH}`） | A5-29 | A5 のやり直しで取り込んだ |
| V2 の N3（`append_breaking_warning` のヘッダー） | A3-24 | A3 のやり直しで具体化した |
| V3 の新たな気付き1・3 | A4-45・A4-46 | A4 のやり直しで取り込んだ |
| A3 のやり直しの担当外1（AI_INDEX・共通 rulebook の昇格エラー） | A3-27 | 同じ根（V4） |
| A5 のやり直しの担当外3（cross の C2・C4・C5 の失敗）と V4 の N3（system の C2 の失敗） | A5-31 | 同じ仕組み（`write_output_file` が `affected_repos` しか出力しない。V4 が再現） |
| V4 の N2（uc-agent の「Section 3-4」） | A4-19 | A4-19 が同じ箇所（uc-agent.md:76）を挙げている |

同じ型だが、別の対象の指摘として残したもの:
- A3-4 と A5-28（`{DOCS}` を `copy2` で丸ごと上書き）
- A3-8 と A5-24（`has_cross` の条件）

### 2.2 検証で否定したもの

| 指摘 | 内容 | 否定の理由 |
|---|---|---|
| A3 の担当外（A2。前回の A3） | AI_INDEX の共通ナビゲーションが Layer 2 の「タグ検索例」を示すが、Layer 2 にタグ別インデックスが無い | promote.py:343 は「タグ検索例」を挙げているだけで、インデックスがあるとは書いていない。Layer 2 のエントリは Layer 1 のエントリを丸ごと写したもの（promote.py:911）で、`**タグ：**` のメタ行を含むので、タグの文字列で検索できる（V2）。A3 のやり直しで、監査者も取り下げた |

### 2.3 重大度・確度を監査者の案から変えたもの

| 指摘 | 監査者 → 統合 | 理由（検証者） |
|---|---|---|
| A2-1 | 🔴 → 🟡 | ラベルを合わせても、A1-7 によりディレクトリのパスが渡るので、analyst は Read の失敗を §0 に記録する（人が気付ける形になる）。知見は `{DOCS}` に残る（V1） |
| A5-4 | 🔴 → 🟡 | 「人が §2 を書いた」「§3 は未記入」「LLM が節番号で書き込み先を決める」の3つが揃ったときだけ起きる。Step 5 で人がドラフトを確認する。同じ根の A5-6・A5-7 にそろえた（V2。A5 のやり直しでも 🟡） |
| A1-6 | 🟡 → 🔵 | 読む側（module-documentation.md:181）は、`**対象:**` の無い制約を内容で照合する作りになっている。食い違いは書く側の中にある（V1） |
| A2-6 | 🟡 → 🔵 | V1 は 🟡、V3 は 🔵 と分かれた。共通知識の節を読むスクリプトは無く（V3 が grep で確認）、rulebook の写しは残るので 🔵 とした |
| A3-28 | 🟡 → 🔵 | 監査者が「空白区切りの書く側」として挙げたのは、タグ一覧（定義の並び）と Layer 2 の入力の例で、Layer 1 のエントリの書式ではない。エントリを書く手順とインデックスを更新する手順は同じ Step C の中にあり、そこに「カンマ区切り」と書いてある（V4） |
| A5-29 | 🔵〜🟡 → 🔵 | fill:122 が `xddp.config.md` を読ませているので、LLM が `REPOS:` のパスを拾える余地がある（V4） |
| A5-33 | 🔵〜🟡 → 🔵 | 修正の呼び出しは、規約を使って書いた既存の文書を最小限に直すだけ（V4） |
| A3-14 | 確度 🔶 → ✅ | テンプレートのままの §9 も1件として集まることを再現した（V2） |

### 2.4 段階2b の候補に移したもの

- **A4-20**（cross の CHD の「影響リポジトリ」を読む約束）:
  - 移した理由: A2 の監査者が「段階2b」と印を付けた候補と同じもの。書く側は工程の成果物（CHD）で、読む側も工程のプロシージャ・チェックリストなので、プラン 3.2.2 の境界の規則により段階2b に移した（6.）。A4 のやり直しでも段階2b として扱った。
  - V3 の検証結果（確認・🔶・🔵）は 6. に残す。

---

## 3. 監査者の担当外・検証者が新たに見つけたもの

監査者の担当外の指摘と、検証者が割り当ての外で見つけた食い違いのうち、どの指摘にも統合しなかったもの（1.4 の N1・N6〜N8）。N2〜N5 は、やり直しの監査の指摘に統合した（2.1）。

| # | 内容 | 書く側・読む側 | 見つけた者・確度 |
|---|---|---|---|
| N1 | survey が AI_INDEX に書く最終更新CR `SURVEY-{TODAY}` が、アーカイブ候補の正規表現 `\bCR-…` に一致しない | CC/skills/xddp-survey/SKILL.md:393,397 → promote.py:636 | V1・✅（別の検証者は検証していない） |
| N6 | AI_INDEX の知識参照ガイドの早見表が、rulebook について `{XDDP_DIR}/…` だけを挙げる（同じ表の lessons-learned は XDDP と DOCS の両方を挙げる） | promote.py:344（写し先は :988,996） | A5 のやり直しの担当外2・V4 が確認 ✅ |
| N7 | 破壊的変更の印を付けた行が、AI_INDEX のクロスインタフェース一覧に重複して残る。印の無い既存の行が `upsert_table` で消えないため | promote.py:445-447,580-582 | V5・✅ 再現（別の検証者は検証していない） |
| N8 | SPO §9 の「なし」の行が、assemble-spo の再実行で残る（残す条件が `[自動転記]` と `{内容}` しか除かない） | CC/skills/xddp-04-specout/scripts/specout_bfs.py:7627,7629-7630 | V4・✅（読んで確認。実行していない。別の検証者は検証していない） |

知識ハブの約束の外なので、件数に入れなかったもの（6. の段階2b の候補に置く）:
- V3 の新たな気付き2（`SPECOUT_DIAGRAM_LEVEL` の説明。A4 のやり直しの担当外にも同じもの）
- V5 の新たな気付き2（工程5・6 の「参照した資料を記録する節」がテンプレートに無い）

---

## 4. 確認した約束の一覧（領域ごと）

約束の表（約束／書く側／読む側／見つけた方法／結果）の全体は、各監査者の報告（付録）の「1. 確認した約束の一覧」にある。A3・A4・A5 は、やり直し版が最新。

| 領域 | 確認した約束 | うち食い違いなし | 付録 |
|---|---|---|---|
| A1 | 41 | 25 | [A1-audit.md](contract-audit-2026-11/A1-audit.md) §1 |
| A2 | 16（前の版の指示のため、1行に複数の約束をまとめた行がある） | 4 | [A2-audit.md](contract-audit-2026-11/A2-audit.md) §1 |
| A3 | 68（前回 37） | 40（前回 21） | [A3-audit-redo.md](contract-audit-2026-11/A3-audit-redo.md) §1 |
| A4 | 75（前回 51） | 33（前回 25） | [A4-audit-redo.md](contract-audit-2026-11/A4-audit-redo.md) §1 |
| A5 | 64（前回 54） | 30（前回 25） | [A5-audit-redo.md](contract-audit-2026-11/A5-audit-redo.md) §1 |

「食い違いなし」は、付録の §1 の表で、結果の列が「なし」で始まる行をスクリプトで数えた。結果の列が「なし（…は A?-n）」のように別の指摘を参照している行も「なし」に数えた。
A3 の約束が増えたのは、やり直しの監査者が、成果物ごと（#23-1〜#23-15）・書く側ごと（#16b・#16c）に行を分けたため。

---

## 5. 時期の約束

各領域の時期の約束の表（書く側の Step → 読む側の Step・順序の根拠）の全体は、各監査者の報告（付録）の「2. 時期の約束の表」にある。食い違いがあったものは次のとおり。

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠 | 指摘 |
|---|---|---|---|
| xddp-close Step C2〜C7（promote.py run。AI_INDEX・rulebook の写し） | 同じ close の Step C3.5・C3.6（knowledge agent が rulebook・code-knowledge を書く） | CC/skills/xddp-close/SKILL.md:299（run）→ :312（agent） | A5-1・A1-8（制約については ADR-0033:80 に、受け入れた制限として記録がある） |
| xddp-11-specs Step DONE（AI_INDEX の先行更新） | 次の CR の xddp-02-analysis Step 0（close の前） | CC/skills/xddp-11-specs/SKILL.md:578 | A4-13（A2-3 を統合） |
| xddp-11-specs Step DONE（`{DOCS}/AI_INDEX.md` を書き換え、コミットしない） | xddp-close Step C0-2（`git -C {DOCS} pull`） | CC/skills/xddp-close/SKILL.md:207-209 | A2-11 |
| xddp-11-specs Step GATE（廃止候補を削除・人の直接編集） | xddp-close Step C0-3（DOCS → latest-specs の取り込み）→ C2 | CC/skills/xddp-11-specs/SKILL.md:512-514 → CC/skills/xddp-close/SKILL.md:211-216 | A4-8・A4-10 |
| xddp-11-specs Step DONE（分割実行で一覧を上書き・処理済みモジュールを書く） | xddp-close Step C0-3／次の工程11 Step 0 | CC/skills/xddp-11-specs/SKILL.md:525,546-573 → :47 | A4-9・A4-39 |
| 工程11 の後に `/xddp-abort` | 後の CR の close C0-3・C2・並行 CR 保護 | CC/skills/xddp-abort/SKILL.md:36-46,138 → CC/skills/xddp-close/SKILL.md:215・promote.py:287-292 | A4-43 |
| xddp-survey (c) Step 6（latest-specs に書く）→ Step 8（承認） | 後の CR の close C0-3・C2 | CC/skills/xddp-survey/SKILL.md:318-332,360-362 | A4-44 |
| xddp-survey Step 8②（latest-specs の architecture.md に追記） | 後の CR の close C0-3／同じ survey の Step 7（レビュー） | CC/skills/xddp-survey/SKILL.md:374-381 → CC/skills/xddp-close/SKILL.md:215、:339 | A4-11・A4-45 |
| close C6（`{DOCS}` を copy2 で上書き） | 別の作業場所の close C0（`{DOCS}` の pull） | CC/skills/xddp-close/SKILL.md:207-277 | A5-28・A3-4 |
| close の再実行（Step B・C の追記の繰り返し） | 同じ実行の extract-ll・promote・knowledge agent | CC/skills/xddp-close/SKILL.md:72-139 → 284/299/312 | A3-29 |
| xddp-01-init Step 4.6（§7 の初期行に {CR}） | 同じ CR の xddp-02-analysis Step B3（冪等性の判定） | CC/skills/xddp-01-init/SKILL.md:223 → CC/skills/xddp-02-analysis/SKILL.md:284-285 | A5-3 |
| 02 Step B3（repo 別の候補） | close C3.5 | 受け渡しの手段が無い（CC/skills/xddp-02-analysis/SKILL.md:287） | A5-18 |

---

## 6. 段階2b の候補

監査者が「段階2b」と印を付けた食い違いと、統合で段階2b に移したもの。プラン 3.2.3 により、段階2b の候補は検証しない（A4-20 は、移す前に検証を受けている）。段階2b を行うかの判断の材料にする。

| # | 内容 | 書く側・読む側 | 確度（出どころ） |
|---|---|---|---|
| 2b-1 | cross の CHD「インタフェース変更サマリ」に「影響リポジトリ」列が無い。そのため、それを読む工程11 の AFFECTED_REPOS の追加条件と、SPEC レビューの照合に拠り所が無い | 書く側 CC/skills/xddp-06-design/SKILL.md:126-130。読む側 CC/skills/xddp-common/SKILL.md:138-141、CC/skills/xddp-common/reviewer-checklists/SPEC.md:31 | A2 の監査者 ✅（LLM が別の表から読み替える可能性は 🔶）。A4-20 として V3 が検証: 確認・🔶・🔵 |
| 2b-2 | 設定テンプレートの `SPECOUT_DIAGRAM_LEVEL` の説明（6.1〜6.9）が、module-documentation.md の Section 4 の生成範囲（4.1〜4.7）と合わない | 書く側 CC/skills/xddp-01-init/templates/xddp.config.md:341-343。読む側 CC/skills/xddp-04-specout/module-documentation.md:233-240 | V3 ✅（検証の途中で見つけたもの）。A4 のやり直しでも担当外として報告 |
| 2b-3 | 工程5・6 の Step 0 は「参照した過去の設計書・現状仕様を DSN・CHD の節に記録する」と書くが、その節がテンプレートに無い（あるのは「参照資料」の行だけ） | 書く側（指示）CC/skills/xddp-05-arch/SKILL.md:124・CC/skills/xddp-06-design/SKILL.md:64（TSP の CC/skills/xddp-09-test/SKILL.md:42 も同じ型）。テンプレート 05_design-approach-memo-template.md:16・06_change-design-document-template.md:24・06_change-design-document-index-template.md:17 | V5 ✅（節が無いこと）／🔶（起きること） |
| 2b-4 | 工程7〜10 のスキル・エージェントが、cross の CHD「インタフェース変更サマリ」を読む（designer・coder・verifier・test-writer・07・08・09）。値の形の食い違いは見つかっていないが、「変更種別」の値の語彙はどこにも決められていない | 書く側 CC/skills/xddp-06-design/SKILL.md:128-130。読む側は V5 の抜き取り確認 #14 の行 | V5（抜き取り確認で、監査者が段階2b として範囲外にした読む側を確認）。A2 の監査者は「新規追加／変更／削除」の読み方に食い違いが無いと報告 |

---

## 7. 抜き取り確認の結果

検証者が、監査者が「食い違いなし」とした約束から、監査者の検索語を使わずに検索し直した結果。

### 7.1 最初の監査（V1〜V3）

| 領域 | 約束（一覧の #） | 検証者が使った検索 | 漏れ | 漏れの内容と食い違い | 検証者 |
|---|---|---|---|---|---|
| A1 | #17 列挙（`list_places`） | `constraints\.md\|code-knowledge/\*\*\|knowledge/code-knowledge`（ClaudeCode・tools/harness）と `list_places\|applicable_places` | なし | — | V1 |
| A1 | #11 `place` の入力 JSON | `knowledge_place\.py\b`（ClaudeCode・tools）と `"targets"\|"fallback"` | なし | — | V1 |
| A2 | #1 progress.md の先行更新セクション | `先行更新\|先行 upsert\|PREUPDATED\|preupdated`（ClaudeCode・tools） | なし | — | V1 |
| A2 | #8 CRS ナビゲーションと写し | `/crs/\|crs/CRS\|"crs"` と、CRS の元のパス | なし | — | V1 |
| A2 | #12 用語集 | `glossary\.md\|## 用語集` と、`_glossary_term_count` の見出し | なし | — | V1 |
| A3 | #1・#16 Layer 1・Layer 2 のパス | `知見ログ\|LESSONS_FILE\|LL-\{\|LL-[0-9N]` と `lessons`（CC 全体） | **あり** | #16 の書く側に `promote.py:1081-1097 append_breaking_warning` が無い。食い違いは無い | V2 |
| A3 | #22・#23・#24 「気づき・提案メモ」の見出しと対象ファイル | `^#{1,6} .*(気づき\|提案メモ)` と、全 agent での `気づき\|提案` | なし | — | V2 |
| A3 | #29 「対応方針」の語彙 | `今回対応\|次回CR\|"保留"` | なし | — | V2 |
| A4 | #37 module-catalog のパス | `CATALOG_FILE\s*[=:]\|catalog\.md\|--module-catalog` と `MODULE_CATALOG\|module_catalog` | **あり** | 読む側4か所が無い。パスは一致し、食い違いは無い | V3 |
| A4 | #41 glossary のパス | `glossary\.md\|GLOSSARY\|用語集` と、`KNOW_DIR` の定義 | なし | — | V3 |
| A5 | #31 RULEBOOK_CONTEXT の読み込み方 | `Steering Context`・`RULEBOOK`・`INCLUDE_CROSS` | **あり（軽い）** | 説明の文と開発用のひな形が無い。食い違いは無い | V3 |
| A5 | #3 cross ファイルのパス | `rulebook-cross\|cross/project-rulebook\|rulebook_cross\|cross_rb`・`CROSS_RULEBOOK_CONTEXT` | **あり** | fill-rulebook・01-init・promote.py:534 が無い。新しい食い違いは無い | V3 |
| A5 | #34 verifier が使う禁止事項の節番号 | `禁止事項\|Section 5\|Section 6\|§5\|§6` | なし | — | V3 |

**人の判断:** 漏れがあった A3・A4・A5 の監査を**やり直した**（2026-11-04）。

### 7.2 やり直しの後（V4・V5。前回と別の約束を選んだ）

| 領域 | 約束（やり直し版の一覧の #） | 検証者が使った検索 | 漏れ | 漏れの内容と食い違い | 検証者 |
|---|---|---|---|---|---|
| A3 | #2 LL の見出し `### LL-{NNN}：` | `LL-`（CC の .md・.py。既知の書く側を除く）と、domain_refs.py・xddp-common/scripts での `LL\b\|LL-\|LL_` | **あり（軽い）** | 読む側に `CC/agents/xddp-close-knowledge-agent.md:60`（見出しの ID を出典に使う）が無い。見出しは extract-ll がそのまま写すので、食い違いは無い | V4 |
| A3 | #21 INSIGHTS の収集サマリ | `収集サマリ\|抽出エントリ\|走査ファイル数\|節ありファイル数\|…`（CC・tools・README・docs/adr） | なし | — | V4 |
| A3 | #19 PENDING-PROMOTE の要確認LL一覧 | `unresolved\|repo: ?unknown\|repo：unknown\|昇格スキップ` | なし | — | V4 |
| A4 | #14 cross CHD「インタフェース変更サマリ」の列 | `breaking`・`CHD-{CR}-cross\|-cross\.md` をファイルごとに数え、`detect_breaking_changes` を読んだ | **あり（読む側）** | 工程6〜9 の designer・coder・verifier・test-writer・07・08・09 が一覧に無い。監査者は「工程7〜10 が cross CHD を読む約束は段階2b」として、確認していないことに明記していた。値の形の食い違いは無い（6. の 2b-4） | V5 |
| A4 | #16 latest-specs のフロントマターの必須キー | 15個の `11_*-template.md` のフロントマターのキーを取り出し、`artifact_lint._required_keys_for_path` と突き合わせた（実行） | なし | — | V5 |
| A4 | #24 `CURRENT_SPECS_REFS` | `{DOCS}/{repo}/specs\|latest-specs/{repo}/{mod\|specs/{mod`・`SPEC_FILE_PATHS\|CURRENT_SPECS\|SPECS_REFS` | なし | 隣の約束で食い違いを見つけた（6. の 2b-3） | V5 |
| A5 | #14 `## 1.6 ドメイン制約` | `1\.6\|[Dd]omain [Cc]onstraint\|domain_constraint\|load-domain`（CC・tools/harness） | **あり（説明だけ）** | xddp-common SKILL.md:240（索引の説明）。食い違いは無い | V4 |
| A5 | #21 `## 7. 変更履歴` | `変更履歴\|Change History\|history`（rulebook を書く全員） | **あり（書く側）** | fill-rulebook は rulebook を書いても §7 に行を足さない。読む側（02:284）は {CR} の行だけを見るので、食い違いは無い | V4 |
| A5 | #1 共通ファイルのパス（補助） | `プロジェクト規約\|規約ファイル\|steering`（`Load Steering Context` を含む行は除く） | **あり（軽い）** | sync-design の `STEERING_MAP` は #35 にある。promote.py:344 は N6 と同じもの。新しい食い違いは無い | V4 |

**検証者の所見（やり直しの監査の質）:**
- V4・V5 とも、約束の一覧の網羅と、書く側・読む側の洗い出しは前回より改善したとしている。
- 今回見つかった漏れは、説明の行、食い違いの無い読み手・書き手、監査者が範囲外と明記していた読む側だけで、結論を変える漏れは無かった。
- 残っている弱い点として、検証者は次を挙げている（それぞれの報告の末尾）:
  - 読む側が実際に読んでいる別の入力を見落とした結論（A4-38・A2-2 の補足）
  - 根拠の性格の取り違え（A3-28）
  - 起きる条件の洗い出しが狭い（A3-24・A3-29）
  - 同じ仕組みの横展開が途中で止まった（A5-31 の system・A5-33 の 06:358）
  - 範囲外にした読む側を一覧の行に書いていない（A4 #14）
- これらの指摘は、検証で補ったうえで 1. に反映した。

**人の判断（プラン 3.2.3）:** やり直しの後も漏れがあった A3・A4・A5 の監査を、もう一度やり直すか → **未決（10. の 1.）**

---

## 8. 段階3 の割り当て

### 8.1 段階1 の指摘

段階1 の指摘は fbf3956 が対象。監査の対象リビジョン ecb54c4 の `ClaudeCode/`・`tools/` は fbf3956 と同一なので、5件とも解消されずに残っている。

| 段階1 の # | 内容 | 割り当て（案） |
|---|---|---|
| R1 | 予約名と同じ名前のディレクトリの制約が読まれない（約束の食い違い。1.3 にも載せた） | P2 |
| R2 | LL の本文のコードブロックの中の `### LL-NNN：` で、エントリを切る | P3 |
| R3 | 短いフェンスで長いフェンスが閉じる | P3 |
| R4 | ワークスペースの外の絶対パスが `not-found` になる（約束の食い違い。1.4 にも載せた） | P2 |
| R5 | `_common_dir` は `posixpath.commonpath` の再実装 | P2 |

### 8.2 修正プランのまとまり（案。人の判断待ち）

プラン 3.3 に従い、同じファイルを直す指摘を1つのプランにまとめる案。**どの指摘を直すか、どのプランにするか、「直さない」とするかは、人が決める**（10. の 3.）。

| 案 | プラン | 主に直すファイル | 割り当てる指摘 |
|---|---|---|---|
| P1 | PLAN-20261103-domain-refs-shared-knowledge（プラン 3.3 のとおり書き換える） | `domain_refs.py`、`promote.py` の `update_ai_index`、01-init の AI_INDEX のひな形、11-specs の先行更新、close C0 の git の照合 | A1-7・A1-8・A2-1・A2-2・A2-4・A2-5・A2-6・A2-7・A2-8・A2-9・A2-11・A4-12・A4-13・A4-15・N1・N6・N7 |
| P2 | 新規（code-knowledge の書く側） | `xddp-close-knowledge-agent`（C3.6）、`xddp-survey-promote-agent`、`xddp-update-knowledge`、`knowledge_place.py`、code-knowledge のテンプレート、`code-knowledge-boundary.md`、`xddp-survey`、`specout_bfs.py`（`confirmed_modules`） | A1-1〜A1-6・A1-9〜A1-17・R1・R4・R5 |
| P3 | 新規（知見ログ・バックログ） | `promote.py` の LL・backlog の部分（`extract-ll`・`promote_lessons_learned`・`append_breaking_warning`・`promote_backlog`）、`collect_insights.py`、close Step B・C・D・E、update-knowledge（lesson）、analyst／architect／test-writer／coder／verifier の agent、abort、LL と backlog のテンプレート、SPO §9 のテンプレートと `specout_bfs.py` の §9 | A3-1〜A3-30・R2・R3・N8 |
| P4 | 新規（最新仕様） | 11-specs の SKILL、`xddp-specs-mod-agent`、`xddp-specs-uc-agent`、`spec_version_delta.py`、close C0-3、abort、survey の (c)、05／06 の latest-specs の参照、codemap、設定テンプレート、review | A4-1〜A4-19・A4-21〜A4-47（A4-20 は段階2b） |
| P5 | 新規（project-rulebook） | `xddp-fill-rulebook`、`xddp-close-knowledge-agent`（C3.5）、01-init、02-analysis Step B3、close の順序、`promote.py` の rulebook の写しと `write_output_file`、`load-steering-context.md`・`load-domain-constraints.md`、05／06 の呼び出し、rulebook のテンプレート、README | A5-1〜A5-33 |

**まとまりの間で同じファイルを直すもの**（衝突を避ける順序を、各プランで決める必要がある）:
- `promote.py`: P1（`update_ai_index`）・P3（LL・backlog）・P4（C0-3 の取り込みに関わる部分）・P5（rulebook の写し・`write_output_file`）
- `xddp-close-knowledge-agent`: P2（C3.6）・P5（C3.5）
- `xddp-close/SKILL.md`: P5（A5-1 の順序）・P1（A1-8 の時期）・P3（A3-27 の Step D・E、A3-29 の再実行）・P4（C0-3）
- `xddp-survey/SKILL.md`: P2（§2.6 の昇格）・P4（(c) の承認・衝突判定）

**同じ型で、まとめて直すかを決めるもの:**
- A3-4／A5-28（`{DOCS}` を丸ごと上書き）
- A3-8／A5-24（`has_cross` の条件）
- A3-27／A5-31（promote.py の失敗が close の Step D に出ない）

### 8.3 他のプランを書き換える予定（プラン 3.3）

- **PLAN-20261102-cochange-knowledge・PLAN-20261102-impact-hypotheses:** A1・A2 の指摘を割り当てたすべての修正プランの実装の後に、プラン 3.3 のとおり書き換える。足すのは再発防止（書く側→読む側のテスト・共有の値の単一定義）で、AI レビューをやり直してから承認・実装に進む。8.2 の案では、対象は P1（PLAN-20261103-domain-refs-shared-knowledge）と P2。割り当てが決まったら、ここにプラン名を書く。
- **PLAN-20260730-specout-recall-crosscheck:** A3 の指摘を割り当てたすべての修正プランの実装の後（割り当てた修正プランが無ければ、A3 の指摘の扱いをこの節に記録した後）に、プラン 3.3 のとおり書き換え、AI レビューをやり直してから承認・実装に進む。8.2 の案では、対象は P3。割り当てが決まったら、ここにプラン名を書く。

---

## 9. 実行の記録

| 項目 | 内容 |
|---|---|
| 対象リビジョン | ecb54c4 |
| 実行日 | 2026-11-03（A2、A1・A3・A4・A5 の最初の監査、V1〜V3、最初の統合）、2026-11-04（A3・A4・A5 のやり直し、V4・V5、再統合） |
| エージェント | すべて `general-purpose`・モデル claude-opus-5-5。計13体（下の内訳） |
| 体数とプランとの違い | 13体は、プラン 3.2.4 の「監査5体＋検証1〜3体で10体未満」を超える。超えたのは、人の判断（7.1）で A3・A4・A5 をやり直し、その検証を足したため。最初の監査と検証だけなら8体 |
| A2 の後に手順を直したか | **直した**（人の指示「手順を直して4体を実行」）。直した点は次の3つ |
| A2 をやり直したか | **やり直していない**（人の指示は、残りの4体の実行。A2 の一覧の粒度は、4. と 1.4 の A2-9 に注記した） |
| A3・A4・A5 のやり直し | 人の判断（2026-11-04）。共通の指示に足したのは次の3つ（[付録](contract-audit-2026-11/instructions-auditor-redo.md)） |

**エージェントの内訳（13体）:**
- 監査者8体: A2 を先に1体、残りの A1・A3・A4・A5 を並列、A3・A4・A5 のやり直しを並列
- 検証者5体:
  - V1: A1・A2・段階1 の R1・R4
  - V2: A3・A5-1〜A5-14
  - V3: A4・A5-15〜A5-28
  - V4: A3・A5 のやり直しで足した指摘
  - V5: A4 のやり直しで足した指摘

**A2 の後に直した点:**
- (a) Grep・Glob が無い環境なので、監査者に Bash の読み取りのコマンドを使ってよいと明記し、書き込みを禁じた。
- (b) 「確認した約束の一覧」の1行を、食い違いの有無を別々に判断できる単位にし、別々に直せる食い違いは別の指摘にする。
- (c) 書く側・読む側ごとに、見つけた方法（パターンと範囲、または参照元のファイル:行）を書く。

**やり直しで共通の指示に足した点:**
- 前回の報告を前提にせず、置き換える完全な報告にする。前回の番号を引き継ぎ、取り下げる指摘には理由を書く。
- 書く側・読む側を、約束ごとに2つ以上の独立した探し方で探す。
- 「前回からの変更」の節を書く。

**プランとの違い（ツール）:**
- プラン 3.2.4 は、監査者のツールを Read・Grep・Glob だけとしている。この環境のサブエージェントには Grep・Glob ツールが無かったので、監査者は Bash の読み取りのコマンドで検索した（A2 では指示外、それ以外は (a) の指示による）。
- 各 Bash の呼び出しが読み取りだけだったかは、すべては確認していません。A2 については、20回の呼び出しがすべて worktree に `cd` してから始まることを確かめた。
- 監査・検証の後、worktree に変更は無かった（冒頭）。

**トークンの実績:**

| エージェント | `subagent_tokens`（ハーネスの通知） | 出力（記録ファイルの `usage` の合計） | キャッシュ作成 | キャッシュ読み | ツールの呼び出し | 所要時間 |
|---|---|---|---|---|---|---|
| A2 | 245,008 | 38,049 | 229,975 | 5,370,113 | 32 | 397秒 |
| A1 | 252,113 | 47,186 | 238,135 | 9,076,861 | 53 | 502秒 |
| A3 | 254,158 | 50,147 | 237,759 | 7,619,185 | 49 | 525秒 |
| A4 | 333,243 | 61,148 | 308,606 | 13,535,999 | 66 | 650秒 |
| A5 | 232,824 | 43,557 | 218,843 | 5,039,067 | 35 | 437秒 |
| V1 | 261,430 | 42,005 | 253,227 | 13,096,705 | 70 | 470秒 |
| V2 | 239,155 | 37,271 | 232,035 | 10,548,454 | 62 | 423秒 |
| V3 | 275,039 | 42,667 | 265,196 | 13,763,866 | 71 | 488秒 |
| 小計（最初の監査・検証） | 2,092,970 | 362,030 | 1,983,776 | 78,050,250 | 438 | — |
| A3（やり直し） | 296,753 | 57,790 | 274,105 | 13,495,434 | 71 | 627秒 |
| A4（やり直し） | 378,453 | 80,599 | 354,137 | 21,342,208 | 86 | 850秒 |
| A5（やり直し） | 296,946 | 50,924 | 278,964 | 12,359,004 | 63 | 544秒 |
| V4 | 247,789 | 37,886 | 237,328 | 10,441,091 | 59 | 510秒 |
| V5 | 224,642 | 33,134 | 216,978 | 8,379,143 | 52 | 427秒 |
| 小計（やり直し・検証） | 1,444,583 | 260,333 | 1,361,512 | 66,016,880 | 331 | — |
| **計** | **3,537,553** | **622,363** | **3,345,288** | **144,067,130** | **769** | — |

- **集計の仕方:** ツールの呼び出しと所要時間は、ハーネスの通知の値。出力・キャッシュは、各エージェントの記録ファイルの API 応答の `usage` を、メッセージの id ごとに1回だけ数えて合計した。
- **確認していないこと:** `subagent_tokens` が何を数えているかは確認していません。料金は、キャッシュ読みの単価がほかと違うので出していない。
- **見積もりとの比較:** A2 の後に示した残り4体の見積もりは約100万〜220万（`subagent_tokens` 相当）。実績は 1,072,338 で、見積もりの下限に近かった。やり直しの3体は 972,152 で、最初の3体（820,225）の約1.19倍だった。
- **メインのセッションの分:** 統合・報告書の執筆・段階1 のレビューに使った分は、上の表に含まない（計測していません）。

---

## 10. 人に決めてほしいこと

1. **抜き取り確認の漏れ**（7.2）: やり直しの後も、A3・A4・A5 で書く側・読む側の漏れがあった（A3 で1件・A4 で1件・A5 で3件の約束）。
   - 漏れていたのは、説明の行、食い違いの無い読み手・書き手、監査者が段階2b として範囲外に明記していた読む側だけで、結論を変える漏れは無かった。
   - これらの領域の監査を、もう一度やり直すか（プラン 3.2.3）。
2. **段階2b を行うか**（6.。プラン 7. の 2.）。候補は4件。
3. **段階3 の割り当て**（8.2 の案 P1〜P5）。どの指摘を直すか、「直さない」とするか（理由を記録する）、プランのまとまりをどうするか。
