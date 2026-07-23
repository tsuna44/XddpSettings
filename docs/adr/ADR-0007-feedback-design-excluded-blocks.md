# ADR-0007: xddp.feedback design で3ブロックを除外する根拠

Status: Accepted
Date: 2026-07-12

## Context

`/xddp.06.design`「## Step C'」と `/xddp.feedback`（DOC_TYPE=design）の「## Step 5」は
一部ロジックが重複しており、`/xddp.06.design` 側の複数ブロックを `/xddp.feedback` にも
複製すべきかを個別に判断する必要がある。

## Decision

以下「適用しない」3ブロックは複製しない: (1) 見出し `## Step C'` 直後のコメント注記と
`progress.md` 6b詳細ステップ更新行、(2) 太字ラベル `**progress.md の 成果物 列を更新**` のブロック、
(3) 末尾の「Tell the user」ブロック。
一方、太字ラベル `**警告の出力**` のブロック（「CHD未対応SPの警告」「SP間ファイル衝突の警告」
「未実装SRの警告」の3種）は複製する。

## Consequences

上記3ブロックはいずれもTM生成・CRS更新ロジックとは独立したprogress.md書き込み処理または
`/xddp.06.design` 固有の報告文言であり、これを含めて複製すると「progress.md は更新しない」という
`xddp.feedback` の設計方針と直接矛盾するか、報告内容が二重になる。一方 `**警告の出力**` ブロックは
TM/CRSの整合性に関する実質的な検証結果でありprogress.mdへの書き込みを伴わないため、
`xddp.feedback` でも同一に提示することで `/xddp.06.design` と `/xddp.feedback design` の間で
機能パリティを保ち、事後編集によって生じたCHD未対応SP・SP間衝突・未実装SRを見落とさないようにする。
