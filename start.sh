#!/bin/bash
# Claudio 一键启动 — 网易云 API + Flask 服务器

cd "$(dirname "$0")"

echo "══════════════════════════════════════"
echo "  Claudio · 个人AI音乐电台"
echo "══════════════════════════════════════"

# 1. 网易云音乐 API (端口 3000)
echo "[1/2] 启动网易云音乐 API (port 3000)..."
node node_modules/NeteaseCloudMusicApi/app.js &
NETEASE_PID=$!

# 等网易云 API 就绪
for i in $(seq 1 15); do
  sleep 1
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null)
  if [ "$STATUS" = "200" ]; then
    echo "  网易云 API 就绪 (PID: $NETEASE_PID)"
    break
  fi
done

# 2. Flask 主服务器 (端口 8080)
echo "[2/2] 启动 Claudio 服务器 (port 8080)..."
python app.py &
FLASK_PID=$!

sleep 2
echo ""
echo "══════════════════════════════════════"
echo "  http://localhost:8080"
echo "  PID: netease=$NETEASE_PID  flask=$FLASK_PID"
echo "  关闭: kill $NETEASE_PID $FLASK_PID"
echo "══════════════════════════════════════"

wait
