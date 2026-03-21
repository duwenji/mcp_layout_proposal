# mcp-postgres (for mcp_layout_proposal)

## 概要

`mcp-postgres` は、PostgreSQL を操作する MCP サーバーです。
`mcp_layout_proposal` のマルチサーバー構成に合わせて、`mcp_servers/mcp-postgres` 配下へ再配置されています。

このサーバーは以下を提供します。

- PostgreSQL への CRUD 操作
- スキーマ取得、テーブル管理、トランザクション支援
- サンプリング/分析補助ツール
- リソース提供 (`database://...`)
- プロンプト提供 (データ分析系)
- Docker 自動セットアップ (任意)

## 主な機能

### 1. Tools

主に以下カテゴリのツールを持ちます。

- CRUD (`create_entity`, `read_entity`, `update_entity`, `delete_entity`, ほか)
- Schema (`get_tables`, `get_table_schema`, `get_database_info`)
- Table (`create_table`, `alter_table`, `drop_table`)
- Sampling (複数テーブルスキーマ取得、関係分析、正規化分析補助)
- Transaction (変更セッション、バックアップ、ロールバック、コミット)
- Sampling Integration (LLM 分析連携の準備/補助)
- Elicitation (対話的分析ワークフロー)
- Health Check (`health_check`)

### 2. Resources

- `database://tables`
- `database://info`
- `database://connection`
- `database://schema/{table_name}`

### 3. Prompts

分析用途のプロンプトを提供します。

- `data_analysis_basic`
- `data_analysis_advanced`
- `query_optimization`
- `schema_design`
- `data_quality_assessment`
- `relationship_analysis`
- `index_optimization`
- `migration_planning`
- `performance_troubleshooting`
- `backup_recovery_planning`

## 仕組み (ロードの流れ)

`mcp_layout_proposal` 側では、以下の順でロードされます。

1. `run_multi_server.py` が起動モードを選択
2. `MultiServerLayoutLoader` が `mcp_servers/mcp-postgres` を発見
3. `Tools -> Prompts -> Resource` の順で `*.py` を import
4. 各モジュールの `register(server)` を呼んで機能を登録
5. `proxy_server.py` が `server.json` の `path` を使って `/postgres/mcp` にマウント

補足:

- `server.json` の `path` は `postgres`
- そのため公開エンドポイントは `http://127.0.0.1:8000/postgres/mcp`

## ディレクトリ構成

```text
mcp-postgres/
  .env.example
  bootstrap.py
  server.json
  README.md
  Tools/
    postgres_tools.py
  Prompts/
    postgres_prompts.py
  Resource/
    postgres_resources.py
  _impl/
    mcp_postgres_duwenji/
      config.py
      context.py
      database.py
      docker_manager.py
      resources.py
      prompts.py
      tools/
        ...
```

### 役割分担

- `Tools/`, `Prompts/`, `Resource/`
  - ローダー互換の薄いラッパー (`register(server)`)
- `_impl/mcp_postgres_duwenji/`
  - 元実装ベースの本体ロジック
- `bootstrap.py`
  - コンテキスト初期化、DB プール初期化、終了処理

## 使い方

以下は `mcp_layout_proposal` ディレクトリで実行します。

### 1. 環境変数を用意

`mcp_servers/mcp-postgres/.env.example` を参考に `.env` を作成してください。

最低限の通常接続設定例:

```env
MCP_DOCKER_AUTO_SETUP=false
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mcp-postgres-db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Docker 自動セットアップを使う場合:

```env
MCP_DOCKER_AUTO_SETUP=true
MCP_DOCKER_IMAGE=postgres:16
MCP_DOCKER_CONTAINER_NAME=mcp-postgres-auto
MCP_DOCKER_PORT=5432
MCP_DOCKER_DATABASE=mcp-postgres-auto-db
MCP_DOCKER_USERNAME=postgres
MCP_DOCKER_PASSWORD=postgres
```

### 2. Proxy モードで起動 (推奨)

```bash
python run_multi_server.py --server mcp-postgres
```

起動後:

- MCP エンドポイント: `http://127.0.0.1:8000/postgres/mcp`
- ヘルスチェック: `http://127.0.0.1:8000/health`

### 3. stdio モードで起動 (デバッグ向け)

```bash
python run_multi_server.py --transport stdio --server mcp-postgres
```

## DB 接続情報の決まり方

接続先は `config.py` で決まります。

- `MCP_DOCKER_AUTO_SETUP=true` の場合
  - Docker 設定 (`MCP_DOCKER_*`) を優先
  - host は `localhost` を使用
- `MCP_DOCKER_AUTO_SETUP=false` の場合
  - `POSTGRES_*` を使用

接続オプション:

- `POSTGRES_SSL_MODE` (default: `prefer`)
- `POSTGRES_POOL_SIZE` (default: `5`)
- `POSTGRES_MAX_OVERFLOW` (default: `10`)
- `POSTGRES_CONNECT_TIMEOUT` (default: `30`)

## 運用と確認

### ロード状況を確認

- Resource: `layout://load-report`
- Tool: `layout_list`

どのモジュールが成功/失敗したかを確認できます。

### サーバー情報を確認

- Resource: `server://info`

`server.json` の内容を確認できます。

## 拡張方法

### Tool を追加する

1. `_impl/mcp_postgres_duwenji/tools/` に実装を追加
2. `get_*_tools()` と `get_*_handlers()` へ登録
3. `Tools/postgres_tools.py` で集約済みハンドラに含める

### Prompt を追加する

1. `_impl/mcp_postgres_duwenji/prompts.py` の定義へ追加
2. `Prompts/postgres_prompts.py` が自動的に register

### Resource を追加する

1. `_impl/mcp_postgres_duwenji/resources.py` に Resource/handler を追加
2. `Resource/postgres_resources.py` から登録されるようにする

## トラブルシューティング

### 1. ロード失敗 (`Missing callable register(server)`)

- `Tools/`, `Prompts/`, `Resource/` 側ファイルに `register(server)` が必要です。

### 2. import エラー

- ラッパーモジュールが `bootstrap.py` と `_impl` を import できることを確認してください。

### 3. DB 接続失敗

- `.env` の `POSTGRES_*` または `MCP_DOCKER_*` を確認
- ポート競合 (`5432`) を確認
- Docker 利用時は Docker デーモン起動状態を確認

## 注意事項

- `mcp-postgres` はマルチサーバー配下向けの再配置版です。
- 実装本体は `_impl` に保持し、ローダーとの接点は `register(server)` ラッパーに集約しています。
- `path` は `server.json` で管理され、現在は `postgres` です。
