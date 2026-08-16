# tools/harness — 開発時テストハーネス 完全ガイド

このディレクトリのツールは、**XddpSettings リポジトリ自身**（`ClaudeCode/.claude/` 配下の
スキル・エージェント定義）の品質を検証するための開発時メタツールです。XDDP を使った実際の
開発作業（`/xddp.01.init` などのスラッシュコマンド）とは別物で、「スキル・エージェント定義を
編集したときに壊れていないか確認する」ためのテストスイートです。

`setup.sh` によるデプロイ対象（`~/.claude/`）には含まれません。このリポジトリ（XddpSettings）
自体を開発する人だけが使います。

ルートの [README.md](../README.md) は XDDP そのものの使い方（対象プロジェクトでの
スラッシュコマンド運用）を説明しています。本ファイルはそこからリンクされている
「開発時テストハーネス」の詳細版です。

## 1. 全体像：5つの検証レベル

| レベル | 何を検証するか | 使うコマンド | LLM呼び出し |
|---|---|---|---|
| L1 | スキル/エージェント間の参照整合（見出し・`subagent_type`・テンプレート変数） | `make lint` | なし |
| L2 | 決定的処理スクリプト（`xddp_progress.py` 等）の単体テスト | `make unit` | なし |
| L3 | スキルの決定的スクリプト呼び出しが実在サブコマンド／フラグに解決するか | `make lint`（検査D） | なし |
| L4 | スキルを実際に起動してオーケストレーション（工程の流れ）を検証 | `make smoke-full PHASE=NN` | あり |
| L5 | 生成された成果物が構造的に妥当か（見出し・ID・フロントマターの有無） | `make smoke-full PHASE=NN`（ゴールデン照合） | あり（L4と同時） |

L1〜L3 はまとめて `make test` で一括実行できます（**0トークン**・数秒）。編集のたびに、
コミット前に必ず一度実行してください。

L4/L5 は `claude` CLI で実際にスキルを起動するため**トークン課金が発生**します。挙動に関わる
変更をしたときだけ、該当工程に絞って実行してください（`CLAUDE.md`「ツール修正後のハーネス実行」参照）。

## 2. 事前準備

### 2.1 共通（L1〜L3。全員必須）

- `python3`（標準ライブラリのみで動作。追加パッケージのインストール不要）
- GNU make
- リポジトリのルート（`tools/` の1つ上の階層）で実行する

```bash
cd XddpSettings
make test
```

これが緑（exit 0）になることをまず確認してから先に進んでください。

### 2.2 L4/L5（full-run スモーク・校正ラン）を実行する場合のみ必須

L4/L5 は、隔離した仮想の HOME ディレクトリの中で `claude` CLI を実際に起動します。
以下の2つが必要です。

1. **`claude` CLI のインストール**（未導入の場合は通常の Claude Code のインストール手順に
   従ってください。導入済みか確認するには `claude --version`）
2. **非対話認証用の環境変数**（隔離 HOME では、ふだんの `claude` ログインセッションを
   引き継げないため必須です）

認証方法は「どこにリクエストを送るか」で2パターンに分かれます。

#### パターンA: Anthropic 公式へ送る場合（最も一般的・`ANTHROPIC_BASE_URL` は設定しない）

以下のいずれか1つを設定します（未設定の場合はこの順で自動探索されます）。

