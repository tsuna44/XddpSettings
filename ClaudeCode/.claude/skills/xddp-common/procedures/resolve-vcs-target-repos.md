# Resolve VCS Target Repos

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Resolve VCS Target Repos

VCS の副作用（ブランチ作成/切替・コミット・revert 案内）の対象となるリポジトリ集合を、
当該 CR が実際に変更設計を持つリポジトリに限定して解決する共通手順。

**Input:**
- `REPO_CANDIDATES`: 候補リポジトリ名のリスト（呼び出し元が `AFFECTED_REPOS` または `REPOS_KEYS` を渡す）
- `CR_PATH`: CRフォルダのパス
- `CR`: CR番号
- `DEVELOPMENT_MODE`（暗黙）: `## CR Resolution`/`## Load Config` 経由で解決済みの値をそのまま参照する
  （`MD2EXCEL_PYTHON_BIN` と同じ扱いのため、apply 呼び出し時に明示的に渡す必要はない）
- `VCS_TYPE`（暗黙）: 同上。手順3の警告の要否判定にのみ使用する（判定ロジック本体は VCS 種別に
  依存しない純粋なファイル存在確認である）

**Output:** `VCS_TARGET_REPOS`

**Process:**
1. If `DEVELOPMENT_MODE` is `new`:
   `VCS_TARGET_REPOS` = `REPO_CANDIDATES` のうち `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`
   （CHD インデックスファイル）が存在するリポジトリのみ。Go to 手順3。
   （`DEVELOPMENT_MODE: new` では工程4がスキップされ SPO が原理的に存在しないため、手順2の判定材料が
   使えない。新規開発ではワークスペース全体が CR の対象であるのが通常であり、CHD ベースの判定＝
   実質的に全リポジトリになることは想定内である）
2. Else（`DEVELOPMENT_MODE` is `change`。既定）:
   `VCS_TARGET_REPOS` = `REPO_CANDIDATES` のうち `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
   （スペックアウト成果物）が存在するリポジトリのみ。
   （本プロシージャは同ファイルの Read を行わず**存在確認のみ**を行う）
3. `VCS_TARGET_REPOS` が空の場合:
   - If `VCS_TYPE` is `none`: 警告を出さずに空リストを返す（`VCS_TYPE: none` は利用者が VCS 統合機能を
     明示的に無効化した状態であり、そもそも VCS 操作が一切行われない。この状態で「VCS 操作をスキップ
     します／必要に応じて手動でコミットしてください」と案内するのは無意味なノイズであり、`none` を
     選んだ意図とも矛盾する）。
   - Else（`VCS_TYPE` が `auto`/`git`）: `DEVELOPMENT_MODE` に応じた以下の警告を出して空リストを返す
     （`DEVELOPMENT_MODE: new` では工程4が仕様上スキップされるため、「工程4を実施済みか確認」という
     案内は誤誘導になる。判定材料が異なる以上、警告文も分ける）。
     - `DEVELOPMENT_MODE` is `new` の場合:
       Warn: "⚠️ 本 CR の変更設計書（CHD）を持つリポジトリが見つからないため、VCS 操作（ブランチ作成・
       コミット）の対象を特定できません。VCS 操作をスキップします。工程6（変更設計書作成）を実施済みか
       確認し、必要に応じて手動でコミットしてください。"
     - `DEVELOPMENT_MODE` is `change` の場合:
       Warn: "⚠️ 本 CR のスペックアウト成果物（SPO）を持つリポジトリが見つからないため、VCS 操作
       （ブランチ作成・コミット）の対象を特定できません。VCS 操作をスキップします。工程4を実施済みか
       確認し、必要に応じて手動でコミットしてください。"
   （呼び出し元は空リストを受け取ると For each ループが0回になり、結果として VCS 操作が行われない。
   該当工程を完了していれば対象リポジトリの成果物は必ず存在するため、通常フローでこの分岐には到達しない）

**この判定で残る限界:** SPO の存在が表すのは「調査対象にしたリポジトリ」であって「調査の結果、影響ありと
確定したリポジトリ」ではない。`xddp-04-specout/SKILL.md` は全リポジトリのスペックアウトを推奨しており、
Step 0.5 の確認ゲートで人が絞り込まない既定フローでは `VCS_TARGET_REPOS` は結果的に `REPOS_KEYS` と
一致する。すなわち本プロシージャは「限定できる**手段**を用意し、人の絞り込みが VCS 側にも反映される経路を
作る」ものであって、「すべての構成で必ず限定される」ことを保証するものではない。利用者への当面の回避
手段は、`xddp-04-specout` の Step 0.5 で本 CR に無関係なリポジトリを対象から外すことである（この操作が
SPO の有無を通じて VCS 対象にも反映される）。設計判断の詳細は `docs/adr/ADR-0011-vcs-abstraction.md`
Decision 5 を参照。
