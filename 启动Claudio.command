#!/bin/bash
# Claudio · macOS 一键启动
# 首次使用前： chmod +x 启动Claudio.command
cd "$(dirname "$0")" || exit 1

# Homebrew / nvm 用户按需添加 PATH（双击启动时不会加载 ~/.zshrc）
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
# Homebrew 的版本化安装不会把 python3/node 放进默认 PATH。
for brew_prefix in /usr/local /opt/homebrew; do
  [ ! -d "$brew_prefix/opt/python@3.12/libexec/bin" ] || export PATH="$brew_prefix/opt/python@3.12/libexec/bin:$PATH"
  [ ! -d "$brew_prefix/opt/node@22/bin" ] || export PATH="$brew_prefix/opt/node@22/bin:$PATH"
done
if ! command -v node >/dev/null 2>&1; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  [ ! -s "$NVM_DIR/nvm.sh" ] || . "$NVM_DIR/nvm.sh"
fi

fail() {
  echo "ERROR: $1"
  if [ -t 0 ]; then read -r -p "按回车关闭…"; fi
  exit 1
}

python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null || fail "需要 Python 3.10+"
node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 18 ? 0 : 1)' 2>/dev/null || fail "需要 Node.js 18+"
command -v npm >/dev/null 2>&1 || fail "未找到 npm，请检查 Node.js 安装"

echo "══════════════════════════════════════"
echo "  Claudio · AI Music Radio"
echo "══════════════════════════════════════"

# 1. Node 依赖
if [ ! -d node_modules/NeteaseCloudMusicApi ]; then
  echo "[1/3] 安装 Node 依赖…"
  # 当前桌面壳使用 pywebview，无需下载开发依赖 Electron。
  npm install --omit=dev || fail "npm 安装失败，请检查网络后重试"
fi

# 2. Python 虚拟环境
if [ ! -x .venv/bin/python ]; then
  echo "[2/3] 创建虚拟环境…"
  python3 -m venv .venv || fail "创建 Python 虚拟环境失败"
fi
.venv/bin/python -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null || fail ".venv 需要使用 Python 3.10+ 重新创建"

# 3. Python 依赖
if ! .venv/bin/python -c 'import webview, flask, flask_cors, flask_sock, edge_tts, requests, websockets; from importlib.metadata import version; assert tuple(map(int, version("edge-tts").split(".")[:3])) >= (7, 3, 1)' 2>/dev/null; then
  echo "[3/3] 安装 Python 依赖…"
  .venv/bin/python -m pip install -r requirements.txt || fail "pip 安装失败，可尝试清华镜像；请勿降低 edge-tts 版本"
fi

if [ ! -f config.json ]; then
  echo ""
  echo "缺少 config.json —— 先复制模板并填入 API Key："
  echo "  cp config.example.json config.json"
  echo ""
  fail "请先配置 API Key"
fi

# .app 内的解释器提供独立的 Cocoa 应用身份，依赖仍来自项目虚拟环境。
if [ -n "${CLAUDIO_APP_PYTHON:-}" ]; then
  [ -x "$CLAUDIO_APP_PYTHON" ] || fail "Claudio.app 运行入口缺失，请重新构建应用"
  exec env __PYVENV_LAUNCHER__="$PWD/.venv/bin/python" "$CLAUDIO_APP_PYTHON" desktop.py
fi
exec .venv/bin/python desktop.py