| 環境変数 | 取得方法 | 課金 |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN`（推奨） | `claude setup-token` を実行しブラウザで認可 | Claude Pro/Max のサブスク枠を消費（追加課金なし） |
| `ANTHROPIC_API_KEY` | Anthropic Console で API キーを発行 | API従量課金 |
| `ANTHROPIC_AUTH_TOKEN` | 特殊用途向け（通常は上の2つのどちらかで足ります） | - |

初めて実行するなら `CLAUDE_CODE_OAUTH_TOKEN` が一番手軽です。

```bash
claude setup-token
# ブラウザでログイン・認可 → 1年有効なトークンが表示される
export CLAUDE_CODE_OAUTH_TOKEN='sk-ant-oat...'   # 表示された値を貼る
```

> トークンはコマンド履歴やチャット、コミットに残さないよう注意してください。
> `export` はそのシェルセッションの中だけで有効です（新しい端末を開くたびに再設定が必要）。
> 恒久的にしたい場合は `~/.zshrc` 等に追記してください。

#### パターンB: Anthropic互換の第三者エンドポイントへ送る場合（例: SakuraAI）

`ANTHROPIC_BASE_URL` を設定すると、認証の探索順が変わります。`CLAUDE_CODE_OAUTH_TOKEN` は
Anthropic サブスクの資格情報であり第三者側では認証に使えないため、**意図的に候補から
外れます**（`ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY` の順で探索）。

```bash
export ANTHROPIC_BASE_URL="https://api.ai.sakura.ad.jp"     # 利用するエンドポイントのURL
export ANTHROPIC_AUTH_TOKEN="..."                             # そのサービスで発行されたトークン
export ANTHROPIC_DEFAULT_SONNET_MODEL="preview/Kimi-K2.6"     # `sonnet` エイリアスの上書き先モデルID
# Opus/Haiku を使う工程もあるなら同様に設定（未設定でも動作はする）
# export ANTHROPIC_DEFAULT_OPUS_MODEL="preview/Kimi-K2.6"
# export ANTHROPIC_DEFAULT_HAIKU_MODEL="preview/Kimi-K2.6"
```

第三者エンドポイントの詳細（ゴールデンの分離保存先・予算ガードの扱い・未確認事項）は
[harness/smoke_config.md](harness/smoke_config.md) を参照してください。

### 2.3 認証の実機確認（任意だが推奨）

本番の校正ランに入る前に、隔離 HOME での認証が正しく通るかを軽量なモデルで確認できます
（パターンAの `CLAUDE_CODE_OAUTH_TOKEN` 前提）。

```bash
bash tools/harness/verify_isolated_auth.sh
```

トークンはスクリプトに書かず、必ずシェルの `export` で渡してください。

## 3. 実行手順

### 3.1 まず: 0トークンの静的チェック

```bash
make test        # unit + lint 一括（推奨・毎回これでOK）
make lint         # refcheck のみ
make unit         # unittest のみ
```

### 3.2 単一工程の full-run スモーク（ゴールデンが既にある場合）

```bash
make smoke-full PHASE=04
```

`PHASE` は `02`／`03`／`04`／`05`／`06`／`07`／`09`／`10`／`11`／`close` のいずれかです
（工程01は次項3.4の理由により `--phase` の対象外、工程08は工程07に統合済みのため対象外）。

このコマンドは既存のゴールデン（`test-fixtures/golden/`）と成果物の構造性質を照合します。
ゴールデンがまだ無い工程・モデルの組み合わせで実行すると `golden_missing`（exit 8）で
停止します。その場合は次の3.3を先に実行してください。

### 3.3 ゴールデンの新規作成・更新（`--update-golden`）

`make` にはショートカットが無いため、`smoke_full.py` を直接呼びます。

```bash
python3 tools/harness/smoke_full.py --phase 04 --update-golden
```

書き込み・更新される内容は必ず人が diff を確認してからコミットしてください（LLM生成の
構造性質を無条件に正としないため）。

### 3.4 複数工程をまとめてゴールデン確定したい場合

一見「`--all --harvest` を使えば一括でできそう」に見えますが、**このコマンドは使えません**。
`--harvest` は各工程の入力シードを前工程の出力から自動で連鎖生成しようとしますが、XDDP は
要求記入・進捗完了の確認など人間参加型ゲートを挟むため、無人では連鎖生成できず途中で
止まります（ルート [README.md](../README.md) の「校正の実施結果」節に詳細があります）。

まとめて実行したい場合は、工程ごとに `--phase NN --update-golden` をシェルでループしてください
（既存の静的シード `test-fixtures/scratch-workspace-min/seeds/` を使うので連鎖が不要で、
この方式なら動きます）。

```bash
for p in 02 03 04 05 06 07 09 10 11; do
  python3 tools/harness/smoke_full.py --phase "$p" --update-golden
done

