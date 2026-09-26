# ADR-0017: スキルディレクトリ名をドット区切りからハイフン区切りへ統一する

Status: Accepted
Date: 2026-09-21

## Context

`ClaudeCode/.claude/skills/*/SKILL.md` の `name:` フロントマターは、Anthropic 公式仕様
（Agent Skills Best Practices）により小文字・数字・ハイフンのみ許可（ドット禁止）と判明した
（[PLAN-20260921-skill-name-frontmatter.md](../../plans/PLAN-20260921-skill-name-frontmatter.md)）。
この結果、`name:` の値をディレクトリ名の `.` を `-` に置換したものとして追加したが、
ディレクトリ名自体は従来のドット区切り（例: `xddp.01.init`）のまま残り、同一スキルを指す
識別子が2種類（ドット区切りのディレクトリ名／ハイフン区切りの `name:`）に分かれる非対称な
状態になった。

## Decision

`ClaudeCode/.claude/skills/` 配下の全ディレクトリ名（28スキル + 非スキルの共通ファイル
格納庫2件 `xddp.rules`・`xddp.templates`）をハイフン区切りにリネームし、`name:` フロントマター
の値と完全一致させる（例: `xddp.01.init/` → `xddp-01-init/`、`name: xddp-01-init`）。
これに伴い全スキルのスラッシュコマンド名も変わる（例: `/xddp.01.init` → `/xddp-01-init`）。
既存の `OLD_XDDP_DIRS`／`OLD_XDDP_FILES`（`ClaudeCode/setup.sh`）による旧ディレクトリ
クリーンアップの前例に倣い、本リネームでも同様のクリーンアップエントリを追加する。
後方互換シム（旧コマンド名のエイリアス等）は設けない
（CLAUDE.md「後方互換性ポリシー」に基づく一括移行）。

## Consequences

- 利点: ディレクトリ名と `name:` の一致により、スキルの識別子が単一になり、
  `tools/harness/refcheck.py` の一致検査ロジックも agent 版と完全対称な単純比較に簡略化できる。
- リスク: 既存ユーザーのスラッシュコマンド操作習慣（`/xddp.01.init` 等）が変わる破壊的変更。
  `setup.sh` 実行後は旧ディレクトリが `~/.claude/skills/` から削除されるため、`setup.sh`
  未実行のユーザー環境では新旧コマンドが混在した状態になりうる（`setup.sh` の再実行を促す
  必要がある）。
- 今後の再検討条件: 今後新規スキルを追加する際は、CLAUDE.md「新規スキル作成のルール」に
  従いハイフン区切りディレクトリ名を用いること（ドット区切りへの回帰を防ぐ）。
