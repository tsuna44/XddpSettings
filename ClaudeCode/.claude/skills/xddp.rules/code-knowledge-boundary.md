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
| `{DOCS}/{repo}/specs/overview/architecture.md` | 現在の正確なシステム構造（仕様の一部として管理） | xddp.11.specs（工程11）／ xddp.survey（追記のみ） |
| `{DOCS}/{repo}/knowledge/code-knowledge/_structures/` | モジュール間の構造体依存関係 ＋ 落とし穴注記 | xddp.close（クローズ時に蓄積）／ xddp.survey ／ xddp.update-knowledge |

**書き分け基準:**
- `architecture.md`: 「今この時点のシステム構造はこうなっている」（仕様的記述・常に最新に保つ）
- `_structures/{domain}-relations.md`: 「このモジュールがあのモジュールを参照するときの注意点」（経験的知識・CR を重ねるごとに精緻化）

**更新のトリガー:**
- `architecture.md` はモジュール構造が変わるたびに更新する（xddp.11.specs が担当）
- `_structures/` は構造体間の依存関係から生じる落とし穴・制約が判明したときに更新する
  （xddp.close Step C3.6 ／ xddp.survey の knowledge 昇格 ／ xddp.update-knowledge が担当）

**昇格条件（重要）:** `_structures/` へエントリを作るのは、構造体依存関係に**落とし穴・注意点の記述が
伴う場合のみ**とする。純粋な構造記述（依存図・型定義のみで注意点を伴わないもの）は仕様側
（`specs/overview/architecture.md`・`specs/overview/data-model.md`・`cross/interfaces/{if}/schema.md`）に
置き、`_structures/` へは昇格しない。

両ファイルが同一 CR で更新される場合がある（構造体変更 CR）が、記述の視点が異なるため重複ではない。

## 宛先ルーティング表

> code-knowledge へ書き込む全経路（xddp.close Step C3.6・xddp.survey の knowledge 昇格・
> xddp.update-knowledge Step 3）はこの表を単一情報源とする。
> 宛先パス・テンプレート・セクションをこの表以外の場所に定義してはならない。
>
> **経路ごとの拘束範囲:**
> - **自動抽出経路**（xddp.close Step C3.6・xddp.survey の knowledge 昇格）:
>   全列に拘束される（**昇格条件列を含む**）。
> - **手動登録経路**（xddp.update-knowledge）: **出力パス・テンプレート・セクション列のみ**に拘束される。
>   昇格条件列は適用しない（人が登録対象を判断済みであるため、機械的な条件で拒否しない）。

**判断軸:** 宛先は次の2軸のいずれかに該当するかで決まる。

| 軸 | 問い | 該当する場合 |
|---|---|---|
| 軸1（性質） | 仕様（どう動くか）ではなく、コードを正しく使う・直すための注意事項か | code-knowledge へ |
| 軸2（スコープ） | 単一モジュールに閉じず、モジュール／リポジトリを横断する情報か | code-knowledge へ |

軸2が必要な理由: `specs/{module}/spec.md` はモジュール単位のファイルであり、
モジュールを横断する情報には仕様側に置き場が無い。

**パス略記:** `{KNOW}` = `{DOCS}/{repo}/knowledge/code-knowledge`、
`{XKNOW}` = `{DOCS}/cross/knowledge/code-knowledge`（`IS_MULTI` の場合のみ）。

| 知識種別 | 昇格条件 | 軸 | 出力パス | テンプレート | セクション |
|---|---|---|---|---|---|
| 制約・落とし穴 | 常に | 1 | `{KNOW}/{MODULE}/constraints.md` | `xddp.close/templates/code-knowledge-constraints-template.md` | 既知の制約・落とし穴 ／ 仕様上の暗黙の前提 ／ パフォーマンス・非機能特性 |
| 構造体依存関係 | 落とし穴・注意点の記述が伴う場合のみ | 1 | `{KNOW}/_structures/{DOMAIN}-relations.md` ／ `{XKNOW}/_structures/{DOMAIN}-relations.md` | `xddp.close/templates/code-knowledge-structures-template.md` | 注意事項・制約 |
| 共有定数・列挙値 | モジュール横断／リポジトリ間で共有されるもののみ | 2 | `{KNOW}/_constants/{DOMAIN}-constants.md` ／ `{XKNOW}/_constants/{DOMAIN}-constants.md` | `xddp.close/templates/code-knowledge-constants-template.md` | — |
| 機能間フロー（シーケンス） | 複数モジュール／複数リポジトリにまたがるフローのみ | 2 | `{KNOW}/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md` ／ `{XKNOW}/_flows/...` | `xddp.close/templates/code-knowledge-flows-sequence-template.md` | — |
| データフロー図（DFD） | 複数モジュールにまたがる場合のみ | 2 | `{KNOW}/_flows/{DOMAIN}-{FLOW_NAME}-dfd.md` | `xddp.close/templates/code-knowledge-flows-dfd-template.md` | — |
| 変数データフロー（callgraph） | モジュール横断で更新・参照される識別子のみ | 2 | `{KNOW}/_flows/{DOMAIN}-{VAR_NAME}-callgraph.md` | `xddp.update-knowledge/templates/callgraph-template.md` | — |

**per-repo / cross の使い分け:**
単一リポジトリ内のモジュール間で共有される情報 → per-repo（`{KNOW}`）。
リポジトリ間で共有される情報 → cross（`{XKNOW}`。`IS_MULTI` の場合のみ）。

**昇格条件を満たさない情報の行き先:** 仕様側（`specs/{module}/spec.md`・
`specs/overview/architecture.md`・`specs/overview/data-model.md`・`cross/interfaces/{if}/schema.md`）。
code-knowledge へは昇格しない。
