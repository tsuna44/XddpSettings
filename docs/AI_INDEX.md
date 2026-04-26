# AI向けナビゲーションインデックス（ルート）

> AIツール（Claude Code / GitHub Copilot）が知識の在り処を一発で把握するためのルートインデックスです。
> Claude Code では `@docs/AI_INDEX.md`、Copilot では `#docs/AI_INDEX.md` で参照してください。

---

## 知識の階層構造

```
docs/
├── AI_INDEX.md              ← 今ここ（ルートインデックス）
├── shared/                  # 複数プロジェクト横断の共通知識
│   ├── AI_INDEX.md
│   └── glossary.md
└── projects/                # プロジェクト別知識
    └── {project-name}/
        ├── AI_INDEX.md      # プロジェクトインデックス
        ├── glossary.md      # プロジェクト固有用語集
        ├── inter-repo/      # リポジトリ間IF文書
        └── repos/
            └── {repo-name}/
                ├── AI_INDEX.md        # リポジトリインデックス
                ├── specs/             # ✅ 承認済みベースライン（AIが信頼して参照）
                │   ├── AI_INDEX.md
                │   └── {module}-spec.md
                ├── knowledge/         # 知見・Tips（承認不要・即時参照可）
                │   ├── lessons-learned.md
                │   └── patterns.md
                └── modules/           # モジュール詳細仕様
                    └── {module-name}/
                        └── spec.md

※ latest-specs/ はプロジェクトルートに自動生成されるドラフト領域。
  xddp.close が人レビュー後に docs/specs/ へ昇格する。AIへの自動注入は行わない。
```

---

## 共通知識（複数プロジェクト横断）

| ファイル | 内容 |
|---|---|
| [shared/AI_INDEX.md](shared/AI_INDEX.md) | 共通知識インデックス |
| [shared/glossary.md](shared/glossary.md) | 全プロジェクト共通用語集 |

---

## プロジェクト一覧

| プロジェクト | インデックス | 備考 |
|---|---|---|
| （プロジェクトを追加してください） | — | — |

> プロジェクト追加時は `docs/projects/{project-name}/` を作成し、上の表にエントリを追加する。

---

## このリポジトリ固有のドキュメント

| ファイル | 内容 |
|---|---|
| [xddp-process-dfd.md](xddp-process-dfd.md) | XDDPプロセス全体のデータフロー図 |
| [ai-knowledge-system-design.md](ai-knowledge-system-design.md) | AI知識システム設計（スケーラビリティ含む） |
| [xddp-ai-era-assessment.md](xddp-ai-era-assessment.md) | 生成AI時代における XDDP の適合性評価 |
| [REQ-2026-001_要求書.md](REQ-2026-001_要求書.md) | 要求書サンプル（REQ-2026-001） |

---

## インデックス更新ルール

- 新規プロジェクト追加 → `docs/projects/{name}/` を作成し「プロジェクト一覧」に追記
- 新規リポジトリ追加 → `docs/projects/{project}/repos/{repo}/` を作成しプロジェクトインデックスに追記
- 新規モジュール追加 → `docs/projects/{project}/repos/{repo}/modules/{module}/` を作成しリポジトリインデックスに追記
- `xddp.close` 実行時に自動更新される
