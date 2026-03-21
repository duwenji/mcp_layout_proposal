from __future__ import annotations

import sys
from pathlib import Path
from typing import Awaitable, Callable

_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))

from bootstrap import ensure_context
from mcp_postgres_duwenji.resources import (
    get_database_resources,
    get_resource_handlers,
    get_table_schema_resource_handler,
)


def _resource_wrapper(handler: Callable[[], Awaitable[str]]) -> Callable[[], Awaitable[str]]:
    async def _wrapped() -> str:
        await ensure_context()
        return await handler()

    return _wrapped


def register(server) -> None:
    static_resources = get_database_resources()
    resource_handlers = get_resource_handlers()

    for resource in static_resources:
        uri = str(resource.uri)
        handler = resource_handlers.get(uri)
        if handler is None:
            continue

        wrapped = _resource_wrapper(handler)
        wrapped.__name__ = f"resource_{resource.name.lower().replace(' ', '_')}"

        decorator = server.resource(
            uri,
            name=resource.name,
            description=resource.description,
            mime_type=resource.mimeType,
        )
        decorator(wrapped)

    table_schema_handler = get_table_schema_resource_handler()

    @server.resource(
        "database://schema/{table_name}",
        name="Table Schema",
        description="Schema information for a table",
        mime_type="text/markdown",
    )
    async def table_schema_resource(table_name: str) -> str:
        await ensure_context()
        return await table_schema_handler(table_name, "public")
