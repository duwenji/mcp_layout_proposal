from __future__ import annotations

import asyncio
import atexit
import sys
from pathlib import Path
from typing import Optional

_IMPL_ROOT = Path(__file__).resolve().parent / "_impl"
if str(_IMPL_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPL_ROOT))

from mcp_postgres_duwenji.context import (  # noqa: E402
    AppContext,
    _initialize_context,
    set_global_context,
)

_context: Optional[AppContext] = None
_init_lock = asyncio.Lock()


async def ensure_context() -> AppContext:
    global _context

    if _context and _context.is_initialized():
        return _context

    async with _init_lock:
        if _context and _context.is_initialized():
            return _context

        context = AppContext()
        await _initialize_context(context)
        context.mark_initialized()
        set_global_context(context)
        _context = context
        return context


async def shutdown_context() -> None:
    global _context
    if _context and _context.is_initialized():
        await _context.shutdown()
    _context = None


def _shutdown_on_exit() -> None:
    try:
        asyncio.run(shutdown_context())
    except RuntimeError:
        # Ignore cases where an event loop is already running at interpreter exit.
        pass


atexit.register(_shutdown_on_exit)
