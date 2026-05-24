import json
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Any
from schemas.models import Skill, SkillType

logger = logging.getLogger(__name__)

# ── Built-in skill implementations ───────────────────────────────────────────

async def _get_current_time(args: dict) -> str:
    tz_offset = args.get("timezone", "Asia/Shanghai")
    now = datetime.now(timezone(timedelta(hours=8)))
    return f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')} (UTC+8)"


async def _calculate(args: dict) -> str:
    expr = args.get("expression", "")
    try:
        # Safe eval: only allow basic math
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expr):
            return f"不安全的表达式: {expr}"
        result = eval(expr)
        return f"计算结果: {expr} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


async def _web_search(args: dict) -> str:
    query = args.get("query", "")
    # Stub implementation for demo
    return f'搜索结果（模拟）：关于 "{query}" 的信息暂时无法获取，这是一个演示功能。'


async def _transfer_call(args: dict) -> str:
    target = args.get("target_agent_id", "")
    reason = args.get("reason", "")
    return f"[HANDOFF:{target}] 原因：{reason}"


BUILTIN_SKILLS = {
    "get_current_time": _get_current_time,
    "calculate": _calculate,
    "web_search": _web_search,
    "transfer_call": _transfer_call,
}

# ── Default skill definitions ────────────────────────────────────────────────

DEFAULT_SKILLS = [
    Skill(
        id="skill_time",
        name="get_current_time",
        description="获取当前时间",
        type=SkillType.BUILTIN,
        enabled=True,
        parameters={
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "时区，如 Asia/Shanghai"}
            },
        },
    ),
    Skill(
        id="skill_calc",
        name="calculate",
        description="数学计算器",
        type=SkillType.BUILTIN,
        enabled=True,
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "数学表达式，如 2+3*4"}
            },
            "required": ["expression"],
        },
    ),
    Skill(
        id="skill_search",
        name="web_search",
        description="网络搜索（演示）",
        type=SkillType.BUILTIN,
        enabled=True,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"],
        },
    ),
    Skill(
        id="skill_transfer",
        name="transfer_call",
        description="转接给其他客服",
        type=SkillType.BUILTIN,
        enabled=True,
        parameters={
            "type": "object",
            "properties": {
                "target_agent_id": {"type": "string", "description": "目标客服ID"},
                "reason": {"type": "string", "description": "转接原因"},
            },
            "required": ["target_agent_id", "reason"],
        },
    ),
]


class SkillExecutor:
    """Execute skills/tools based on LLM tool calls."""

    def __init__(self, skills: list[Skill]):
        self._skills = {s.name: s for s in skills if s.enabled}

    def update_skills(self, skills: list[Skill]):
        self._skills = {s.name: s for s in skills if s.enabled}

    def get_tool_definitions(self) -> str:
        """Format enabled skills as tool definitions for LLM prompt."""
        lines = []
        for name, skill in self._skills.items():
            params = skill.parameters.get("properties", {})
            param_str = ", ".join(f"{k}: {v.get('type', 'string')}" for k, v in params.items())
            lines.append(f"- {name}({param_str}): {skill.description}")
        return "\n".join(lines) if lines else "无可用工具"

    def get_tools_json_schema(self) -> list[dict]:
        """Return OpenAI function-calling compatible tool definitions."""
        tools = []
        for name, skill in self._skills.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": skill.description,
                    "parameters": skill.parameters,
                }
            })
        return tools

    def parse_tool_call(self, llm_output: str):  # returns tuple[str, dict] or None
        """Try to extract a tool call from LLM output."""
        decoder = json.JSONDecoder()
        candidates = [llm_output.strip()]
        candidates.extend(llm_output[i:] for i, ch in enumerate(llm_output) if ch == "{")

        for candidate in candidates:
            try:
                data, _ = decoder.raw_decode(candidate.lstrip())
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and "tool_call" in data:
                tc = data["tool_call"]
                if isinstance(tc, dict):
                    return tc.get("name", ""), tc.get("arguments", {})

        return None

    async def execute(self, tool_name: str, arguments: dict) -> str:
        """Execute a skill and return the result."""
        skill = self._skills.get(tool_name)
        if not skill:
            return f"未知工具: {tool_name}"

        if skill.type == SkillType.BUILTIN:
            func = BUILTIN_SKILLS.get(tool_name)
            if func:
                return await func(arguments)
            return f"内置工具未实现: {tool_name}"

        elif skill.type == SkillType.HTTP:
            return await self._execute_http(skill, arguments)

        elif skill.type == SkillType.SCRIPT:
            return f"脚本执行暂不支持: {tool_name}"

        return f"未知工具类型: {skill.type}"

    async def _execute_http(self, skill: Skill, arguments: dict) -> str:
        """Execute HTTP skill."""
        url = skill.config.url or ""
        for key, value in arguments.items():
            url = url.replace(f"{{{key}}}", str(value))

        method = (skill.config.method or "GET").upper()
        headers = skill.config.headers or {}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers, params=arguments)
                else:
                    resp = await client.post(url, headers=headers, json=arguments)
                resp.raise_for_status()
                return resp.text[:2000]  # Limit response size
        except Exception as e:
            return f"HTTP请求失败: {e}"
