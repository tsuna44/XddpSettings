# PLAN-20260809-specout-code-knowledge-relay

作成日: 2026-08-09
ステータス: 草案 / **承認待ち** / 承認済み / 実装完了

> 起票元: [PLAN-20260806-specout-phase3-parallel-classification.md](PLAN-20260806-specout-phase3-parallel-classification.md)
> §4.3「スコープ外として記録する既存欠陥 — code-knowledge 参照が成果物へ到達しない」。
> Phase 3（波内 classification の並列化）は本欠陥を是正も悪化もさせない（無条件 no-op のまま等価）ため、
> スコープ外として当該プランから切り出した。詳細な発見根拠は同プラン §4.3 を参照。

---

## 1. 背景・目的

### 1.1 現状（実コード確認済み・PLAN-20260806 Phase 3 Stage 2 実装完了後の状態）

`ClaudeCode/.claude/agents/xddp-specout-agent.md`「### Wave 0 完了後: code-knowledge 参照
（MODE: discovery-setup のみ）」節は、`specout_bfs.py status` の `confirmed_files` から
`confirmed_modules` を推定し、該当モジュールの `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
を読んで `{OUTPUT_DIR}/_observation-memo.md` に「## 既知制約との照合」セクションを生成する機能を持つ。

**この機能は現行の実装では成果物（SPO）へ到達しない。** 根拠は以下の4点（実コード照合済み）:

1. **生成物が削除される:** `MODE: document` の Step 0 が `_observation-memo.md` を
   「前回実行の残骸を引き継がないため」削除する。discovery-setup フェーズで生成しても
   document 開始時に消える。
2. **SPO への転記手順が存在しない:** Step 10 の集約対象は Section 4.1（外部副作用）・4.2・5.6
   （非機能特性）・Section 9 転記に固定されており、「## 既知制約との照合」を読む手順がない。
   さらに Step 10 の後処理で `_observation-memo.md` 自体が削除される。
3. **制約メモの消費者が別コンテキストにある:** `KNOWN_CONSTRAINTS` の利用先として当該節が指定するのは
   「Phase 2 の各ファイル観察時（Step 2・3）」であるが、Phase 2 は `MODE: document` として
   **別 Task で起動される独立コンテキスト**である。したがって in-memory で保持された
   `KNOWN_CONSTRAINTS` は原理的に消費者へ届かない（唯一の受け渡し手段がファイル＝上記1で消える）。
4. **記載位置（副次的根拠）:** 当該節は `init` を実行するブロックよりも**前**に記載されている
   （見出しは「Wave 0 完了後」だが、`init` の実行記述はその後方にある）。新規実行時に記載順どおりに
   実行されると `bfs-state.json` が未作成で `status` が成立しない。ただし姉妹節
   「Wave 0 完了後: モジュールカタログによる BFS 優先度設定」も同様に前方に置かれつつ実処理は
   `commit-wave` 側で行われるため、記載順がそのまま実行順である保証はない。この項目は
   「成立しない可能性がある」という位置づけに留め、上記1〜3（条件によらず成立する）を主たる根拠とする。

**PLAN-20260806 Phase 3 Stage 2 による影響（悪化なし）:** 波ループの実行主体が `xddp-specout-agent`
（`discovery-setup`）から `xddp.04.specout/SKILL.md` へ移設され、`discovery-setup` は `commit-wave`
を実行しなくなった。したがって `confirmed_files` は `discovery-setup` フェーズ終了時点で常に空であり、
`confirmed_modules` も空 → `KNOWN_CONSTRAINTS` も空となり、当該節は**無条件に no-op** となる
（Stage 2 適用前は「稀に空でない場合がある」実装だったのに対し、Stage 2 適用後は「常に空」に固定される。
いずれにせよ成果物へは到達しないため、成果物観点での等価性は保たれる）。

### 1.2 影響（現状で起きていること）

- code-knowledge（`{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`）に蓄積された
  既知の制約・落とし穴が、スペックアウト（工程4a）実行時に**一切参照されない**。
- CRS・SPO のいずれにも「この変更は過去に記録された既知の制約と矛盾していないか」の自動照合結果が
  現れない。人手による目視確認に完全依存している。
- スキル定義上は「実施している」ように読める（`agents/xddp-specout-agent.md` に手順が明記されている）
  ため、レビュー時に見落とされやすい（実装は存在するが到達しない、という最も気づきにくい種類の欠陥）。

### 1.3 目的

`{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md` に蓄積された既知制約が、
スペックアウト完了後の成果物（SPO または discovery-log）に実際に反映される経路を作る。

---

## 2. 変更対象ファイル（草案時点の想定・確定は承認前レビューで見直す）

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/agents/xddp-specout-agent.md` | 修正 | code-knowledge 参照の実行フェーズ・入出力を再設計（§3.1） |
| `ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md` | 修正（要否は§3.1の設計選択に依存） | `MODE: document` 呼び出しへの `DOCS` 受け渡し追加（現状 discovery-setup 呼び出しにのみ渡している） |
| `ClaudeCode/.claude/skills/xddp.04.specout/templates/04_specout-summary-template.md` | 修正 | 「## 既知制約との照合」の転記先セクション新設 |

---

## 3. 変更内容（草案・要検討）

### 3.1 実行フェーズの再設計（最重要・要検討事項）

**制約:** `confirmed_modules` の推定には BFS 完了後の `confirmed_files` が必要である。
`confirmed_files` は現在 `xddp.04.specout/SKILL.md` の波ループ内 `commit-wave` 呼び出し（Bash）が
更新する state にのみ存在し、いずれの Agent（`discovery-setup`・`document`）もこれを直接持たない。
「`discovery-setup` に残したまま SPO 転記だけ足す」案は、`discovery-setup` が `commit-wave` を実行しない
（＝ `confirmed_files` に到達しない）ため成立しない。

**検討すべき選択肢（いずれも一長一短があり、承認前に選定すること）:**

1. **`MODE: document` の Step 0 直後へ移設する。**
   `document` 開始時点では該当 repo の波ループが完了しており `confirmed_files` が確定している
   （`specout_bfs.py status --path ... ` で取得可能）。ただし
   [PLAN-20260806-specout-phase3-parallel-classification.md](PLAN-20260806-specout-phase3-parallel-classification.md)
   §4.3 が指摘する既存の懸念を再検証すること:
   - `xddp.04.specout/SKILL.md` の `MODE: document` pass ブロックに `DOCS:` キーが無い
     （渡しているのは discovery-setup 呼び出しのみ）。エージェントは「`DOCS` が未設定または空の場合は
     このセクションを全てスキップする」と自己規定しているため、追加しない限り no-op が場所を変えて
     再発する。
   - Step 0 直後にメモを生成すると、Step 2 の「ファイルが存在しない場合にヘッダを作成する」条件と、
     Step 10 前処理の「`_observation-memo.md` 不在 ＝ 観察が一切行われなかった」判定の**両方**を
     壊しうる（既存の冪等性シグナルとの衝突）。両判定の再設計要否を検討すること。
2. **SKILL 側（波ループ終了後・document 呼び出し前）で confirmed_modules を算出し、
   `MODE: document` の Task Input として直接渡す。**
   決定的に算出できる集合（confirmed_files → モジュール名への変換）を SKILL 側 Bash 処理または
   軽量スクリプトへ切り出せば、エージェントは「渡された `KNOWN_CONSTRAINTS` を SPO へ書く」だけになり、
   CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」の役割分離にも整合する。
   ただし constraints.md の読み込み・矛盾判定自体は意味判定であり LLM 側に残る。
3. **見送り（no-op を維持し、運用でカバーする）。**
   構造変更のコストに対して効果が見合わない場合の選択肢。この場合は
   `agents/xddp-specout-agent.md` から当該節を削除し、「code-knowledge は人が手動で確認すること」を
   明記する（実装が存在するのに到達しないという状態そのものを解消する）。

**SPO への転記手順の新設（選択肢1・2いずれを選んでも必要）:**
「## 既知制約との照合」を読み SPO の該当セクションへ転記する手順と、転記先セクションの新設が要る
（現行 Step 10 の集約対象は Section 4.1/4.2/5.6/Section 9 に固定されている）。

**メモ不在シグナルの再設計（選択肢1・2いずれを選んでも要検証）:**
Step 2 の「ファイルが存在しない場合にヘッダを作成する」条件と、Step 10 前処理の
「`_observation-memo.md` 不在 ＝ 観察が一切行われなかった」判定は、いずれもファイル不在を
シグナルとして使っている。早い段階でメモを生成する設計に変えるなら両方の再設計が必要になりうる。

### 3.2 ドメイン中立性の確認

`constraints.md` の内容・照合結果の記述形式が特定ドメイン（Web・業務・組み込み）に偏らないよう、
CLAUDE.md「適用ドメインの中立性」チェックリストを実装時に適用すること。

---

## 4. 影響範囲

- **影響するスキル・コマンド:** `/xddp.04.specout`（工程4a）のみ。
- **影響する工程:** 工程4a。既存の確定影響ファイル一覧・discovery-log・SPO 本体の構成には影響しない
  （追加セクションのみ）。
- **後方互換性:** CLAUDE.md「後方互換性ポリシー」により保証しない。本欠陥は現状「到達しない」機能の
  修正であり、既存 CR の成果物には影響を与えない（追加動作のみ）。

---

## 5. 確認項目

- [ ] スキルの同期（`xddp-specout-agent.md`・`xddp.04.specout/SKILL.md`・SPO テンプレートが整合）
- [ ] `constraints.md` を持つ sample-project で、スペックアウト完了後の SPO に「既知制約との照合」が
      実際に現れること（成果物への到達を実地確認する ＝ 本欠陥の直接的な再現・解消確認）
- [ ] `constraints.md` が存在しない・空の repo で従来どおり no-op のままであること（回帰なし）
- [ ] マルチリポジトリで repo ごとに独立して照合されること
- [ ] CLAUDE.md の記述と整合
- [ ] 特定ドメイン（Web・業務・組み込み）への偏りがないか（CLAUDE.md「適用ドメインの中立性」参照）
- [ ] `make test`（refcheck ＋ unittest）が緑
- [ ] `make smoke-full PHASE=04` で挙動確認（code-knowledge を持つシードを用意する必要がある場合は
      その旨を確認項目に明記する）

---

## 6. レビュー

AIレビュー結果: [plans/review/PLAN-20260809-specout-code-knowledge-relay-review.md](review/PLAN-20260809-specout-code-knowledge-relay-review.md)

---

## 7. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
