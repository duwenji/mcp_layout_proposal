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
    Tools/*.py
    Prompts/*.py
    Resource/*.py
  mcp_server_b/
    Tools/*.py
    Prompts/*.py
    Resource/*.py
  ...
  mcp_server_m/
    Tools/*.py
    Prompts/*.py
    Resource/*.py
```

各 `.py` は `register(server)` を実装する。

## ロード方式
1. `run_multi_server.py` が `--server` で対象サーバを指定
2. `multi_server_loader.py` が対象サーバディレクトリのみ読み込み
3. `Tools` / `Prompts` / `Resource` の順でimportして `register(server)` 実行
4. 管理用 `layout://load-report` と `layout_list` を登録

## 期待効果
- サーバ境界の明確化
- 指定サーバのみの起動による副作用低減
- A〜Mの横展開が容易

## セキュリティと運用
- 許可ルートは `mcp_servers/` 以下に限定
- 失敗モジュールは結果に記録し、起動継続
- 将来的に署名/ハッシュ検証を追加

## 標準化観点
既存MCP仕様との互換性を維持しつつ、将来的には capability の実験拡張として定義可能。

## 現在の生成物
- `multi_server_loader.py`
- `run_multi_server.py`
- `mcp_servers/mcp_server_a/` サンプル
