# 約束の監査の報告書（PLAN-20261103-contract-audit 段階2a）

作成日: 2026-11-03
**状態:** 監査（A1〜A5）・検証・統合が終わった。次の3つは人の判断を待っている（10.）。
1. 抜き取り確認で漏れがあった領域の監査をやり直すか
2. 段階2b を行うか
3. 段階3 の割り当て（案）

- **対象リビジョン:** ecb54c4（`audit/contract-audit-2026-11` の、段階2a を始めた時点の HEAD）。`ClaudeCode/`・`tools/` は fbf3956 と同一（`git diff --stat fbf3956 ecb54c4 -- ClaudeCode tools` の出力が空）。
- **読んだ場所:** 監査者・検証者は、セッションのスクラッチのディレクトリに作った worktree（`git worktree add --detach … ecb54c4`）だけを読んだ。検証者3体は、終わった時点でその worktree の `git status --short` が空であることを報告した。メインのセッションも、A2 の後に同じことを確かめた。
- **行番号:** ecb54c4 の値。パスの `CC/` は `ClaudeCode/.claude/` の略。
- **段階1 の報告書:** [review-fbf3956-2026-11.md](review-fbf3956-2026-11.md)
- **付録（原文）:**
  - 監査者の報告: [A1](contract-audit-2026-11/A1-audit.md)・[A2](contract-audit-2026-11/A2-audit.md)・[A3](contract-audit-2026-11/A3-audit.md)・[A4](contract-audit-2026-11/A4-audit.md)・[A5](contract-audit-2026-11/A5-audit.md)
  - 検証者の報告: [V1](contract-audit-2026-11/V1-verify.md)・[V2](contract-audit-2026-11/V2-verify.md)・[V3](contract-audit-2026-11/V3-verify.md)
  - 渡した指示: [監査者](contract-audit-2026-11/instructions-auditor.md)（A1・A3・A4・A5 に渡した版）・[検証者](contract-audit-2026-11/instructions-verifier.md)。A2 に渡した指示は、A2 の監査者の起動時の依頼文で、ファイルにしていない（内容は 9. の「A2 の後に直した点」との差分）。

**指摘ごとの詳細の置き場所（プラン 3.2.5 の「指摘ごと」）:** 指摘ごとの約束／書く側／読む側／食い違い／起きること／修正案は、各監査者の報告（付録）の「3. 指摘」にある。検証の判定・確度・根拠（再現の手順を含む）は、各検証者の報告（付録）の「1. 指摘の検証の表」にある。統合で変えた点（重複・否定・重大度・段階2b への移動）は 2. に書く。この報告書の 1. は、統合した後の結果。

---

## 1. 指摘の一覧（統合後）

### 1.1 件数

| | 🔴 | 🟡 | 🔵 | 計 |
|---|---|---|---|---|
| A1 code-knowledge（段階1 の R1・R4 を含む） | 1 | 6 | 12 | 19 |
| A2 AI_INDEX.md | 0 | 7 | 2 | 9 |
| A3 知見ログ・バックログ | 4 | 8 | 11 | 23 |
| A4 仕様・用語・カタログ | 3 | 12 | 15 | 30 |
| A5 project-rulebook | 0 | 12 | 16 | 28 |
| 検証者が新たに見つけたもの（3.） | 0 | 0 | 5 | 5 |
| **計** | **8** | **45** | **61** | **114** |

- **重大度の凡例:** 🔴 知見・成果物が黙って失われる／誤った内容が下流に渡る。🟡 人が気付ける形で失われる・限定的な条件でだけ起きる。🔵 記述の不整合（動作への影響は無い）。
- **重大度の決め方:** 検証者の案を採った。監査者の案と違うものは 2.3。
- **件数に入れていないもの:** 他の指摘に統合したもの（2.1）、検証で否定したもの（2.2）、段階2b の候補に移したもの（6.）。

**確度の凡例:**
- ✅ 確かめた（両側を読んで確認した。「再現」は検証者がスクリプト・git を実行して再現した）
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
| A1-1 | A1 | survey の knowledge への昇格で、§2.6 の全項目が同じ出典 `SURVEY-{TODAY}` を持つ。そのため同じ置き場所の制約が互いに置き換わり、最後の1件しか残らない（CC/agents/xddp-survey-promote-agent.md:59-60,63） | ✅ | 確認 |
| A3-1 | A3 | Layer 2 の LL の重複判定が ID だけ（CC/skills/xddp-close/scripts/promote.py:904-908）。update-knowledge の lesson は Layer 2 で別に番号を採る（CC/skills/xddp-update-knowledge/SKILL.md:206-209）。同じ ID になった Layer 1 の LL は Layer 2 に入らず、どこにも示されない | ✅ 再現（前提の書式は 🔶） | 確認 |
| A3-3 | A3 | ワークスペースごとに Layer 1 の LL を LL-001 から採番すると、共有の `{DOCS}` の Layer 2 で番号が重なり、後からクローズした側の LL が入らない | 仕組みは ✅・運用は 🔶 | 確認（条件つき） |
| A3-5 | A3 | cross の TSP（`09_test-spec/cross/TSP-{CR}-cross.md`）の「気づき・提案メモ」を `collect_insights.py`（:170-171）が集めない | ✅ 再現 | 確認 |
| A3-6 | A3 | progress.md の「## 気づき・提案メモ」（テンプレートは「バックログの入力として活用する」と書く）を `collect_insights.py` が集めない。人が書いた場合に失われる | ✅ 再現 | 確認 |
| A4-1 | A4 | 工程11（CC/agents/xddp-specs-mod-agent.md:49,161）は、`04_specout/{repo}/modules/` の**ディレクトリ**だけをモジュール資料とみなす。工程4a は、分割パスでは `modules/{名前}-spo.md` という**ファイル**を書く（CC/skills/xddp-04-specout/module-documentation.md:268-270）。同じ工程11 の `spec_version_delta.py:181-183` はファイルを前提にしている | ✅ | 確認 |
| A4-2 | A4 | 統合パス（`SPO-{CR}.md` の §2.A…）のモジュール資料を工程11 が読まない（統合パスの読み方の記述が無い）。文書化したファイルが10件以下の CR では、モジュール仕様が作られない | ✅ | 確認 |
| A4-8 | A4 | 工程11 の Step GATE で人が削除したモジュール・ユースケースを、close の Step C0-3 が `{DOCS}` から latest-specs に書き戻す。そのため C2 の削除候補にもならない（CC/skills/xddp-11-specs/SKILL.md:512-514 → CC/skills/xddp-close/SKILL.md:211-216 → promote.py:297-301,317-322） | ✅ | 確認 |

