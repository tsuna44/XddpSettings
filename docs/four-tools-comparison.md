# cc-sdd / GitHub Spec Kit / OpenSpec / Spec Workflow MCP / XDDP 5ツール横断比較

作成日: 2026-04-26 / 最終更新: 2026-09-06（各ツールのソースを再精読して全面改訂）

> ファイル名は `four-tools-comparison.md` だが、内容は当初から5ツールを対象としている。
> 名前と内容が一致していないので、リネームするかどうかは別途判断すること。

---

## 0. 今回の改訂で何が変わったか

前版（2026-05-11）から4ヶ月で、比較対象の前提が大きく崩れていた。

| ツール | 前版の記述 | 実際（2026-09-06 時点） | 影響 |
|---|---|---|---|
| GitHub Spec Kit | v0.8.8.dev0 / 5コマンド＋3オプション / 30以上のAIツール | **v1.0.5.dev0** / 7コアコマンド＋3オプション（`converge`・`taskstoissues` 追加）/ **integrations カタログ41件** / **コミュニティ拡張165件・プリセット34件** / bundle 機構 | 「エコシステム最強」の差がさらに拡大。ブラウンフィールド運用モデルも文書化された |
| OpenSpec | v1.3.1 / 11コマンド | **v1.12.0** / core 6＋expanded 6 の12コマンド（`/opsx:update` 追加）/ **対応ツール49件** / **Stores（beta）＝計画専用リポジトリのチーム共有** / ダッシュボード | 「軽量・探索的」だけのツールではなくなった。**マルチリポジトリ計画共有で XDDP の領域に接近** |
| cc-sdd | v3.0 / 17 skills | **v3.0.2**（コミット HEAD は 2026-04-27 で前版時点から進んでいない）/ 17 skills は同じ | 実質変化なし。ただし4ヶ月コミットが止まっている点は評価に織り込むべき |
| Spec Workflow MCP | v2.2.7 | **v2.2.7 のまま**。最終コミット 2026-07-03。README 冒頭に作者の活動休止告知 | **メンテナンスリスクが顕在化**。新規採用の推奨度を下げるべき |
| XDDP | 15工程・9スキル | **11主工程／15詳細ステップ・27スキル・19エージェント**。Python 決定的処理 6,848行＋テスト 6,390行、メタ検証ハーネス（`make test`）、ADR 13件 | 前版の記述はスキル数・工程番号ともに古い |

**結論の先出し:** XDDP の差別化領域は4ヶ月で **3点に絞り込まれた**——(1) シンボル起点の BFS 波及調査（specout）、(2) USDM 3層 ID の機械検査付きトレーサビリティ、(3) Excel 往復。それ以外（ブラウンフィールド対応・マルチリポジトリ・知見蓄積・プロジェクトメモリ）は、他ツールが同等以上の解を出し始めている。

---

## 1. 調査の根拠と限界

| 対象 | 根拠 | 確度 |
|---|---|---|
| 各ツールのバージョン・コマンド体系・ファイル構成 | 各リポジトリを `git fetch` して最新 HEAD を直接読取（cc-sdd `29aee95`／spec-kit `4a7341a9`／OpenSpec `e062b95`／spec-workflow-mcp `d38e82e`） | **高**（一次情報） |
| 各ツールの設計思想 | 各リポジトリの README・philosophy ドキュメント（cc-sdd `docs/guides/why-cc-sdd.md` 等）を直接読取 | **高**（一次情報） |
| XDDP の内部構造 | 本リポジトリのスキル・エージェント・スクリプトを直接読取 | **高**（一次情報） |
| 適性判断・優劣評価（セクション 5〜8） | 上記事実からの論理的推論 | **中**。実プロジェクトでの比較適用データは持っていない |
| トークンコスト・所要時間の定量比較 | **未計測** | — |

**明示しておく限界:** 5ツールを同一の課題に適用した比較実験は行っていない。「どちらが速いか／安いか」の問いには本書は答えられない。答えられるのは「どういう構造になっているか」「その構造から何が導かれるか」まで。

---

## 2. ポジショニング

| ツール | 提供元 | 配布 | 核心思想 | 現在の勢い |
|--------|--------|------|---------|------|
| **cc-sdd v3.0.2** | gotalab（OSS） | `npx cc-sdd@latest` | 仕様＝**部品間の契約**。境界の外を守り、内側は自由にさせる | 4ヶ月コミット停止 |
| **GitHub Spec Kit v1.0.5.dev0** | GitHub（OSS） | `uv tool install specify-cli` | 仕様を実行可能にする。**プラットフォーム化**（拡張・プリセット・バンドル） | 極めて活発（日次リリース） |
| **OpenSpec v1.12.0** | Fission AI（OSS） | `npm i -g @fission-ai/openspec` | **デルタ仕様**。変更差分だけ書けばよいのでブラウンフィールドから始められる | 活発 |
| **Spec Workflow MCP v2.2.7** | pimzino（OSS） | `npx @pimzino/spec-workflow-mcp` | MCP 標準＋ダッシュボード承認 | **活動休止中** |
| **XDDP** | 本リポジトリ | `git clone` + `bash setup.sh` | 人と AI の協働工程管理＋母体調査＋知見蓄積 | 活発（社内単独開発） |

