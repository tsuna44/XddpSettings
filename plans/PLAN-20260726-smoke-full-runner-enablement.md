# PLAN-20260726-smoke-full-runner-enablement

作成日: 2026-07-26
ステータス: **A（0トークン実装）実装完了＋A追補（連鎖ハーベスト）実装完了 / B・C・D（トークン消費・運用）着手中**

> **A追補（2026-07-26・0トークン）:** B 着手時に「§5.1 の `--all --harvest` が実装上シードを起こせない」
> 不整合を発見（工程非連鎖・harvest 成果物破棄）。詳細と是正設計は Section 5.0（追補）を参照。
> `run_harvest_chain`（連鎖ハーベスト）を追加し `make test` 緑（67 unittest・refcheck errors=0）。

> **段階着手（Section 11 備考）:** A（オーケストレーションループ・0トークン）を 2026-07-26 に実装・
> unittest 済み（`make test` 緑）。B/C/D（シード生成・ゴールデン確定・偽失敗率測定）は
> トークンを消費する運用ステップのため未着手。A 実装後に B の試走1件で1起動単価を把握してから
> D のバッチ計画を確定する。

> **位置付け:** 親プラン `plans/PLAN-20260725-p2-test-harness.md`（P2 テストハーネス）の
> **L4/L5 を実走可能にする残作業**を回収する子プラン。親プランが「実装状況」ブロックの
> **L4〜L5（LLM 層・骨格のみ／校正ラン待ち）**として申し送った部分——`smoke_full.py` の
> LLM 起動オーケストレーション（設計自体は親 Section 3.2「実行モデル」。`_invoke_phase` の
> 実起動ループが未有効）——と、Section 3.5 の校正ラン本体（シード・ゴールデン・偽失敗率・
> 予算確定）を対象とする。認証是正（`CLAUDE_CODE_OAUTH_TOKEN`）は
> `plans/PLAN-20260725-smoke-full-api-key-auth.md`（実装完了）で解決済みを前提とする。

---

## 1. 背景・目的

現状 `make smoke-full PHASE=NN` / `make smoke-full-all` / `make smoke-calibrate` は入口こそ
あるが、**LLM を起動せず手前でゲートされて停止する**。事実（2026-07-26 実測）:

- `smoke_full.py:main` は「校正ラン完了後に有効化されます」で `return 4` し、`_invoke_phase`
  を呼ぶ**オーケストレーションループが未実装**（`tools/harness/smoke_full.py` の `main` 末尾）。
- `test-fixtures/scratch-workspace-min/seeds/` は `README.md` のみで**工程別シードが未作成**。
- `test-fixtures/golden/` も `README.md` のみで**ゴールデンが未確定**。
- `tools/harness/smoke_config.md` の `SMOKE_TOKEN_BUDGET: 0.0`（＝未校正・LLM 起動不許可）、
  工程別モデルは全工程「校正待ち」。

**既に済んでいる前提（実装・実測済み）:**
- 前提スパイク（親 3.5 step 0）: `claude -p --output-format json` の `usage`/`total_cost_usd`
  取得・サブエージェント消費の親積算・frontmatter `model:` 注入の有効性を確認済み。
- 認証是正: 隔離 HOME + `CLAUDE_CODE_OAUTH_TOKEN`（優先）/`ANTHROPIC_API_KEY`（フォールバック）
  で `is_error=false`・user-scope スキルのランタイム解決を実測済み（`verify_isolated_auth.sh`）。
- 純ロジック: `BudgetTracker`・`extract_structural_properties`・`compare_to_golden`・
  `resolve_phase`・`_resolve_auth_env` は unittest 済み（0トークン）。

**目的:** 上記の「済んでいる部品」を**実際に結線して L4/L5 を end-to-end で走らせられる状態**に
する。具体的には ① オーケストレーションループ（隔離ステージング → 工程起動 → 予算ガード →
構造アサート → 後片付け）の実装（0トークン・モックで unittest 可能）、② シード生成、
③ ゴールデン確定、④ 偽失敗率測定と工程別モデル・`SMOKE_TOKEN_BUDGET` 確定、を段階的に行う。

**トークン方針（親プラン踏襲）:** ①は 0トークン。②③④は LLM を消費するが、すべて予算ガード
配下・バッチ分割で実施し、消費を本プランの記録節へ追記しながら進める（親 3.5 step 2 の分割方針）。

---

## 2. スコープと非スコープ

### 対象（本プランの成果物）

| 区分 | 成果物 |
|---|---|
| A. 実装（0トークン） | `smoke_full.py` のオーケストレーションループ・隔離ステージング・モデル注入・ランナー分岐（`--all`/`--phase`/`--update-golden`/`--calibrate`）＋ モック unittest |
| B. 運用（トークン） | 工程別シード（`seeds/phaseNN-*/`）を `--all` 生成物から起こし人が最小化 |
| C. 運用（トークン） | ゴールデン（`golden/phaseNN-*.json`）を `--update-golden` → 人 diff 確認で確定 |
| D. 運用（トークン） | 偽失敗率測定 → 工程別モデル確定 → `SMOKE_TOKEN_BUDGET` 確定 → `smoke_config.md` 書き込み |

### 非対象

- **`ClaudeCode/.claude/` 配下（skills / agents）の変更なし。** 本プランは `tools/harness/` と
  `test-fixtures/` のみを扱う（母体エージェント定義は隔離 HOME デプロイ後のコピーにのみ `model:`
  を注入し、リポジトリ側は読み取りのみ＝親 3.2「モデル適用機構」踏襲）。
- 親プランで確定済みの設計（守備レイヤー L1〜L5・トークン戦略・シード母体解決規則）の再設計。
- CI サービス結線・Windows ネイティブ対応（親プラン非対象を踏襲）。
- 後方互換性（CLAUDE.md 後方互換性ポリシー）。

---

