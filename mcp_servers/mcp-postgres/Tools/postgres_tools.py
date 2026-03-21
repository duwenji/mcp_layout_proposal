from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))

from bootstrap import ensure_context
from mcp_postgres_duwenji.tools.crud_tools import get_crud_handlers, get_crud_tools
from mcp_postgres_duwenji.tools.elicitation_tools import (
    get_elicitation_handlers,
    get_elicitation_tools,
)
from mcp_postgres_duwenji.tools.sampling_integration import (
    get_sampling_integration_handlers,
    get_sampling_integration_tools,
)
from mcp_postgres_duwenji.tools.sampling_tools import (
    get_sampling_handlers,
    get_sampling_tools,
)
from mcp_postgres_duwenji.tools.schema_tools import (
    get_schema_handlers,
    get_schema_tools,
)
from mcp_postgres_duwenji.tools.table_tools import get_table_handlers, get_table_tools
from mcp_postgres_duwenji.tools.transaction_tools import (
    get_transaction_handlers,
    get_transaction_tools,
)


async def _health_check() -> Dict[str, Any]:
    context = await ensure_context()
    status: Dict[str, Any] = {
        "status": "healthy",
        "components": {},
    }

    if context.pool_manager:
        try:
            db_healthy = context.pool_manager.test_connection()
            status["components"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "connection_test": db_healthy,
            }
            if not db_healthy:
                status["status"] = "unhealthy"
        except Exception as exc:
            status["components"]["database"] = {
                "status": "error",
                "error": str(exc),
            }
            status["status"] = "unhealthy"
    else:
        status["components"]["database"] = {"status": "not_initialized"}
        status["status"] = "unhealthy"

    return status


def _tool_wrapper(
    handler: Callable[..., Awaitable[Dict[str, Any]]],
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    async def _wrapped(**kwargs: Any) -> Dict[str, Any]:
        await ensure_context()
        try:
            return await handler(**kwargs)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return _wrapped


def register(server) -> None:
    tool_defs = (
        get_crud_tools()
        + get_schema_tools()
        + get_table_tools()
        + get_sampling_tools()
        + get_transaction_tools()
        + get_sampling_integration_tools()
        + get_elicitation_tools()
    )
    handlers = {
        **get_crud_handlers(),
        **get_schema_handlers(),
        **get_table_handlers(),
        **get_sampling_handlers(),
        **get_transaction_handlers(),
        **get_sampling_integration_handlers(),
        **get_elicitation_handlers(),
    }
    metadata_by_name = {tool.name: tool for tool in tool_defs}

    for tool_name, handler in handlers.items():
        wrapped = _tool_wrapper(handler)
        wrapped.__name__ = f"tool_{tool_name}"

        tool_def = metadata_by_name.get(tool_name)
        description = tool_def.description if tool_def else None
        meta = getattr(tool_def, "_meta", None) if tool_def else None

        server.add_tool(
            wrapped,
            name=tool_name,
            description=description,
            meta=meta,
            structured_output=True,
        )

    @server.tool(name="health_check", description="Check server health status", structured_output=True)
    async def health_check() -> Dict[str, Any]:
        return {"success": True, "health": await _health_check()}