---

## 3. プロセス体系の比較

| 観点 | cc-sdd | Spec Kit | OpenSpec | Spec Workflow MCP | XDDP |
|------|--------|----------|----------|-------------------|------|
| コマンド／工程数 | 17 skills（うち6は内部ディスパッチ） | 7コア＋3オプション（＋拡張が追加） | core 6／expanded +6 | MCP Tools 5種・4フェーズ | **11主工程／15詳細ステップ・27スキル** |
| 人の介入点 | フェーズゲート＋タスク単位の diff レビュー | フェーズゲート | 任意（フェーズロックなし） | ダッシュボード承認ゲート | **各主工程に必須の人レビューゲート** |
| 実装の自動化 | **最高**（実装者／レビュアー／デバッガを自動ディスパッチ、TDD 自律ループ） | 高（`implement` → `converge` 反復） | 高（`apply`） | なし（AI 任せ） | 中（コーダー1回＋静的検証、ループなし） |
| テストの位置 | **実装前**（RED→GREEN をフィーチャーフラグで強制） | タスク内（preset で先行化可） | タスク内 | タスク内 | **実装後**（工程9設計→工程10実行） |
| 対応 AI ツール | 8（Claude Code / Codex が stable、他6は beta） | **41**（integrations カタログ実測） | **49**（supported-tools 一覧実測） | 9 | **1（Claude Code 専用）** |
| マルチリポジトリ | 非対応 | 非対応（monorepo ガイドあり） | **Stores（beta）＝計画専用リポジトリを別立てし複数コードリポジトリで共有** | 非対応 | `REPOS:` ＋ `cross/` 仮想リポジトリ |
| 影響範囲調査 | `kiro-validate-gap`（LLM が Grep/Glob で探索。帳簿・網羅性保証なし） | `analyze`／`converge`（成果物間の整合と実装ギャップ。コード波及追跡ではない） | delta 仕様＋`explore`（LLM 探索） | なし | **specout（BFS 波及調査。機械が候補抽出、LLM は行の意味判定のみ）** |
| トレーサビリティ | 境界契約（`_Boundary:_`／`_Depends:_`） | FR-xxx／SC-xxx の ID 付与（機械検査なし） | ADDED/MODIFIED/REMOVED デルタ | タスク単位 | **UR/SR/SP 3層 ID・CHD 一対一・`artifact_lint` で L1〜L13 機械検査** |
| 拡張機構 | `settings/templates` `settings/rules` 編集 | **extension / preset / bundle ＋カタログ配布** | **カスタムスキーマ（`openspec schema fork`）＋コミュニティスキーマ** | なし | `xddp.config.md` の設定キーのみ（新工程追加は fork） |
| 知見蓄積 | `## Implementation Notes`（後続タスクに注入） | なし（標準機能） | なし | 実装ログ | lessons-learned / improvement-backlog（CR 間） |
| 非エンジニア参画 | なし | なし | ダッシュボード（beta） | **Web ダッシュボード＋VSCode 拡張** | **Excel 往復（USDM 形式）** |

---

## 4. 各ツールの核心（リードエンジニア視点）

### cc-sdd — 「実装ループを工学的に閉じた」唯一のツール

`kiro-impl/SKILL.md` は本比較で最も完成度の高い自律実装の記述だった。評価すべきは自律性そのものではなく、**自律ループを暴走させないための制約設計**にある。

- **構造化ハンドオフの強制:** 実装者の状態は `## Status Report` ブロックの `- STATUS:` フィールドからのみ読む。散文から推測することを明示的に禁止し、パースできなければ再ディスパッチする。LLM 間の受け渡しを「型のある境界」として扱っている。
- **有界化:** レビュー却下は2ラウンドまで→デバッグへ。デバッグは2ラウンドまで→タスクをブロック。最終検証の是正は3ラウンドまで。**すべてのループに上限がある。**
- **コンテキスト汚染の遮断:** デバッグサブエージェントは失敗履歴を渡さず、エラー情報だけを新しいコンテキストで受け取る。「無限リトライループの原因はコンテキスト汚染」という診断が明文化されている。
- **破壊的操作の禁止:** `git add -A` 禁止、`git checkout .`／`git reset --hard` 禁止。ステージングは明示パスのみ。

これはプロンプトエンジニアリングではなく、**分散システムの障害設計**の作法をエージェント間通信に適用したものだ。XDDP の `## Review Loop` が「レビュー結果ファイルに 🔴/🟡 があるか」で判定しているのと比べると、ハンドオフ契約の厳密さに明確な差がある。

**弱点:** 4ヶ月コミットが止まっている。「8エージェント対応」のうち6つは beta で、実運用実績は Claude Code / Codex に偏る。

### GitHub Spec Kit — プロセスツールからプラットフォームへ

v1.0 到達時のメンテナ表明が「1.0.0 は単なる数字である。エージェントが変更コストを劇的に下げた今、価値は安定性から適応性へ移る」というもので、これが実装にそのまま出ている。

