# code-knowledge 書き分け規約

## spec.md に書くもの（機能の「今何ができるか」）

- 機能の入力・出力・振る舞いの定義
- 正常系・異常系のシーケンス
- インタフェースの型定義・シグネチャ
- データ構造のフィールド定義

## constraints.md に書くもの（コードの「気をつけること」）

- 制限事項（呼び出しスレッド・タイミング制約・再入不可等）
- 落とし穴・過去の不具合パターン
- 暗黙の前提（コードを読んでも分からないビジネス・ハードウェア制約）
- パフォーマンス感度・非機能特性の観察

## 判断フローチャート

```
SPO Section 5.6 / LL エントリを見て:
  「この情報はモジュールの仕様（どう動くか）か？」
    YES → spec.md（または latest-specs に書かれているはず）
    NO  → 「コードを正しく使う / 修正するための注意事項か？」
      YES → constraints.md（code-knowledge）
      NO  → lessons-learned.md（プロセス知見）
```

## overview/ vs _structures/ の役割分担

| 場所 | 目的 | 管理工程 |
|---|---|---|
| `{DOCS}/{repo}/specs/overview/architecture.md` | 現在の正確なシステム構造（仕様の一部として管理） | xddp.11.specs（工程11） |
| `{DOCS}/{repo}/knowledge/code-knowledge/_structures/` | モジュール間の構造体依存関係 ＋ 落とし穴注記 | xddp.close（クローズ時に蓄積） |

**書き分け基準:**
- `architecture.md`: 「今この時点のシステム構造はこうなっている」（仕様的記述・常に最新に保つ）
- `_structures/{domain}-relations.md`: 「このモジュールがあのモジュールを参照するときの注意点」（経験的知識・CR を重ねるごとに精緻化）

**更新のトリガー:**
- `architecture.md` はモジュール構造が変わるたびに更新する（xddp.11.specs が担当）
- `_structures/` は構造体間の依存関係から生じる落とし穴・制約が判明したときに更新する（xddp.close Step C3.6 が担当）

両ファイルが同一 CR で更新される場合がある（構造体変更 CR）が、記述の視点が異なるため重複ではない。
