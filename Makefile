# XDDP 開発時テストハーネス（tools/harness/）のエントリポイント
#
#   make test            L1〜L3 一括（全 unittest + refcheck）。0トークン・数秒。git pre-commit 実用圏
#   make lint            refcheck（検査A/B/C/D）のみ
#   make unit            全 unittest のみ
#   make smoke-full PHASE=NN   L4/L5 full-run スモーク（LLM・予算ガード・隔離HOME）。触った1工程のみ
#   make smoke-full-all        全通し（init→close。稀）
#   make smoke-calibrate [PHASE=NN] [MODEL=haiku]  校正ラン（偽失敗率・トークン実測）
#
# 実行要件: python3（標準ライブラリのみ）・GNU make。smoke-full*／smoke-calibrate のみ `claude` CLI と
# 非対話認証用の環境変数（CLAUDE_CODE_OAUTH_TOKEN優先・追加課金なし／ANTHROPIC_API_KEYフォールバック）が必要。
# Git Bash 環境で python3 が無い場合は `PY=python make test` のように上書きする。

PY ?= python3
HARNESS := tools/harness

.PHONY: test lint unit smoke-full smoke-full-all smoke-calibrate help

test:            ## L1〜L3 一括（0トークン）
	$(PY) $(HARNESS)/run_all.py

lint:            ## refcheck のみ（検査A/B/C/D）
	$(PY) $(HARNESS)/refcheck.py

unit:            ## 全 unittest のみ
	$(PY) $(HARNESS)/run_all.py --only unit

smoke-full:      ## 単一工程 full-run スモーク（LLM・予算ガード）
	$(PY) $(HARNESS)/smoke_full.py --phase $(PHASE)

smoke-full-all:  ## 全通し full-run スモーク（稀）
	$(PY) $(HARNESS)/smoke_full.py --all

smoke-calibrate: ## 校正ラン（工程/モデルを絞ってバッチ分割可）
	$(PY) $(HARNESS)/smoke_full.py --calibrate $(if $(PHASE),--phase $(PHASE)) $(if $(MODEL),--model $(MODEL))

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n", $$1, $$2}'