- **4層のテンプレート解決スタック:** プロジェクトローカル override > preset > extension > コア。実行時に上から解決し最初に一致したものを使う。**組織標準・規制要件・方法論の差し替えを、本体を fork せずに行える。**
- **カタログ実測:** integrations 41件、コミュニティ拡張 165件、コミュニティプリセット 34件。bundle（役割別に拡張・プリセット・ワークフローを束ねてバージョン固定）まである。
- **`/speckit.converge` の追加が重要:** 「spec/plan/tasks が求めるもの」と「コードの現状」の差分を評価し、**残作業を新しいタスクとして tasks.md に追記のみする（既存タスクの書き換え・コードの変更を禁止）**。implement→converge を Converged になるまで反復する運用。差分ツールではなく現状評価ツールと明記されている。
- **ブラウンフィールドの運用モデルを文書化:** `docs/concepts/spec-persistence.md` と `docs/guides/evolving-specs.md` で flow-forward（履歴として残す）／living spec（spec.md が契約、下流を再生成）／flow-back（実装の発見が成果物を書き換える）の3モデルを定義。

**弱点:** 仕様の ID（FR-001 等）に機械検査がない。テンプレートに書かれているだけで、一意性も参照整合も検査されない。**トレーサビリティは「書式の推奨」であって「保証」ではない。**

### OpenSpec — デルタ仕様というブラウンフィールドの正解

`docs/existing-projects.md` の冒頭が本質を突いている——「コードベース全体を文書化してから始めるのではない。これから変更する部分だけ仕様を書く」。

- **delta-first:** 仕様は `## ADDED Requirements` / `MODIFIED` / `REMOVED` で書く。`openspec/specs/` は空から始まり、archive のたびにデルタがマージされて育つ。**8万行のレガシーでも初日から回せる。**
- **Stores（beta）が XDDP の領域に踏み込んだ:** 計画（specs と changes）を専用リポジトリに置き、`git push` で複数コードリポジトリ・複数チーム・複数エージェントが共有する。「1つの変更が API サーバ・Web アプリ・共有ライブラリにまたがる」「プラットフォームチームが仕様を所有し、プロダクトチームが read-only で参照する」という、まさに XDDP の `REPOS:` ＋ `cross/` が解こうとしている問題を、**より運用しやすい形（普通の git リポジトリ）で解いている。**
- **スキーマの fork:** `openspec schema fork` で成果物の種類と依存関係そのものを再定義できる。ワークフローの形自体がユーザー拡張点。

**弱点:** 品質ゲートが弱い。フェーズロックがないのは強みでもあるが、「合意なしに実装へ進む」ことを機構的に止めない。規制産業・監査要求には素のままでは足りない。

### Spec Workflow MCP — 採用を推奨できる状態にない

MCP 標準化とダッシュボード承認は今も他にない特徴だが、**README 冒頭に作者の活動休止告知が掲示され、最終コミットは 2026-07-03**。MCP Tools は5種のまま（`spec-workflow-guide`／`steering-guide`／`spec-status`／`approvals`／`log-implementation`）。

新規採用は推奨しない。「ダッシュボードでの承認フロー」が要件なら、OpenSpec のダッシュボードか、spec-kit の拡張で作る方が将来性がある。

### XDDP — 母体調査と決定性は本物、それ以外は追いつかれた

詳細はセクション6で正直に書く。

---

## 5. 設計軸別の分析

前版は「自動化の境界」1軸で整理していたが、それでは差が見えなくなった。**7軸で分解する。**

### 軸1: 仕様の粒度と寿命

```
cc-sdd     機能スペック（数時間〜数日で出荷できる単位）。federated。roadmap で分割
Spec Kit   機能スペック（specs/NNN-feature/）。3つの永続化モデルから選ぶ
OpenSpec   デルタ（変更差分）。archive で main 仕様へマージされ蓄積
SWF MCP    機能スペック
XDDP       CR（変更要求）単位。CRS→SPO→DSN→CHD→TSP と成果物が段階的に増える
```

**評価:** OpenSpec のデルタが最も摩擦が少ない。XDDP の CR 単位は「変更管理台帳」としては正しいが、**1 CR あたりの成果物点数が多い**（CRS・SPO・DSN・CHD・TSP・TSR・VERIFY・latest-specs）。成果物が多いこと自体は監査要求があれば正当だが、無ければ純粋なコストになる。

### 軸2: 自動化の境界

```
cc-sdd     実装ループを自律化（実装者→レビュアー→デバッガ）。ゲートは仕様3点＋タスク diff
Spec Kit   implement→converge を Converged まで反復。ゲートは各コマンド境界
OpenSpec   propose→apply。ゲートは実質 propose 後のみ
SWF MCP    ワークフロー誘導のみ。実装は AI 任せ
XDDP       各主工程に人ゲート。実装は1パス（コーダー→静的検証、失敗時は人へ差し戻し）
```

**評価:** XDDP は**実装の自動化度が5ツール中最も低い**。工程7でコーダーエージェントが CHD 通りに書き、工程8の静的検証が NG なら「実装バグは直接修正、設計誤りは人に差し戻して工程6からやり直し」で止まる。cc-sdd のような有界リトライループを持たない。

これは「AI に任せない」という思想の帰結でもあるが、実務上は **`/xddp.06.design` からの再実行コストが高い**（CHD 再生成＋AIレビュー2ラウンド＋人ゲート）。設計誤りの検出が実装後になる構造なので、差し戻しが起きたときの損失が大きい。

