# OmniVoice 项目代码审查与完善计划

## 一、项目概述

OmniVoice 是一个端到端大模型语音助手，核心设计目标：
1. **Omni 原生语音理解**：语音直送大模型，无需 ASR 文本中转
2. **VoxCPM2 流式 TTS**：边生成边播放，毫秒级首句延迟
3. **Agent 智能路由 + 实时工具调用**：多 Agent 动态路由，支持工具调用
4. **沉浸式实时交互**：通话打断、音频环境模拟、TTS 文本清洗

## 二、设计目标 vs 代码实现对照分析

### 2.1 已完整实现的功能

| 设计目标 | 实现状态 | 代码位置 |
|---------|---------|---------|
| FastAPI 后端框架 | 完整 | `backend/main.py` |
| React 19 前端框架 | 完整 | `frontend/src/App.tsx` |
| WebSocket 语音流传输 | 完整 | `backend/routers/ws_voice.py`, `frontend/src/api/wsClient.ts` |
| Omni 模式音频输入 | 完整 | `backend/routers/ws_voice.py:run_omni_response()` |
| ASR fallback 降级链路 | 完整 | `backend/routers/ws_voice.py:run_asr_text_response()` |
| 流式 TTS 智能切片 | 完整 | `backend/routers/ws_voice.py:StreamingTTSBridge` |
| TTS 文本清洗 | 完整 | `backend/routers/ws_voice.py:sanitize_tts_text()` |
| 通话打断 | 完整 | `backend/routers/ws_voice.py:cancel_active_response()` |
| 多 Agent 动态路由 | 完整 | `backend/core/agent_manager.py:route_to_agent()` |
| Agent 协作转接 [HANDOFF] | 完整 | `backend/core/agent_manager.py:process_message()` |
| 工具调用循环 | 完整 | `backend/core/agent_manager.py:process_message()` |
| RAG 知识库 | 完整 | `backend/core/rag_engine.py` |
| 背景噪音混音 | 完整 | `backend/core/noise_manager.py` |
| 前端 PCM 采集 16kHz | 完整 | `frontend/src/hooks/useAudioRecorder.ts` |
| 前端 AudioContext 48kHz 播放 | 完整 | `frontend/src/hooks/useAudioPlayer.ts` |
| 暗色玻璃拟态 UI | 完整 | `frontend/src/index.css` |
| Agent/Group CRUD | 完整 | `backend/routers/agents.py`, `frontend/src/components/config/AgentConfig.tsx` |
| RAG 文档管理 | 完整 | `backend/routers/rag.py`, `frontend/src/components/config/RAGManager.tsx` |
| Skill 插件管理 | 完整 | `backend/routers/skills.py`, `frontend/src/components/config/SkillManager.tsx` |
| 系统设置面板 | 完整 | `frontend/src/components/config/SettingsPanel.tsx` |
| 服务健康检测 | 完整 | `backend/routers/config.py:test_llm/test_tts/test_asr/test_embed` |
| 环境噪音上传/预览 | 完整 | `backend/routers/config.py`, `frontend/src/components/config/SettingsPanel.tsx` |
| VoxCPM2 本地 TTS Server | 完整 | `backend/voxcpm_tts_server.py` |

### 2.2 存在缺陷或不完善的部分

#### 🔴 严重问题

1. **ASR 客户端是 Mock 实现**
   - 文件：`backend/core/asr_client.py`
   - 问题：`ASRClient` 是硬编码的 mock，始终返回 "你好，我想咨询业务。"
   - 影响：ASR fallback 链路和 text_asr 模式完全不可用
   - 设计目标要求："ASR 并行兜底"，但当前 ASR 根本无法识别真实语音

2. **LLM 流式响应中 on_token 回调未被调用**
   - 文件：`backend/core/agent_manager.py:process_message()`
   - 问题：第 155-158 行先收集完整响应，然后才一次性发送，流式 token 回调在循环结束后才调用
   - 影响：前端无法实时显示 LLM 生成的 token，只能等完整响应后一次性显示
   - 代码逻辑：
     ```python
     async for token in stream:
         full_response += token  # 只累加，不回调
     # 循环结束后才调用 on_token(full_response) —— 这不是流式！
     ```

3. **Omni 模式下 process_voice 的 on_token 回调在异常时丢失**
   - 文件：`backend/core/agent_manager.py:process_voice()`
   - 问题：第 255-258 行虽然实时回调 token，但如果 Omni 失败 fallback 到 process_message，process_message 中的 on_token 不会实时回调

4. **前端 WebSocket 未处理 binary 消息**
   - 文件：`frontend/src/api/wsClient.ts`
   - 问题：第 46-55 行 `onmessage` 只处理 `typeof event.data === 'string'`，binary 音频数据被忽略
   - 虽然 `CallPanel.tsx` 第 73-77 行单独添加了 binary 监听器，但这是双重监听，设计不够优雅

#### 🟡 中等问题

