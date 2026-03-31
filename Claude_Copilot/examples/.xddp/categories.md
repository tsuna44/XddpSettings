# プロジェクト固有 カテゴリ定義

このファイルは `~/claude/xddp/categories.md` より優先される。
プロジェクトルートの `.xddp/categories.md` として配置する。

---

## カスタマイズ例

グローバル定義をベースに「安全規格」カテゴリを追加した例：

```yaml
categories:
  - name: 機能
    description: システムの動作・振る舞い・データ処理を変える仕様
    excel_color: D6E4F0

  - name: デバッグツール
    description: 製品出荷時には無効化されるデバッグ・開発支援機能に関する仕様
    excel_color: E2EFDA

  - name: 安全規格
    description: 機能安全・セキュリティ規格への適合に関する仕様（プロジェクト固有）
    examples:
      - ISO 26262対応
      - MISRA-C準拠
    excel_color: D9D2E9

  - name: テスト
    description: テストケース・テスト手順・テスト環境・テストツールに関する仕様
    excel_color: FFF2CC

  - name: 日程
    description: リリース日・納期・マイルストーン・作業スケジュールに関する仕様
    excel_color: FCE4D6

  - name: 成果物管理
    description: 設計書・仕様書・ソースコード・バイナリなどの成果物の管理・提出・形式に関する仕様
    excel_color: EAD1DC
```
