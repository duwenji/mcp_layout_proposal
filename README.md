# MCP改善: 複数サーバ階層レイアウト方式

このディレクトリは、最新形式として「MCPサーバごとの配下に `Tools` / `Prompts` / `Resource` を置く」構成のみを採用します。

## 採用する唯一の構成

```text
mcp_servers/
    mcp_server_a/
        server.json          ← サーバーメタデータ（オプション）
        Tools/
            calc.py
        Prompts/
            summarize.py
        Resource/
            profile.py
    mcp_server_b/
        server.json          ← 配置なしでも起動可能
        Tools/
        Prompts/
        Resource/
    ...
    mcp_server_m/
        server.json
        Tools/
        Prompts/
        Resource/
```

- `server.json` はサーバーのメタデータを定義（オプション、配置しない場合は`server://info`でエラーを返します）
- 各 `.py` は `register(server)` を実装します。
- `Resource` は `Resources`、`Tools` は `Tool`、`Prompts` は `Prompt` でも読めます。

## ロードフロー

使用する Transport により異なります。

### Proxy Mode（SSE / Streamable-HTTP）
1. `run_multi_server.py` が起動（transport: sse or streamable-http）
2. `proxy_server.py` をサブプロセスで実行
3. すべてのサーバーを同一プロセス内でビルド
4. FastMCP の ASGI アプリケーション（`sse_app()`）として Starlette にマウント
5. Uvicorn で **1つのポート（8000）** で複数サーバーをパスベース公開
   - `http://localhost:8000/server_a/mcp`
   - `http://localhost:8000/server_b/mcp`

### Debug Mode（STDIO）
**注意: Stdio モードは単一サーバのみをサポートします**

1. `run_multi_server.py` が起動（transport: stdio, --server で単一サーバを指定）
2. `run_server_subprocess.py` を subprocess.Popen で実行
3. サーバーの stdout/stderr を親プロセスがキャプチャ
4. リアルタイムログ監視機能付き（`[server_name]` プリフィックス）
5. FastMCP サーバーを STDIO transport で起動
6. **external access 不可**（開発・デバッグ用）

### アーキテクチャ図

```mermaid
graph TD
    A["User<br/>$ python run_multi_server.py --transport sse"]
    B["User<br/>$ python run_multi_server.py --transport stdio --server server_a"]
    
    A -->|Proxy Mode| PA["proxy_server.py<br/>(Starlette + Uvicorn)"]
    B -->|Debug Mode| MB["run_server_subprocess.py<br/>(Subprocess)"]
    
    PA -->|Mount ASGI<br/>sse_app| SA["FastMCP<br/>server_a"]
    PA -->|Mount ASGI<br/>sse_app| SB["FastMCP<br/>server_b"]
    
    MB -->|Pipe stdout/stderr| P1["FastMCP<br/>server_a<br/>stdio"]
    
    SA --> EP_A["http://127.0.0.1:8000<br/>/server_a/mcp"]
    SB --> EP_B["http://127.0.0.1:8000<br/>/server_b/mcp"]
    
    P1 --> LOG["[server_a] log output<br/>Real-time monitoring"]
```

## 実行方法

### Transport による自動モード選択

`--transport` 値により自動的に実行モードが決まります：

| Transport | Mode | 用途 | 複数サーバ | ポート |
|-----------|------|------|---------|--------|
| `sse` (デフォルト) | Proxy | **推奨** 本番・テスト共通 | ✅ 対応 | 8000 |
| `streamable-http` | Proxy | 双方向通信が必要な場合 | ✅ 対応 | 8000 |
| `stdio` | Debug | 開発時・デバッグ用（単一サーバのみ） | ❌ 非対応 | 不要 |

### 実行例

**Proxy Mode（推奨）- SSE transport（デフォルト）**
```bash
# すべてのサーバーを単一ポートで公開
python run_multi_server.py

# 特定のサーバーのみ
python run_multi_server.py --server server_a server_b

# ホスト・ポートを指定
python run_multi_server.py --host 0.0.0.0 --port 9000

# Streamable-HTTP transport を使用
python run_multi_server.py --transport streamable-http
```

**Debug Mode - STDIO transport（開発用・単一サーバのみ）**

⚠️ **注意**: Stdio モードは単一サーバのみをサポートします。`--server` パラメータで**必ず1つのサーバを指定**してください。

```bash
# 単一サーバをデバッグモードで実行（リアルタイムログ監視機能付き）
python run_multi_server.py --transport stdio --server mcp_server_a

# 出力例：
# Debug Mode (stdio): Starting mcp_server_a
# [mcp_server_a] <log output line 1>
# [mcp_server_a] <log output line 2>
# ...
```

