# 共有定数・グローバル変数 — alert

> 更新ルール: Upsert（定数名で識別して上書き更新）。出典は（CR-NNN）で記録。
>
> **⚠️ 暫定ドメイン名:** `alert` は AI が SPO 内容（アラート重大度レベル）から推定した暫定値です。人による確認・命名修正を推奨します（OUTPUT_FILE 参照）。

| 定数名 / 変数名 | 型 | 値 / 初期値 | 定義場所 | 参照モジュール | 説明 | 出典 |
|---|---|---|---|---|---|---|
| SEVERITY_LOW | str | "LOW" | device-svc | device-svc, notify-svc | 軽微なアラート（通知遅延可） | CR-2026-900 |
| SEVERITY_MEDIUM | str | "MEDIUM" | device-svc | device-svc, notify-svc | 通常アラート | CR-2026-900 |
| SEVERITY_HIGH | str | "HIGH" | device-svc | device-svc, notify-svc | 緊急アラート（即時通知） | CR-2026-900 |
