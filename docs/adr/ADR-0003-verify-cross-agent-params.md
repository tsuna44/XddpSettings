# ADR-0003: cross検証でCODE_AGENT_SHAREDを使わない理由

Status: Accepted
Date: 2026-07-11

## Context

`xddp-verifier-agent` の cross 検証呼び出しで、他呼び出しと共通の `CODE_AGENT_SHARED` ブロックを
使うか、パラメータを個別指定するかを決める必要がある。

## Decision

`CODE_AGENT_SHARED` は使用せず、パラメータを個別に指定する。

## Consequences

本呼び出しはインタフェース整合性のみを検証するため、コーディング規約 `CODING_RULES`・
`ADDITIONAL_REFS`・`RULEBOOK_CONTEXT` を必要としない。`CR_NUMBER`/`TODAY` のみ値としては
`CODE_AGENT_SHARED` と同一だが、上記の理由によりブロック全体を展開する対象とはしない。
