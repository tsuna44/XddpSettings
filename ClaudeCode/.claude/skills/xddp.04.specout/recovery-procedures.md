# xddp.04.specout Recovery Procedures

> このファイルは `xddp.04.specout/SKILL.md` の Step A（checkpoint状態テーブル）が参照する
> low-frequency リカバリ手順（re-discover・paused-at-limit）。SKILL.md 本体の主経路から分離し、
> 該当分岐が成立したときのみ Read される。他スキルから参照しないこと
> （xddp.common とは異なり specout 専用ロジックのため）。

## Re-discover Processing

適用条件: checkpoint 状態 = `complete` かつ `RE_DISCOVER = true`

**Input:** `CR_PATH`, `repo`, `ENTRY_POINTS`, `TODAY`

**Process:**
1. `{CR_PATH}/04_specout/{repo}/checkpoint.md` を読み取り、
   既存の `Visited` セットと `最終完了 Wave` 番号（= N）を取得する。
2. checkpoint.md を以下の内容で上書きする（フィールド名は xddp-specout-agent.md Step 2d 準拠）:
   - 状態: `in-progress`
   - Visited: 既存の Visited セットをそのまま保持（平文改行区切り）
   - Frontier: ENTRY_POINTS の各シンボルを HIGH 平文形式（1行1シンボル）で設定
   - 現在 Wave 番号: N（最終完了 Wave の番号をそのまま設定。Wave 書き込み完了 = true との組み合わせで
     エージェントが自動的に Wave N+1 から再開するため、ここで +1 しない）
   - Wave 書き込み完了: `true`（エージェントの再開ロジック「Wave N は完了済み → Wave N+1 から継続（discovery-log.md に追記）」
     を利用するため `true` を設定する。`false` にするとエージェントが Wave N を書き直す動作になり不正な重複が生じる）
   - 上限到達回数: `0`（前回サイクルとは独立した新しい BFS セッションとして扱うためリセット。
     リセットしない場合、前回の上限到達回数を引き継いで不要な自動パス B 移行が発生しうる）
3. `{CR_PATH}/04_specout/{repo}/discovery-log.md` の末尾に以下を追記する
   （手順5のエージェント呼び出しより先に実行すること。エージェントが Wave N+1 を追記モードで書くため、
   マーカーはその直前に置く必要がある）:
   ```
   ---
   ## [re-discover] セッション開始: {TODAY}
   追加エントリポイント: {ENTRY_POINTS}
   Wave {N + 1} から再開（既存 visited セット引き継ぎ）
   ```
4. progress.md の `## 備考・メモ` に以下を追記する（セクションがなければ末尾に作成）:
   `re-discover 実施（{TODAY}）追加エントリポイント: {ENTRY_POINTS}`
   （備考追記は checkpoint 状態 = complete の場合のみ。checkpoint なし・in-progress・paused の場合は追記しない）
5. Discovery エージェントを通常通り呼び出す（エージェントは `in-progress` として再開ロジックを実行し、
   Wave N+1 から BFS を継続する）。

## Paused-at-limit Handling

適用条件: checkpoint 状態 = `paused-at-limit`

**Input:** `CR`, `CR_PATH`, `repo`, `MAX_WAVE_DEPTH`

**Process:**
状態が "paused-at-limit" の場合、人に対して以下を提示する:

> ⚠️ {repo} の Discovery が探索上限（{MAX_WAVE_DEPTH} 波）に達して一時停止しています。
> `{CR_PATH}/04_specout/{repo}/discovery-log.md` の残存フロンティア一覧を確認して、
> 以下 A/B/C のいずれかを選択してください:
>
> **A（フロンティア剪定・BFS 再開）:**
>   `{CR_PATH}/04_specout/{repo}/checkpoint.md` の Frontier から不要シンボルを削除し、
>   状態フィールドを `in-progress` に手動で書き換えてください。
>   その後 `/xddp.04.specout {CR}` を再実行すると、スキルが自動で Discovery を再起動します。
>   ※ Frontier の書式: HIGH シンボルは平文、MEDIUM シンボルは `symbol[MEDIUM:filepath]` 形式
>
> **B（モジュール一括記録）:**
>   残存フロンティアのシンボルが属するモジュール全体を `MODULE-LEVEL` として記録して Discovery を完了します。
>   「B を選択」と入力してください。
>
> **C（スコープ外承認）:**
>   残存フロンティアがスコープ外であることを確認した根拠を記録して Discovery を完了します。
>   「C を選択: {根拠}」と入力してください。

選択肢 B が選ばれた場合:
  1. checkpoint.md から Frontier を読み取り、各シンボルが所属するファイル・モジュールを特定する
  2. discovery-log.md に「⚠️ 継続パス B: 以下のモジュールは探索上限により一括記録。個別調査は設計・テスト工程で実施すること。」を記録する
  3. 該当モジュール配下の全ファイルを確定ファイル一覧に追加（確信度: MODULE-LEVEL）し discovery-log.md を更新する
  4. checkpoint.md の状態を "complete" に更新する

選択肢 C が選ばれた場合:
  1. discovery-log.md に「継続パス C: {ユーザーが提示した根拠}。残存フロンティアをスコープ外として承認。」を記録する
  2. checkpoint.md の状態を "complete" に更新する

## Paused-at-limit-2nd Handling

適用条件: checkpoint 状態 = `paused-at-limit-2nd`

**Input:** `CR_PATH`, `repo`

**Process:**
（エージェントが自動設定するが、エージェント終了前にクラッシュした場合の復旧用。
2回目以降の上限到達につき、人への確認を挟まず自動でパス B 相当を適用する）

上記「Paused-at-limit Handling」の選択肢 B と同じ手順を自動で適用する。
