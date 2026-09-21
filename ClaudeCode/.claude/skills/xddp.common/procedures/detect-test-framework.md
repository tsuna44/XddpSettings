# Detect Test Framework

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Detect Test Framework

リポジトリのテストフレームワークを自動検出して返す共通手順。

**Input:**
- `REPO_PATH`: リポジトリのルートパス
- `LANGUAGE`（任意）: 言語ヒント（`python`, `java`, `javascript`, `go`, `ruby` 等）。指定時は対応フレームワークのみを検出対象とする。

**Process:**
0. If `LANGUAGE` is provided: Limit detection to frameworks matching `{LANGUAGE}` (e.g., `python` → pytest のみチェック).
1. Check for framework configuration files in `{REPO_PATH}`:
   - `pytest.ini`, `setup.cfg [tool:pytest]`, `pyproject.toml [tool.pytest]` → Python/pytest
   - `pom.xml` with junit dependency → Java/JUnit
   - `package.json` with jest/vitest dependency → JavaScript/Jest or Vitest
   - `go.mod` → Go/testing
   - `Gemfile` with rspec → Ruby/RSpec
2. If exactly one framework is detected → return `(FRAMEWORK_NAME, VERSION, CONFIG_FILE)`.
3. If multiple or none detected:
   - Multiple: return all candidates, note ambiguity.
   - None: return `(unknown, -, -)` and recommend manual specification.