### 1.3 🟡（45件）

| # | 領域 | 内容 | 確度 | 検証 |
|---|---|---|---|---|
| A1-2 | A1 | update-knowledge の constraint: 同じ出典の別の制約を置き換え、プレビューにも示さない | ✅ | 確認 |
| A1-3 | A1 | close の SPO §5.6・LL 由来の制約に upsert の鍵が無い（鍵を定めているのは TRS だけ） | 鍵が無いことは ✅・置き換わるかは 🔶 | 確認 |
| A1-4 | A1 | TRS の NG の upsert の鍵 `CR-{CR} / NG-{NNN}` に実行回が入っていない。回ごとに NG を振り直すと置き換わる（repo は置き場所で分かれるので問題ない） | 🔶 | 一部確認 |
| A1-7 | A1 | `domain_refs.py:308-311` が `DOMAIN_REF_PATHS` に `_structures`・`_constants` の**ディレクトリ**を入れる。analyst はファイルを Read する前提 | ✅ 再現 | 確認 |
| A1-8 | A1 | `_structures`・`_constants` だけを、AI_INDEX のラベル経由で集める。AI_INDEX が無い場合・クローズ直後・survey や手での登録の後は工程2 に届かない（A2-10 を統合） | ✅ 再現 | 確認 |
| R1 | A1 | 予約名（`_structures` 等）と同じ名前のディレクトリにある対象の制約は、置き場所がその予約名になる。`list_places` はそれを除くので読まれない（段階1） | ✅ 再現 | 確認 |
| A2-1 | A2 | code-knowledge インデックスの `_structures` のラベルが、書く側は `構造体関連図`（promote.py:601）、読む側は `共有構造体`（domain_refs.py:35-38）で食い違う | ✅ 再現 | 確認 |
| A2-2 | A2 | クロスインタフェース一覧の「⚠️ 破壊的変更あり」が付かない。CHD の生の名前とケバブ形式のディレクトリ名を比べているため。付いた場合も、キー列が変わって行が増える | (a)(c) は ✅ 再現・(b) は 🔶 | 確認 |
| A2-4 | A2 | 過去の DSN／CHD を AI_INDEX から引く読む側（工程5・6）に、書く側が無い | ✅ | 確認 |
| A2-5 | A2 | TSP／TRS の表のキーが repo だけで、過去の CR の一覧にならない | ✅（影響は 🔶） | 確認 |
| A2-7 | A2 | 「最終更新CR」を、今の CR が触っていない行にも付ける。11-specs が引用する promote.py の文は実在しない | ✅ | 確認 |
| A2-8 | A2 | 先行更新のモジュール名（SPO のディレクトリ名）と latest-specs のケバブ名がずれうる | 🔶 | 判断できず |
| A2-11 | A2 | 11-specs がコミットせずに AI_INDEX を書き換えると、close C0-2 の `git pull` が止まる（失敗時の扱いが無い）。`git diff --name-only` は git のリポジトリのルートからの相対パスを返すので、`AI_INDEX.md` との照合（C0-4 の PROTECTED_FILES の照合も）が一致しない | git の振る舞いは ✅ 再現・LLM の扱いは 🔶 | 確認 |
| A3-2 | A3 | Layer 1 の LL の採番の規則が無い（アーカイブの後に番号が重なりうる） | ✅／🔶 | 確認 |
| A3-4 | A3 | `improvement-backlog.md` を `{DOCS}` に丸ごと上書きする（A5-28 と同じ型） | ✅（運用は 🔶） | 確認 |
| A3-7 | A3 | `collect_insights.py` が `repos_keys` の全 repo・cross・system の latest-specs を毎回走査する。前の CR の気づきが出典の CR の分からない形で集まる（V2 の N2 を含む） | ✅ 再現 | 確認 |
| A3-8 | A3 | multi-repo で cross の成果物の無い CR の `repo: cross` の LL を、Layer 2 に入れず、示しもしない（A5-24 と同じ型） | ✅ 再現 | 確認 |
| A3-9 | A3 | LL の `repo` 欄を検証せずにパスにする（`全リポジトリ` でディレクトリができる） | ✅ 再現 | 確認 |
| A3-10 | A3 | xddp-analyst-agent が `LESSONS_CONTEXT` を Inputs に持たない | 宣言が無いことは ✅・使われないかは 🔶 | 確認 |
| A3-11 | A3 | xddp-architect-agent が `LESSONS_CONTEXT` を Inputs に持たない | 同上 | 確認 |
| A3-12 | A3 | xddp-test-writer-agent が `LESSONS_CONTEXT` を Inputs に持たない | 同上 | 確認 |
| A4-3 | A4 | `SPECOUT_MODULES` を `modules/` のディレクトリ名から取る（統合パスでは空。V1 の新たな気付き1 と同じ） | ✅ | 確認 |
| A4-4 | A4 | 工程11 の廃止モジュールの判定の照合先がディレクトリ。既存のモジュールが毎回廃止候補になる | ✅ | 確認 |
| A4-6 | A4 | structure.md の材料の見出し `クラス図` が SPO に無い（SPO は `### 4.2 データ型関連図`） | ✅ 再現 | 確認 |
| A4-9 | A4 | 工程11 を分割して実行すると、前の回の更新が「更新仕様書ファイル一覧」から外れ、C0-3 で上書きされうる | 🔶 | 判断できず |
| A4-10 | A4 | GATE で人が直接編集した、一覧に無いファイルが、C0-3 で `{DOCS}` の前の版に戻る | ✅ | 確認 |
| A4-11 | A4 | survey の (c) で architecture.md に追記した内容が `{DOCS}` に届かず、後の CR の C0-3 で上書きされうる | ✅ | 確認 |
| A4-12 | A4 | AI_INDEX が無いとき、`domain_refs.py:354-359` は cross のインタフェース仕様を誤ったパスで探す | ✅ | 確認 |
| A4-13 | A4 | 01-init が `{DOCS}/{repo}/specs/` を必ず作るので、`domain_refs.py` の latest-specs へのフォールバック（a）は働かない。11-specs の「close の前でも次の CR の工程2 が参照できる」という先行更新の目的と案内も成り立たない（A2-3 を統合） | ✅ 再現 | 確認 |
| A4-14 | A4 | 工程5・6 が latest-specs を探すとき、SPO のモジュール名をそのまま使う（ケバブ名とずれる） | 🔶 | 確認 |
| A4-15 | A4 | ユースケースの `related-modules` の値が、latest-specs のディレクトリ名とずれうる | 🔶 | 確認 |
| A4-16 | A4 | survey の `MODULE_KEBAB` と、CR のモジュール名の決め方が違う。同じコードの仕様が二重にできうる | 🔶 | 一部確認 |
| A4-17 | A4 | SPEC レビューに SPO が渡らない（チェックリストは SPO との照合を求める） | ✅ | 確認 |
| A5-1 | A5 | close で、C3.5 の rulebook の upsert が、C6 の `{DOCS}` への写し（promote.py run）の後に行われる | ✅ | 確認 |
| A5-2 | A5 | シングルリポジトリでも C3.5 が `project-rulebook-{repo}.md` を作る。init・fill-rulebook はそのファイルが無い前提 | ✅ | 確認 |
| A5-3 | A5 | 最初の CR では、init が §7 の初期行に {CR} を入れるので、02 Step B3 が「抽出済み」と判定してスキップする | ✅ | 確認 |
| A5-4 | A5 | fill-rulebook の repo 別ファイルの §2 の判定に、§3 のプレースホルダーを使っている | 対応のずれは ✅・上書きが起きるかは 🔶 | 確認 |
| A5-6 | A5 | fill-rulebook の「§5 (ADR)」の規則が、共通ファイルでは §5 禁止事項に当たる | ✅／🔶 | 確認 |
| A5-7 | A5 | fill-rulebook に §6 の規則が2つある。repo 別の §6 禁止事項にモジュール構成を書く | ✅／🔶 | 確認 |
| A5-8 | A5 | fill-rulebook が §4 を「スペックアウトで記入」の注記で置き換えるが、工程4 は rulebook を書かない | ✅／🔶 | 確認 |
| A5-9 | A5 | fill-rulebook の「§1 / §2 Cross-repo overview」が、cross の §2 API バージョニング規約に当たる | ✅／🔶 | 確認 |
| A5-10 | A5 | fill-rulebook に cross §3〜§6 用のドラフト規則が無い | ✅／🔶 | 確認 |
| A5-12 | A5 | C3.5 で cross に追記する節が決まっていない | 🔶 | 確認 |
| A5-18 | A5 | 02 Step B3 の「repo 別は C3.5 で行う」に、受け渡しの仕組みが無い | 🔶 | 確認 |
| A5-28 | A5 | `{DOCS}` の rulebook を、競合を検出せずに丸ごと上書きする（A3-4 と同じ型） | 🔶 | 確認 |

