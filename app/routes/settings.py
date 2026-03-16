from fastapi import APIRouter, HTTPException
from starlette.requests import Request

from app.auth import get_operator_from_request, is_admin
from app.services.prompt_config import get_all_prompts, update_prompts, reset_prompt
from app.services.operator_profile import get_profile, upsert_profile

router = APIRouter()


@router.get("/api/settings/prompts")
async def get_prompts_endpoint():
    return await get_all_prompts()


@router.put("/api/settings/prompts")
async def put_prompts_endpoint(req: Request):
    operator = get_operator_from_request(req)
    if not is_admin(operator):
        raise HTTPException(status_code=403, detail="Admin only")

    body = await req.json()
    updates = {}
    resets = []
    for key, value in body.items():
        if value is not None:
            updates[key] = value
        else:
            resets.append(key)

    if updates:
        await update_prompts(updates)
    for key in resets:
        await reset_prompt(key)

    return {"status": "ok"}


@router.get("/api/settings/profile")
async def get_profile_endpoint(req: Request):
    operator = get_operator_from_request(req)
    if not operator:
        return {"display_name": "", "context": ""}
    profile = await get_profile(operator)
    if not profile:
        return {"display_name": "", "context": ""}
    return {"display_name": profile["display_name"] or "", "context": profile["context"] or ""}


@router.put("/api/settings/profile")
async def put_profile_endpoint(req: Request):
    operator = get_operator_from_request(req)
    if not operator:
        raise HTTPException(status_code=400, detail="No operator in session")
    body = await req.json()
    await upsert_profile(operator, body.get("display_name", ""), body.get("context", ""))
    return {"status": "ok"}


@router.get("/api/settings/is-admin")
async def is_admin_endpoint(req: Request):
    operator = get_operator_from_request(req)
    return {"is_admin": is_admin(operator)}