# 04・11 は multi 版シード（cross 生成あり）も持つので、必要なら追加で確定
python3 tools/harness/smoke_full.py --phase 04 --multi --update-golden
python3 tools/harness/smoke_full.py --phase 11 --multi --update-golden
```

`close` は成果物 glob が CR 全体の close 実出力（`baseline_docs`）を見ないため advisory 対象外
（意図的にゴールデンを作らず手動検証とする方針）。上のループに `close` を含めないでください。

第三者エンドポイントを設定した状態で実行すると、ゴールデンは自動的に
`test-fixtures/golden/providers/{host}__{実モデルID}/` へ分離保存されます。Sonnet公式で
校正済みの平坦ゴールデン（`test-fixtures/golden/phaseNN-*.json`）は上書きされません
（詳細: [test-fixtures/golden/README.md](../test-fixtures/golden/README.md)）。

### 3.5 `make smoke-full-all`（全工程一括 assert）の既知の制限

```bash
make smoke-full-all   # = smoke_full.py --all
```

`--all` は工程01（init）を含めてタスクを組み立てますが、工程01用のゴールデン
（`test-fixtures/golden/phase01-single.json`）は存在しません（本ドキュメント作成時点で
`test-fixtures/golden/` を確認）。assert モードはゴールデンの有無を LLM 起動前に確認するため、
現状 `make smoke-full-all` は**工程01の時点で `golden_missing`（exit 8）となり直後に停止します**。

実質的には3.4でゴールデンを確定したあと、02〜closeの各工程を個別に
`make smoke-full PHASE=NN` で確認する運用にしてください。この制限を解消したい場合
（工程01を対象から外す、等）は `CLAUDE.md` の「変更前の計画・合意」に従いプランを起票してください。

### 3.6 校正ラン（偽失敗率・トークン実測）

```bash
make smoke-calibrate PHASE=04 MODEL=haiku
```

シード起こし（B）→ゴールデン確定（C）→校正（D）の3段階のうち最後の段階です。
通常の開発では使いません（`smoke_config.md` の予算・モデル設定値を見直すときのみ使用）。

## 4. 終了コード一覧

| exit | 意味 | 対処 |
|---|---|---|
| 0 | 成功（違反なし） | - |
| 1 | 構造性質の違反あり（advisory） | レポートを見て人が解釈・判断する |
| 2 | 引数エラー（`--all`/`--phase` 未指定、未知の PHASE 等） | コマンドを見直す |
| 3 | `claude` CLI 未導入・認証未了 | CLI をインストールする |
| 5 | 非対話認証の環境変数が未設定 | 本README「2.2」の手順で設定する |
| 6 | 予算未供給（`SMOKE_TOKEN_BUDGET` 等が0/未設定） | `smoke_config.md` か `--budget` で予算を設定する |
| 7 | 予算超過で中断 | 予算を見直す・対象工程を絞る |
| 8 | ゴールデン未確定で assert しようとした | 先に `--update-golden`（3.3）を実行する |
| 9 | スキル起動失敗（セッション上限・認証・レート制限等） | 時間を置く・認証を確認する |

## 5. よくあるつまずき

- **`make smoke-full` がすぐ exit 5 で落ちる** → 非対話認証の環境変数が未設定です。「2.2」を参照してください。
- **`make smoke-full` が exit 8 で落ちる** → そのモデル／エンドポイント向けのゴールデンがまだありません。「3.3」で先に確定してください。
- **`make smoke-full-all` がすぐ止まる** → 既知の制限です。「3.5」を参照してください。
- **`--all --harvest` を実行したら途中で失敗する** → 想定内です。「3.4」の人間参加型ゲートの説明とループ方式を参照してください。
- **トークン量を抑えたい** → まず `make test`（0トークン）で問題が再現するか確認し、L4/L5 は本当に必要な工程だけに絞って実行してください。
- **第三者エンドポイントで assert したら violations だらけになる** → モデルが変わると見出し・ID の展開粒度も変わるため、Sonnet公式のゴールデンとは一致しません。「3.4」の手順で当該プロバイダ専用のゴールデンを先に確定してください。

## 6. 関連ドキュメント

- [harness/smoke_config.md](harness/smoke_config.md) — ハーネスレベルの設定（トークン予算・工程別実行モデル・第三者エンドポイントの詳細・未確認事項）
- [test-fixtures/golden/README.md](../test-fixtures/golden/README.md) — ゴールデンの表現形式・ブートストラップ手順・プロバイダ別分離
- [docs/xddp-tool-verification-checklist.md](../docs/xddp-tool-verification-checklist.md) — 修正箇所別の動作確認チェックリスト
- ルート [README.md](../README.md) — XDDP 自体の使い方（このハーネスは XDDP ツールの開発者向け）