## 3. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `tools/harness/smoke_full.py` | 修正 | `main` の exit-4 ゲートを撤去し、オーケストレーションループへ差し替え。隔離ステージング（`stage_workspace`）・モデル注入（`inject_agent_models`）・ランナー（`run_phase`）・CLI フラグ分岐（`--all`／`--phase`／`--harvest`＝ハーベスト(no-assert)／`--update-golden`／`--calibrate`／`--budget`＝予算上限の明示指定／`--json`＝機械可読レポート）・人可読レポートを実装。実効予算（`SMOKE_TOKEN_BUDGET`／`SMOKE_CALIBRATE_BUDGET`／`--budget` がいずれも 0・未指定）が無い通常ランを拒否する新ゲートに置換。あわせて `load_smoke_config` を `SMOKE_CALIBRATE_BUDGET` パース対応へ拡張する（現行は `SMOKE_TOKEN_BUDGET`／`SMOKE_MAX_PHASES` のみ格納し `SMOKE_CALIBRATE_BUDGET` を無視するため、4.4 の実効予算ゲートが config 供給の校正用予算を読めるようにする） |
| `tools/harness/tests/test_smoke_full.py` | 修正 | ステージング・モデル注入・ランナーループ・レポートの純ロジックを、`_invoke_phase` と `subprocess`（setup.sh）をモックした unittest で追加（0トークン） |
| `tools/harness/smoke_config.md` | 修正 | 校正確定値（工程別モデル・`SMOKE_TOKEN_BUDGET`）を書き込み（D 完了後）。校正用予算 `SMOKE_CALIBRATE_BUDGET` 節を追記（**B 着手前に暫定値を置き、D で実測に基づく確定値へ更新**。B の `--all --harvest`／`--phase NN --harvest` はこの値で 4.4 の実効予算ゲートを通過する）。あわせて既存の `SMOKE_TOKEN_BUDGET` 行コメント「0 = 未校正（LLM 起動を許可しない）」を新ゲート（4.4）の実挙動へ整合させる。`SMOKE_TOKEN_BUDGET=0` は「LLM 起動が一律不可」を意味しない——`SMOKE_CALIBRATE_BUDGET`／`--budget` のいずれか>0 なら実効予算ゲート（exit 6）を通過し、harvest／update-golden／calibrate に加え、ゴールデン確定済み工程の通常 assert ランも起動しうる（ゴールデン未確定工程の assert は exit 8 で停止）。是正後の骨子は「0 = `SMOKE_TOKEN_BUDGET` 未校正。ただし `SMOKE_CALIBRATE_BUDGET`／`--budget` があれば exit 6 を通過して起動する（ゴールデン未確定工程の assert は exit 8）」等、exit 6／exit 8 の実挙動に沿った表現とする（運用者の誤読防止） |
| `test-fixtures/scratch-workspace-min/seeds/phaseNN-{single,multi}/` | 追加 | 工程別入口状態スナップショット（B。README のレイアウト定義に従い実体を作成） |
| `test-fixtures/golden/phaseNN-{single,multi}.json` | 追加 | 構造性質ゴールデン（C。README の表現形式に従い実体を作成） |
| `plans/PLAN-20260725-p2-test-harness.md` | 修正 | Section 5「L4/L5」の未チェック項目（モデル適用機構の実測・校正・隔離完走・予算ガード実演・回帰検出）を本プラン完了に合わせて `[x]` へ更新。「実装状況」ブロックの L4〜L5 記述（`_invoke_phase` の実起動ループが「校正ラン待ち」で未有効）に「オーケストレーションループは子プラン PLAN-20260726-smoke-full-runner-enablement で実装」を追記（設計自体は親 Section 3.2「実行モデル」）。詳細な挿入アンカー・実文は本プラン Section 3.1 を参照 |
| `README.md` | 修正 | 「開発時テストハーネス（make）」節に「初回は校正が必要／校正後に `make smoke-full PHASE=NN` が実走」する旨と手順概要を追記（挿入アンカー・実文は本プラン Section 3.1 を参照） |
| `Makefile` | 修正 | ブートストラップ（B）の入口 `smoke-harvest` ターゲットを新設（`$(PY) $(HARNESS)/smoke_full.py $(if $(PHASE),--phase $(PHASE),--all) --harvest`＝`--harvest` を make から起動可能にする）。`.PHONY` へ `smoke-harvest` を追加し、`help` 行にも1行追記。予算は `smoke_config.md` の `SMOKE_CALIBRATE_BUDGET`（config 値）で供給するため `BUDGET=` 透過は追加しない（既存ターゲットと同方針＝4.4 の実効予算ゲート参照）。これにより B が make 経由で起動でき、README（Section 3.1）の運用手順と Makefile 実体が整合する |

**変更不要（確認済み）:** `refcheck.py`・`run_all.py`（L1〜L3、本プラン非関与）・
`ClaudeCode/setup.sh`（隔離 HOME への利用のみ）。
既存の `smoke-full`/`smoke-full-all`/`smoke-calibrate` ターゲット自体は改変不要（ブートストラップ（B）の
予算は `--budget` を `make` 経由で透過させるのではなく `smoke_config.md` の `SMOKE_CALIBRATE_BUDGET`
（config 値）で供給するため、`BUDGET=` 透過を足す必要はない＝4.4 の実効予算ゲート参照）。ただし B の
`--harvest` 起動口が既存ターゲットに無いため、上表の通り `smoke-harvest` ターゲットのみ新設する。

### 3.1. ドキュメント編集の確定（見出しアンカー＋挿入実文）

親プラン Section 3.6 の方式（行番号を使わず**見出し名アンカー＋挿入する実文**で確定。CLAUDE.md
行番号参照禁止に準拠）に倣い、本プランのドキュメント編集を以下で確定する。

**`README.md`**（アンカー: `#### 開発時テストハーネス（make）` 節内、`L4/L5 のゴールデン値・工程別
モデル・トークン予算上限は…有効化されない。` の箇条書きの直後）
- **Before:** 当該節は「L4/L5 のゴールデン値・工程別モデル・トークン予算上限は**校正ラン（plan 3.5）で
  実測確定**するまで有効化されない」とのみ記載し、有効化の手順が無い。
- **After（挿入する実文の骨子）:** 「**初回は校正が必要。** `make smoke-harvest`（＝`--all --harvest`。
  no-assert のハーベストモードで工程別シードを起こす。B）→ `smoke_full.py --phase NN --update-golden`
  でゴールデンを確定（C。update-golden はブートストラップ扱いで校正前でも実行可。専用 make ターゲットは
  持たず raw 起動）→ 偽失敗率測定（`make smoke-calibrate`）で工程別モデルと
  `SMOKE_TOKEN_BUDGET` を確定（D。`smoke_config.md` に書き込み）した後、`make smoke-full PHASE=NN` が
  実走可能になる。予算未供給（`SMOKE_TOKEN_BUDGET`／`SMOKE_CALIBRATE_BUDGET`／`--budget` がいずれも
  未設定）なら exit 6、ゴールデン未確定の工程を assert 実行した場合は exit 8 で停止し、それぞれ校正手順
  （B→C→D）を案内する」旨を追記。

**`plans/PLAN-20260725-p2-test-harness.md`**（アンカー2箇所）
- **アンカー1: `### 実装状況（2026-07-25）` の「L4〜L5（LLM 層・骨格のみ／校正ラン待ち）」ブロック**
  - **Before:** 「実 LLM 起動経路（`_invoke_phase`・隔離HOMEデプロイ・モデル適用）…は校正ラン
    （Section 3.5）で実測確定するまで未有効」と記載。
  - **After（挿入する実文）:** 同ブロックに「**オーケストレーションループ（隔離ステージング→工程起動
    →予算ガード→構造アサート→後片付け）は子プラン `PLAN-20260726-smoke-full-runner-enablement` で
    実装済み**（0トークン・モック unittest 済み。設計は本プラン Section 3.2）。残るシード・ゴールデン・
    工程別モデル・`SMOKE_TOKEN_BUDGET` の確定は同子プランの B/C/D で実施」を追記。
