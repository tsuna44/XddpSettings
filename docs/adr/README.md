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
| [ADR-0005](ADR-0005-knowledge-guide-once.md) | 知識参照ガイドを初回のみ生成する理由 | xddp.close/scripts/promote.py |
| [ADR-0006](ADR-0006-backfill-no-version-bump.md) | BACKFILL_SP_IDSモードで版数をインクリメントしない理由 | xddp-designer-agent.md |
| [ADR-0007](ADR-0007-feedback-design-excluded-blocks.md) | xddp.feedback design で3ブロックを除外する根拠 | xddp.feedback/SKILL.md |
| [ADR-0008](ADR-0008-specout-backend-abstraction.md) | Discovery BFS の参照解決を差し替え可能な Backend として抽象化する理由 | xddp.04.specout/scripts/specout_bfs.py |
| [ADR-0009](ADR-0009-specout-hit-reduction.md) | Discovery BFS のヒット削減（前倒し縮退・簡易 module-priority）の等価性根拠 | xddp.04.specout/scripts/specout_bfs.py |
| [ADR-0010](ADR-0010-specout-parallel-classification.md) | Discovery BFS の波内 classification をチャンク並列化する理由 | xddp.04.specout/SKILL.md, agents/xddp-specout-agent.md, agents/xddp-specout-classifier-agent.md, xddp.04.specout/scripts/specout_bfs.py, xddp.04.specout/scripts/merge_classification.py |
| [ADR-0011](ADR-0011-vcs-abstraction.md) | VCS（バージョン管理システム）抽象層の設計判断（SVN非対応・関数ベースディスパッチ・ブランチ起点解決・dirtyゲート適用範囲 等、20件の決定） | xddp.common/scripts/xddp_vcs.py, xddp.common/SKILL.md, xddp.07.code/SKILL.md, xddp.08.verify/SKILL.md, xddp.10.test-run/SKILL.md, xddp.close/SKILL.md |
| [ADR-0012](ADR-0012-specout-classifier-scope-summary.md) | classifier への CRS 全文配布をやめスコープ要約をチャンク JSON に埋め込む理由 | xddp.04.specout/SKILL.md, agents/xddp-specout-agent.md, agents/xddp-specout-classifier-agent.md, xddp.04.specout/scripts/specout_bfs.py |
| [ADR-0013](ADR-0013-close-promote-script.md) | close-promote を LLM 転写から promote.py へ全面移管する理由 | xddp.close/SKILL.md, xddp.close/scripts/promote.py |

新規 ADR を追加する場合は連番を1つ進め、本表に追記すること。
