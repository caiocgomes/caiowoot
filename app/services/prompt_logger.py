import hashlib
import os
from pathlib import Path

from app.config import settings


def save_prompt(prompt_text: str) -> str:
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()
    prompts_dir = Path(settings.database_path).parent / "prompts"
    os.makedirs(prompts_dir, exist_ok=True)
    prompt_file = prompts_dir / f"{prompt_hash}.txt"
    if not prompt_file.exists():
        prompt_file.write_text(prompt_text, encoding="utf-8")
    return prompt_hash
