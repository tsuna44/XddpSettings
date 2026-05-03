# XDDP グローバル設定

## スキル・コマンドファイルの同期ルール

`~/.claude/skills/xddp.0X.*.md` を変更した場合、対応する `~/.claude/commands/xddp.0X.*.md` の要約も必ず同時に更新すること。

### 対応表

| スキルファイル | コマンドファイル |
|---|---|
| `~/.claude/skills/xddp.01.init.md` | `~/.claude/commands/xddp.01.init.md` |
| `~/.claude/skills/xddp.02.analysis.md` | `~/.claude/commands/xddp.02.analysis.md` |
| `~/.claude/skills/xddp.03.req.md` | `~/.claude/commands/xddp.03.req.md` |
| `~/.claude/skills/xddp.04.specout.md` | `~/.claude/commands/xddp.04.specout.md` |
| `~/.claude/skills/xddp.05.arch.md` | `~/.claude/commands/xddp.05.arch.md` |
| `~/.claude/skills/xddp.06.design.md` | `~/.claude/commands/xddp.06.design.md` |
| `~/.claude/skills/xddp.07.code.md` | `~/.claude/commands/xddp.07.code.md` |
| `~/.claude/skills/xddp.08.test.md` | `~/.claude/commands/xddp.08.test.md` |
| `~/.claude/skills/xddp.09.specs.md` | `~/.claude/commands/xddp.09.specs.md` |
| `~/.claude/skills/xddp.review.md` | `~/.claude/commands/xddp.review.md` |
| `~/.claude/skills/xddp.excel2md.md` | `~/.claude/commands/xddp.excel2md.md` |

### commands ファイルの書き方

- スキルへの委譲を宣言し、処理ステップを番条書きで要約する
- 詳細ロジックはスキルファイルに持ち、commands には書かない
- `See ~/.claude/skills/xddp.0X.*.md for full orchestration logic.` で締める

### ファイル生成の承認

commands, skills, template のファイルを作成するときに write 確認を人にせず、書き込みします。

---

## xddp.config.md 探索アルゴリズム

XDDP スキル（`xddp.01.init` を除く）は、`xddp.config.md` を以下の手順で発見する。

1. cwd に `xddp.config.md` が存在するか確認する
2. 存在しない場合、親ディレクトリを順に確認する（cwd → parent → grandparent → …）
3. ファイルが見つかった最初のディレクトリを **ワークスペースルート** とし、そのファイルを読み込む
4. ファイルシステムのルートまで探索しても見つからない場合は、
   "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。"
   を報告して停止する

> **Note:** `xddp.01.init` のみ例外。init は cwd に `xddp.config.md` を生成するコマンドであり、上位探索は行わない。