### 1.4 🔵（61件）

| # | 領域 | 内容 | 確度 | 検証 |
|---|---|---|---|---|
| A1-5 | A1 | 出典の `CR-{CR_NUMBER}` で、CR フォルダ名が `CR-` で始まると接頭辞が二重になる | 🔶 | 確認 |
| A1-6 | A1 | 「対象」を書けという指示に対して、constraints テンプレートの2つの節に `**対象:**` 欄が無い | 文面は ✅・影響は 🔶 | 一部確認 |
| A1-9 | A1 | SPO §4.5 の `定義モジュール` と、`_constants` テンプレートの `定義場所` の列が合わない | ✅ | 確認 |
| A1-10 | A1 | 「## 昇格見送り一覧」を close の Step D で示さない | ✅ | 確認 |
| A1-11 | A1 | `_domain名要確認一覧` から、cross の `_constants`・`_structures` が漏れうる | ✅ | 一部確認 |
| A1-12 | A1 | update-knowledge の callgraph で、入力させた「フロー名」をファイル名に使わない | ✅ | 確認 |
| A1-13 | A1 | update-knowledge が flow・callgraph のパスを自分で定義している（単一情報源の規則に反する） | ✅ | 確認 |
| A1-14 | A1 | survey が昇格先のパスを自分で定義している | ✅ | 確認 |
| A1-15 | A1 | survey の「topic では §2.6 の昇格は発生しない」という記述が誤り | ✅ | 確認 |
| A1-16 | A1 | `specout_bfs.py status` の `confirmed_modules`（第1階層）を読むのがテストだけ | ✅ | 確認 |
| A1-17 | A1 | ヒアドキュメントに人の入力をそのまま JSON 文字列として埋め込む。`\` で exit 2 になるか、`\n` 等で黙って `no-path` になる | ✅ 再現（LLM がエスケープするかは 🔶） | 確認 |
| R4 | A1 | ワークスペースの外の絶対パスの `status` が `not-found` になる（段階1） | ✅ 再現 | 確認 |
| A2-6 | A2 | AI_INDEX「共通知識」の列が init と promote で違う。repo 別・cross の rulebook があると、共通の rulebook の行が消える（A5 の担当外を統合。V1 は 🟡、V3 は 🔵。共通知識の節を読むスクリプトは無く、写しは残るので 🔵 とした） | ✅ 再現 | 一部確認 |
| A2-9 | A2 | AI_INDEX のひな形・説明の不整合（ひな形が3つ・プレースホルダー行・知識参照ガイドの参照先・`state` 列・`related-modules: []`・セルの `|`）。A2 は前の版の指示で監査したため、6件を1つの指摘にまとめている | ✅（一部 再現） | 確認 |
| A3-13 | A3 | analyst の「なし」を、`collect_insights.py` が未記入と判定しない | ✅ 再現 | 確認 |
| A3-14 | A3 | SPO §9 の「なし」の行と、テンプレートのままの §9 を、未記入と判定しない | ✅ 再現 | 確認 |
| A3-15 | A3 | IDEA のエントリの書式が、テンプレートと違う | ✅ | 確認 |
| A3-16 | A3 | close Step B の「summary table」がどの表を指すか不明 | ✅ | 確認 |
| A3-17 | A3 | Layer 2 の「エントリ一覧」の表を誰も更新しない | ✅ | 確認 |
| A3-18 | A3 | update-knowledge の lesson のエントリの書式が決まっていない | 🔶 | 確認 |
| A3-19 | A3 | LL テンプレートの「管理場所」が、実際のパスと違う | ✅ | 確認 |
| A3-20 | A3 | close Step B・C の「create from template」が、テンプレートのパスを示さない | ✅ | 確認 |
| A3-21 | A3 | close Step C の抽出の観点が「same as before」で、何から抽出するかが書かれていない | ✅ | 一部確認 |
| A3-22 | A3 | abort が「update-knowledge 等で backlog に登録」と案内するが、update-knowledge に backlog の種別が無い | ✅ | 確認 |
| A3-23 | A3 | close のコメントにある Layer 1 の読み手の一覧が足りない | ✅ | 確認 |
| A4-5 | A4 | precheck が SPO ファイルをケバブ名で引くので、`_`・大文字のモジュールで見つからない | ✅ 再現 | 確認 |
| A4-7 | A4 | compare が、SPO の無いモジュールにも版の下限を当てはめる | ✅ | 確認 |
| A4-18 | A4 | SPO §4.3 の `source` 注記を書く側がいない | ✅ | 確認 |
| A4-19 | A4 | 「Section 3-0」「Section 3-4」を参照しているが、その節が無い | ✅ | 確認 |
| A4-21 | A4 | module-catalog のディレクトリ（入れ子）と、specout が照合に使う値（第1要素）の形が合わない | ✅ | 確認 |
| A4-22 | A4 | architecture.md の材料にする SPO の節の名前が、テンプレートの別名と違う | ✅ | 一部確認 |
| A4-23 | A4 | 日本語の見出しのケバブ変換が決まっていない（precheck が判定を飛ばす） | ✅ 再現 | 確認 |
| A4-24 | A4 | 工程11 の自動修正の対象キーと、lint の必須キーが違う | ✅ | 確認 |
| A4-25 | A4 | compare が §1 の「バージョン」行を書き換えない | ✅ | 確認 |
| A4-26 | A4 | 設定テンプレートの latest-specs のパスに `{repo}/` が無い | ✅ | 確認 |
| A4-27 | A4 | 下調べエージェントの `LATEST_SPECS_DIR` の説明に `{XDDP_DIR}/` が無い | ✅ | 確認 |
| A4-28 | A4 | abort の説明が、close の動作と違う | ✅ | 確認 |
| A4-29 | A4 | sync-design の説明が、工程11 の動作と違う | ✅ | 確認 |
| A4-30 | A4 | code-knowledge-boundary の書き手の欄が、survey の実際の書き先と違う | ✅ | 確認 |
| A4-31 | A4 | glossary をテンプレートから作ると、見本の行が用語数に数えられる | ✅ 再現 | 確認 |
| A5-5 | A5 | fill-rulebook の repo 別ファイルの §6 の行に、テンプレートに無いプレースホルダーがある | ✅ | 確認 |
| A5-11 | A5 | fill-rulebook がテンプレートから作るとき、日付と CR のプレースホルダーを置き換えない | ✅ | 確認 |
| A5-13 | A5 | C3.5 の宛先の表の Section 5 の名前が、テンプレートと違う | ✅ | 確認 |
| A5-14 | A5 | C3.5 の宛先の表の Section 4 の名前が、テンプレートと違う（同じエージェントの中でも食い違う） | ✅ | 確認 |
| A5-15 | A5 | C3.5 の Section 4 のテーマ見出しの例が、テンプレートの見出しと一致しない | 🔶 | 確認 |
| A5-16 | A5 | C3.5 がテンプレートからファイルを作るときの、テンプレートと置き換えが決まっていない | ✅ | 確認 |
| A5-17 | A5 | LL のタグ `#レビュー` が、C3.5 の宛先の表に無い | ✅ | 確認 |
| A5-19 | A5 | 02 Step B3 の「既存のコードブロックの末尾」で、どのブロックかが決まらない | ✅ | 確認 |
| A5-20 | A5 | 禁止事項の行の書式が、書く側どうしで違う | ✅ | 確認 |
| A5-21 | A5 | init の `{CR}` の置き換えで、cross テンプレート §6 の一般的な手順の文に CR 番号が入る | ✅（全部の出現を置き換えるかは 🔶） | 確認 |
| A5-22 | A5 | init の置き換えで、ADR の書式のコメントに日付と CR が入る | 同上 | 確認 |
| A5-23 | A5 | load-domain-constraints の「未記入」の判定が、テンプレートの §1.6 の行の形に合わない | 🔶 | 確認 |
| A5-24 | A5 | cross の rulebook の写しが、今の CR の cross の成果物の有無で決まる（A3-8 と同じ型） | ✅ | 確認 |
| A5-25 | A5 | close Step D が、写していない rulebook も「昇格」と報告する | ✅ | 確認 |
| A5-26 | A5 | cross テンプレート §6 が、存在しない形のパスを指す（「移行ガイド」の節は存在する） | ✅ | 一部確認 |
| A5-27 | A5 | README の §1.5 の説明が、テンプレートと合わない | ✅ | 確認 |
| N1 | A2 | survey が AI_INDEX に書く最終更新CR `SURVEY-{TODAY}` が、アーカイブ候補の正規表現に一致しない（V1） | ✅ | — |
| N2 | A5 | fill-rulebook が使う `{REPO_PATH}` が、どこにも定義されていない（V2。V2 の案は 🔵〜🟡） | ✅ | — |
| N3 | A3 | `append_breaking_warning` が、ヘッダーの無い Layer 2 のファイルを作りうる（V2） | 🔶 | — |
| N4 | A4 | survey Step 7 が、Step 8② でまだ書いていない architecture.md をレビューの対象に入れる（時期。V3） | ✅ | — |
| N5 | A4 | precheck が spec.md の全体と SPO §2 だけを比べるので、行数の変化率が大きく出る（V3） | ✅ 再現 | — |

