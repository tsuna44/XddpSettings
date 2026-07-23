# docs/adr — XddpSettings 設計判断記録

このディレクトリは **XddpSettings リポジトリ自身**（XDDP ツールのスキル・エージェント定義）の
設計判断を記録する。**開発リポジトリ限定の参考資料であり、`setup.sh` によるデプロイ対象
（`~/.claude/`）には含まれない。** スキル・エージェント本文からの参照は実行時に読む必要がなく、
背景を知りたい開発者向けの手がかりとして機能する。

対象開発プロジェクト（母体リポジトリ）側の ADR（`project-rulebook.md` に蓄積するもの）とは別物。

| ADR | タイトル | 対象ファイル |
|---|---|---|
| [ADR-0001](ADR-0001-sp-id-check-timing.md) | SP-ID照合チェックを工程5開始時に行う理由 | xddp.05.arch/SKILL.md |
| [ADR-0002](ADR-0002-coverage-backfill-ambiguous-repo.md) | カバレッジ自動補完でrepoが一意に決まらない場合に補完しない理由 | xddp.06.design/SKILL.md |
| [ADR-0003](ADR-0003-verify-cross-agent-params.md) | cross検証でCODE_AGENT_SHAREDを使わない理由 | xddp.07.code/SKILL.md |
| [ADR-0004](ADR-0004-history-add-vs-note-add.md) | re-discover監査ログにhistory-addを使う理由 | xddp.04.specout/recovery-procedures.md |
| [ADR-0005](ADR-0005-knowledge-guide-once.md) | 知識参照ガイドを初回のみ生成する理由 | xddp-close-promote-agent.md |
| [ADR-0006](ADR-0006-backfill-no-version-bump.md) | BACKFILL_SP_IDSモードで版数をインクリメントしない理由 | xddp-designer-agent.md |
| [ADR-0007](ADR-0007-feedback-design-excluded-blocks.md) | xddp.feedback design で3ブロックを除外する根拠 | xddp.feedback/SKILL.md |

新規 ADR を追加する場合は連番を1つ進め、本表に追記すること。
