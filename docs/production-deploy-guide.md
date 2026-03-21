# MCP本番デプロイ手順書（Kubernetes + HTTP/SSE）

この手順書は、mcp_layout_proposal を本番環境へデプロイし、GitHub Copilot から MCP サーバへ接続するための運用手順です。

対象:
- 実行基盤: Kubernetes
- 接続方式: HTTP/SSE（proxy_server 経由）
- 対象サーバ: mcp_servers/mcp-postgres

補足:
- run_multi_server.py には streamable-http 選択肢がありますが、現行の proxy_server.py は sse_app をマウントしており、実運用は SSE 前提です。

## 1. 前提条件

- Kubernetes クラスタにアクセス可能
- Ingress コントローラ（例: nginx ingress）が有効
- TLS 証明書が利用可能
- GitHub Copilot で MCP 設定を編集できること
- PostgreSQL の永続ボリュームが利用可能

## 2. リポジトリ内のサンプル資材

- Docker Compose サンプル: deploy/docker/docker-compose.prod.yml
- Kubernetes サンプル: deploy/k8s/
- Copilot 登録サンプル: deploy/copilot/mcp-settings-http-sse.example.json

## 3. Step 1: 実行環境に配置して起動

### 3-1. サンプルとして Docker Compose で起動

Docker Compose は本番前検証や単一ノード運用の基準構成として利用します。

1. 環境変数ファイルを作成

- ひな形: deploy/docker/.env.prod.example
- 保存先: deploy/docker/.env.prod

2. 起動

```bash
cd deploy/docker
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

3. 確認

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

### 3-2. 本番 Kubernetes にデプロイ

1. Secret を作成

- deploy/k8s/secret.example.yaml を secret.yaml にコピーして値を更新

2. リソースを適用

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.yaml
kubectl apply -f deploy/k8s/postgres-statefulset.yaml
kubectl apply -f deploy/k8s/mcp-proxy-deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

3. 稼働確認

```bash
kubectl -n mcp-prod get pods
kubectl -n mcp-prod get svc
kubectl -n mcp-prod get ingress
```

4. ヘルス確認

```bash
curl https://mcp.example.com/health
# {"status":"ok"}
```

## 4. Step 2: GitHub Copilot 側で MCP 登録

Copilot の MCP 設定に、HTTP/SSE エンドポイントを登録します。

サンプル:
- deploy/copilot/mcp-settings-http-sse.example.json

ポイント:
- URL は Ingress の公開 URL を指定
- 本番では HTTPS を使用
- タイムアウトはネットワーク特性に合わせて調整

## 5. Step 3: 接続確認後にツール/リソースを呼び出す

### 5-1. 最低限の確認順序

1. MCP 接続できる
2. list_tools が成功する
3. list_resources が成功する
4. health_check ツールが成功する
5. PostgreSQL 依存ツール（例: get_tables）が成功する

### 5-2. 運用時の確認観点

- MCP endpoint の到達性
- DB 接続失敗率
- レイテンシ（p95）
- Pod 再起動回数

## 6. 監視

最低限の監視:
- /health の外形監視
- Pod の liveness/readiness 失敗回数
- アプリログの ERROR 件数
- PostgreSQL 接続エラー件数

推奨:
- Prometheus + Grafana
- しきい値アラート（5xx増加、再起動増加、DB接続失敗増加）

## 7. バックアップ

StatefulSet で PostgreSQL を運用する場合:
- 日次スナップショット
- WAL または増分バックアップ
- 週次でリストア演習

Managed DB を使う場合:
- クラウド標準バックアップ + PITR
- 保持期間と復旧RTO/RPOを明文化

## 8. ロールバック

### 8-1. MCP サーバ

- Deployment を前リビジョンへ戻す

```bash
kubectl -n mcp-prod rollout undo deployment/mcp-proxy
```

### 8-2. DB スキーマ

- アプリロールバックより先に DB 互換性を確認
- 破壊的変更は後方互換を持つ段階的マイグレーションに限定

## 9. 障害切り分け

1. /health が失敗
- Pod 状態確認
- Ingress ルーティング確認
- mcp-proxy ログ確認

2. tools/resources が失敗
- mcp_servers/mcp-postgres のロード結果確認
- layout://load-report と layout_list で読み込み状態確認

3. DB 接続失敗
- Secret 値確認
- Postgres Service 名とポート確認
- PostgreSQL Pod の readiness 確認

## 10. 運用上の注意

- 本番は Docker 自動セットアップ（MCP_DOCKER_AUTO_SETUP=true）を避け、外部DBまたは明示的なDBサービスを使用
- Ingress で TLS 終端を必須化
- Secret は Git に平文コミットしない
- 初回リリース前に障害注入テスト（DB停止、Ingress遮断）を実施