---

## 2. 統合で変えた点

### 2.1 重複の統合

| 統合したもの | 残したもの | 理由 |
|---|---|---|
| A1 の担当外（構造体のラベル） | A2-1 | 同じ食い違い（V1） |
| A4 の担当外 #1（breaking の印） | A2-2 | 同じ食い違い（V3） |
| A4 の担当外 #2（先行更新の行の集合） | A2-7 | 同じ食い違い（V3） |
| A5 の担当外（共通知識） | A2-6 | 同じ食い違い（V3） |
| A2-10（`_structures`・`_constants` は AI_INDEX 経由でしか読まれない。時期） | A1-8 | 同じ食い違い（V1）。書かれるもの（code-knowledge の読み方）の領域 A1 に寄せた |
| A2-3（先行更新の目的が達成されない） | A4-13 | 同じ原因（init が `{DOCS}/{repo}/specs/` を作るので latest-specs へのフォールバックが働かない。V3）。latest-specs の読み方の領域 A4 に寄せた |
| V1 の新たな気付き1（工程11 は `modules/` をディレクトリとして読む） | A4-1・A4-3・A4-4 | 同じ食い違い |
| V1 の新たな気付き2（C0-4 の PROTECTED_FILES の照合） | A2-11 | 同じ原因（git が返すパスの基準） |
| V2 の N2（`repos_keys` の全 repo を走査） | A3-7 | V2 が「A3-7 に含めてよい」とした |

