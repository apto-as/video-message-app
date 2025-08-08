FROM node:18-alpine

# ヘルスチェック用にcurlをインストール
RUN apk add --no-cache curl

# 作業ディレクトリ設定
WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# Mac環境対応: package-lock.jsonの不整合を解決
# 依存関係をインストール（開発環境では npm install を使用）
# BuildKitキャッシュマウントでnpmキャッシュを最適化
RUN --mount=type=cache,target=/root/.npm \
    npm install --omit=dev

# アプリケーションコードをコピー
COPY . .

# 環境変数設定
ENV REACT_APP_API_BASE_URL=https://3.115.141.166/api
ENV NODE_ENV=production
ENV PORT=55434
ENV HOST=0.0.0.0

# WebSocket設定（HMR無効化）
ENV WDS_SOCKET_HOST=3.115.141.166
ENV WDS_SOCKET_PORT=443
ENV WDS_SOCKET_PATH=/ws
ENV PUBLIC_URL=https://3.115.141.166
ENV GENERATE_SOURCEMAP=false

# ポート公開
EXPOSE 55434

# ヘルスチェック（コンテナ内部ポート使用）
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:55434 || exit 1

# アプリケーション起動
CMD ["npm", "start"]