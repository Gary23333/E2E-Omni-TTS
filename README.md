<div align="center">

# 🔮 OmniVoice

**本地语音助手实验项目：Omni 音频理解 × VoxCPM 流式 TTS × Agent 工具调用**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Offline checks](https://github.com/Gary23333/E2E-Omni-TTS/actions/workflows/ci.yml/badge.svg)](https://github.com/Gary23333/E2E-Omni-TTS/actions/workflows/ci.yml)

React 19 / TypeScript / Vite · Python / FastAPI · WebSocket

</div>

> **仅用于受信任的本机开发与实验。** 当前没有账户认证或多用户隔离，不应开放到局域网、公网、反向代理或隧道。详见 [安全边界](SECURITY.md)。

## 项目能做什么

- 浏览器采集 16 kHz 单声道 PCM，通过 WebSocket 发送给后端。
- Omni 模式将 WAV 音频交给兼容 `input_audio` 的模型；ASR 文本用于转写及降级。
- 文本模式使用 ASR → 文本 LLM → TTS 链路，也支持直接输入文字。
- LLM 文字片段送入 TTS，前端接收二进制音频；支持取消当前回复和清空播放。
- 配置 Agent、客服组、提示词、工具允许列表和 RAG 文档；文本工具调用默认采用提示词 JSON 协议。
- 保存本地通话记录，提供本地背景音上传与预览。

这里的“Omni”指输入模型能够理解音频。输出仍经过 **LLM 文字 → TTS**，不是一个模型直接生成完整语音对话。当前 ASR 和 Omni 调用按代码流程执行，不能视为已经验证的并行双路识别。

这是实验性实现，不能仅凭功能列表认定为生产就绪。首句延迟、识别率、音色和设备兼容性取决于实际模型与硬件，项目未提供可复现的性能基准。

## 快速开始

### 环境

- Python **3.10+**；CI 使用 3.10 和 3.12。
- Node.js **22.12+**，或兼容 Vite 8 的较新 LTS 版本。
- 可访问的 LLM、ASR、TTS 服务。离线单元测试不需要模型或 API Key。

```sh
git clone https://github.com/Gary23333/E2E-Omni-TTS.git
cd E2E-Omni-TTS

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
(cd backend && python main.py)
```

后端默认监听 `http://127.0.0.1:8900`。在另一个终端启动前端：

```sh
cd E2E-Omni-TTS/frontend
npm ci
npm run dev
```

打开 `http://localhost:5173` 或 `http://127.0.0.1:5173`，在系统设置中配置服务。不要使用 `--host 0.0.0.0` 或公开隧道绕过本地边界。开发端口 5173 被占用时，先释放端口；其他浏览器 Origin 会被拒绝。

macOS 还提供 `./start.command`，依赖 Terminal/AppleScript。Linux 与 Windows 请使用上述分步命令；macOS 启动脚本没有在 Linux CI 中做运行验证。

### 服务配置

| 配置 | 默认地址 | 说明 |
|---|---|---|
| LLM | `http://localhost:8000/v1` | OpenAI-compatible 文本接口；Omni 需要支持项目所用 `input_audio` 格式 |
| TTS | `http://localhost:8001/v1` | 兼容 `/audio/speech` 的服务，项目默认消费 PCM |
| ASR | `ws://localhost:10095` | FunASR WebSocket，输入原始 16 kHz / 16-bit / mono PCM |
| Embedding | `http://localhost:8000/v1` | 兼容 `/embeddings`；留空会尝试下载/加载本地模型 |

密钥只写入后端本地配置，GET/PUT 响应不回传已保存值。输入框留空表示保留已有密钥；需要删除时使用明确的“清除已保存密钥”按钮并保存。更换服务端点而没有输入新密钥时，原密钥会被清除，避免发送给不同服务。

ASR 也支持明确配置的 HTTP(S) 自定义接口：上传 multipart 字段 `audio`（WAV 文件），响应为 `{"text":"..."}` 或字符串 `result` 字段。裸域名默认路径为 `/asr`，显式路径保持不变。**这不是 Whisper/OpenAI 转写接口**。WebSocket 失败不会把音频发送到猜测的 HTTP 地址，也不会伪造识别文本。

界面中的连接测试主要验证可达性，不能代替真实语音识别、工具执行或音频质量测试。

### VoxCPM

参考 [OpenBMB/VoxCPM 官方项目](https://github.com/OpenBMB/VoxCPM) 配置模型、硬件和运行环境。项目提供的 `backend/voxcpm_tts_server.py` 是轻量包装，不能代替官方安装说明。

若已在对应 Python 环境安装 VoxCPM、FastAPI、Uvicorn 等依赖并准备模型，可从 backend 目录启动：

```sh
VOXCPM_MODEL_PATH=/absolute/path/to/VoxCPM2 \
  python -m uvicorn voxcpm_tts_server:app --host 127.0.0.1 --port 8001
```

`backend/run_voxcpm_tts.sh` 另外依赖 `.tts-venv` 和 ModelScope，会下载模型后启动服务。下载大小、模型许可和硬件需求请先查阅上游；普通应用启动和 CI 不会自动启动该脚本。

## 本地数据与安全

- 配置：`backend/data/configs/global_config.json`，含明文服务密钥，已被 Git 忽略。
- 会话：`backend/data/configs/sessions.json`，含通话文本，已被 Git 忽略。
- RAG：本地文档、向量索引和模型缓存，不应提交私人内容。
- 上传文件限制为 10 MiB，HTTP 请求体限制为 12 MiB；支持音频 WAV/MP3/M4A 与文档 PDF/DOCX/TXT/MD。
- HTTP 和 WebSocket 同时检查本机来源、Host 与浏览器 Origin；本地进程仍是受信任方。
- 无加密存储、自动保留期限或公开部署认证。请保护系统账户、磁盘与备份。

完整说明见 [SECURITY.md](SECURITY.md)。

## 测试与验证边界

```sh
python -m pip install -r backend/requirements-core.txt
(cd backend && python -m unittest discover -s tests -v)
python -m compileall -q backend

cd frontend
npm ci
npm run build
node --test tests/*.test.mjs
```

GitHub Actions 配置运行 Python 离线回归、前端构建与回归、Shell 语法检查，不访问真实模型服务。`backend/test_*.py` 是独立的手动服务探测脚本，不属于离线测试集。

通过这些检查并不等于通过真实麦克风、浏览器播放、ASR/Omni/TTS 全链路测试。跨模型工具兼容性、长时间运行和公网安全仍需要单独评估。

## 目录

```text
backend/
  core/          LLM、ASR、TTS、Agent、工具、存储与本地访问边界
  routers/       HTTP 与 WebSocket 入口
  schemas/       配置和会话模型
  tests/         不依赖模型服务的回归测试
  voxcpm_tts_server.py
frontend/
  src/           页面、音频钩子、状态与 API 客户端
  tests/         组件和连接逻辑回归
.github/workflows/ci.yml
```

欢迎提交聚焦的草稿 PR，附变更原因、检查结果和未验证部分。参见 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [PR #1 整合记录](docs/pr-1-integration.md)。

## License

项目代码使用 [MIT License](LICENSE)。模型、数据和上游依赖遵循各自许可。