同じ型だが、別の対象の指摘として残したもの:
- A3-4 と A5-28（`{DOCS}` を `copy2` で丸ごと上書き）
- A3-8 と A5-24（`has_cross` の条件）

### 2.2 検証で否定したもの

| 指摘 | 内容 | 否定の理由（V2） |
|---|---|---|
| A3 の担当外（A2） | AI_INDEX の共通ナビゲーションが Layer 2 の「タグ検索例」を示すが、Layer 2 にタグ別インデックスが無い | promote.py:343 は「タグ検索例」を挙げているだけで、インデックスがあるとは書いていない。Layer 2 のエントリは Layer 1 のエントリを丸ごと写したもので（promote.py:911）、`**タグ：**` のメタ行を含むので、タグの文字列での検索は成り立つ |

### 2.3 重大度を監査者の案から変えたもの

| 指摘 | 監査者 → 統合 | 理由（検証者） |
|---|---|---|
| A2-1 | 🔴 → 🟡 | ラベルを合わせても、A1-7 によりディレクトリのパスが渡り、analyst は Read の失敗を §0 に記録する（人が気付ける形になる）。知見は `{DOCS}` に残る（V1） |
| A5-4 | 🔴 → 🟡 | 「人が §2 を書いた」「§3 は未記入」「LLM が節番号で書き込み先を決める」の3つが揃ったときだけ起きる。Step 5 で人がドラフトを確認する。同じ根の A5-6・A5-7 と揃えた（V2） |
| A1-6 | 🟡 → 🔵 | 読む側（module-documentation.md:181）は `**対象:**` の無い制約を内容で照合する作りで、食い違いは書く側の中にある（V1） |
| A2-6 | 🟡 → 🔵 | V1 は 🟡、V3 は 🔵 と分かれた。共通知識の節を読むスクリプトは無く（V3 が grep で確認）、rulebook の写しは残るので 🔵 とした |
| A3-14 | 確度 🔶 → ✅ | テンプレートのままの §9 も1件として集まることを再現した（V2） |

### 2.4 段階2b の候補に移したもの

- A4-20（cross の CHD の「影響リポジトリ」を読む約束）: A2 の監査者が「段階2b」と印を付けた候補と同じ。書く側が工程の成果物（CHD）で、読む側も工程のプロシージャ・チェックリストなので、プラン 3.2.2 の境界の規則により段階2b に移した（6.）。V3 の検証結果（確認・🔶・🔵）は 6. に残す。

---

## 3. 検証者が新たに見つけた食い違い

検証者が、割り当てた指摘の外で見つけたもの（1.4 の N1〜N5）。見つけた検証者だけが確かめたもので、別の検証者の検証は受けていない。

| # | 内容 | 書く側・読む側 | 見つけた検証者・確度 |
|---|---|---|---|
| N1 | survey が AI_INDEX に書く最終更新CR `SURVEY-{TODAY}` が、アーカイブ候補の正規表現 `\bCR-…` に一致しない | CC/skills/xddp-survey/SKILL.md:393,397 → promote.py:636 | V1・✅ |
| N2 | fill-rulebook が使う `{REPO_PATH}` が、どこにも定義されていない（ADR の候補の git log は、LLM がパスを推測して実行することになる） | CC/skills/xddp-fill-rulebook/SKILL.md:172,174,178（Step 1 の :40-42 で受け取るのは WORKSPACE_ROOT・XDDP_DIR・REPOS_KEYS だけ） | V2・✅ |
| N3 | `append_breaking_warning` は、ファイルが無いとき `# 知見ログ` のヘッダーなしで Layer 2 を作る | promote.py:1082-1088 | V2・🔶 |
| N4 | survey Step 7 は「Step 8② で architecture.md を作成・追記した場合はそれもレビューの対象に含める」と書くが、Step 8② は Step 7 と人の承認の後に実行される | CC/skills/xddp-survey/SKILL.md:339 → :357-375 | V3・✅ |
| N5 | precheck は、latest-specs の spec.md の全体と SPO の §2 だけを比べるので、テンプレートの他の節の分だけ行数の変化率が大きく出る（再現で 46.15%・71%） | CC/skills/xddp-11-specs/scripts/spec_version_delta.py:203-214,236-237 | V3・✅ 再現 |

