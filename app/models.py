from datetime import datetime

from pydantic import BaseModel


class Message(BaseModel):
    id: int
    conversation_id: int
    evolution_message_id: str | None = None
    direction: str
    content: str
    media_url: str | None = None
    media_type: str | None = None
    created_at: datetime


class Draft(BaseModel):
    id: int
    conversation_id: int
    trigger_message_id: int
    draft_text: str
    justification: str | None = None
    status: str = "pending"
    draft_group_id: str | None = None
    variation_index: int | None = None
    approach: str | None = None
    prompt_hash: str | None = None
    operator_instruction: str | None = None
    created_at: datetime


class Conversation(BaseModel):
    id: int
    phone_number: str
    contact_name: str | None = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None
    last_message_at: datetime | None = None
    has_unread: bool = False


class ConversationDetail(BaseModel):
    conversation: Conversation
    messages: list[Message]
    pending_drafts: list[Draft] = []


class EditPair(BaseModel):
    id: int
    conversation_id: int
    customer_message: str
    original_draft: str
    final_message: str
    was_edited: bool
    operator_instruction: str | None = None
    all_drafts_json: str | None = None
    selected_draft_index: int | None = None
    prompt_hash: str | None = None
    regeneration_count: int = 0
    created_at: datetime


class SendRequest(BaseModel):
    text: str
    draft_id: int | None = None
    draft_group_id: str | None = None
    selected_draft_index: int | None = None
    operator_instruction: str | None = None
    regeneration_count: int = 0


class RegenerateRequest(BaseModel):
    draft_index: int | None = None
    operator_instruction: str | None = None
    trigger_message_id: int
