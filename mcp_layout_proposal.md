# AI Agent Module方式によるMCP改善案 (最新形式)

## 方針
本検討では、最新形式として以下のみを採用する。

- `mcp_servers/<server_name>/Tools`
- `mcp_servers/<server_name>/Prompts`
- `mcp_servers/<server_name>/Resource`

単一フォルダへ集約する旧形式は採用しない。

## 目的
- サーバA〜Mを同一ルールで管理する。
- サーバごとに機能境界を分離する。
- Pythonファイル配置だけで機能拡張できる運用を維持する。

## 採用ディレクトリ規約

```text
mcp_servers/
  mcp_server_a/
    server.json          ← サーバーメタデータ（オプション）
    Tools/*.py
    Prompts/*.py
    Resource/*.py
  mcp_server_b/
    server.json          ← 配置なしでも起動可能
    Tools/*.py
    Prompts/*.py
    Resource/*.py
  ...
  mcp_server_m/
    server.json
    Tools/*.py
    Prompts/*.py
    Resource/*.py
```

各 `.py` は `register(server)` を実装する。

## ロード方式

### 自動モード判定（Transport ベース）

`--transport` の値により自動的に実行モードが決まります：

#### Proxy Mode（SSE / Streamable-HTTP）
```
python run_multi_server.py                          # transport=sse（デフォルト）
python run_multi_server.py --transport streamable-http
```

**処理フロー：**
1. `run_multi_server.py` が起動
2. `proxy_server.py` をサブプロセスで実行
3. すべてのサーバーをメインプロセスでビルド
4. FastMCP の http_app() を ASGI アプリケーションとしてマウント
5. Starlette + Uvicorn で **1つのポートで複数サーバーをパスベース公開**
   ```
   http://localhost:8000/server_a/mcp
   http://localhost:8000/server_b/mcp
   ```

**利点：**
- ポート数が最小化（1ポートのみ）
- ログが統一される
- 本番環境に適している
- **推奨モード**

#### Multi Mode（STDIO）
```
python run_multi_server.py --transport stdio
```

**処理フロー：**
1. `run_multi_server.py` が起動
2. 各サーバーを **別々のプロセス（`multiprocessing.Process`）で同時実行**
3. 各プロセスが **独立した標準入出力を持つ**（**ポート番号不要**）
4. 各プロセス内で：
   - `multi_server_loader.py` が対象サーバディレクトリを読み込み
   - `server.json` を読み込みメタデータを取得
   - `Tools` / `Prompts` / `Resource` の順でimportして `register(server)` 実行
   - 管理用リソース/ツール を登録
   - STDIO transport でサーバを起動

**利点：**
- プロセスの完全独立（1つのサーバクラッシュが他に影響しない）
- 開発・デバッグに適している
- ポート管理が不要
- シンプルな実装

## 期待効果
- サーバ境界の明確化
- 指定サーバのみの起動による副作用低減
- A〜Mの横展開が容易

## セキュリティと運用
- 許可ルートは `mcp_servers/` 以下に限定
- 失敗モジュールは結果に記録し、起動継続
- 将来的に署名/ハッシュ検証を追加

## 標準化観点
既存MCP仕様との互換性を維持しつつ、capability の実験拡張として定義可能。
- `server://info` リソースで標準化されたメタデータ取得に対応
- MCPクライアントからのサーバー情報照会に対応

## 現在の生成物
- `multi_server_loader.py` — JSON メタデータ読み込み機能付きローダ
- `run_multi_server.py` — マルチ/プロキシ起動スクリプト（メインエントリーポイント）
- `proxy_server.py` — パスベースプロキシサーバー実装（Starlette + Uvicorn）
- `mcp_servers/mcp_server_a/server.json` — メタデータサンプル（`path`, `port` フィールド追加）
- `mcp_servers/mcp_server_a/` — サンプルサーバ構成
