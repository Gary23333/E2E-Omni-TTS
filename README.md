<div align="center">

# 🔮 OmniVoice

**真正的端到端语音助手 · Omni 多模态大模型 × 面壁智能 VoxCPM2 流式 TTS × 可调用工具**

[![Omni](https://img.shields.io/badge/Architecture-Omni_End--to--End-6C5CE7?logo=audiomack&logoColor=white)]()
[![VoxCPM2](https://img.shields.io/badge/TTS-VoxCPM2_Streaming-FF6B6B?logo=openai&logoColor=white)](https://github.com/OpenBMB/VoxCPM)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![Vibe Coding](https://img.shields.io/badge/Built_with-Vibe_Coding-8A2BE2)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <strong>🎙️ 语音进 → 🧠 Omni 理解 → 🔧 工具调用 → 🔊 语音出</strong><br>
  <em>全程无需文本中转，一句话完成复杂任务</em>
</p>

</div>

---

## ✨ 这是什么？

> **OmniVoice** 是一个**端到端大模型语音助手**（End-to-End Voice Agent）。
>
> 你对它**说话**，它用**语音**回答你，中途还能**调用工具**查天气、查订单、创建工单——全部在一条语音流里完成，无需键盘、无需屏幕、无需等待整段文本生成完毕。

传统语音助手是 **"语音 → ASR → 文本 LLM → TTS → 语音"** 的级联 pipeline，每一步都在累积延迟和信息损耗。

**OmniVoice 做的完全不同：**

```
传统方案:  🎙️ 语音 → 📝 ASR → 🧠 文本 LLM → 🔊 TTS → 🔈 语音  (延迟高、失真大)
OmniVoice: 🎙️ 语音 ───────────────→ 🧠 Omni 多模态大模型 ──→ 🔊 VoxCPM2 流式语音  (端到端)
                                         ↓
                                    🔧 实时调用工具
```

- **Omni 多模态大模型**（如 MiMo-v2-Omni）直接理解原始音频波形，无需 ASR 中转
- **面壁智能 VoxCPM2** 以流式 chunk 输出 48kHz 高保真语音，LLM 刚吐 token 你就能听到声音
- **Agent 工具链**让语音助手能真正"动手"完成任务，而不只是聊天

这是一个 **Vibe Coding 实验项目**。核心架构与绝大多数功能由 AI Agent 辅助生成，人类负责审校、调试与体验打磨。代码或许不够"教科书级"，但每一个 feature 都经过真实场景验证。**欢迎懂代码的朋友一起优化、重构、提 PR！**

---

## 🚀 端到端能力全景

### 🎙️➡️🧠 Omni 原生语音理解

支持 **Omni 模式**的端云大模型可以直接"听懂"你的声音：

- 前端采集 **16kHz Mono PCM**，自动封装 WAV Header，以 `data:audio/wav;base64,...` 直送大模型
- **无需 ASR 文本中转**，模型直接对原始音频进行语义理解
- 兼容 **MiMo-v2-Omni** 等支持 `input_audio` 多模态输入的 OpenAI-compatible API
- **ASR 并行兜底**：Omni 模式下系统后台同步跑 ASR 文本识别。若模型返回空或遇到纯文本模型拒识，自动 fallback 到 `ASR → Text LLM → TTS` 降级链路，**通话绝不中断**

### 🔊 面壁智能 VoxCPM2 端到端流式 TTS

语音输出的质量直接决定用户体验。我们选用 [**面壁智能 OpenBMB 的 VoxCPM2**](https://github.com/OpenBMB/VoxCPM) —— 业界领先的端到端语音合成模型：

| 能力 | 说明 |
|------|------|
| **Tokenizer-Free Diffusion AR** | 摒弃传统"文本→音素→声学特征→声码器"级联架构，直接对语音分布建模，音色自然度与跨语言一致性碾压级联方案 |
| **真 · 流式生成** | 支持 `stream=true` 的 chunk-by-chunk 输出。后端按标点与语义长度智能切片，**LLM token 与 TTS 音频并行流水线处理**，首句延迟降至毫秒级 |
| **48kHz 高保真** | 配合前端 Web Audio API 的 AudioContext 时间轴预排队播放，实现跨 chunk 无缝衔接 |
| **零样本音色控制** | 通过 voice descriptor（如 `(A warm young woman)`）即时切换说话风格，无需微调 |
| **30+ 语言原生支持** | 非拼接式多语言，跨语言音色一致 |

> **为什么这很重要？** 传统 TTS 必须等 LLM 输出完整回复才能开始合成，用户要干等数秒。VoxCPM2 的流式能力让"边想边说"成为现实——大模型刚想到前半句，你已经听到前半句了。

### 🔧 Agent 智能路由 + 实时工具调用

说话就能办事，才是真正的语音助手：

- **多 Agent 动态路由**：LLM 根据用户意图自动将通话转接给最适合的 Agent
  - 🎧 **小欢**（总机接待）· 阳光热情，负责初次导诊
  - 🔧 **智工**（技术专家）· 深度集成 RAG 知识库，处理技术难题
  - 💼 **倩倩**（业务顾问）· 负责产品套餐、价格与优惠
  - 🛡️ **德哥**（售后主管）· 同理心极高，处理投诉与情绪安抚
- **Agent 协作转接**：支持 `[HANDOFF:agent_id]` 协议，Agent 之间可主动移交会话
- **工具调用循环**：内置天气查询、订单追踪、工单创建等 HTTP/Script 插件
  - 工具调用 JSON **仅在后端解析执行**，不会出现在对话区，也不会被 TTS "朗读"出来
  - 支持 **多轮工具调用**：LLM 可连续调用多个工具完成复杂任务
- **RAG 知识库**：FAISS 向量索引，实时检索文档注入上下文，让 Agent 掌握企业私有知识

### ⚡ 沉浸式实时交互

- **🛑 通话打断**：前端发送 `interrupt`，后端立即取消当前 LLM/TTS 任务，清空队列并广播 `tts_stop`
- **🎧 音频环境模拟**：咖啡厅、写字楼、街道等背景噪音实时混音，让 Demo 更有"临场感"
- **🧼 TTS 文本清洗**：自动去除 emoji、Markdown、代码块，避免 TTS "朗读"视觉标记
- **📡 WebSocket 二进制/文本混合协议**：`llm_token` 流式文字、二进制 PCM 音频帧、状态事件实时同步

---

## 🏗️ 端到端架构

```
                              ┌─────────────────────────────────────┐
                              │         用户说话 / 打断              │
                              └──────────────┬──────────────────────┘
                                             │
                              ┌──────────────▼──────────────────────┐
                              │   🎙️ 浏览器 (React 19 + Web Audio)   │
                              │   · PCM 采集 16kHz Mono              │
                              │   · AudioContext 队列播放 48kHz      │
                              │   · 实时打断 / 背景混音              │
                              └──────────────┬──────────────────────┘
                                             │ WebSocket 二进制+JSON
                              ┌──────────────▼──────────────────────┐
                              │      🚀 FastAPI 后端 (:8900)         │
                              │                                      │
                              │   ┌─────────────────────────────┐    │
                              │   │   ws_voice.py 语音中枢       │    │
                              │   │   · Omni/ASR 双模式路由      │    │
                              │   │   · 流式 TTS 智能切片缓冲    │    │
                              │   │   · 打断信号 + 任务取消      │    │
                              │   └─────────────┬───────────────┘    │
                              │                 │                    │
                              │    ┌────────────┼────────────┐       │
                              │    ▼            ▼            ▼       │
                              │ ┌──────┐   ┌────────┐   ┌────────┐  │
                              │ │ LLM  │   │  TTS   │   │ Tools  │  │
                              │ │Client│   │Client  │   │Skill   │  │
                              │ │(Omni)│   │(Stream)│   │Executor│  │
                              │ └──┬───┘   └───┬────┘   └───┬────┘  │
                              └────┼───────────┼────────────┼────────┘
                                   │           │            │
                                   ▼           ▼            ▼
                           ┌────────────┐ ┌──────────┐ ┌────────────┐
                           │   Omni     │ │ VoxCPM2  │ │  天气/订单  │
                           │ Multimodal │ │Streaming │ │ /工单/知识库│
                           │    LLM     │ │ 48kHz PCM│ │  HTTP API  │
                           └────────────┘ └──────────┘ └────────────┘
```

### 数据流：一句语音指令的完整旅程

```
1. 用户说："帮我查一下明天北京的天气，然后用温柔的声音告诉我。"
   │
2. 🎙️ 前端采集 PCM → WebSocket 发送二进制音频流
   │
3. 🧠 Omni LLM 直接理解音频（或 ASR fallback）
   │
4. 🔧 Agent 识别意图 → 调用天气 API 工具
   │
5. 🧠 LLM 根据工具返回结果组织回复文本
   │
6. 🔊 VoxCPM2 流式 TTS 开始合成："北京明天晴朗..."（边说边播）
   │
7. 🔈 前端 AudioContext 实时播放 PCM chunk
```

---

## 🛠️ 快速启动

### 前置要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.9 | 后端运行环境 |
| Node.js | ≥ 20 | 前端构建环境 |
| VoxCPM2 | — | 端到端 TTS 引擎（见下方） |

### 1. 部署 VoxCPM2 端到端 TTS 服务

OmniVoice 的语音输出质量完全依赖 **面壁智能 VoxCPM2**。你需要先启动一个兼容 OpenAI `/v1/audio/speech` 接口的 TTS 服务：

```bash
# 参考 OpenBMB 官方仓库部署 VoxCPM2
# https://github.com/OpenBMB/VoxCPM

# 启动后默认监听 http://localhost:8001
```

项目内置了一个轻量级的 VoxCPM2 wrapper（`backend/voxcpm_tts_server.py`），如果你已安装 `voxcpm` 包，可直接运行：

```bash
cd backend
python voxcpm_tts_server.py  # 运行于 localhost:8001
```

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动 FastAPI 服务
python main.py  # 运行于 http://localhost:8900
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev  # 运行于 http://localhost:5173
```

### macOS 一键启动

```bash
./start.command
```

---

## ⚙️ 配置指南

首次启动后，访问前端 **系统设置** 页面配置以下服务：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| **LLM Endpoint** | `http://localhost:8000/v1` | 任意 OpenAI-compatible API。支持 Omni 多模态的推荐 **MiMo-v2-Omni** |
| **LLM API Key** | — | 你的 API Key |
| **LLM Model** | `gpt-4o` | 模型名称。Omni 模式请填写支持 `input_audio` 的模型 |
| **TTS Endpoint** | `http://localhost:8001/v1` | **VoxCPM2** 服务地址 |
| **ASR Endpoint** | `ws://localhost:10095` | FunASR 语音识别（Omni 模式下的 fallback 兜底） |
| **Embed Endpoint** | `http://localhost:8000/v1` | Embedding 服务（留空则自动加载本地模型） |
| **LLM Mode** | `text_asr` | `omni` = 原生语音理解 · `text_asr` = ASR+文本链路 |

> **💡 推荐体验路径**：如果你有 MiMo-v2-Omni 或同类 Omni 模型，将 **LLM Mode** 设为 `omni`，即可体验"语音直进大模型→语音直出"的端到端快感。
>
> **💡 提示**：项目已通过 `.gitignore` 保护 `backend/data/configs/global_config.json`，你的本地配置（含 API Key）不会被意外提交。

---

## 🎯 为什么 Omni + VoxCPM2 是语音助手的未来？

| 维度 | 传统级联语音助手 | OmniVoice (Omni + VoxCPM2) |
|------|-----------------|---------------------------|
| **输入链路** | 语音 → ASR → 文本（信息损耗） | 🟢 **语音直送大模型**（端到端理解） |
| **推理能力** | 纯文本 LLM，无多模态 | 🟢 **Omni 多模态大模型**，能"听"懂语气、停顿、背景音 |
| **输出链路** | 文本 → TTS（延迟累积） | 🟢 **流式端到端 TTS**，边生成边播放 |
| **工具调用** | 文本中转，延迟高 | 🟢 **语音→工具→语音**，全程无文本界面 |
| **首句延迟** | 3~5 秒（等整段文本） | 🟢 **< 1 秒**（流式切片，说到哪播到哪） |
| **音色一致性** | 长文本分段易跳变 | 🟢 **VoxCPM2 全局建模**，长对话音色稳定 |
| **多语言** | 需单独训练语言模块 | 🟢 **30+ 语言原生支持**，跨语言音色一致 |

---

## 🤝 参与贡献

> **这是一个 Vibe Coding 项目。** 大量代码由 AI Agent 在对话中生成，虽然功能完整且经过场景验证，但在工程规范、边界 case 处理、性能优化上还有很大提升空间。

**我们特别欢迎以下方向的贡献：**

- 🔧 **代码重构**：模块解耦、类型注解完善、异常处理增强
- ⚡ **性能优化**：WebSocket 连接池、TTS 切片算法、前端音频缓冲策略
- 🧪 **测试覆盖**：当前测试脚本较粗糙，需要单元测试与集成测试
- 🌍 **多语言支持**：VoxCPM2 本身支持 30 语言，但前端与提示词目前以中文为主
- 🎨 **UI/UX 打磨**：更多的动画、响应式适配、无障碍支持
- 📖 **文档完善**：API 文档、部署指南、架构设计说明

**提交 PR 前请确保：**
1. 代码通过本地运行验证
2. 不引入新的硬编码敏感信息（API Key、个人路径等）
3. 遵循现有代码风格

---

## 📂 项目结构

```
voice-cs-demo/
├── backend/
│   ├── core/
│   │   ├── agent_manager.py      # 多 Agent 编排 / 工具调用循环 / Omni fallback
│   │   ├── llm_client.py         # OpenAI-compatible 客户端（MiMo Omni 自动兼容）
│   │   ├── tts_client.py         # VoxCPM2 流式 TTS 客户端 + 噪音混音
│   │   ├── rag_engine.py         # FAISS + 本地/远程 Embedding 双模
│   │   ├── noise_manager.py      # 背景音频实时合成
│   │   └── skill_executor.py     # HTTP / Script 工具执行器
│   ├── routers/
│   │   ├── ws_voice.py           # WebSocket 核心语音流 / 双流式 TTS / 打断
│   │   ├── config.py             # 全局配置 + 服务健康检测 + 音频管理
│   │   ├── agents.py             # Agent & Group CRUD
│   │   ├── rag.py                # 文档上传与检索
│   │   └── skills.py             # 技能插件管理
│   ├── voxcpm_tts_server.py      # 轻量级 VoxCPM2 OpenAI-compatible 服务
│   └── data/
│       ├── configs/              # 运行时配置（.gitignored）
│       └── noise_samples/        # 背景音预设
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── call/             # 通话界面 / 转录面板 / 等待遮罩
│   │   │   ├── config/           # 设置面板 / RAG 管理 / 技能管理
│   │   │   └── layout/           # 侧边栏导航
│   │   ├── hooks/
│   │   │   ├── useAudioRecorder.ts   # Web Audio API 原生 PCM 采集
│   │   │   ├── useAudioPlayer.ts     # PCM 队列播放 / 打断 / 字节对齐
│   │   │   └── useWebSocket.ts       # WS 事件处理
│   │   └── stores/               # Zustand 状态管理
│   └── package.json
└── start.command                 # macOS 一键启动脚本
```

---

## 🧠 Vibe Coding 手记

> *"让 AI 写代码，让人类定方向。"*

这个项目诞生于一次实验：如果让 AI Agent 从零开始搭建一个**完整的端到端语音助手**——能听懂、能思考、能调用工具、能开口说话——能做到什么程度？

答案是：**架构可用，体验可期，工程待打磨。**

- AI 在数小时内完成了 Omni 协议对接、WebSocket 语音流、TTS 流式切片的骨架
- 人类花了数天调试音频字节对齐、Omni fallback 策略、流式播放的边界 case
- 最终呈现的效果，是人与 AI 协作的产物

**OmniVoice 不是一个玩具 Demo，它是一个证明**：当 Omni 多模态大模型遇见端到端流式 TTS，语音助手终于可以从"语音转文字再转语音"的笨重 pipeline，进化成真正"听说一体、能思会干"的智能体。

如果你也是 Vibe Coding 的践行者，欢迎来交流经验，更欢迎来一起把这个项目打磨成 Production Ready 的系统。

---

## 📄 许可证

[MIT](LICENSE)

---

<div align="center">

**Powered by <a href="https://github.com/OpenBMB/VoxCPM">面壁智能 VoxCPM2</a> · Built with Vibe Coding**

</div>
