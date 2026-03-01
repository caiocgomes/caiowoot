from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.learned_rules import create_rule, get_all_rules, toggle_rule, update_rule

router = APIRouter()


class RuleCreate(BaseModel):
    rule_text: str
    source_edit_pair_id: int | None = None


class RuleUpdate(BaseModel):
    rule_text: str


@router.get("/rules")
async def list_rules():
    rules = await get_all_rules()
    return {"rules": rules}


@router.post("/rules")
async def create_new_rule(req: RuleCreate):
    rule = await create_rule(req.rule_text, req.source_edit_pair_id)
    return rule


@router.put("/rules/{rule_id}")
async def update_existing_rule(rule_id: int, req: RuleUpdate):
    rule = await update_rule(rule_id, req.rule_text)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.patch("/rules/{rule_id}/toggle")
async def toggle_existing_rule(rule_id: int):
    rule = await toggle_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule
