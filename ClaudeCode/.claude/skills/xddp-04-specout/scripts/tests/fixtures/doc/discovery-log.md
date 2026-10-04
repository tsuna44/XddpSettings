# Discovery Log — CR-2026-970 / svc

## 探索設定
- 開始日時: 2026-10-04
- 初期シンボル（Wave 0）:
  - `session_start`

## grep未対応パターン（手動確認必要）
| パターン種別 | 根拠（CRS/コードより） | 確認状況 |
|---|---|---|
| function-pointer-call | src/net/conn.c:2（cb(v)） | ⬜ 未確認 |

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH-compound | `\b(session_start)\b` | 全域 | 2 |

**除外:** tests/

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | `session_start` | src/auth/session.c | 1 | `int session_start(const char *user) {` | `session_start` | slice(none=self-def) | HIGH | — | seed(session_start) |
| W0-R2 | W0-C1 | `session_start` | src/auth/login.c | 4 | `int rc = session_start(user);` | `login_check` | slice(escape=return) | HIGH | `login_check` | seed(session_start) |

→ Wave 1 frontier: `login_check`[HIGH]

### 件数一致検証

| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |
|---|---|---|---|---|---|---|
| W0-C1 | 2 | 0 | 0 | 0 | 2 | ✅ |

## Wave 1

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W1-C1 | HIGH-compound | `\b(login_check)\b` | 全域 | 4 |

**除外:** tests/

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 2 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W1-R1 | W1-C1 | `login_check` | src/net/conn.c | 2 | `return login_check("x") + shared(fd);` | `conn_open` | slice(escape=return) | HIGH | `conn_open` | W0-R2 |
| W1-R2 | W1-C1 | `login_check` | src/util/helper.c | 2 | `return login_check("h") + util_fn();` | `helper` | slice(escape=return) | HIGH | `helper` | W0-R2 |
| W1-R3 | W1-C1 | `login_check` | main.c | 2 | `return login_check("m") + util_fn();` | `main` | slice(escape=return) | HIGH | `main` | W0-R2 |
| W1-R4 | W1-C1 | `login_check` | src/auth/login.c | 3 | `int login_check(const char *user) {` | `login_check` | slice(none=self-def) | HIGH | — | W0-R2 |

→ Wave 2 frontier: `conn_open`[HIGH], `helper`[HIGH], `main`[HIGH]

### 件数一致検証

| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |
|---|---|---|---|---|---|---|
| W1-C1 | 4 | 0 | 0 | 0 | 4 | ✅ |

## Wave 2

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W2-C1 | HIGH-compound | `\b(conn_open)\b` | 全域 | 3 |

**除外:** tests/

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 3 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W2-R1 | W2-C1 | `conn_open` | src/net/sub/x.c | 2 | `return conn_open(1);` | `x_fn` | slice(escape=return) | HIGH | `x_fn` | W1-R1 |
| W2-R2 | W2-C1 | `conn_open` | src/net/other.c | 2 | `return conn_open(2) + shared(1);` | `other` | slice(escape=return) | HIGH | `other` | W1-R1 |
| W2-R3 | W2-C1 | `conn_open` | src/net/conn.c | 1 | `// conn_open comment` | - | false-positive | — | — | W1-R1 |

→ Wave 3 frontier: （なし）

### 件数一致検証

| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |
|---|---|---|---|---|---|---|
| W2-C1 | 3 | 0 | 0 | 0 | 3 | ✅ |

## 確定した波及ファイル一覧（Documentation チェックリスト）
| ファイル | 発見波 | 最高確信度 | ドキュメント化 |
|---|---|---|---|
| src/auth/session.c | Wave 0 | HIGH | ⬜ 未 |
