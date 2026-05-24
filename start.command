#!/bin/bash
cd "$(dirname "$0")"

# Terminal colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   智能语音客服系统 - 一键启动${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ── Backend ──
echo -e "${GREEN}[1/2] 启动后端 (FastAPI on :8900) ...${NC}"
cd backend

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "  → 创建 Python 虚拟环境..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install deps if needed
if [ ! -f ".venv/.deps_installed" ]; then
    echo "  → 安装后端依赖（首次运行需要几分钟）..."
    pip install -r requirements.txt -q
    touch .venv/.deps_installed
fi

# Start backend in a new Terminal tab
osascript -e "
tell application \"Terminal\"
    activate
    do script \"cd '$(pwd)' && source .venv/bin/activate && python main.py\"
end tell
"

cd ..
echo "  → 后端已启动"

# ── Frontend ──
echo -e "${GREEN}[2/2] 启动前端 (Vite on :5173) ...${NC}"
cd frontend

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "  → 安装前端依赖（首次运行需要几分钟）..."
    npm install --silent
fi

# Start frontend in a new Terminal tab
osascript -e "
tell application \"Terminal\"
    activate
    do script \"cd '$(pwd)' && npm run dev\"
end tell
"

cd ..
echo "  → 前端已启动"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   启动完成！${NC}"
echo -e "${GREEN}   前端: http://localhost:5173${NC}"
echo -e "${GREEN}   后端: http://localhost:8900${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "关闭此窗口不影响运行，关闭对应 Terminal 标签页即可停止服务。"
echo ""
read -p "按回车键关闭此窗口..."