### 軸3: 決定性の置き場所 ★XDDP が明確に優位

LLM ワークフローツールの最大の脆弱性は「手順書が自然言語で、実行するのが LLM」という点にある。分岐の取りこぼしは静的に検出できない。各ツールがどこまで決定的処理を機械側に寄せているか：

| ツール | 決定的処理の実体 |
|---|---|
| cc-sdd | なし（プロンプト内の制約記述のみ。ただし構造化ハンドオフのパース契約は厳密） |
| Spec Kit | `check-prerequisites`（前提チェック）程度。CLI 本体（59k行）は配布・カタログ・拡張機構であってワークフロー実行中の帳簿ではない |
| OpenSpec | `openspec validate`（仕様の構造検証）、`openspec status`。CLI は TypeScript で本体機能を持つ |
| SWF MCP | MCP サーバがファイル I/O と承認状態を管理 |
| **XDDP** | **本番 6,848行＋テスト 6,390行の Python。** BFS 帳簿エンジン（`specout_bfs.py` 2,132行）、件数一致の独立回帰検証（`specout_verify_counts.py`）、成果物 lint（`artifact_lint.py` L1〜L13）、進捗更新、ゲート変更検知（`xddp_gate_snapshot.py`）、レビューブリーフ生成、VCS 抽象層、昇格処理 |

**これは XDDP の最大の技術的優位であり、他4ツールが到達していない領域。** 「決定的処理はスクリプト・意味判定は LLM」という開発ルールが CLAUDE.md に明文化され、実装がそれに従っている。テストコード比率 93%（6,390 / 6,848）も他に類を見ない。

さらに **ツール自身のメタ検証ハーネス**（`make test` ＝ refcheck による参照整合静的検査＋全 unittest、0トークン、数秒）を持つ。プロンプトを長期資産として扱うなら、スキル間の `apply` 見出し参照・`subagent_type` 名・テンプレートプレースホルダーの整合を静的に検査する仕組みは必須で、確認した範囲では**これを持っているのは XDDP のみ**。

ただし限界も正確に書く。**決定性を寄せられているのは「帳簿管理」であって「制御フロー」ではない。** `xddp.common/SKILL.md` 929行には、日本語で書かれた while ループ・3段階の優先順位判定（`REVIEW_MAX_ROUNDS` が明示的に0 > `MAX_ROUNDS_OVERRIDE` > 設定値）・例外時のフォールバックが並ぶ。これを実行するのは LLM であり、分岐の取りこぼしは refcheck では検出できない（refcheck が見るのは参照の存在であって意味ではない）。`make smoke-full` はこれを実走で検証する仕組みだが、**advisory 扱い・1工程ずつ・トークン予算が必要**で、常時回せるものではない。

### 軸4: 影響範囲調査 ★XDDP の固有価値

```
cc-sdd     kiro-validate-gap: LLM が Grep/Glob で既存実装を調べ、extend/new/hybrid を比較
           → 探索の網羅性は LLM の判断次第。帳簿も件数照合もない
Spec Kit   converge: 成果物 vs コード現状のギャップをタスク化
           → 「spec が要求することが実装されているか」であって「変更がどこに波及するか」ではない
OpenSpec   explore: LLM がコードを読んで方針を提案
           → 同上、LLM の探索
SWF MCP    なし
XDDP       specout: Wave 0 シンボルから BFS で波及を追う
           → grep/rg が候補行を機械的に抽出 → LLM は各行の伝播種別を判定するだけ
           → 波ごとにチェックポイント（中断耐性）、件数一致の独立回帰検証、
              高ノイズ時の前倒し縮退、チャンク並列分類、除外パターン、深さ上限と継続パスA/B/C
```

**この差は「程度」ではなく「種類」の差。** 他4ツールの影響範囲調査は本質的に「LLM に聞く」であり、探索の網羅性に機械的な保証がない。XDDP の specout は「機械が候補を出し、LLM は意味判定だけする」という役割分担で、**規模に対するスケールの効かせ方が構造的に正しい**。

しかも監査可能性の設計が入っている：除外・dedup された行は「## フィルタ除外一覧」に全件記録され、「生 = 記録 + dedup除外 + フィルタ除外 + noise-collapse除外」で件数照合される。`specout_verify_counts.py` は `commit-wave` の自己検証（メモリ上のデータ突合）とは独立に、**書き出されたログのテキストを突き合わせる**ため、ログ書き出し自体の欠陥を検出できる。この二重化は設計者が「自己検証は自分のバグを検出できない」と理解していることの証拠で、評価に値する。

**ただし注意:** これは「母体（既存の大規模コード）に変更を加える」文脈でのみ価値がある。グリーンフィールドでは丸ごと無駄になる（`DEVELOPMENT_MODE: new` で工程4をスキップできるようになってはいる）。

### 軸5: 配布・バージョニング・アップグレード ★XDDP が明確に劣位

