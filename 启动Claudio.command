#!/bin/bash
# Claudio · macOS 一键启动
# 首次使用前： chmod +x 启动Claudio.command
cd "$(dirname "$0")"

# Homebrew / nvm 用户按需添加 PATH（双击启动时不会加载 ~/.zshrc）
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

echo "══════════════════════════════════════"
echo "  Claudio · AI Music Radio"
echo "══════════════════════════════════════"

# 1. Node 依赖
if [ ! -d node_modules/NeteaseCloudMusicApi ]; then
  echo "[1/3] 安装 Node 依赖…"
  npm install || { echo "ERROR: npm 失败，检查 Node.js 是否已安装"; read; exit 1; }
fi

# 2. Python 虚拟环境
if [ ! -x .venv/bin/python ]; then
  echo "[2/3] 创建虚拟环境…"
  python3 -m venv .venv || { echo "ERROR: 需要 Python 3.10+"; read; exit 1; }
fi

# 3. Python 依赖
if ! .venv/bin/python -c "import webview, flask, flask_cors, flask_sock, edge_tts" 2>/dev/null; then
  echo "[3/3] 安装 Python 依赖…"
  .venv/bin/pip install -r requirements.txt || { echo "ERROR: pip 失败"; read; exit 1; }
fi

if [ ! -f config.json ]; then
  echo ""
  echo "缺少 config.json —— 先复制模板并填入 API Key："
  echo "  cp config.example.json config.json"
  echo ""
  read
  exit 1
fi

exec .venv/bin/python desktop.py
