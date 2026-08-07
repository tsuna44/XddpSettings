# scratch-workspace-p4-new-mode（新規開発モード動的検証用フィクスチャ）

`plans/PLAN-20260719-p4-new-development-profile.md`（DEVELOPMENT_MODE=new 対応）の
確認項目（プラン Section 5）のうち、静的ファイル検証では確認できない動的E2E項目を
実際に工程を通し実行して検証するために作成した合成XDDPワークスペース。

## 構成

- `xddp.config.md`: `DEVELOPMENT_MODE: new`、`REPOS:` は `widget-svc` の1エントリのみ（シングルリポジトリ）
- `widget-svc/`: ダミーの空gitリポジトリ（README.mdのみ。母体コードが存在しない新規開発を模す）
- `xddp/CR-2026-950/`: 検証用CR（「設定値の読み込みと検証を行う新規モジュール」、UR8件・SP16件の小規模CR）

## このフィクスチャで実機確認済みの項目（P4プラン確認項目2・4に対応）

- **CRS（工程3）:** SPが単一「仕様：」記述になる（Before/After対比なし）。Section 4（影響範囲）が
  「工程5・6aで具体化する（新規開発のためスペックアウトは実施しない）」になる
- **CRS→DSN ルーティング:** `xddp.03.req/SKILL.md` の `DEVELOPMENT_MODE=new` 分岐により、
  レビュアーの次工程受け取り可否レビューが「次工程: DSN（実装方式検討）作成工程」と
  正しくCRS→DSN（新規開発モード）分岐を使用することを確認
- **DSN（工程5）レビューループ:** SPO/funcmapなしで方式比較（案A/B）・AIレビュー→修正→再レビューの
  ループが正常動作
- **MODE=update-design の文法保持（ラウンド2レビュー指摘#11対応の実地確認）:** 工程5の設計判断を
  CRSへフィードバックする際、新設したSP-001-001.001が既存CRSの「仕様：」記法のまま追加され、
  Before/Afterラベルが誤って混入しないことを確認
- **CHD（工程6a）:** 全SPで「#### Before 設計」が「（新規実装のため対象外）」と一律記載されること、
  確認項目（Section 7）に「Inter-SP dependency integration（新規コンポーネント間の依存整合性）」観点が
  含まれ、UR間の具体的な依存関係（Facade⇔ConfigLoader等）を検証する項目として機能することを確認
- **xddp-reviewer のCHDチェック:** SPO不在時も新規開発モード分岐で正しく評価され、
  SPO不在自体を理由にした誤った🔴指摘は発生しないことを確認（実際の🔴指摘はCHD内容自体の
  整合性問題であり、P4分岐とは無関係）
- **TSP（工程9）:** Section 3.4「回帰テスト」が「回帰テスト（新規開発モード：Inter-SP dependency
  integration）」に置き換わり、CHDの確認項目から依存整合性TCを導出すること、テーブル構造
  （TC番号・テスト項目・確認意図・自動化）が維持されることを確認

## 未完了・スコープ外（検証目的のため意図的に省略）

- UR-003〜UR-008のCHD・関連TSPは未生成（CHD-CR-2026-950.mdインデックスに明記）。
  分岐ロジックの動作確認が目的のため、全UR完走はスコープ外とした
- CRS Excel再生成（UR-016）は本環境にopenpyxl未インストールのためスキップ（環境要因。P4とは無関係）
- 工程7以降（コーディング・静的検証・テスト実行・最新仕様書作成）は未着手

## 検証中に発見した、P4とは無関係の既存の課題

- `chd_sp_coverage.py`（`ClaudeCode/.claude/skills/xddp.06.design/scripts/`）の
  `extract_covered_sp_ids` が `TM_HEADING` の2行後を固定的にテーブル開始位置とみなしているため、
  テンプレート（`06_change-design-document-template.md`）が示す「見出し→空行→ガイダンス引用→空行→表」
  という正規の構成（ガイダンス引用文を残した場合）ではテーブルの検出に失敗し、当該ファイルのSPが
  すべて「未カバー」と誤判定される（CHD-CR-2026-950-UR-001.md で実際に再現。UR-002はガイダンス
  引用文を省略した出力だったため誤判定されなかった）
- `crs_md2excel.py` のMarkdownパーサが、親URを持たないSR（USDMの例外的パターン。本CRのSR-009-001
  「スコープ除外の宣言」等）を直前のUR見出しの子として誤って取り込む（CRS-CR-2026-950.md
  レビュー指摘#7で発見）

## 再実行する場合

```
cd test-fixtures/scratch-workspace-p4-new-mode
# /xddp.06.design CR-2026-950 で UR-003以降のCHD生成を再開できる
```