- **アンカー2: `## 5. 確認項目` の「L4/L5（full-run スモーク）」内の未チェック項目**
  - **Before:** 「サブエージェントのモデル適用機構（3.2）が…効くことを確認」「校正ラン（3.5）を実施し…
    偽失敗率とトークンを実測」「基準…を満たすモデルが Sonnet でも得られない工程は『手動検証』へ退避」
    「ゴールデンのブートストラップ順序…」「`make smoke-full PHASE=NN` が隔離 HOME で完走…`~/.claude/`
    を変更しない」「予算ガードが機能する…途中中断・赤報告」「full-run スモークがスキル挙動回帰を検出」
    が `- [ ]`（未チェック）。
  - **After:** 本プランの B/C/D 完了で該当項目を `- [x]` に更新し、実測メモ（実施日・工程・モデル・
    累積コスト）を付す。

---

## 4. 変更内容（A: オーケストレーションループ実装・0トークン）

親プラン Section 3.2「実行モデル」step 1〜5 を実装に落とす。純ロジックは既存関数を再利用し、
新規は「外界に触れるグルー」（ファイル I/O・subprocess）に限定して**モックで unittest 可能**に保つ。

### 4.1. 隔離ステージング `stage_workspace(seed_dir, temp) -> (home, ws)`

親 3.2「隔離コピー時の母体解決規則」（`{temp}/ws` + `{temp}/multi` 固定レイアウト）を組み立てる。

- `{temp}/ws/` ← `seed_dir`（`seeds/phaseNN-single/`）の中身を複製（ワークスペースルート）。
- `{temp}/multi/` ← `multi/svc-a`・`multi/svc-b` の `src/` を同伴コピー（single 版シードの
  `REPOS: svc-a: ../multi/svc-a` を `{temp}/ws` 基準の depth=1 で解決させる）。multi 版シードは
  母体内包のため同伴コピーをスキップ。
- `{temp}/home/` を作成し `ClaudeCode/setup.sh` を `HOME={temp}/home` で実行（`subprocess`）→
  スキル・エージェントを隔離 HOME にデプロイ。実利用者の `~/.claude/` は無改変。
- 戻り値 `(home={temp}/home, ws={temp}/ws)`。

**テスト:** 実 setup.sh は subprocess をモックし、レイアウト（`ws`/`multi`/`home` の生成・
seed との内容一致・multi 同伴の有無が single/multi で切り替わる）をアサート。

### 4.2. モデル注入 `inject_agent_models(home, model_map)`

親 3.2「サブエージェントのモデル適用機構」step 2。`{home}/.claude/agents/*.md` の frontmatter に
`model:` を注入（母体リポジトリの `agents/*.md` は触らない＝隔離コピーのみ）。工程全体を単一
モデルで回す場合は `--model` 継承で足りるため注入は空 map で no-op。

**テスト:** 一時 agents コピーへ注入し、frontmatter に `model:` 行が入る／既存キーを壊さない／
リポジトリ側パスを引数に取らない（home 配下のみ書く）ことをアサート。

### 4.3. 工程ランナー `run_phase(phase, variant, model, budget, golden_dir, mode) -> dict`

`variant` は `"single"`／`"multi"`（既定 `"single"`）。04/11 のように multi 版シードを持つ工程を
multi で起動するために必要（`resolve_phase(phase, multi)`・`stage_workspace` の母体同伴分岐が variant を要する）。

1. `resolve_phase(phase, multi=(variant=="multi"))` でシード名解決（`seeds/phaseNN-{variant}/`）→
   `stage_workspace(seed_dir, temp)`（single のみ母体同伴コピー・4.1）→ `inject_agent_models`。
2. `budget.can_start(estimated)` が False なら起動せず「残予算不足で中断」を記録して返す。
3. `_invoke_phase(phase, ws, model, home, auth_env)` を呼び、応答 JSON を得る。
4. `budget.add_response(resp)`（超過なら `BudgetExceeded` を送出＝以降中断）。
5. 生成成果物ディレクトリから `extract_structural_properties` → `normalize_properties`。
6. `mode`:
   - `harvest`（`--harvest`。B のブートストラップ専用）: 工程を起動して**成果物を生成するのみ**。
     `compare_to_golden` もゴールデン書き出しも行わない（ゴールデン未確定でも exit 8 にならない＝
     予算ゲートの `SMOKE_CALIBRATE_BUDGET` バイパスに**対称なゴールデンゲートのバイパス**）。シードの
     ハーベストと母体解決の立ち上がり確認（specout が `mod_a2.py` へ到達する等）に用いる。
   - `assert`（既定・**校正後の通常ラン**）: 対象ゴールデン（`golden/phaseNN-*.json`）が**未確定
     （ファイル不在）なら `compare_to_golden` を行わず「当該工程のゴールデンが未確定。確定シードに対し
     `--update-golden`（C）で先に確定せよ（B のハーベストは `--harvest` を使いこのゲート対象外）」と案内して
     停止（exit 8）**——信頼できない赤（偽失敗）を作らない。ゴールデンがあれば
     `compare_to_golden(actual, golden)` → violations を記録。
   - `update-golden`: 構造性質を `golden/phaseNN-*.json` に書き出し（diff は人が確認）。校正前でも実行可。
   - `calibrate`: golden と照合して「偽失敗（正しいツリーが赤）」有無・トークンを記録（書き込まない）。
7. `finally` で temp を破棄（`shutil.rmtree`）。

**成果物ディレクトリの特定:** 工程 NN が書き出す成果物パス（`{CR_PATH}/NN_*/`・`latest-specs/` 等）を
`smoke_config.md` の工程別に対応付ける（正準表を config 側に置く）。

### 4.4. `main` のループ差し替え（exit-4 ゲート撤去）

現行の「校正ラン完了後に有効化されます（return 4）」を撤去し、以下に置換:

- **共通事前チェック（順序維持）:** `--phase` 検証(exit 2) → `claude` 導入(exit 3) → 認証(exit 5)。
- **実効予算ゲート（新）:** 通常ラン（`--phase`/`--all`、`--update-golden`/`--calibrate` を伴わない）は
  **実効予算**——`SMOKE_TOKEN_BUDGET`（校正確定値）／`SMOKE_CALIBRATE_BUDGET`（校正用・config 値）／
  CLI `--budget`（明示指定）のいずれか > 0——を要求する（LLM を予算上限なしに起動しないための不変条件）。
  いずれも 0・未指定なら「予算未供給。校正済みなら `SMOKE_TOKEN_BUDGET` を、ブートストラップ（B）なら
  `SMOKE_CALIBRATE_BUDGET` か `--budget` を与えよ」と案内して停止（新 exit コード=6）。これが旧 exit 4 の
  役割を継ぐ。**B（5.1）の `--all --harvest`／`--phase NN --harvest`（ハーベスト）は
  `SMOKE_CALIBRATE_BUDGET`（config）で本ゲートを通過し、校正用予算の上限内でハーベストできる（鶏卵回避）。**
