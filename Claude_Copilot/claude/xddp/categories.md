# XDDP 変更要求仕様書 カテゴリ定義

このファイルは `xddp.04.crs-draft` および `xddp.06.crs-excel` が参照するカテゴリ定義。
プロジェクトに合わせてカテゴリ名・定義・色を変更できる。

**優先順位**：
1. プロジェクトルートの `.xddp/categories.md`（プロジェクト固有・最優先）
2. `~/claude/xddp/categories.md`（グローバル共通）
3. コマンドファイル内のデフォルト定義（フォールバック）

---

## カテゴリ一覧

```yaml
categories:
  - name: 機能
    description: システムの動作・振る舞い・データ処理を変える仕様
    examples:
      - センサーのしきい値変更
      - 通信プロトコルの変更
      - 演算ロジックの変更
    not_for:
      - テスト手順
      - ドキュメント更新
      - リリース日程
    excel_color: D6E4F0   # 青系

  - name: デバッグツール
    description: 製品出荷時には無効化されるデバッグ・開発支援機能に関する仕様
    examples:
      - デバッグログの出力仕様
      - 診断コマンドの追加
      - シリアルモニタ出力
    not_for:
      - 製品機能として常時動作するもの
    excel_color: E2EFDA   # 緑系

  - name: テスト
    description: テストケース・テスト手順・テスト環境・テストツールに関する仕様
    examples:
      - テストケースの境界値変更
      - テスト環境のセットアップ手順
      - 回帰テスト範囲の変更
    not_for:
      - 製品の機能仕様
    excel_color: FFF2CC   # 黄系

  - name: 日程
    description: リリース日・納期・マイルストーン・作業スケジュールに関する仕様
    examples:
      - v2.3リリース日
      - 顧客検収期限
      - 中間レビュー日程
    not_for:
      - 機能要件
    excel_color: FCE4D6   # 橙系

  - name: 成果物管理
    description: 設計書・仕様書・ソースコード・バイナリなどの成果物の管理・提出・形式に関する仕様
    examples:
      - 変更設計書の提出形式
      - ソースコードのブランチ管理方針
      - バイナリの命名規則
    not_for:
      - 製品の動作仕様
    excel_color: EAD1DC   # 赤系
```

---

## カスタマイズ方法

カテゴリを追加・変更・削除する場合は上記の `categories:` ブロックを編集する。

**カテゴリを追加する場合の例：**
```yaml
  - name: 安全規格
    description: 機能安全・セキュリティ規格への適合に関する仕様
    examples:
      - ISO 26262対応
      - MISRA-C準拠
    not_for:
      - 通常の機能仕様
    excel_color: D9D2E9   # 紫系
```

**注意事項：**
- カテゴリ名は変更要求仕様書テンプレートとExcel生成スクリプトと一致させること
- `excel_color` は6桁の16進数カラーコード（`#`なし）
- カテゴリを削除した場合、既存の成果物との整合性を確認すること