知識ハブの約束の外のため、件数に入れなかったもの:
- V3 の新たな気付き2: 設定テンプレートの `SPECOUT_DIAGRAM_LEVEL` の説明（CC/skills/xddp-01-init/templates/xddp.config.md:341-343）が、module-documentation.md の Section 4 の生成範囲と合わない（✅・🔵）。工程4a の設定と手順の約束なので、6. の段階2b の候補に置く。

---

## 4. 確認した約束の一覧（領域ごと）

約束の表（約束／書く側／読む側／見つけた方法／結果）の全体は、各監査者の報告（付録）の「1. 確認した約束の一覧」にある。

| 領域 | 確認した約束 | うち食い違いなし | 付録 |
|---|---|---|---|
| A1 | 41 | 25 | [A1-audit.md](contract-audit-2026-11/A1-audit.md) §1 |
| A2 | 16（前の版の指示のため、1行に複数の約束をまとめた行がある） | 4 | [A2-audit.md](contract-audit-2026-11/A2-audit.md) §1 |
| A3 | 37 | 21 | [A3-audit.md](contract-audit-2026-11/A3-audit.md) §1 |
| A4 | 51 | 25 | [A4-audit.md](contract-audit-2026-11/A4-audit.md) §1 |
| A5 | 54 | 25 | [A5-audit.md](contract-audit-2026-11/A5-audit.md) §1 |

「食い違いなし」は、各監査者の一覧（付録の §1 の表）の結果の列が「なし」で始まる行を、スクリプトで数えた。結果の列が「なし（…は A?-n）」のように別の指摘を参照している行も「なし」に数えた。

---

## 5. 時期の約束

各領域の時期の約束の表（書く側の Step → 読む側の Step・順序の根拠）は、各監査者の報告（付録）の「2. 時期の約束の表」にある。食い違いがあったもの:

| 書く側（スキル・Step） | 読む側（スキル・Step） | 順序の根拠 | 指摘 |
|---|---|---|---|
| xddp-close Step C2〜C7（promote.py run。AI_INDEX・rulebook の写し） | 同じ close の Step C3.5・C3.6（knowledge agent が rulebook・code-knowledge を書く） | CC/skills/xddp-close/SKILL.md:299（run）→ :312（agent） | A5-1・A1-8（制約だけは ADR-0033:80 に受け入れた制限として記録がある） |
| xddp-11-specs Step DONE（AI_INDEX の先行更新） | 次の CR の xddp-02-analysis Step 0（close の前） | CC/skills/xddp-11-specs/SKILL.md:578 | A4-13（A2-3 を統合） |
| xddp-11-specs Step DONE（`{DOCS}/AI_INDEX.md` を書き換え、コミットしない） | xddp-close Step C0-2（`git -C {DOCS} pull`） | CC/skills/xddp-close/SKILL.md:207-209 | A2-11 |
| xddp-11-specs Step GATE（廃止候補を削除・人の直接編集） | xddp-close Step C0-3（DOCS → latest-specs の取り込み）→ C2 | CC/skills/xddp-11-specs/SKILL.md:512-514 → CC/skills/xddp-close/SKILL.md:211-216 | A4-8・A4-10 |
| xddp-11-specs Step DONE（分割実行で一覧を上書き） | xddp-close Step C0-3 | CC/skills/xddp-11-specs/SKILL.md:550-573 | A4-9 |
| xddp-survey Step 8②（latest-specs の architecture.md に追記） | 後の CR の xddp-close Step C0-3 | CC/skills/xddp-survey/SKILL.md:374-381 → CC/skills/xddp-close/SKILL.md:215 | A4-11 |
| xddp-survey Step 8② | xddp-survey Step 7（レビュー） | CC/skills/xddp-survey/SKILL.md:339 → :357-375 | N4 |
| close C6（`{DOCS}` を copy2 で上書き） | 別の作業場所の close C0（`{DOCS}` の pull） | CC/skills/xddp-close/SKILL.md:207-277 | A5-28・A3-4 |
| xddp-01-init Step 4.6（§7 の初期行に {CR}） | 同じ CR の xddp-02-analysis Step B3（冪等性の判定） | CC/skills/xddp-01-init/SKILL.md:223 → CC/skills/xddp-02-analysis/SKILL.md:284-285 | A5-3 |

---

## 6. 段階2b の候補

監査者が「段階2b」と印を付けた食い違いと、統合で段階2b に移したもの。プラン 3.2.3 により、段階2b の候補は検証しない（A4-20 は、移す前に検証を受けている）。段階2b を行うかの判断の材料にする。

| # | 内容 | 書く側・読む側 | 確度（出どころ） |
|---|---|---|---|
| 2b-1 | cross の CHD「インタフェース変更サマリ」に「影響リポジトリ」列が無い。それを読む工程11 の AFFECTED_REPOS の追加条件と、SPEC レビューの照合の拠り所が無い | 書く側 CC/skills/xddp-06-design/SKILL.md:126-130。読む側 CC/skills/xddp-common/SKILL.md:138-141、CC/skills/xddp-common/reviewer-checklists/SPEC.md:31 | A2 の監査者 ✅（LLM が別の表から読み替える可能性は 🔶）。A4-20 として V3 が検証: 確認・🔶・🔵 |
| 2b-2 | 設定テンプレートの `SPECOUT_DIAGRAM_LEVEL` の説明（6.1〜6.9）が、module-documentation.md の Section 4 の生成範囲（4.1〜4.7）と合わない | 書く側 CC/skills/xddp-01-init/templates/xddp.config.md:341-343。読む側 CC/skills/xddp-04-specout/module-documentation.md「Section 4（モジュール内ダイアグラム）の生成範囲」 | V3 ✅（検証の途中で見つけたもの） |