- **`--all`:** init→close を順に `run_phase(phase, variant="single", ...)`（既定 `mode="assert"`。B は下記
  `--harvest` を併用）。cross 生成が絡む 04/11 は single に加えて `variant="multi"` でも `run_phase` を起動する
  （multi 版シードの照合・ハーベスト対象。親 3.2／Section 5.1）。init は前工程シード非依存でワークスペース
  自体を生成するため、`--all` 先頭で「空ワークスペース→init 起動」の特別扱いにする（親 3.2「init は
  `--all` 専用」）。
- **`--phase NN`:** 単一工程を `run_phase`（既定 `mode="assert"`）。
- **`--harvest`:** `run_phase(mode="harvest")`。B（5.1）のシードハーベスト・立ち上がり確認専用
  （no-assert・ゴールデン書き込みなし＝ゴールデン未確定でも exit 8 にならない）。`--all`/`--phase` と併用し、
  予算は `SMOKE_CALIBRATE_BUDGET`（未確定なら CLI `--budget` 必須）でガード。これが 5.2「B を飛ばして C を
  実行しない」順序と exit 8（assert のゴールデンゲート）の循環を断つ。
- **`--update-golden`:** `run_phase(mode="update-golden")`。校正前でも実行可（ブートストラップ）。
  予算は `SMOKE_CALIBRATE_BUDGET`（未確定なら CLI `--budget` 必須）でガード。
- **`--calibrate`:** 指定工程×モデルを N 回 `run_phase(mode="calibrate")`。偽失敗率・トークンを集計。
  `--budget`/`SMOKE_CALIBRATE_BUDGET` でガードし、上限到達で中断・赤報告。
- **レポート:** 実行工程・累積コスト・違反一覧・偽失敗率（校正時）を JSON（`--json`）と人可読で出力。
  中断時は「どこまで実行し累積いくら消費したか」を残す（親 3.4 可観測性）。

**テスト:** `_invoke_phase` をモック応答（`usage`/`total_cost_usd`/成果物ツリーを temp に用意）へ
差し替え、①実効予算ゲートが実効予算ゼロの通常ランを止める ②`--all` が順に工程を回す ③予算超過で中断・非0 exit
④`--update-golden` がゴールデン JSON を書く ⑤`--calibrate` が偽失敗をカウントする ⑥`--harvest` が assert・
ゴールデン書き込みをせず成果物のみ生成する（ゴールデン未確定でも exit 8 にならない）、を 0トークンで検証。

### 4.5. 新設 exit コード一覧（回帰防止のため固定）

| exit | 意味 |
|---|---|
| 0 | 成功（全工程緑） |
| 1 | 構造アサート違反（赤） |
| 2 | 未定義 PHASE |
| 3 | `claude` 未導入 |
| 5 | 認証環境変数未設定 |
| 6 | 実効予算なし（`SMOKE_TOKEN_BUDGET`／`SMOKE_CALIBRATE_BUDGET`／`--budget` がいずれも 0・未指定）で通常ラン要求 |
| 7 | 予算超過による中断 |
| 8 | assert 要求だが対象ゴールデン未確定（`--update-golden` で先に確定が必要） |
| 9 | スキル起動失敗（`is_error`／非0終了／セッション上限等）。ゴールデンは書き込まず中断 |

（旧 exit 4「校正完了後に有効化」は撤去。`test_smoke_full.py` で exit コード対応を固定する。）

---

## 5. 変更内容（B/C/D: 運用ステップ・トークン消費・順序固定）

親プラン Section 3.5 の順序を厳守する（鶏卵回避）。**各ステップ後に累積コストを本プラン
「9. 実測記録」へ追記**し、5時間枠の残量を確認しながらバッチ分割で進める。

### 5.0. A追補：連鎖ハーベストの追加（2026-07-26・0トークン・不整合是正）

**発見した不整合（事実）:** B 着手時、当初 A 実装の `--all --harvest` は §5.1 が想定する
「init→close を通してシードを起こす」動作を満たさないと判明した。根拠は `smoke_full.py`（追補前）の
2点:
1. **工程非連鎖:** `--all` は `_build_tasks` で工程を独立タスク列に展開し、`run_phase` が毎回
   新規 temp を作り `seeds/phaseNN-single/` からステージする。前工程の成果物を次工程へ渡さない。
   fresh リポジトリでは seed 未存在 → `stage_workspace` が空 ws を作るため、02〜close は空ワークスペース
   上で起動してしまう。
2. **成果物破棄:** `run_phase` は `finally` で temp を破棄し、harvest 分岐は成果物を永続化しない。
   人がシードを切り出す元が残らない。

**是正設計（実装済み）:** `--all --harvest` 専用の連鎖オーケストレーション `run_harvest_chain` を追加。
`run_phase`（工程独立・破棄）とは別経路で、以下を行う（single チェーン先行・multi は後続バッチ）:
- 永続ステージング（`{temp}/ws` + 同伴 `multi/` 母体 + `home`＝setup.sh 1回）を1つ作り、
  `01→02→…→close` を**同じ ws 上で順に起動**（前工程成果物が次工程入力）。
- 起点 ws に `single/xddp.config.md`（`REPOS: svc-a: ../multi/svc-a`）を配置。init は既存 config を
  尊重する（`xddp.01.init` Step 4「if not exists」）ため、母体解決の効いた CR を新規作成できる。
- 各工程を起動する**直前に** ws を `seeds/phase{NN}-single/` へスナップショット（工程01は seed 無し）。
  スナップショットは ws のみ（母体 `multi/`・`home` は含めない）。
- 予算は既存 `BudgetTracker` で共有ガード。超過は `BudgetExceeded`→exit 7。生成物は「生」シードで
  §5.1 の通り人が最小化して確定する。
- CLI: `--harvest-out DIR`（seed 出力先。既定 `seeds/`）を追加。`--phase NN --harvest`（単一工程・
  seed 既存前提の立ち上がり確認）は現状のまま `run_phase` 経路で残す。
- テスト（0トークン）: `TestRunHarvestChain`（連鎖が同一 ws を使い回す／工程01は seed 無し・以降は
  起動前スナップショット＝入口状態／母体・home 非混入／予算超過 raise／予算不足 skip）＋
  `test_all_harvest_routes_to_chain`（main 結線）。

**この追補は §4.3/§4.4/§5.1 を実装実態に合わせて更新するもの**であり、`tools/harness/` のみ・
`ClaudeCode/.claude/` 無改変（承認ゲート対象外）・0トークン。

