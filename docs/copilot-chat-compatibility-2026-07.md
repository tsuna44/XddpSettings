# GitHub Copilot Chat（VS Code）との互換性調査

> **作成日**: 2026-07-19
> **調査方法**: WebSearch / WebFetch（公式VS Codeドキュメントへの直接アクセスを中心に、一部コミュニティ記事で補完）
> **目的**: 本リポジトリ（XDDPツール、Claude Code専用実装）を GitHub Copilot Chat 上でも動作させる場合の
> 前提条件を整理する。[PLAN-20260628-copilot-chat-pilot-port.md](../plans/PLAN-20260628-copilot-chat-pilot-port.md)
> （2026-06-28時点の移植プラン）にある未確認事項のうち、本調査で解決したものを更新する位置づけ。

## 信頼度の表記ルール

このドキュメントでは、事実の確からしさを示すため各項目に以下のタグを付ける。

| タグ | 意味 |
|---|---|
| 🟢 一次情報・逐語確認済み | 公式ドキュメントを直接fetchし、原文を逐語抽出して確認 |
| 🟡 一次情報・要約経由 | 公式ドキュメントは確認したが、AIによる要約を介しており逐語確認まではしていない |
| 🟠 二次情報・複数ソースで整合 | 公式ドキュメントに明記はないが、コミュニティ記事等の複数ソースで内容が一致 |
| 🔴 未確認・実機検証要 | ドキュメント上の記載がない、または断定できる根拠が確認できていない |

---

## 1. Agent Skills（`.claude/skills/`）

🟢 プロジェクトレベル・ユーザーレベルともに公式サポート対象。

公式ドキュメント（`code.visualstudio.com/docs/agent-customization/agent-skills`）原文：

> "Project skills, stored in your repository `.github/skills/`, `.claude/skills/`, `.agents/skills/`"
> "Personal skills, stored in your user profile `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/`"

- **リポジトリ直下** `.claude/skills/` と、**ユーザーホーム** `~/.claude/skills/` の両方が公式に検出対象。
- 本リポジトリの `setup.sh` によるデプロイ先（`~/.claude/skills/`）は、この「Personal skills」に該当するため、
  **追加設定なしでそのまま読める**と判断できる。
- ファイルは Claude Code と同じ `SKILL.md`（フロントマター + Markdown本文）形式。`name`/`description` は必須。
  `user-invocable: false` 等のフィールドもCopilot側がドキュメント上でサポート。

🟡 未確認事項: Claude Code固有のフロントマター拡張（例: 本リポジトリの `xddp.common/SKILL.md` が使う
`user-invocable: false`）が完全に無視されるのか、エラーになるのかは、明示的な断定を公式ドキュメントから
得られていない。「利用不可なツールは無視される」という別項目の記述から類推できるのみ。

---

## 2. Custom Agents（`.claude/agents/`）

### 2.1 プロジェクト（ワークスペース）レベル

🟢 公式サポート対象。原文（`code.visualstudio.com/docs/agent-customization/custom-agents`）：

> "VS Code also detects `.md` files in the `.claude/agents` folder, following the Claude sub-agents format.
> This enables you to use the same agent definitions across VS Code and Claude Code."

- Copilot純正のカスタムエージェントは `*.agent.md` 拡張子を要求するが、`.claude/agents/` 配下は例外的に
  素の `*.md`（本リポジトリの `xddp-analyst-agent.md` 等そのままの命名）で認識される。
- ツール指定はClaude側がカンマ区切り文字列（例: `Tools: Read, Grep, Glob, Write, Edit`）、Copilot純正は
  YAML配列だが、VS Code側がClaudeのツール名をCopilotのツール名にマッピングして解釈するとドキュメントに明記。

### 2.2 ユーザー（ホームディレクトリ）レベル

🔴 **`~/.claude/agents/` はユーザーレベル自動検出の対象として明記されていない。**

同ドキュメントでユーザープロファイルの既定パスとして挙げられているのは：

> "User profile: `~/.copilot/agents` or your user data (specific to your VS Code profile)"

`~/.claude/agents` はこのリストに含まれない。Skills（1節）とは異なり、**Agentsについてはユーザーレベルの
Claude互換パスがドキュメント上サポートされていない**という非対称性がある。

- **本リポジトリへの影響**: `ClaudeCode/.claude/agents/` は `setup.sh` により `~/.claude/agents/`
  （ユーザーレベル）へ配置される運用だが、この配置のままではCopilot Chatから自動検出されない可能性が高い。
  Copilotで使うには、各ワークスペース（母体リポジトリ直下）に `.claude/agents/` または `.github/agents/`
  としてコピーする運用に切り替える必要が出てくる。

### 2.3 回避策: `chat.agentFilesLocations` 設定での明示指定

🟡 設定自体の存在と用途は公式ドキュメントで確認済み：

> "You can configure additional file locations for workspace custom agent files with the
> **chat.agentFilesLocations** setting."

🟠 具体的な挙動（複数のコミュニティ記事で一致、ただし公式ドキュメントの詳細ページでは未確認）:

- **絶対パスを指定可能**。設定例に `/home/yourusername/.copilot/agents` のようなホームディレクトリの
  絶対パスが含まれている。
- **`~`（チルダ）は自動展開されない**。`~/.claude/agents` とそのまま書いても解決されず、
  `/Users/tsuna/.claude/agents` のようにフルパスへ展開して書く必要がある。
- 設定は "workspace-scoped, restricted: true" とされ、Workspace Trust ダイアログの対象になる
  （User settings.json に書いた場合に全ワークスペースへ既定値として効くかどうかは未検証）。

