from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))

from mcp_postgres_duwenji.prompts import get_prompt_manager


def _build_prompt_func(template: str):
    def _prompt_func(**kwargs) -> str:
        try:
            return template.format(**kwargs)
        except KeyError as exc:
            missing = str(exc).strip("'")
            return f"Missing prompt argument: {missing}"

    return _prompt_func


def register(server) -> None:
    prompt_manager = get_prompt_manager()
    prompts: Dict[str, Dict] = prompt_manager.prompts

    for key, config in prompts.items():
        messages = config.get("messages", [])
        text = ""
        if messages:
            content = getattr(messages[0], "content", None)
            text = getattr(content, "text", "") or ""

        fn = _build_prompt_func(text)
        fn.__name__ = f"prompt_{key}"

        decorator = server.prompt(name=key, description=config.get("description", ""))
        decorator(fn)