A2 の監査者は、工程7〜11 の CHD の「新規追加／変更／削除」の読み方は、06-design の「変更種別」列と矛盾しないことも報告している（食い違いなし）。

---

## 7. 抜き取り確認の結果

検証者が、監査者が「食い違いなし」とした約束から、監査者の検索語を使わずに検索し直した結果。

| 領域 | 約束（一覧の #） | 検証者が使った検索 | 漏れ | 漏れの内容と食い違い | 検証者 |
|---|---|---|---|---|---|
| A1 | #17 列挙（`list_places`） | `constraints\.md\|code-knowledge/\*\*\|knowledge/code-knowledge`（ClaudeCode・tools/harness）と `list_places\|applicable_places` | なし | — | V1 |
| A1 | #11 `place` の入力 JSON | `knowledge_place\.py\b`（ClaudeCode・tools）と `"targets"\|"fallback"` | なし | — | V1 |
| A2 | #1 progress.md の先行更新セクション | `先行更新\|先行 upsert\|PREUPDATED\|preupdated`（ClaudeCode・tools） | なし | — | V1 |
| A2 | #8 CRS ナビゲーションと写し | `/crs/\|crs/CRS\|"crs"` と CRS の元のパス | なし | — | V1 |
| A2 | #12 用語集 | `glossary\.md\|## 用語集` と `_glossary_term_count` の見出し | なし | — | V1 |
| A3 | #1・#16 Layer 1・Layer 2 のパス | `知見ログ\|LESSONS_FILE\|LL-\{\|LL-[0-9N]` と `lessons`（CC 全体） | **あり** | #16 の書く側の一覧に `promote.py:1081-1097 append_breaking_warning`（Layer 2 に書く）が無い。時期の表には出ている。**食い違いは無い**（マーカーは `LL_ENTRY_RE` に当たらない） | V2 |
| A3 | #22・#23・#24 「気づき・提案メモ」の見出しと対象ファイル | `^#{1,6} .*(気づき\|提案メモ)`（CC 全体）と、全 agent での `気づき\|提案` | なし | — | V2 |
| A3 | #29 「対応方針」の語彙 | `今回対応\|次回CR\|"保留"`（templates を除く） | なし | — | V2 |
| A4 | #37 module-catalog のパス | `CATALOG_FILE\s*[=:]\|catalog\.md\|--module-catalog` と `MODULE_CATALOG\|module_catalog` | **あり** | 読む側の一覧に、04-specout/SKILL.md:257・CC/agents/xddp-specout-prelim-agent.md:32・CC/skills/xddp-survey/SKILL.md:213・CC/agents/xddp-survey-agent.md:59 が無い。どれもパスは一致し、**食い違いは無い** | V3 |
| A4 | #41 glossary のパス | `glossary\.md\|GLOSSARY\|用語集` と `KNOW_DIR` の定義 | なし | — | V3 |
| A5 | #31 RULEBOOK_CONTEXT の読み込み方 | `Steering Context`・`RULEBOOK`・`INCLUDE_CROSS` | **あり（軽い）** | CC/skills/xddp-07-code/SKILL.md:111（説明の文）・CC/skills/xddp-templates/xddp.skill-template.md:35,44（開発用のひな形）が一覧に無い。**食い違いは無い** | V3 |
| A5 | #3 cross ファイルのパス | `rulebook-cross\|cross/project-rulebook\|rulebook_cross\|cross_rb`・`CROSS_RULEBOOK_CONTEXT` | **あり** | CC/skills/xddp-fill-rulebook/SKILL.md:12,52,62・CC/skills/xddp-01-init/SKILL.md:268・promote.py:534 が一覧に無い。パスは一致。promote.py:534 の条件は A5-24 と同じ型で、**新しい食い違いは無い** | V3 |
| A5 | #34 verifier が使う禁止事項の節番号 | `禁止事項\|Section 5\|Section 6\|§5\|§6`（各 agent） | なし | — | V3 |

**人の判断（プラン 3.2.3）:** 漏れがあった A3・A4・A5 の監査をやり直すか → **未決（10. の 1.）**

---

## 8. 段階3 の割り当て

### 8.1 段階1 の指摘

段階1 の指摘は fbf3956 が対象。監査の対象リビジョン ecb54c4 の `ClaudeCode/`・`tools/` は fbf3956 と同一なので、5件とも解消されずに残っている。

| 段階1 の # | 内容 | 割り当て（案） |
|---|---|---|
| R1 | 予約名と同じ名前のディレクトリの制約が読まれない（約束の食い違い。1.3 にも載せた） | P2 |
| R2 | LL の本文のコードブロックの中の `### LL-NNN：` でエントリを切る | P3 |
| R3 | 短いフェンスで長いフェンスが閉じる | P3 |
| R4 | ワークスペースの外の絶対パスが `not-found` になる（約束の食い違い。1.4 にも載せた） | P2 |
| R5 | `_common_dir` は `posixpath.commonpath` の再実装 | P2 |

### 8.2 修正プランのまとまり（案。人の判断待ち）

プラン 3.3 に従い、同じファイルを直す指摘を1つのプランにまとめる案。**どの指摘を直すか、どのプランにするか、「直さない」とするかは、人が決める**（10. の 3.）。

