# ADR-0013: close-promote を LLM 転写から promote.py へ全面移管する理由

Status: Accepted
Date: 2026-08-29

## Context

`xddp.close` Step C2〜C7（成果物昇格・AI_INDEX.md 更新）は `xddp-close-promote-agent.md` が
`Bash` 権限を持たないまま latest-specs→DOCS のファイル全文転写と AI_INDEX.md の7セクション構成を
LLM の Read→Write で行っていた。トークン消費は昇格対象の仕様書総量に比例し、かつ LLM 生成のため
出力構造（見出し・行順・表現）が実行のたびに揺れうる。この揺れにより、close を
`tools/harness/smoke_full.py` の構造プロパティ比較（golden との diff）に組み込んでも偽陽性だらけに
なり、smoke 対象化が事実上不可能だった（`tools/harness/smoke_config.md` が phaseClose を
advisory 対象から除外していた理由）。

## Decision

Step C2〜C7 の全手続き（`xddp-close-promote-agent.md:20-260` 実測）を判断業務ゼロの決定的処理と
結論し、専用エージェントを廃止して `promote.py`（`xddp.close/scripts/`）に一本化する。
オーケストレーター（`xddp.close/SKILL.md`）が `chd_sp_coverage.py`（`xddp.06.design/SKILL.md`）と
同じパターンで直接 Bash 呼び出しする。

検討した代替案（Bash 権限のみ追加した薄いエージェントとして残す）は、残存判断業務がない以上
エージェント層を挟む理由がないため不採用。

## Consequences

トークン消費が仕様書量に依存しなくなる。出力が決定的になるため、close を smoke advisory 対象に
含められるようになる（PLAN-20260829-close-promote-script-and-smoke Stage 2）。

半面、AI_INDEX.md の表構造・LL の `repo:` タグ形式・CHD cross の「インタフェース変更サマリ」表形式が
変わった場合、`promote.py` 側の追随修正が必要になる（LLM が自然文の揺れを吸収していた柔軟性を失う）。
CHD cross の表形式は breaking 列をヘッダ名で検出する実装とし、列順・列数の変化には追随できるが、
breaking 列自体が存在しない場合は「判定不能」として fail-loud に警告する（無警告で「なし」扱いにしない）。