| ツール | 配布 | バージョン固定 | アップグレード | ロールバック |
|---|---|---|---|---|
| cc-sdd | `npx cc-sdd@latest` | ✅ npm semver | migration guide（v1.x/v2.x→v3.0） | npm でバージョン指定 |
| Spec Kit | `uv tool install ...@vX.Y.Z` | ✅ タグ固定 | `specify self check` / `self upgrade [--tag]` / `--dry-run` | `self upgrade --tag` で任意タグへ |
| OpenSpec | `npm i -g @fission-ai/openspec@latest` | ✅ npm semver | `openspec update`（プロジェクト内の生成物を再生成） | npm でバージョン指定 |
| SWF MCP | `npx @pimzino/spec-workflow-mcp@latest` | ✅ npm semver | npx が解決 | npm でバージョン指定 |
| **XDDP** | `git clone` + `bash setup.sh` | ❌ **なし** | mtime 比較で自動上書き | ❌ **なし** |

**これは XDDP の構造的な弱点で、しかも自己矛盾を含んでいる。**

- バージョン番号もリリースタグも CHANGELOG もない。「どのバージョンの XDDP でこの CR を回したか」を記録する手段がない。
- `setup.sh` は `~/.claude/` へコピーする。**`~/.claude/` はマシン単位のグローバル状態**なので、プロジェクト A は旧版・プロジェクト B は新版、という固定ができない。他4ツールはすべてプロジェクトローカルにファイルを書き出すので固定できる。
- アンインストール手段がない。ロールバック手段がない。
- `CLAUDE.md` は「後方互換性は保証しない。既存 CR が追従できない場合は再実行・再生成を求めることを許容する」と宣言している。開発中のツールとしては妥当な割り切りだが、**「監査・トレーサビリティ・長期保守」を価値として掲げるツールが、自分自身のバージョン追跡を持たない**のは一貫していない。数年後に「この CR はどの規約で作られたか」を問われたとき、答える手段がない。

**優先度最高の改善項目はここ。** semver 付与＋`ClaudeCode/.claude/VERSION` 相当のファイル＋`progress.md` へのツールバージョン記録、が最小の一歩。

### 軸6: エコシステム・拡張性

```
Spec Kit   extension 165（コミュニティ）+ preset 34 + bundle + 4層テンプレート解決
           → ドメイン特化・組織標準・規制対応をユーザー側で完結できる
OpenSpec   カスタムスキーマ（成果物の種類と依存を再定義）+ コミュニティスキーマカタログ
           + openspec/config.yaml で context / per-artifact rules / per-operation guidance
cc-sdd     settings/templates と settings/rules の編集（本体は触らない）
SWF MCP    なし
XDDP       xddp.config.md の設定キー（31個）+ project-rulebook 3種
           → 工程の追加・成果物の追加・成果物書式の差し替えは本体 fork のみ
```

**評価:** XDDP は `CLAUDE.md` で「適用ドメインの中立性（必須）」を厳しく規定し、Web・組込み・制御・業務のすべてで意味を持つ記述だけを許している。設計判断としては筋が通っているが、**裏返すと「ドメイン特化はユーザーができない」**。spec-kit の preset はまさにその穴を埋める機構（規制トレーサビリティ強制、方法論の差し替え、用語のローカライズ）で、方向性が正反対になっている。

XDDP が社内単独利用ならこれで問題ない。OSS として広げる意図があるなら、**「中立なコア＋ドメイン特化のオーバーレイ」に構造を変える**必要がある。

### 軸7: コンテキスト経済 ★未計測

XDDP は 1 CR で以下を消費する：

- SKILL.md 合計 8,067行。うち `xddp.common/SKILL.md` 929行は**ほぼ全工程で読まれる**
- 主工程ごとに: 生成エージェント1回 ＋ レビュアーサブエージェント 2〜3回（`REVIEW_MAX_ROUNDS` デフォルト ANA/CRS/DSN/CHD/TSP=2、SPO=3）＋ フィクサーエージェント 1〜2回
- specout は波ごとに classifier サブエージェントを最大4並列（`SPECOUT_CLASSIFY_PARALLEL`）

`xddp_metrics.py` はテレメトリを持つが、記録するのは `duration_ms`（壁時計）・レビューラウンド数・`reference_bytes`（レビュアーへの入力バイト数）であって、**トークン数は記録していない**（ライブ実行中のスキルからは取得不可能という理由が明記されている）。

**「推測ではなく計測に基づいて最適化」を掲げるリポジトリで、自ツールの最大コスト要因が代理指標止まりなのは一貫していない。** `reference_bytes` は入力側の代理にはなるが、出力トークン・サブエージェント起動回数の累積は捉えられない。PLAN-20260830（レビューループ参照ファイル削減）で `crs_ur_scope.py`・`extract-review-scope` を導入して入力を絞っているのは正しい方向だが、**削減の効果を測る単位が bytes のままでは最適化の意思決定ができない**。

比較対象がないので「XDDP は高い」と断言はできない。だが構造上、**11工程 ×（生成＋2〜3レビュー＋修正）のサブエージェント起動は、OpenSpec の propose→apply の2ステップとは桁が違う**ことは構造から言える。

---

## 6. XDDP の正直な評価

### 6.1 本物の優位（他4ツールに等価物がない）