**追補2（2026-07-26・単価トライアルで発覚した `_invoke_phase` の空振り是正）:** 上記連鎖ハーベストの
実トークン・トライアル（`--budget 0.50`）で init→04 が完走したが、**生成 seed が `xddp.config.md`
のみ＝成果物ゼロ**と判明。原因は `_invoke_phase` の3欠陥（§7 リスク表「実スラッシュコマンド名」が
顕在化）:
1. **コマンド名誤り:** `/xddp.{phase}`（`/xddp.02`）を渡していたが実在は `/xddp.02.analysis` 等。
2. **引数欠落:** init に CR番号・タイトル未指定（→対話質問で停止・生成なし）。他工程も CR 未指定。
3. **権限バイパス欠落:** headless で Write が通らない（`--dangerously-skip-permissions` 未指定）。

是正: 正準表 `PHASE_COMMANDS`（工程→実コマンド名）＋ `HARVEST_CR`/`HARVEST_TITLE` を追加し、
`_phase_command(phase, cr, title)` で引数込みコマンドを構築。`_invoke_phase` に
`--dangerously-skip-permissions` と、母体参照のための `--add-dir {temp}/multi`（存在時）を追加。
テスト: `TestPhaseCommand`・`TestInvokePhaseCommand`（全工程が 3 セグメント `/xddp.NN.name` を渡す・
権限バイパス付与・母体 add-dir）。**この時点でトライアルの $0.47 を消費（発見の対価）。**

**追補2b（同日・再トライアルの診断で発覚した argv 飲み込み）:** 上記是正後の init 単独再トライアル
（`--harvest-debug` で生レスポンス捕捉）で全工程が `_returncode=1`・
`"Input must be provided ... as a prompt argument when using --print"` を返し、依然成果物ゼロ・
コスト $0 と判明。原因は **`--add-dir <directories...>` が可変長引数**で、直後に置いたプロンプト
（`/xddp.01.init ...`）まで「ディレクトリ」として飲み込み、`-p` のプロンプトが消えていたこと。
是正: `--add-dir <multi>` の後に必ず別オプション（`--dangerously-skip-permissions`）を挟んでから
プロンプトを最後の位置引数に置く（`TestInvokePhaseCommand.test_adds_multi_dir_when_present` で
「add-dir 値の直後は option・prompt は末尾」を固定）。診断のため `_invoke_phase` は `_returncode`/
`_stderr` を resp へ格納し、`run_harvest_chain` に `--harvest-debug DIR`（各工程の生レスポンス保存）を
追加した。

**追補2c（同日・init 実起動成功の確認と堅牢化）:** 是正後の再々トライアルで init が実起動成功
（`_returncode=0`・`is_error=false`・24 turns・`total_cost_usd=$0.6734`）し、`xddp/CR-2026-970/` 一式・
`REQ`・`progress.md`・`latest-specs`・`baseline_docs`・`project-rulebook.md` を生成、既存 config を尊重
（母体解決の起点が有効）と実地確認。**ハーネスの LLM 起動経路は機能する。** ただし `--budget 0.15`（低）で
init 成功直後の `add_response` が超過→temp 破棄で成果物をスナップショット前に喪失した。堅牢化として
`run_harvest_chain` を「工程出力を**予算計上の前に**次工程シードへスナップショット」する順序に変更
（超過しても生成済み成果物を失わない）。**実コスト所見: init 単独で約 $0.67／24 turns（sonnet）。
全 single チェーンは相応の subscription 使用量になるため、ハーベストは `--budget` を十分大きく
（例 $15）与える。** `make test` 緑（74 unittest・errors=0）。

### 5.1. B: シード生成（`--all` からハーベスト）

- 空ワークスペースに対し `smoke_full.py --all --harvest`（**連鎖ハーベスト＝Section 5.0 の
  `run_harvest_chain`**。no-assert・ゴールデン未確定でも exit 8 で止まらない）で init→close を1つの
  ws で連鎖起動し、各工程入口状態を `seeds/phaseNN-single/` へ切り出す。**この時点では
  `SMOKE_TOKEN_BUDGET==0`（未校正）だが、`smoke_config.md` に先立って置いた `SMOKE_CALIBRATE_BUDGET`
  の暫定値（または CLI `--budget`）が 4.4 の実効予算ゲートを通し、その上限内で起動する**（校正用予算節は
  成果物 D で実測確定値へ更新するが、B 着手前に暫定値を置く）。
- 各工程の**入口状態**（前工程まで完了した成果物・progress.md・状態ファイル）を
  `seeds/phaseNN-{single,multi}/` として切り出す。**人が最小化**（不要な散文・重複を削り
  UR1本・SP1本の極小構成に）して確定。
- multi 版は cross 生成が絡む 04/11 のみ（親 3.2）。
- 確定条件: 各シードから `--phase NN --harvest`（同じく `SMOKE_CALIBRATE_BUDGET` 下・no-assert で起動）を
  実行して当該工程が正常に立ち上がる（specout は `mod_a2.py` へ到達する＝母体解決が効く）ことを確認。

### 5.2. C: ゴールデン確定

- 確定シードに対し各工程を1回 `--phase NN --update-golden` で起動 → 構造性質を収集。
- **人が diff を確認**して `golden/phaseNN-*.json` を確定・コミット（README の表現形式に従う）。
- B を飛ばして C を実行しない（シードが無いと起動できない）。

### 5.3. D: 偽失敗率測定・モデル/予算確定

> **【実施結果・2026-07-26】本節の当初設計（N=20〜30 × 2モデルの厳密校正）は実行不能と判明し、
> 「軽量 advisory」へ再設計した。確定内容は §9 の「D 再設計・確定」を参照（Sonnet 単一・
> `SMOKE_TOKEN_BUDGET`=30・phaseClose は手動退避）。以下の当初設計は経緯として残す。**

- 確定ゴールデンに対し各工程を Haiku/Sonnet で **N 回** `--calibrate` 起動（親 3.5 step 2）。
  - N は rule of three: 上側95%≤15%→**N=20**、cross・SPカバレッジ等の重要工程は ≤10%→**N=30**。
  - **採用は「N 回すべて緑（0 失敗）」を必須**。1回でも偽失敗が出たモデルはその工程で不採用。
- 各工程の基準を満たす**最安モデル**を採用（単純=Haiku、複雑=Sonnet）。Sonnet でも満たせない
  工程は「L4/L5 自動対象外＝手動検証」に退避（信頼できない緑/赤を作らない）。
- `SMOKE_TOKEN_BUDGET` ＝ 採用モデル実測 `total_cost_usd` × 安全係数（例 1.5）。全通し＝各工程和。
- 確定値を `smoke_config.md` に書き込み、測定表（工程×モデル×N・トークン）を「9. 実測記録」へ残す。
- **校正総コスト概算:** N(20〜30) × 約10工程 × 2モデル ＝ 約400〜600 起動。**必ずバッチ分割**
  （工程単位・モデル単位）し、まず単純工程1件を Haiku/Sonnet で試走して1起動単価を把握してから
  全体所要を見積もり、バッチ計画を確定する。

