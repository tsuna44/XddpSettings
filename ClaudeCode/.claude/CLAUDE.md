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