| # | 項目 | 根拠 | 代替可能性 |
|---|---|---|---|
| 1 | **specout（BFS 波及調査）** | `specout_bfs.py` 2,132行＋テスト 2,248行。波ごとチェックポイント・件数一致の独立回帰検証・除外の全件記録 | **なし**。他4ツールの影響範囲調査は LLM 探索で網羅性の保証がない |
| 2 | **決定的処理のスクリプト化** | 本番 6,848行／テスト 6,390行 | **なし**。他4ツールのワークフロー本体はプロンプト |
| 3 | **ツール自身のメタ検証** | `make test`（refcheck ＋ unittest、0トークン）、`make smoke-full`（実走 advisory） | **なし**（確認した範囲） |
| 4 | **成果物書式の機械検査** | `artifact_lint.py` L1〜L13。ID 一意性・CR プレフィクス欠落 fail-loud・曖昧表現検出・要求3階層兆候・SP 本文重複 | **なし**。spec-kit の FR-xxx は書式推奨のみで検査なし |
| 5 | **Excel 往復（USDM）** | `crs_md2excel.py` 708行／`excel_dump.py` | **なし**。非エンジニアの参画経路として日本の製造業・SIer で実務的に効く |
| 6 | **ツール開発自体のガバナンス** | plan → AI レビュー → 人承認 → 実装 → ドキュメント更新の強制、ADR 13件 | 他4ツールにも近いものはあるが、ここまで明文化されているのは XDDP のみ |

### 6.2 弱点（優先度順）

**🔴 P0: 配布・バージョニングが存在しない**（軸5）
semver なし、リリースなし、CHANGELOG なし、ロールバックなし、プロジェクト単位のバージョン固定不可。監査を価値として掲げるツールが自分のバージョンを追跡できない。**最優先で直すべき。**

**🔴 P0: 単一エージェント依存**
Claude Code 専用。スキル記述が Claude Code の Agent tool / Skill 機構に強く結合している（`subagent_type=xddp-...` の直書き、`~/.claude/skills/` パス直書き）。他4ツールは 8〜49 のエージェントに対応。

リスクの本質は「ベンダーロックイン」ではなく、**Claude Code の仕様変更に単独で追随し続けるコスト**。cc-sdd は 8プラットフォーム分のテンプレート生成を CLI 側に持ち、spec-kit は integrations カタログで抽象化している。XDDP は抽象層を持たない。

**🟡 P1: テストが後付け（test-after）**
工程7コーディング → 工程8静的検証 → 工程9テスト設計 → 工程10テスト実行。TSP は CHD の確認項目から導出されるので V 字プロセスとしては筋が通っており、規制産業の慣行にも合う。

ただし **AI に実装させるツールとしては明確なハンデ**。工程7の `xddp-coder-agent` に渡せる成功条件は「CHD 通りに書いたか」だけで、**実行可能な合否判定がない**。cc-sdd は RED→GREEN をフィーチャーフラグ付きで強制し、実装者は「テストが通る」という機械判定可能なゴールを持つ。この差は実装品質そのものより「LLM が自分の出力を検証できるか」に効く。

思想の違いなので単純に「劣っている」とは言わないが、**トレードオフとして明示的に文書化されているべき**で、現状 CLAUDE.md にその記述はない。

**🟡 P1: 実装フェーズの有界リトライループがない**（軸2）
工程8で設計誤りが検出されると工程6へ差し戻し、人が介在する。cc-sdd の「レビュー却下2回→デバッグ、デバッグ2回→ブロック」のような自動回復パスがない。差し戻しコストが高い（CHD 再生成＋AIレビュー＋人ゲート）。

**🟡 P1: コンテキスト経済が未計測**（軸7）
トークン計測の手段がない状態で削減施策（PLAN-20260830 等）を進めている。効果の検証が bytes の代理指標に留まる。

**🔵 P2: 人ゲートの本数**
15詳細ステップ、主工程ごとに人レビューゲート。1 CR の壁時計時間が人の可用性に律速される。レビューブリーフ（不確実性マーカー トップN・前工程差分・推奨レビュー順序と所要時間）は緩和策として良い設計だが、**ゲート数そのものは減らしていない**。`CR_PROFILE: quick` も工程を統合するだけでゲートは残る。

**🔵 P2: エコシステムがない**（軸6）
拡張点が設定キーと rulebook のみ。ドメイン特化・組織標準の差し替えには fork が必要。

**🔵 P2: ハンドオフ契約が緩い**
`## Review Loop` は「レビュー結果ファイルに 🔴/🟡 があるか」で継続判定する。cc-sdd のような「構造化フィールドからのみ読み、パースできなければ再ディスパッチ」という契約になっていない。レビュアーが絵文字を書き忘れる／散文で書く／別の記号を使う場合の挙動が定義されていない。**cc-sdd の `## Status Report` / `## Review Verdict` パース規約は、そのまま XDDP に移植する価値がある。**

### 6.3 競合の接近によって失われた優位

前版で XDDP の強みとしていたが、もはや差別化にならない項目：

| 前版の主張 | 現状 |
|---|---|
| ブラウンフィールド対応 | OpenSpec が delta-first を「brownfield-first」として明示し専用ガイドを新設。spec-kit も3つの永続化モデル＋`converge` を追加 |
| マルチリポジトリ | OpenSpec Stores（beta）が計画専用リポジトリの git 共有を実装。XDDP の `cross/` 仮想リポジトリより運用モデルが素直 |
| プロジェクトメモリ | 全ツールが steering / constitution / config.yaml context で対応済み |
| 品質ゲート外部化 | spec-kit の preset が同等以上（テンプレート・コマンドまで差し替え可能） |
| 知見蓄積 | cc-sdd の `## Implementation Notes`（後続タスクへ自動注入）は XDDP の lessons-learned（CR 間・人が読む）より即効性が高い |