**結論（🔴実機未検証）**: `~/.claude/agents/` を自動検出させることはできないが、
`chat.agentFilesLocations` にフルパスで明示登録すれば読み込める可能性が高い。ただし挙動の詳細は
一次情報での断定ができておらず、実際に設定して動作確認するまでは確定情報として扱わない。

---

## 3. コンテキスト分離モデルの比較

Claude CodeのTask tool（サブエージェント）とVS Code Copilot Chatの `agent/runSubagent` の
コンテキスト分離モデルは、確認できた範囲では近い設計だった。

🟢 VS Code側の該当記述は逐語確認済み（`code.visualstudio.com/docs/agents/subagents`、原文引用）:

> "The main agent starts a subagent, passing only the relevant subtask."
> "The subagent works autonomously and returns a summary."

| 項目 | Claude Code（Task tool） | VS Code Copilot Chat（`agent/runSubagent`） |
|---|---|---|
| 親から渡る情報 | 親の会話全履歴は渡らず、タスク用プロンプトのみ | 同左（🟢逐語確認: "passing only the relevant subtask"） |
| 親へ返る情報 | 最終結果のみ（詳細ログは分離） | 同左（🟢逐語確認: "returns a summary"） |
| 名指しでの呼び出し | 呼び出し元（SKILL.md等）が `subagent_type=` で明示指定 | 🟡 `agents:` フロントマターの許可リスト＋指示文中の名指しで、決定的に狙ったエージェントを呼べる（1回のfetchで確認、複数ソースでの裏取りはしていない） |
| 前提条件 | 常時利用可能 | `agent/runSubagent` ツールの有効化が前提（🟡） |

---

## 4. サブエージェントのネスト呼び出し

🟢 実装されている。逐語確認済み（同ドキュメント、直接fetch + 別経由のWebSearchで独立に整合確認）:

> "By default, subagents themselves cannot invoke further subagents."
> 「有効化するには `chat.subagents.allowInvocationsFromSubagents` 設定を有効にする（デフォルト `false`）」
> "When enabled, subagents can spawn their own subagents, up to a maximum nesting depth of 5."

- デフォルトは無効（無限ループ防止のため意図的にopt-in設計）。
- 有効化した場合の最大ネスト深度は5。
- 2026年4月頃のVS Codeアップデートで追加された機能と見られる（🟠、VS Code Weekly記事の日付から推測）。

**本リポジトリへの影響**: XDDPエージェント構成で多段呼び出し（サブエージェントが別のサブエージェントを
呼ぶ構成）がある場合、`chat.subagents.allowInvocationsFromSubagents` を明示的に有効化する必要がある。
現状の `ClaudeCode/.claude/agents/` 内に多段呼び出し構成があるかどうかは本調査では確認していない。

---

## 5. 未解決・実機検証が必要な事項（まとめ）

- [ ] 🔴 `~/.claude/agents/`（ユーザーレベル）を `chat.agentFilesLocations` で明示登録した場合に
      実際に読み込まれるか。フルパス指定・User settings.json記載時の全ワークスペースへの適用可否を含む。
- [ ] 🟡 Claude Code固有のフロントマターフィールド（`user-invocable: false` 等）がCopilot側で
      エラーにならず無視されるか。
- [ ] 🟡 `agents:` フロントマター許可リストによる名指しサブエージェント呼び出しの確実性
      （PLAN-20260628側では未確定のツールID対応表の問題とも関連）。
- [ ] 🟠→要実機 `chat.agentFilesLocations` のtilde非展開・絶対パス対応・スコープの詳細（公式ドキュメントの
      当該設定の専用ページ相当が見つからず、コミュニティ記事の一致で代替確認した状態）。

## 6. PLAN-20260628-copilot-chat-pilot-port.md との関係

2026-06-28時点のプランでは「Copilot Agent Skills には Claude Code の `~/.claude/` のような共通デプロイ先
パスの仕組みが確認できておらず（未確認）」として、`CopilotChat/.github/` 配下への全面フォーク（実体コピー）
を前提にしていた。

今回の調査で判明した差分：

- **Skills**: `~/.claude/skills/` はユーザーレベルで公式サポート対象と確認できた（1節）。
  そのため `~/.claude/skills/xddp.common/SKILL.md` 等は `CopilotChat/.github/skills/` へコピーしなくても、
  既存の `~/.claude/skills/` デプロイ先のままCopilot Chatから読める可能性がある（🔴実機未検証だが、
  ドキュメント上の記載としては明確）。
- **Agents**: 逆に `~/.claude/agents/`（ユーザーレベル）はサポート対象外と判明した（2.2節）。
  プランがワークスペース直下への配置（`.github/agents/` または `.claude/agents/`）を前提としていたのは、
  この非対称性を踏まえると妥当な設計だったことになる。

いずれもプラン自体の記述を変更するものではないため、`plans/` 側の更新はこのドキュメントの承認プロセス外で
別途検討する。

---

## 参考資料（出典URL）

- [Use Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [Custom agents in VS Code](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [Subagents in Visual Studio Code](https://code.visualstudio.com/docs/agents/subagents)
- [vscode-docs/docs/copilot/agents/subagents.md（GitHub一次ソース）](https://github.com/microsoft/vscode-docs/blob/main/docs/copilot/agents/subagents.md)
- [VS Code Weekly: AI Gets an Effort Dial and Nested Subagents（2026-04-01）](https://htek.dev/articles/vscode-weekly-2026-04-01)
- [Custom Copilot Agents in VS Code: Fixes & Best Practices（コミュニティ記事、chat.agentFilesLocations詳細）](https://devactivity.com/insights/unlocking-custom-copilot-agents-in-vs-code-a-developer-s-guide-to-enhanced-productivity/)
- 内部: [PLAN-20260628-copilot-chat-pilot-port.md](../plans/PLAN-20260628-copilot-chat-pilot-port.md)

---

**最終更新**: 2026-07-19