### 5.4. 有効化

- D 完了で `SMOKE_TOKEN_BUDGET > 0`（校正確定値）となり、4.4 の実効予算ゲート（exit 6）を
  校正確定値で通過して `make smoke-full PHASE=NN` が実走可能になる。
- **【実施済み・2026-07-26】`SMOKE_TOKEN_BUDGET`=30（C 実測確定）で有効化。`make smoke-full PHASE=NN`
  （NN∈02〜11・ゴールデン確定済み）が実走可能。close は advisory 対象外（golden 未確定＝exit 8 で
  手動検証へ誘導）。**

---

## 6. 影響範囲

- **影響するスキル・コマンド:** なし（`ClaudeCode/.claude/` 無改変。母体エージェント定義は隔離
  コピーにのみ `model:` 注入）。
- **影響する工程:** なし（開発時メタツール。XDDP プロセス実行時に介在しない。full-run は工程を
  「テスト対象」として隔離 HOME で起動するのみで本番ワークスペースに触れない）。
- **デプロイ（setup.sh）:** 影響なし（`tools/harness/`・`test-fixtures/`・`Makefile` はいずれもデプロイ
  対象外）。`Makefile` への `smoke-harvest` ターゲット追加は既存ターゲット（`smoke-full`/`smoke-full-all`/
  `smoke-calibrate`）を改変しない純増のため、既存の make 呼び出し・`make test`（L1〜L3）に影響しない。
- **トークン/コスト:** A は 0トークン。B/C/D は消費するが予算ガード＋バッチ分割で上限を構造的に
  キャップ。`CLAUDE_CODE_OAUTH_TOKEN` 利用時は Pro/Max サブスク枠消費で追加課金なし（公式明言では
  ない妥当推論＝PLAN-20260725-smoke-full-api-key-auth 留意）。
- **後方互換性:** 考慮不要。exit 4 撤去・exit 6/7 追加は開発時ツールの内部仕様変更で既存フロー不変。
- **ドメイン中立性:** ハーネスは言語・ドメイン非依存の構造検証のみ。シード母体もドメイン中立な
  最小合成コード（`mod_a.py` 等）を踏襲。

---

## 7. リスクと未検証仮定

| 項目 | リスク | 緩和 |
|---|---|---|
| 実スラッシュコマンド名 | `_invoke_phase` の `/xddp.{phase}` が実コマンド名と一致するか未確定（`close` 等は `/xddp.close`、番号工程は `/xddp.NN.*`） | **【2026-07-26 顕在化・是正済み】** 単価トライアルで空振り（成果物ゼロ）を検出。正準表 `PHASE_COMMANDS`（工程→`/xddp.NN.name`）＋引数（CR番号・init はタイトル）＋`--dangerously-skip-permissions`＋母体 `--add-dir` を `_invoke_phase` に実装。Section 5.0 追補2 参照。次の再トライアルで実起動を確認 |
| 成果物パスの工程対応 | 各工程が書く成果物ディレクトリの特定を誤ると構造アサートが空振り | config 側に工程→成果物パスの正準表を置き、B 生成物で実パスを確認して確定 |
| `--all` の init 特別扱い | init は空ワークスペースから起動するため他工程と起動形が異なる | `--all` 先頭で分岐（親 3.2「init は `--all` 専用」）。unittest でモック検証 |
| 偽失敗率が Sonnet でも高い工程 | 自動化不能な工程が出る | D で「手動検証へ退避」を明示的に許容（信頼できないシグナルを作らない） |

---

## 8. 確認項目

**A（実装・0トークン）** — 2026-07-26 実装完了（`make test` 緑・61 unittest／refcheck errors=0）
- [x] `make test` が引き続き緑（新規 unittest 追加後も L1〜L3 に regression なし）— **errors=0・warnings=10（baseline と同一）・`tools/harness/tests` 61件 OK**
- [x] `stage_workspace` が `{temp}/ws`+`{temp}/multi`+`{temp}/home` を組み立て、single は母体同伴・
      multi は非同伴になる（subprocess=setup.sh をモックして検証）— **`TestStageWorkspace`（single 母体同伴／multi 非同伴／missing seed で空 ws）**
- [x] `inject_agent_models` が隔離 HOME 側 agents のみに `model:` を注入し、リポジトリ `agents/*.md` を
      変更しない — **`TestInjectAgentModels`（注入＋既存キー保持／既存 model 置換／空 map は no-op）**
- [x] `run_phase` が予算超過で `BudgetExceeded`→中断・非0 exit（`_invoke_phase` モックで実演）— **`test_budget_exceeded_raises`（run_phase）＋ `test_budget_exceeded_returns_7`（main exit 7）**
- [x] `main` の実効予算ゲート（exit 6）が実効予算ゼロの通常ランを止め、`SMOKE_CALIBRATE_BUDGET`／`--budget` 供給時の `--all --harvest`／`--phase NN --harvest`（ブートストラップ）・`--update-golden`/`--calibrate` は通す — **`test_no_budget_returns_6`／`test_calibrate_budget_passes_gate_for_harvest`／`test_cli_budget_passes_gate`＋`TestEffectiveBudget`**
- [x] exit コード表（0/1/2/3/5/6/7/8）が unittest で固定される（旧 exit 4 が消えたことを含む。exit 8＝ゴールデン未確定 assert）— **`TestMainExitCodes`（`test_no_exit_4_anymore` 含む）。exit 2/5 は CLI 実機でも確認**
- [x] `run_phase(mode=assert)` が対象ゴールデン不在時に exit 8 で停止し `compare_to_golden` を呼ばない（偽赤を作らない）ことを `_invoke_phase` モックで検証 — **`test_assert_golden_missing_stops_without_invoking`（compare 未呼出・invoke 未起動）＋ `test_golden_missing_returns_8`**
- [x] `run_phase(mode=harvest)` がゴールデン照合も書き込みもせず成果物のみ生成する（ゴールデン未確定でも exit 8 にならない＝B のブートストラップ経路）ことをモックで検証 — **`test_harvest_generates_only_no_golden`**
- [x] `run_phase(phase, variant="multi", ...)` が `seeds/phaseNN-multi/` を解決し、`--all` が 04/11 を single＋multi の両 variant で起動する（single は母体同伴・multi は非同伴）ことをモックで検証 — **`test_multi_variant_resolves_multi_seed`＋`TestBuildTasks.test_all_includes_init_and_multi`**
- [x] `load_smoke_config` が `SMOKE_CALIBRATE_BUDGET` をパースし cfg に格納する（未設定時は 0 相当）ことを unittest で検証 — **`test_reads_calibrate_budget`／`test_calibrate_budget_defaults_absent`。あわせて行末インラインコメント除去の潜在バグを是正（`test_strips_inline_comment`）**