---

## 7. 適性判断

前版の「Web系 vs システム系」の二分法は維持するが、**判断軸は「変更1件のコストと影響範囲」に置く**方が実態に合う。

```
                  変更コスト小・影響範囲小  ←→  変更コスト大・影響範囲大
                  （SaaS・アプリ・PoC）        （基幹・組込み・制御・規制）

OpenSpec          ◎◎◎                       ○   （Stores で規模には対応、監査には不足）
GitHub Spec Kit   ◎◎◎                       ○〜◎（preset で規制対応を作り込めば◎）
cc-sdd            ◎◎                        ○   （境界契約は効くが母体調査がない）
Spec Workflow MCP △                          △   （活動休止のため新規採用非推奨）
XDDP              △                          ◎◎◎
```

### XDDP を選ぶべき条件（すべて満たすとき）

1. 母体（既存の大規模コード）への変更が主で、**影響範囲の把握が実際にコストの大半を占めている**
2. 設計書・仕様書が法令・契約・社内規程で**成果物として要求される**
3. 非エンジニア（品証・顧客・上流工程）が **Excel で仕様をレビューする**運用がある
4. Claude Code に統一できる（他エージェントを併用しない）
5. 1 CR あたり数日〜数週間のリードタイムを許容できる

### XDDP を選ぶべきでない条件（いずれか1つでも該当）

- グリーンフィールド中心（specout の価値がゼロで、工程の重さだけが残る）
- 週次以上の頻度で小変更を出荷する
- 複数の AI エージェントを併用している／する予定がある
- ツールのバージョンを固定・追跡する必要がある（現状不可能）
- チーム外・社外に配布する必要がある（配布機構がない）

### 併用の可能性

XDDP の specout（工程4a）は**単体で価値がある**。`/xddp.survey` は CR 非依存で動く。

> 他ツールで開発しつつ、影響範囲調査だけ XDDP の specout を使う、という併用は構造上可能。
> ただし現状 specout は `xddp.config.md` と `{XDDP_DIR}` 構造に依存しており、単独ツールとして
> 切り出す設計にはなっていない。切り出せば **XDDP で最も外販価値のある部品**になる可能性がある。
> （これは推論であり、実際に切り出しを試みた事実はない）

---

## 8. 推奨アクション

### 優先度 🔴 最高

| # | 項目 | 内容 | 参考 |
|---|---|---|---|
| 1 | **バージョニングの導入** | semver 付与、`ClaudeCode/.claude/VERSION`、CHANGELOG、`progress.md` へのツールバージョン記録。最小でも「どの版で回した CR か」を残す | spec-kit `specify self check/upgrade --tag` |
| 2 | **プロジェクトローカル配置への移行検討** | `~/.claude/` グローバル配置をやめ、プロジェクト直下へ配置する選択肢を用意（プロジェクト単位のバージョン固定が可能になる） | cc-sdd / spec-kit / OpenSpec すべてこの方式 |
| 3 | **ハンドオフ契約の厳密化** | レビュー判定を絵文字スキャンから構造化フィールド（`- VERDICT: PASS \| ISSUES_FOUND`）へ。パース不能なら再ディスパッチ | cc-sdd `kiro-impl` の Strict Handoff Parsing |

### 優先度 🟡 高

| # | 項目 | 内容 | 参考 |
|---|---|---|---|
| 4 | **トークン計測の確立** | サブエージェント起動回数・推定入出力トークンを `metrics.jsonl` に記録。削減施策の効果を測れるようにする | — |
| 5 | **実装フェーズの有界リトライ** | 工程7〜8に「検証NG→修正→再検証」の有界ループ（上限付き）を入れ、人への差し戻しを最後の手段にする | cc-sdd の2ラウンド／2デバッグ上限 |
| 6 | **test-after のトレードオフ明文化** | CLAUDE.md に「工程9が工程7の後にある理由」と「その代償（コーダーに機械判定可能なゴールがない）」を記録。ADR が適切 | — |
| 7 | **specout の単体切り出し検討** | `xddp.config.md` 依存を薄くし、CR 非依存で動く影響範囲調査ツールとして独立させる | — |

### 優先度 🔵 中

| # | 項目 | 内容 | 参考 |
|---|---|---|---|
| 8 | **オーバーレイ機構** | 「中立なコア＋ドメイン特化オーバーレイ」。テンプレート解決を多層化し、fork せずに成果物書式を差し替え可能にする | spec-kit の4層テンプレート解決／OpenSpec の schema fork |
| 9 | **知見の自動注入** | lessons-learned を人が読む前提から、次工程のエージェントプロンプトへ自動注入する形へ | cc-sdd `## Implementation Notes` |
| 10 | **人ゲートの削減** | quick プロファイルでゲート**数**を減らす（現状は工程の統合のみでゲートは残る） | OpenSpec core プロファイル |
| 11 | **マルチエージェント対応の抽象層** | `subagent_type` / パス直書きを1箇所に集約し、将来の移植コストを下げる | cc-sdd のテンプレート生成方式 |

