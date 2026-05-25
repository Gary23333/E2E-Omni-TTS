import json
import logging
import re
from typing import AsyncGenerator, Optional, Callable, Awaitable

from schemas.models import Agent, AgentGroup, GlobalConfig
from core.llm_client import LLMClient
from core.tts_client import TTSClient, mix_noise
from core.skill_executor import SkillExecutor
from core.rag_engine import RAGEngine
from prompts.templates import (
    ROUTER_PROMPT, AGENT_SYSTEM_PROMPT, RAG_CONTEXT_TEMPLATE,
    TOOL_CALL_TEMPLATE, TOOL_RESULT_TEMPLATE, WAITING_MESSAGES,
)

logger = logging.getLogger(__name__)


class AgentManager:
    """Multi-agent orchestrator: routing, tool execution, RAG injection, TTS."""

    def __init__(
        self,
        llm: LLMClient,
        tts: TTSClient,
        skill_executor: SkillExecutor,
        rag_engine: RAGEngine,
    ):
        self.llm = llm
        self.tts = tts
        self.skill_executor = skill_executor
        self.rag_engine = rag_engine
        self._active_agent: Optional[Agent] = None
        self._agent_group: Optional[AgentGroup] = None
        self._agents: list[Agent] = []
        self._history: list[dict] = []
        self._max_tool_rounds = 3

    def set_context(self, agents: list[Agent], group: AgentGroup, active_agent: Optional[Agent] = None):
        self._agents = agents
        self._agent_group = group
        self._active_agent = active_agent
        self._history = []

    def _find_agent(self, agent_id: str) -> Optional[Agent]:
        for a in self._agents:
            if a.id == agent_id:
                return a
        return None

    async def route_to_agent(self, user_message: str) -> Optional[Agent]:
        """Use router LLM to select the best agent for a user message."""
        if not self._agent_group or len(self._agents) <= 1:
            return self._agents[0] if self._agents else None

        agent_list = "\n".join(
            f"- ID: {a.id}, 名称: {a.name}, 角色: {a.role}, 描述: {a.systemPrompt[:80]}"
            for a in self._agents if a.enabled
        )

        prompt = self._agent_group.routerPrompt.format(
            agent_list=agent_list,
            user_message=user_message,
        )

        try:
            result = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
                stream=False,
            )
            data = json.loads(result.strip())
            agent_id = data.get("agent_id", "")
            confidence = data.get("confidence", 0)

            if confidence >= 0.6:
                agent = self._find_agent(agent_id)
                if agent and agent.enabled:
                    return agent
        except Exception as e:
            logger.warning(f"Router failed: {e}")

        # Fallback to default
        default_id = self._agent_group.defaultAgentId
        if default_id:
            agent = self._find_agent(default_id)
            if agent:
                return agent

        return self._agents[0] if self._agents else None

    def _build_messages(self, user_message: str, agent: Agent) -> list[dict]:
        """Build message list for LLM with system prompt, RAG context, tools."""
        # RAG context
        rag_section = ""
        if agent.ragEnabled:
            chunks = self.rag_engine.retrieve(user_message)
            if chunks:
                rag_section = RAG_CONTEXT_TEMPLATE.format(
                    chunks="\n---\n".join(chunks)
                )

        # Tools section
        tools_section = ""
        tool_defs = self.skill_executor.get_tool_definitions(agent.enabledToolIds or None)
        if tool_defs and tool_defs != "无可用工具":
            tools_section = TOOL_CALL_TEMPLATE.format(tool_definitions=tool_defs)

        system_prompt = AGENT_SYSTEM_PROMPT.format(
            name=agent.name,
            role=agent.role,
            system_prompt=agent.systemPrompt,
            rag_context=rag_section,
            tools_section=tools_section,
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_message})

        return messages

    async def process_message(
        self,
        user_message: str,
        agent: Agent,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None,
        on_tool_start: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_tool_end: Optional[Callable[[str], Awaitable[None]]] = None,
        on_waiting: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[str, Optional[str]]:
        """
        Process a user message with the given agent.
        Returns (response_text, handoff_target_id).
        """
        logger.info(f"Processing message: {user_message} for agent {agent.name}")
        self._active_agent = agent
        messages = self._build_messages(user_message, agent)

        # Tool call loop
        for round_idx in range(self._max_tool_rounds):
            logger.info(f"LLM Chat Round {round_idx+1}")
            # Stream LLM response
            full_response = ""
            try:
                stream = await self.llm.chat(
                    messages=messages,
                    temperature=agent.temperature,
                    max_tokens=agent.maxTokens,
                    stream=True,
                )
                logger.info("LLM stream started")

                async for token in stream:
                    full_response += token
                    if on_token:
                        await on_token(token)

                logger.info(f"LLM full response received: {full_response}")
            except Exception as e:
                logger.error(f"LLM chat error: {e}")
                return "抱歉，由于网络原因，我现在无法回答您。", None

            # Check for tool call
            tool_call = self.skill_executor.parse_tool_call(full_response)
            if tool_call:
                if round_idx >= self._max_tool_rounds - 1:
                    logger.warning("Tool call skipped because max tool rounds was reached.")
                    return "抱歉，查询过程暂时没有完成，请稍后再试。", None

                tool_name, arguments = tool_call
                # Notify frontend
                if on_tool_start:
                    await on_tool_start(tool_name, WAITING_MESSAGES["tool_call"])
                if on_waiting:
                    await on_waiting(WAITING_MESSAGES["tool_call"])

                # Execute tool
                result = await self.skill_executor.execute(tool_name, arguments)

                if on_tool_end:
                    await on_tool_end(tool_name)

                # Add tool call and result to messages
                messages.append({"role": "assistant", "content": full_response})
                messages.append({"role": "user", "content": TOOL_RESULT_TEMPLATE.format(
                    tool_name=tool_name, result=result
                )})
                continue

            # Check for handoff
            handoff_match = re.search(r'\[HANDOFF:(\w+)\]', full_response)
            handoff_target = None
            if handoff_match:
                handoff_target = handoff_match.group(1)
                full_response = re.sub(r'\[HANDOFF:\w+\]', '', full_response).strip()

            # Save to history
            self._history.append({"role": "user", "content": user_message})
            self._history.append({"role": "assistant", "content": full_response})

            # Keep history manageable
            if len(self._history) > 40:
                self._history = self._history[-20:]

            return full_response, handoff_target

        return full_response if 'full_response' in dir() else "", None

    async def process_voice(
        self,
        text: str,
        audio_base64: str,
        agent: Agent,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None,
        on_waiting: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[str, Optional[str]]:
        """
        Process audio input directly for Omni mode.
        """
        self._active_agent = agent
        
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            name=agent.name,
            role=agent.role,
            system_prompt=agent.systemPrompt,
            rag_context="", 
            tools_section="",
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            *self._history,
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": f"data:audio/wav;base64,{audio_base64}"}},
                    {"type": "text", "text": "请根据这段音频内容回答用户。"}
                ]
            }
        ]

        full_response = ""
        try:
            logger.info("Attempting Omni multi-modal request")
            stream = await self.llm.chat(
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.maxTokens,
                stream=True,
            )

            async for token in stream:
                full_response += token
                if on_token:
                    await on_token(token)
        except Exception as e:
            logger.warning(f"Omni chat failed (likely text-only model): {e}. Falling back to text mode.")
            # Fallback to standard process_message using the ASR text
            return await self.process_message(text, agent, on_token, None, None, on_waiting)

        if not full_response.strip():
            logger.warning("Omni chat returned no visible content. Falling back to ASR text mode.")
            return await self.process_message(text, agent, on_token, None, None, on_waiting)

        # Save to history
        self._history.append({"role": "user", "content": text})
        self._history.append({"role": "assistant", "content": full_response})
        
        return full_response, None

    async def synthesize_speech(
        self,
        text: str,
        voice_descriptor: str = "",
        noise_type: str = "none",
        noise_volume: float = 0.0,
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize speech with optional voice descriptor and noise mixing."""
        # Prepend voice descriptor for VoxCPM2 persona
        tts_input = f"{voice_descriptor}{text}" if voice_descriptor else text

        async for chunk in self.tts.synthesize_streaming(tts_input):
            yield mix_noise(chunk, noise_type, noise_volume)