**認可の失敗例：**
```bash
# ❌ エラー: サーバー指定なし
python run_multi_server.py --transport stdio
# → "Stdio mode requires exactly one --server. Available: mcp_server_a"

# ❌ エラー: 複数サーバ指定（Stdio モードは単一のみ）
python run_multi_server.py --transport stdio --server server_a server_b
# → "Stdio mode requires exactly one --server. Available: mcp_server_a, mcp_server_b"
```

### URL パスのカスタマイズ

Proxy モード時、`server.json` に `path` フィールドを指定してURL パスをカスタマイズできます：

```json
{
  "name": "mcp_server_a",
  "path": "api/v1/chat",      ← URL パスを指定
  "version": "1.0.0",
  "description": "Sample MCP server",
  "capabilities": {
    "tools": true,
    "prompts": true,
    "resources": true
  }
}
```

- `path` 未指定の場合 → サーバー名（`mcp_server_a`）がパスになります
- Multi モード（stdio）では無視されます

**例：**
```
http://localhost:8000/api/v1/chat/mcp  ← path="api/v1/chat" の場合
http://localhost:8000/server_a/mcp      ← path 未指定の場合
```

## 管理機能
- **Resource: `server://info`** — server.json から取得したサーバーメタデータ（JSON形式）
- **Resource: `layout://load-report`** — モジュール読み込み結果のレポート
- **Tool: `layout_list`** — 読み込んだモジュール一覧（JSON形式）

`server://info` で、サーバーのメタデータ（バージョン、説明、機能など）を確認できます。

## ファイル一覧
- `multi_server_loader.py`: 階層レイアウトローダ本体
- `run_multi_server.py`: マルチ/プロキシ起動スクリプト（メインエントリーポイント）
- `run_server_subprocess.py`: Stdio モード用シングルサーバ実行スクリプト
- `proxy_server.py`: パスベースプロキシサーバー実装
- `mcp_servers/mcp_server_a/`: サンプルサーバ構成
  - `server.json`: メタデータファイル（オプション）
  - `Tools/calc.py`: ツール実装例
  - `Prompts/summarize.py`: プロンプト実装例
  - `Resource/profile.py`: リソース実装例
- `mcp_layout_proposal.md`: 方式検討メモ

## server.json の形式
各サーバーディレクトリに `server.json` を配置してメタデータを定義します。（**オプション**）

```json
{
  "name": "mcp_server_a",
  "version": "1.0.0",
  "description": "Server description",
  "author": "Author name",
  "capabilities": {
    "tools": true,
    "prompts": true,
    "resources": true
  },
  "features": [
    "feature1",
    "feature2"
  ]
}
```

### フィールド説明
- `name`: サーバー名（任意）
- `version`: バージョン番号（任意）
- `description`: サーバーの説明（任意）
- `author`: 作成者（任意）
- `capabilities`: 有効な機能（任意）
- `features`: このサーバーが提供する機能リスト（任意）

### 備考
- `server.json` がない場合、`server://info` は `{"name": "<server_name>", "error": "No server.json found"}` を返します。
- `server.json` は有効なJSONである必要があります。パース失敗時はエラー例外が発生します。

## Stdio モード（Debug Mode）の詳細

### 単一サーバのみをサポート
Stdio モードは開発・デバッグ用途として、**単一サーバのみをサポート**します。複数サーバが必要な場合は Proxy Mode (SSE) を使用してください。

### リアルタイムログ監視機能
Stdio モードでサーバを起動すると、サーバプロセスの stdout/stderr をリアルタイムで監視できます：

```bash
$ python run_multi_server.py --transport stdio --server mcp_server_a

Debug Mode (stdio): Starting mcp_server_a
[mcp_server_a] INFO: Server starting...
[mcp_server_a] DEBUG: Loading Tools...
[mcp_server_a] DEBUG: Loaded calc.py
...
```

**特徴：**
- `[server_name]` プリフィックス付きで出力を表示
- Ctrl+C で安全に終了（プロセスを graceful shutdown）
- ログファイル出力とは異なり、開発中のインタラクティブなデバッグに最適

### 实装詳細
- `run_multi_server.py --transport stdio` を実行すると `run_server_subprocess.py` が subprocess.Popen で起動されます
- stdout と stderr は親プロセスがパイプでキャプチャします
- リアルタイムで行ごとに読み込み、プリフィックス付きで表示します