### 実装済み（前版の「未実装ギャップ」からの更新）

| 前版の項目 | 現状 |
|---|---|
| Quick Mode | ✅ `CR_PROFILE: quick`、`/xddp.set-profile` |
| Explore フェーズ | ✅ `/xddp.survey`（CR 非依存の母体調査・knowledge/specs 昇格） |
| プロファイルシステム | ✅ `CR_PROFILE: full/quick` |
| `QUALITY_GATE_MAX_ITERATIONS` | ✅ `REVIEW_MAX_ROUNDS`（種別ごと） |
| ダッシュボード可視化 | ❌ 未実装（`/xddp.status` はテキスト表示） |
| MCP Server 化 | ❌ 未実装 |
| コミュニティ拡張の仕組み | ❌ 未実装 |

---

## 9. 出典

| ツール | 出典（バージョン・コミットは 2026-09-06 時点で `git fetch` 済み） |
|---|---|
| cc-sdd v3.0.2 | ローカルクローン `gotalab/cc-sdd` HEAD `29aee95`（2026-04-27）。`README.md` / `docs/guides/why-cc-sdd.md` / `tools/cc-sdd/templates/agents/claude-code-skills/skills/*/SKILL.md` / `tools/cc-sdd/package.json` |
| GitHub Spec Kit v1.0.5.dev0 | ローカルクローン `github/spec-kit` HEAD `4a7341a9`（2026-09-04）。`README.md` / `CHANGELOG.md` / `pyproject.toml` / `templates/commands/*.md` / `templates/spec-template.md` / `{integrations,extensions,presets,workflows}/catalog*.json` / `docs/guides/evolving-specs.md` |
| OpenSpec v1.12.0 | ローカルクローン `Fission-AI/OpenSpec` HEAD `e062b95`（2026-09-03）。`README.md` / `package.json` / `docs/commands.md` / `docs/cli.md` / `docs/existing-projects.md` / `docs/customization.md` / `docs/supported-tools.md` / `docs/stores-beta/` |
| Spec Workflow MCP v2.2.7 | ローカルクローン `pimzino/spec-workflow-mcp` HEAD `d38e82e`（2026-07-03）。`README.md` / `package.json` / `src/tools/` |
| XDDP | 本リポジトリ。`CLAUDE.md` / `README.md` / `ClaudeCode/.claude/skills/*/SKILL.md`（27件）/ `ClaudeCode/.claude/agents/*.md`（19件）/ `ClaudeCode/.claude/skills/*/scripts/*.py` / `ClaudeCode/.claude/skills/xddp.01.init/templates/xddp.config.md` / `docs/adr/`（13件）/ `docs/specout-discovery-guide.md` |

**外部の比較記事（前版から継続。今回は再検証していない）**

| 出典 |
|---|
| [Martin Fowler: Understanding Spec-Driven-Development tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) |
| [Hashrocket: OpenSpec vs Spec Kit](https://hashrocket.com/blog/posts/openspec-vs-spec-kit-choosing-the-right-ai-driven-development-workflow-for-your-team) |

---

## 付録: 数値の実測値一覧

本書中の定量記述の実測方法。

| 数値 | 実測方法 |
|---|---|
| spec-kit integrations 41件 | `integrations/catalog.json` の `integrations` キー数 |
| spec-kit コミュニティ拡張 165件 | `extensions/catalog.community.json` の `extensions` キー数（同梱拡張は `catalog.json` に4件） |
| spec-kit コミュニティプリセット 34件 | `presets/catalog.community.json` の `presets` キー数（同梱は2件） |
| OpenSpec 対応ツール 49件 | `docs/supported-tools.md` の Tool Directory Reference 表の行数（ヘッダ・区切り行を除く） |
| cc-sdd 17 skills | `tools/cc-sdd/templates/agents/claude-code-skills/skills/` のディレクトリ数 |
| cc-sdd 8エージェント・13言語 | `README.md` Supported Agents 表／`--lang` の列挙 |
| SWF MCP 5 tools | `src/tools/` の `*.ts`（`index.ts` を除く） |
| XDDP 27スキル | `ClaudeCode/.claude/skills/*/SKILL.md` の件数（うち `xddp.common` は `user-invocable: false`） |
| XDDP 19エージェント | `ClaudeCode/.claude/agents/*.md` の件数 |
| XDDP SKILL.md 8,067行 | 上記27ファイルの合計行数 |
| XDDP Python 本番 6,848行／テスト 6,390行 | `ClaudeCode/.claude` 配下の `*.py` を `tests/` の内外で分けた合計行数 |
| XDDP 11主工程／15詳細ステップ | `xddp.01.init/templates/00_progress-management-template.md` の工程進捗表（1, 2, 3, 4a, 4b, 5, 6a, 6b, 7, 8, 9, 10a, 10b, 10c, 11） |
| XDDP ADR 13件 | `docs/adr/ADR-*.md` の件数 |
| XDDP 設定キー 31個 | `xddp.config.md` テンプレート中の行頭 `^[A-Z_]+:` をユニーク化した件数（コメント内でのみ言及される `MD2EXCEL_PYTHON_BIN`・`SPECOUT_BACKEND_BIN` を除く） |
