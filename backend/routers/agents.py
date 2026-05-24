from fastapi import APIRouter, HTTPException
from schemas.models import Agent, AgentGroup
from core.json_store import JsonStore

router = APIRouter()

agent_store = JsonStore("agents.json", Agent)
group_store = JsonStore("agent_groups.json", AgentGroup)

# Initialize default data if empty
if not agent_store.list_all():
    default_agent_1 = Agent(
        id="agent_001",
        name="小美",
        role="general",
        systemPrompt="你是一个专业、友好的客服人员。你叫小美，专门处理客户咨询。",
        voiceDescriptor="(A warm and friendly female voice",
        temperature=0.7,
        maxTokens=1024,
        enabledToolIds=["skill_time", "skill_calc"],
        ragEnabled=False,
        enabled=True,
    )
    default_agent_2 = Agent(
        id="agent_002",
        name="技术支持 小智",
        role="tech_support",
        systemPrompt="你是技术支持专家，专门处理技术问题。",
        voiceDescriptor="(A professional male voice)",
        temperature=0.6,
        maxTokens=1024,
        enabledToolIds=["skill_transfer"],
        ragEnabled=True,
        enabled=True,
    )
    agent_store.create(default_agent_1)
    agent_store.create(default_agent_2)

if not group_store.list_all():
    default_group = AgentGroup(
        id="group_default",
        name="默认客服组",
        description="处理所有一般咨询",
        agentIds=["agent_001", "agent_002"],
        defaultAgentId="agent_001",
        routerPrompt="你是路由代理。根据用户消息判断应该由哪个客服处理。\n可用客服：\n- agent_001: 小美，处理一般咨询\n- agent_002: 技术支持，处理技术问题\n\n用户消息：{user_message}\n\n请返回JSON格式：{\"agent_id\":\"xxx\",\"confidence\":0.9,\"reason\":\"原因\"}",
        collaborationRules=[],
    )
    group_store.create(default_group)


# ── Agents ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_agents():
    return agent_store.list_all()


@router.post("")
async def create_agent(agent: Agent):
    return agent_store.create(agent)


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    agent = agent_store.get(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@router.put("/{agent_id}")
async def update_agent(agent_id: str, updates: dict):
    result = agent_store.update(agent_id, updates)
    if not result:
        raise HTTPException(404, "Agent not found")
    return result


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if not agent_store.delete(agent_id):
        raise HTTPException(404, "Agent not found")
    return {"ok": True}


# ── Agent Groups ─────────────────────────────────────────────────────────────

@router.get("/groups/list")
async def list_groups():
    return group_store.list_all()


@router.post("/groups")
async def create_group(group: AgentGroup):
    return group_store.create(group)


@router.get("/groups/{group_id}")
async def get_group(group_id: str):
    group = group_store.get(group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    return group


@router.put("/groups/{group_id}")
async def update_group(group_id: str, updates: dict):
    result = group_store.update(group_id, updates)
    if not result:
        raise HTTPException(404, "Group not found")
    return result


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str):
    if not group_store.delete(group_id):
        raise HTTPException(404, "Group not found")
    return {"ok": True}
