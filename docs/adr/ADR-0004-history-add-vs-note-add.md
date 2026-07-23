# ADR-0004: re-discover監査ログにhistory-addを使う理由

Status: Accepted
Date: 2026-07-19

## Context

re-discover 実施の監査ログ記録に progress.md 更新スクリプトの `history-add` と `note-add` の
どちらを使うかを決める必要がある。この判断は `plans/PLAN-20260714-p1-deterministic-scripting.md`
（3.3節、ラウンド4レビュー指摘#8対応）で導入された経緯を引き継ぐ。

## Decision

`note-add` ではなく `history-add` を使う（bfs-state.json 状態 = complete の場合のみ実施）。

## Consequences

この監査ログは工程4a が再度 ✅ 完了になっても `## 備考・メモ` の `⚠️ 工程4a:` 行自動削除ロジックの
対象外として残る必要がある。`note-add` で記録すると自動削除の対象になってしまい、監査ログとして
機能しない。
