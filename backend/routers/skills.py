from fastapi import APIRouter, HTTPException
from schemas.models import Skill
from core.json_store import JsonStore
from core.skill_executor import DEFAULT_SKILLS

router = APIRouter()

skill_store = JsonStore("skills.json", Skill)

# Initialize default skills if empty
if not skill_store.list_all():
    for s in DEFAULT_SKILLS:
        skill_store.create(s)


@router.get("")
async def list_skills():
    return skill_store.list_all()


@router.post("")
async def create_skill(skill: Skill):
    return skill_store.create(skill)


@router.put("/{skill_id}")
async def update_skill(skill_id: str, updates: dict):
    result = skill_store.update(skill_id, updates)
    if not result:
        raise HTTPException(404, "Skill not found")
    return result


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    skill = skill_store.get(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.type == "builtin":
        raise HTTPException(400, "Cannot delete built-in skills")
    skill_store.delete(skill_id)
    return {"ok": True}


@router.put("/{skill_id}/toggle")
async def toggle_skill(skill_id: str):
    skill = skill_store.get(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    skill_store.update(skill_id, {"enabled": not skill.enabled})
    return skill_store.get(skill_id)