**B/C/D（運用・トークン）**
- [ ] `make smoke-harvest`（＝`--all --harvest`。no-assert）で init→close が通り、工程別シードをハーベストできる（人が最小化して確定）
- [ ] 各シードから `--phase NN --harvest` が起動し、single specout が `multi/svc-a/src/mod_a2.py` へ到達する
      （母体解決規則が実際に効く＝親 3.2）
- [ ] ゴールデン確定順序（B→C）が守られ、鶏卵問題が起きない
- [ ] 偽失敗率を工程×モデルで実測し、N（20/30・0失敗必須）で工程別モデルを確定
- [ ] Sonnet でも基準未達の工程を「手動検証」へ退避できることを確認
- [ ] `SMOKE_TOKEN_BUDGET`・工程別モデルを `smoke_config.md` に書き込み、測定表を「9」に記録
- [ ] `make smoke-full PHASE=NN` が隔離 HOME で完走し、実利用者の `~/.claude/` を無改変であることを確認
- [ ] 予算ガードの end-to-end 実演（上限を意図的に低くすると途中中断・赤）
- [ ] スキル挙動回帰の検出（あるスキルの `apply` 参照/結線を壊すと該当工程が赤になる）を1件確認

**共通**
- [ ] CLAUDE.md・README.md・親プラン Section 5 の記述と整合
- [ ] 特定ドメインへの偏りがないか（CLAUDE.md「適用ドメインの中立性」）

---

## 9. 実測記録（校正の進行に応じて追記）

> B/C/D の各バッチ実施後に「実施日・工程・モデル・起動回数・偽失敗数・トークン/コスト・累積」を
> 追記する。

- **A（0トークン実装）: 2026-07-26 完了。** LLM 起動なし（`_invoke_phase`・`subprocess`＝setup.sh を
  モックした unittest のみ）。`make test` 緑（`tools/harness/tests` 61件 OK・refcheck errors=0）。
  累積コスト $0.00。
- **A追補（連鎖ハーベスト・0トークン）: 2026-07-26 完了。** B 着手時に §5.1 の `--all --harvest` が
  シードを起こせない不整合を発見（工程非連鎖・harvest 破棄）→ `run_harvest_chain` を追加して是正
  （Section 5.0）。LLM 起動なし（`_invoke_phase`・setup.sh をモックした unittest のみ）。`make test`
  緑（`tools/harness/tests` 67件 OK・refcheck errors=0）。累積コスト $0.00。
- **単価トライアル1（2026-07-26・`--budget 0.50`・sonnet）:** init→04 完走・05 で budget_skip。
  工程別 `total_cost_usd`: 01=$0.0459 / 02=$0.1296 / 03=$0.0149 / 04=$0.2842（累積 $0.4745・4工程）。
  **ただし成果物ゼロ（空振り）**——`_invoke_phase` のコマンド名誤り・引数欠落・権限バイパス欠落が原因
  （Section 5.0 追補2 で是正済み）。よってこの単価は「空振り時のコスト」であり、実成果物生成時の単価は
  再トライアルで測り直す。累積 $0.47。
- **全 single チェーン・ハーベスト実走（2026-07-26・`--budget 15`・sonnet）:** 全11工程が
  `is_error=false`・rc=0・subtype=success で完走（累積 約 $4.6・工程別 turns 5〜24）。**しかし
  init 以外は成果物ゼロ**——全 seed が init 出力の同一11ファイルのみ。応答テキストで理由が確定:
  各スキルが前提条件ガードで正しく停止していた（02=REQ がテンプレのまま「実データなし・続行？」/
  04=CRS 不在・progress 工程1が進行中で前提未達 / 06=CRS・DSN 不在で「捏造せず停止」）。
- **【設計レベルの発見】ヘッドレス連鎖ハーベストは XDDP の人間参加型設計と衝突する。** XDDP スキルは
  (1) REQ 本文の記入、(2) progress.md の工程完了マーク、(3) 上流成果物の存在——を前提とし、
  ヘッドレス連鎖では各工程がガードで停止して成果物を生成しない（init のみ空 WS 起動設計で成功）。
  §5.1 の「実スキルをヘッドレス連鎖でシードを起こす」前提が成立しない。累積 約 $5.7。
  **B のシード生成方式を戦略的に再判断する（人手オーサリング / ガード自動充足 / プラン再設計）。**
- **プローブ（2026-07-26・人手作成 phase02 入口 seed・`--phase 02 --harvest`）:** 前提を整えた
  seed（記入済み REQ＋progress 工程1完了＋config）で xddp.02.analysis が**ヘッドレス完走し ANA を生成**
  （`is_error=false`・39 turns・$2.20）。**自動方式は有効**＝前提が整えば工程はヘッドレスで走り成果物を作る。
  ただし応答末尾は**人レビューゲート待ち**（「レビュー完了と入力してください」）で停止。成果物はゲート手前で
  生成済みのため、ハーベスト・smoke assert は成立するが、**連鎖には工程間で harness が progress.md を
  「工程完了」へ前進させる必要**がある（人の承認代行・`xddp_progress.py` で決定的に可能）。
- **【コスト実測所見】AIレビュー込みで約 $2/工程**（init $0.72・analysis $2.20）。
  `DEFAULT_PHASE_EST_USD=0.10`・`SMOKE_CALIBRATE_BUDGET=5.0` は桁違い。特に **D（§5.3）の N=20〜30 ×
  約10工程 × 2モデルは数百ドル相当**となり、規模の再検討が必要。
- **方式決定（2026-07-26）: B の seed は人手オーサリングとする。** プローブで自動方式（ヘッドレス連鎖
  ＋progress前進）も技術的に有効と確認したが、$2/工程（1パス約$20）＋追加実装が必要なのに対し、
  人手オーサリングは 0トークン・確実・追加コード不要。seed は C/D の入力にすぎず、実スキルを実起動して
  構造検証する smoke の価値は不変。作成は Claude が Write（既存 single/multi フィクスチャ＋テンプレート
  を土台に CR-2026-970／`validate()` ストーリーで一貫作成）、人はレビュー・承認のみ（0トークン）。
- **B（人手オーサリング）: single seed 全10本を作成完了（2026-07-26・0トークン）。** `seeds/phase02〜11・
  Close-single/`。CR-2026-970「svc-a入力値の範囲検証（`validate()` 0〜100）」で一貫させ、既存 single-961
  フィクスチャ（CRS/DSN/CHD/TSP）を読替再利用、ANA/SPO/CODING/VERIFY/TRS/latest-specs はテンプレートから
  最小作成。各 seed は前工程分を累積（3→15ファイル）し progress.md を該当工程まで ✅ 前進・次コマンドを設定。
  未置換トークンなし・`make test` 緑。**人のレビュー・承認済み（2026-07-26）。**（multi 版 04/11 は後続バッチ）