| 案 | プラン | 主に直すファイル | 割り当てる指摘 |
|---|---|---|---|
| P1 | PLAN-20261103-domain-refs-shared-knowledge（プラン 3.3 のとおり書き換える） | `domain_refs.py`・`promote.py` の `update_ai_index`・01-init の AI_INDEX のひな形・11-specs の先行更新・close C0 の git の照合 | A1-7・A1-8・A2-1・A2-2・A2-4・A2-5・A2-6・A2-7・A2-8・A2-9・A2-11・A4-12・A4-13・A4-15・N1 |
| P2 | 新規（code-knowledge の書く側） | `xddp-close-knowledge-agent`（C3.6）・`xddp-survey-promote-agent`・`xddp-update-knowledge`・`knowledge_place.py`・code-knowledge のテンプレート・`code-knowledge-boundary.md`・`xddp-survey`・`specout_bfs.py`（`confirmed_modules`） | A1-1〜A1-6・A1-9〜A1-17・R1・R4・R5 |
| P3 | 新規（知見ログ・バックログ） | `promote.py` の LL・backlog の部分（`extract-ll`・`promote_lessons_learned`・`append_breaking_warning`・`promote_backlog`）・`collect_insights.py`・close Step B・C・update-knowledge（lesson）・analyst／architect／test-writer の agent・abort・LL と backlog のテンプレート | A3-1〜A3-23・R2・R3・N3 |
| P4 | 新規（最新仕様） | 11-specs の SKILL・`xddp-specs-mod-agent`・`xddp-specs-uc-agent`・`spec_version_delta.py`・close C0-3・survey の (c)・05／06 の latest-specs の参照・設定テンプレート・review | A4-1〜A4-11・A4-14・A4-16〜A4-19・A4-21〜A4-31・N4・N5 |
| P5 | 新規（project-rulebook） | `xddp-fill-rulebook`・`xddp-close-knowledge-agent`（C3.5）・01-init・02-analysis Step B3・close の順序・`promote.py` の rulebook の写し・`load-domain-constraints.md`・rulebook のテンプレート・README | A5-1〜A5-28・N2 |

**まとまりの間で同じファイルを直すもの**（衝突を避ける順序を、各プランで決める必要がある）:
- `promote.py`: P1（`update_ai_index`）・P3（LL・backlog）・P4（C0-3 の取り込みに関わる部分）・P5（rulebook の写し）
- `xddp-close-knowledge-agent`: P2（C3.6）・P5（C3.5）
- `xddp-close/SKILL.md` の Step の順序: P5（A5-1）・P1（A1-8 の時期）

**同じ型の指摘で、まとめて直すかを決めるもの:**
- A3-4／A5-28（`{DOCS}` を丸ごと上書き）
- A3-8／A5-24（`has_cross` の条件）

### 8.3 他のプランを書き換える予定（プラン 3.3）

- **PLAN-20261102-cochange-knowledge・PLAN-20261102-impact-hypotheses:** A1・A2 の指摘を割り当てたすべての修正プランの実装の後に、プラン 3.3 のとおり、再発防止（書く側→読む側のテスト・共有の値の単一定義）を足して書き換え、AI レビューをやり直してから承認・実装に進む。8.2 の案では、対象は P1（PLAN-20261103-domain-refs-shared-knowledge）と P2。割り当てが決まったら、ここにプラン名を書く。
- **PLAN-20260730-specout-recall-crosscheck:** A3 の指摘を割り当てたすべての修正プランの実装の後（割り当てた修正プランが無ければ、A3 の指摘の扱いをこの節に記録した後）に、プラン 3.3 のとおり書き換え、AI レビューをやり直してから承認・実装に進む。8.2 の案では、対象は P3。割り当てが決まったら、ここにプラン名を書く。

---

## 9. 実行の記録

| 項目 | 内容 |
|---|---|
| 対象リビジョン | ecb54c4 |
| 実行日 | 2026-11-03 |
| エージェント | 監査者5体（A2 を先に1体、残りの A1・A3・A4・A5 を並列）と検証者3体（V1: A1・A2・段階1 の R1・R4／V2: A3・A5-1〜A5-14／V3: A4・A5-15〜A5-28）。計8体（プランの「10体未満」の範囲）。すべて `general-purpose`・モデル claude-opus-5-5 |
| A2 の後に手順を直したか | **直した**（人の指示「手順を直して4体を実行」）。直した点: (a) Grep・Glob が無い環境なので、監査者に Bash の読み取りのコマンドを使ってよいと明記し、書き込みを禁じた。(b) 「確認した約束の一覧」の1行を、食い違いの有無を別々に判断できる単位にし、別々に直せる食い違いを別の指摘にする。(c) 書く側・読む側ごとに、見つけた方法（パターンと範囲、または参照元のファイル:行）を書く |
| A2 をやり直したか | **やり直していない**（人の指示は残りの4体の実行。A2 の一覧の粒度は、4. と 1.4 の A2-9 に注記した） |

**プランとの違い:** プラン 3.2.4 は、監査者のツールを Read・Grep・Glob だけとしている。この環境のサブエージェントには Grep・Glob ツールが無かったので、監査者は Bash の読み取りのコマンドで検索した（A2 では指示外、A1・A3・A4・A5 では (a) の指示による）。各 Bash の呼び出しが読み取りだけだったかは、すべては確認していません。A2 については、20回の呼び出しがすべて worktree に `cd` してから始まることを確かめた。監査・検証の後、worktree に変更が無かった（2. の冒頭）。

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
| **計** | **2,092,970** | **362,030** | **1,983,776** | **78,050,250** | **438** | — |

- **集計の仕方:** ツールの呼び出しと所要時間は、ハーネスの通知の値。出力・キャッシュは、各エージェントの記録ファイルの API 応答の `usage` を、メッセージの id ごとに1回だけ数えて合計した。`subagent_tokens` が何を数えているかは確認していません。料金は、キャッシュ読みの単価がほかと違うので出していない。
- **見積もりとの比較:** A2 の後に示した残り4体の見積もりは約100万〜220万（`subagent_tokens` 相当）。実績は 1,072,338 で、見積もりの下限に近かった。
- **メインのセッションの分:** 統合・報告書の執筆・段階1 のレビューに使った分は、上の表に含まない（計測していません）。

---

## 10. 人に決めてほしいこと

1. **抜き取り確認の漏れ**（7.）: A3・A4・A5 で、書く側・読む側の漏れがあった（A3 で1件、A4 で4か所、A5 で2件の約束）。漏れていた書く側・読む側には、どれも食い違いは無かった。これらの領域の監査をやり直すか（プラン 3.2.3）。
2. **段階2b を行うか**（6.。プラン 7. の 2.）。候補は2件。
3. **段階3 の割り当て**（8.2 の案 P1〜P5）。どの指摘を直すか・「直さない」とするか（理由を記録する）・プランのまとまり。