5. **TTS 流式生成与 LLM 流式生成未真正并行**
   - 文件：`backend/routers/ws_voice.py:StreamingTTSBridge`
   - 问题：TTS Bridge 等待 LLM 输出完整片段后才送入 TTS，虽然 TTS 内部是流式的，但 LLM→TTS 的流水线存在等待
   - 设计目标声称："LLM token 与 TTS 音频并行流水线处理"
   - 实际：StreamingTTSBridge._run() 是顺序执行的，一个 segment 完整 TTS 完才取下一个

6. **Agent 的 enabledToolIds 未被使用**
   - 文件：`backend/core/agent_manager.py:_build_messages()`
   - 问题：第 106-108 行获取所有可用工具，没有根据 `agent.enabledToolIds` 过滤
   - 每个 Agent 应该只能使用自己被授权的工具

7. **SkillExecutor.parse_tool_call 解析方式脆弱**
   - 文件：`backend/core/skill_executor.py:parse_tool_call()`
   - 问题：依赖 LLM 输出纯 JSON，没有使用 OpenAI function calling 格式
   - 虽然 `get_tools_json_schema()` 提供了标准格式，但 `chat()` 方法没有传入 `tools` 参数

8. **缺少 Session 持久化**
   - 文件：`backend/schemas/models.py:Session`
   - 问题：Session 模型已定义但没有任何地方使用，通话记录不保存

9. **前端缺少路由配置**
   - 文件：`frontend/src/App.tsx`
   - 问题：虽然导入了 `react-router-dom`，但实际使用简单的 state 切换页面，没有使用 Router

10. **噪音样本文件可能不存在**
    - 文件：`backend/data/noise_samples/`
    - 问题：`cafe.wav`, `office.wav`, `street.wav` 文件存在但内容未知，如果格式不正确会导致混音失败

#### 🟢 轻微问题

11. **代码中缺少类型注解完善**
    - 部分函数返回类型为 `Optional` 但没有正确处理 None

12. **测试脚本较粗糙**
    - `test_integration.py`, `test_voice.py`, `test_omni.py` 是手动测试脚本，没有自动化测试框架

13. **前端 `callStore` 中的 `on_hold` 状态未使用**
    - `CallStatus` 类型包含 `'on_hold'` 但 UI 中没有对应处理

14. **CollaborationRule 模型定义但未使用**
    - `AgentGroup.collaborationRules` 字段存在但路由逻辑中没有使用

## 三、修复计划

### Phase 1: 修复严重问题（必须修复）

1. **修复 LLM 流式 token 实时回调**
   - 修改 `backend/core/agent_manager.py:process_message()`
   - 在 `async for token in stream:` 循环内部实时调用 `on_token(token)`
   - 同时需要调整 `ws_voice.py` 中 `handle_llm_token` 的处理逻辑

2. **修复 ASR 客户端为真实实现**
   - 修改 `backend/core/asr_client.py`
   - 接入 FunASR 或其他真实 ASR 服务
   - 或者至少实现基于 HTTP 的 ASR 调用

3. **修复前端 WebSocket binary 消息处理**
   - 修改 `frontend/src/api/wsClient.ts`
   - 在 `onmessage` 中同时处理 binary 数据，通过回调传递给使用者
   - 移除 `CallPanel.tsx` 中额外的 binary 监听器

4. **修复 Agent enabledToolIds 过滤**
   - 修改 `backend/core/agent_manager.py:_build_messages()`
   - 根据 `agent.enabledToolIds` 过滤工具定义

### Phase 2: 修复中等问题（建议修复）

5. **优化 TTS-LLM 并行流水线**
   - 考虑在 `StreamingTTSBridge` 中使用更激进的切片策略
   - 或者实现真正的双线程并行：一个协程读 LLM，一个协程读 TTS

6. **完善工具调用格式**
   - 修改 `backend/core/llm_client.py:chat()`
   - 支持传入 `tools` 参数，使用 OpenAI function calling 标准格式

7. **添加 Session 持久化**
   - 在 `ws_voice.py` 中保存通话记录到 `Session` 存储

8. **修复前端路由**
   - 使用 `react-router-dom` 的 `BrowserRouter` 替代 state 切换

### Phase 3: 优化与完善（可选）

9. **添加单元测试和集成测试**
10. **完善类型注解**
11. **添加 API 文档**
12. **优化错误处理和边界 case**

## 四、结论

**整体评价：代码完成了约 75% 的设计目标。**

- 架构层面：端到端架构完整，前后端分离，WebSocket 通信正常
- UI 层面：暗色玻璃拟态设计精美，所有配置页面完整
- 核心功能：Omni 模式、TTS 流式、Agent 路由、工具调用、RAG、噪音混音均已实现
- **关键缺陷**：LLM 流式回调未实时触发、ASR 是 Mock、工具调用格式非标准

**建议优先级：**
1. 立即修复 LLM 流式回调问题（影响用户体验最大）
2. 实现真实 ASR 客户端（影响核心功能）
3. 完善工具调用标准格式（影响 Agent 能力）
4. 其他优化项可逐步迭代
