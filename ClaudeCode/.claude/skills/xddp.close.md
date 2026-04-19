---
description: XDDP CR クローズ処理: 各工程の気づきをバックログへ集約し、知見ログ（lessons-learned.md）を生成・更新してCRを完了する。「CRをクローズして」「知見をまとめて」などで起動する。
---

You are orchestrating **XDDP Close — CR Closeout & Knowledge Capture**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date (YYYY-MM-DD).

## Step 0: 前提確認

Read `{CR}/progress.md`.  
工程15（最新仕様書作成）が ✅ 完了 になっていない場合は、先に `/xddp.09.specs {CR}` を実行するよう案内してから停止する。

## Step A: 気づき・提案メモの収集

以下のファイルを読み、各ファイルの「気づき・提案メモ」セクションの内容をすべて抽出する。

```
対象ファイル（存在するもののみ）:
- {CR}/01_requirements/ 配下の全 .md
- {CR}/02_analysis/ANA-{CR}.md
- {CR}/03_change-requirements/CRS-{CR}.md
- {CR}/04_specout/SPO-{CR}.md
- {CR}/05_architecture/DSN-{CR}.md
- {CR}/06_design/CHD-{CR}.md
- {CR}/07_test/TSP-{CR}.md
- {CR}/08_test-results/TSR-{CR}.md
```

抽出した全エントリを「発生源ファイル」と「対応方針」とともに一覧化する。

## Step B: 改善バックログの更新

`improvement-backlog.md`（プロジェクトルート）を読む。ファイルが存在しない場合は
`~/.claude/templates/10_improvement-backlog-template.md` から新規作成する。

Step A で収集した気づきのうち、対応方針が **今回対応** 以外のもの（次回CR / 保留 / 検討中）を
`IDEA-{NNN}` エントリとして追記する。

- ID は既存エントリの続き番号にする
- カテゴリは内容から判断: `機能改善` `潜在的バグ` `リファクタリング` `技術的負債` `セキュリティ` `パフォーマンス` `テスト強化` `ドキュメント整備`
- 発生源に CR 番号と資料名を記載する
- サマリ表（セクション1）の件数を更新する

## Step C: 知見ログの生成・更新

`lessons-learned.md`（プロジェクトルート）を読む。ファイルが存在しない場合は
`~/.claude/templates/lessons-learned-template.md` から新規作成する。

Step A で収集した気づき、および今回の CR 全体を通じて得られた教訓を分析し、
**次の CR 以降に活かせる知見** を `LL-{NNN}` エントリとして追記する。

### 知見抽出の観点

以下の問いに答えられる内容を知見として抽出する。なければスキップしてよい。

- **要求分析・仕様定義**（`#要求分析` `#仕様定義`）
  - 要求書では気づかなかったが、分析・設計で発覚した漏れや曖昧さはあったか？
  - ユーザ要求→システム要求→仕様への分解で判断が難しかったポイントは？
- **方式検討・設計**（`#方式検討` `#設計`）
  - 採用した方式で想定外の影響・制約が出たか？
  - 不採用案が後から見て正解だったケースはあったか？
- **実装・テスト**（`#コーディング` `#テスト`）
  - テストで初めて発覚した仕様漏れや設計ミスはあったか？
  - 回帰テストで影響が出たモジュールのパターンはあるか？
- **プロセス**（`#プロセス`）
  - この CR でスムーズだった工程・詰まった工程はどこか？
  - 次回改善すべきプロセス上の判断や手順はあるか？

### エントリ形式

各エントリを以下の形式で `lessons-learned.md` の「知見詳細」セクション末尾に追記する。

```markdown
### LL-{NNN}：{タイトル}

**CR：** {CR番号} ／ **工程：** {工程名} ／ **タグ：** {#タグ1 #タグ2}

**発生状況：**  
{どんな場面・判断でこの知見が生まれたか（1〜2文）}

**学んだこと：**  
{具体的な知見・教訓}

**次回への適用：**  
- {チェックポイント1}
- {チェックポイント2}

---
```

エントリを追加したら「エントリ一覧」テーブルにも1行追記し、`最終更新CR` を {CR} に更新する。

## Step C2: 承認済み仕様書の昇格（latest-specs/ → docs/specs/）

Read `{CR}/progress.md` を確認し、工程15で更新・生成されたすべての `latest-specs/` ファイルのリストを把握する。
（工程15の 詳細ステップに記録されたファイル一覧、または `latest-specs/` 配下を glob して確認する）

**ターゲットパスの決定:**

`xddp.config.md`（プロジェクトルート）に `SPECS_APPROVED_DIR` が定義されている場合はその値を使う。
未定義の場合は `docs/specs/` をデフォルトとする。

**昇格処理:**

各ファイルについて `latest-specs/{path}` → `{SPECS_APPROVED_DIR}/{path}` にコピーする。
既存ファイルがある場合は上書きする（バージョン情報はファイル内の変更履歴で管理する）。

その後 `{SPECS_APPROVED_DIR}/AI_INDEX.md` を読み込み（存在しない場合は新規作成）、
今回昇格したファイルのエントリを追加・更新する。

```markdown
## 承認済み仕様書

| ファイル | バージョン | 最終更新CR | 内容 |
|---|---|---|---|
| [specs/{module}-spec.md](specs/{module}-spec.md) | v{X.Y} | {CR} | {モジュール説明} |
```

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件）
> - 承認済み仕様書: `{SPECS_APPROVED_DIR}/` に昇格（{n} ファイル）
>
> **仕様書の昇格内容（latest-specs/ → {SPECS_APPROVED_DIR}/）：**
> {昇格したファイル一覧}
>
> **修正が必要な場合：**
> - 直接ファイルを編集してください
>
> 確認が完了したら「**クローズ完了**」と入力してください。

Wait for the user to confirm.

## Step E: CR 完了マーク

Read `{CR}/progress.md`.  
末尾に以下を追記する：

```
## CR クローズ

- **クローズ日：** {TODAY}
- **改善バックログ追加：** {n} 件
- **知見ログ追加：** {n} 件
- **ステータス：** ✅ 完了・クローズ済み
```

## Step F: Report in Japanese

追加した IDEA エントリ数・LL エントリ数・主な知見タイトルを報告する。

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.close.md` の要約も合わせて更新すること。