- **B 冗長最小化（2026-07-26・0トークン）:** 生成AI視点レビューで seed の冗長を除去。(a) DSN の同一設計
  3回目を参照化（6ファイル）、(b) SPO §7 の既決事項を"推奨"する冗長行を削除（7ファイル）、
  (c) progress.md の「状態凡例」表・「備考」節を削除（各10ファイル・工程進捗/次コマンド/工程11節は保持）。
  XDDP トレーサビリティ反復と cross-seed 累積は意図的なため保持。`make test` 緑。(a)(c) の最小化は
  single-961 スタイルから外れるため、C 実走で「最小構成でも各工程が受理するか」を実地確認する。
- **C 検証（2026-07-26・phase02・`--update-golden`）:** パイプライン成立を確認（rc=0・success・41 turns・
  $2.01・`golden/phase02-single.json` 生成）。**所見①: ゴールデンが `02_analysis/review/` の AI レビュー
  副産物まで拾い脆かった** → `extract_structural_properties` を `review/` サブディレクトリ・
  `.review-brief.md` 除外へ是正（`test_excludes_review_subdir_and_brief`・75 unittest 緑・0トークン）。
  検証用の旧 golden は削除しバッチで一様再生成する。**所見②: 分析器が UR/SR/SP を実行裁量で展開
  （seed の UR1本 → UR-001/002・SR-001〜003 等）→ ID 数が実行ごとに変動し得る＝assert 偽失敗要因。
  D の測定対象。**
- **C バッチ（2026-07-26・全10工程 `--update-golden`）:** 02〜05 は成功しゴールデン確定（`review/` 除外済み・
  レビュー混入なし）。**phase06 の途中でサブスクのセッション利用上限に到達**（応答: 「You've hit your
  session limit · resets 5pm (Asia/Tokyo)」）→ 06 は部分実行・07〜close は即失敗（1 turn・$0）。
  **ハーネス実バグを発見・是正:** 起動失敗（`is_error`）でも run_phase がゴールデンを書いていた
  （07〜close は成果物欠如→ワークスペース全体を誤取得した偽ゴールデン）。`_invoke_failed` を追加し、
  is_error/非0/セッション上限では**ゴールデンを書かず status=invoke_error・exit 9 で中断**する是正
  （run_phase・run_harvest_chain・main／`test_invoke_error_skips_golden`・`test_invoke_error_returns_9`・
  77 unittest 緑）。無効ゴールデン 06〜close は削除。**確定ゴールデン: phase02〜05（4件）。残 06〜close は
  上限リセット（17:00 JST）後に再実行。**
- **【重大制約】サブスクのセッション利用上限。** 1 セッション窓で走れる工程数に上限があり（今回 ~6工程で到達）、
  リセットは 17:00 JST。**D（§5.3 の N=20〜30 × 約10工程 × 2モデル ＝ 数百起動）は本上限により単一窓で
  実行不能。** D は「窓ごとの少数バッチ分割」または「対象工程・N の大幅縮小」で再設計必須（コスト $2/工程
  ＋所見②の偽失敗リスクと合わせて別途詳細設計）。
- **C 継続（2026-07-26 夕・リセット後）:** 06/07/09/10 が成功しゴールデン確定（計 **02〜10 の8件**）。
  **is_error 是正の実証:** phase11（46 turns 後に上限）・phaseClose（即上限）は golden を書かず飛ばされた
  （前回の偽ゴールデン再発なし）。**seed 最小化 (a)(c) の妥当性も実証**——06(design)/07(code)/09(test)/
  10(test-run) が最小化 seed を受理し CHD/VERIFY/TSP/TRS 構造の成果物を生成（レビュー混入なし）。
  残 **phase11・close** は再び上限（リセット 22:20 JST）で未確定。
- **C 完了（2026-07-26 夜）: 全10ゴールデン確定。** phase11 成功（64 turns・$3.85・クリーン）。
  **phaseClose の注意点:** close の成果物 glob が `xddp/CR-*`（CR 全体）のため golden が CR 全成果物
  （109見出し）を丸ごと捕捉し、close の本来の出力（`baseline_docs/` の lessons-learned・AI_INDEX＝CR 外）を
  見ていない。＝**固定シードの写しで close 出力を検証できていない**（「レビュー」は自作 VERIFY 見出しの
  部分一致で AI レビュー副産物ではない）。**phaseClose は D で成果物ターゲット是正 or 手動検証へ退避を判断。**
  02〜11 の 9 工程は良好（主成果物を正しく捕捉・レビュー混入なし・最小化 seed 受理を実証）。
- **C 累積コスト（実測）:** 校正窓 3 回で約 $30〜32（02〜11 の成功分＋上限で無駄になった部分実行分）。
- **D 再設計・確定（2026-07-26・軽量 advisory 採用・0トークン）:** 当初の厳密校正
  （N=20〜30 × 約10工程 × 2モデル）はセッション上限＋$2/工程で実行不能のため、D を **「軽量 advisory」**
  に再定義（`smoke_config.md` 反映済み）:
  - **モデルは Sonnet 単一**（Haiku 校正なし）。
  - **`SMOKE_TOKEN_BUDGET`=30.0 を C 実測から確定**（工程別 $0.44〜$3.85・合計 ~$18.6 × 安全係数1.5 ≒ $28→30）。
  - smoke は **構造 advisory チェック**（違反は人が解釈）。厳密 N 回偽失敗率測定は行わず、任意で後日
    N=2〜3 の再現性確認を窓ごとに少量実施してよい。
  - **phaseClose は advisory 対象外（手動検証）** ＝ golden を削除し assert 時 exit 8 で手動誘導。
  - **確定ゴールデン: phase02〜11 の9件。** `make smoke-full PHASE=NN`（NN∈02〜11）が
    `SMOKE_TOKEN_BUDGET`=30 で実走可能になった（実効予算ゲート exit 6 を確定値で通過）。
- **B/C/D 完了（トークン消費フェーズ完了）。** 残タスクはドキュメント整合（README・親プラン §5）と、
  任意の phaseClose 成果物ターゲット是正・軽量再現性確認。
  **D の規模（§5.3 の N=20〜30 × 約10工程 × 2モデル ＝ 数百ドル相当）は $2/工程の実測を受けて別途再設計する。**

---

## 10. レビュー

AIレビュー結果: [plans/review/PLAN-20260726-smoke-full-runner-enablement-review.md](review/PLAN-20260726-smoke-full-runner-enablement-review.md)

`/xddp.plan-review` で Critical（🔴）・残指摘（🟡/🔵）がゼロになるまで実施予定。

---

## 11. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | tsuna44 |
| 承認日 | 2026-07-26 |
| 備考 | A（0トークン実装）と B/C/D（トークン消費・運用）は段階承認・段階着手可。A 承認・実装後に B の試走1件で1起動単価を把握してから D のバッチ計画を確定する。**A は 2026-07-26 実装完了（`make test` 緑）。B/C/D は運用者がトークン予算を確認のうえ別途着手する** |
