"""
Main entry point for PostgreSQL MCP Server
"""

import asyncio
import datetime
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .database import DatabaseManager
from .context import AppContext, create_lifespan_context
from .tools.crud_tools import (
    get_crud_tools,
    get_crud_handlers,
)
from .tools.schema_tools import get_schema_tools, get_schema_handlers
from .tools.table_tools import get_table_tools, get_table_handlers
from .tools.sampling_tools import get_sampling_tools, get_sampling_handlers
from .tools.transaction_tools import get_transaction_tools, get_transaction_handlers
from .tools.sampling_integration import (
    get_sampling_integration_tools,
    get_sampling_integration_handlers,
)
from .tools.elicitation_tools import (
    get_elicitation_tools,
    get_elicitation_handlers,
)
from .resources import (
    get_database_resources,
    get_resource_handlers,
    get_table_schema_resource_handler,
)
from .protocol_logging import (
    sanitize_log_output,
    protocol_logging_server,
)
from .prompts import get_prompt_manager
from mcp import (
    Resource,
    Tool,
    ListPromptsRequest,
    ListPromptsResult,
    GetPromptResult,
)
import mcp.types as types


# Note: setup_logging function has been moved to shared.py
# Global variables have been removed in favor of context-based resource management


# Note: Signal handling and graceful shutdown are now managed by the AppContext class


async def health_check(context: AppContext) -> Dict[str, Any]:
    """
    Perform health check of server components

    Args:
        context: Application context containing server resources

    Returns:
        Dictionary with health status information
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "components": {},
    }

    # Check database connection
    components: Dict[str, Any] = {}
    if context.pool_manager:
        try:
            db_healthy = context.pool_manager.test_connection()
            components["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "connection_test": db_healthy,
            }
            if not db_healthy:
                health_status["status"] = "unhealthy"
        except Exception as e:
            components["database"] = {
                "status": "error",
                "error": str(e),
            }
            health_status["status"] = "unhealthy"
    else:
        components["database"] = {"status": "not_initialized"}
        health_status["status"] = "unhealthy"

    health_status["components"] = components

    return health_status


# Note: The lifespan function has been replaced by create_lifespan_context from context.py


async def main() -> None:
    """Main entry point for the MCP server"""
    # Create MCP server with new context-based lifespan management
    async with create_lifespan_context() as context:
        # Validate context is properly initialized
        context.validate()

        # Create MCP server with context stored for handlers
        server = Server("postgres-mcp-server")

        # Store context in server for access by handlers
        # Use type: ignore to bypass mypy check since Server class doesn't have context attribute
        server.context = context  # type: ignore[attr-defined]

        # Check if MCP library supports concerns feature and add concerns to server if supported
        supports_concerns = hasattr(server, "_declared_concerns") or hasattr(
            server, "declare_concerns"
        )
        if supports_concerns:
            context.logger.info("MCP library supports concerns feature")

            # Check if ConcernDefinition exists in types module
            ConcernDefinition = getattr(types, "ConcernDefinition", None)
            if ConcernDefinition is None:
                context.logger.warning(
                    "ConcernDefinition not found in mcp.types - concerns feature disabled"
                )
                supports_concerns = False
            else:
                # Define concerns list using ConcernDefinition
                concerns_list = [
                    ConcernDefinition(
                        name="development",
                        description="開発フェーズ",
                        values=["planning", "development", "testing", "maintenance", "*"],
                        default="development",
                    ),
                    ConcernDefinition(
                        name="maintenance",
                        description="保守フェーズ",
                        values=["none", "basic", "advanced", "*"],
                        default="basic",
                    ),
                    ConcernDefinition(
                        name="using",
                        description="使用フェーズ",
                        values=["exploration", "regular_use", "optimization", "*"],
                        default="regular_use",
                    ),
                    ConcernDefinition(
                        name="tuning",
                        description="チューニング要件",
                        values=["none", "basic", "advanced", "performance", "*"],
                        default="basic",
                    ),
                ]

                # Add concerns to server before creating initialization options
                if hasattr(server, "_declared_concerns"):
                    server._declared_concerns = concerns_list
                    context.logger.info("Added concerns to server._declared_concerns")
                elif hasattr(server, "declare_concerns"):
                    server.declare_concerns(concerns_list)
                    context.logger.info("Added concerns via server.declare_concerns()")

        if not supports_concerns:
            context.logger.warning(
                "MCP library does not support concerns feature - filtering disabled"
            )

        # Get tools and handlers
        crud_tools = get_crud_tools()
        crud_handlers = get_crud_handlers()
        schema_tools = get_schema_tools()
        schema_handlers = get_schema_handlers()
        table_tools = get_table_tools()
        table_handlers = get_table_handlers()
        sampling_tools = get_sampling_tools()
        sampling_handlers = get_sampling_handlers()
        transaction_tools = get_transaction_tools()
        transaction_handlers = get_transaction_handlers()
        sampling_integration_tools = get_sampling_integration_tools()
        sampling_integration_handlers = get_sampling_integration_handlers()
        elicitation_tools = get_elicitation_tools()
        elicitation_handlers = get_elicitation_handlers()

        # Combine all tools and handlers
        all_tools = (
            crud_tools
            + schema_tools
            + table_tools
            + sampling_tools
            + transaction_tools
            + sampling_integration_tools
            + elicitation_tools
        )
        all_handlers = {
            **crud_handlers,
            **schema_handlers,
            **table_handlers,
            **sampling_handlers,
            **transaction_handlers,
            **sampling_integration_handlers,
            **elicitation_handlers,
        }

        # Register tool handlers
        @server.call_tool()
        async def handle_tool_call(name: str, arguments: dict) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
            """Handle tool execution requests"""

            # Get context from server
            context = server.context  # type: ignore[attr-defined]
            logger = context.logger
            config = context.config

            logger.info(f"TOOL_INPUT - Tool: {name}, Arguments: {arguments}")

            # Handle health check tool
            if name == "health_check":
                try:
                    result = await health_check(context)
                    logger.info(f"HEALTH_CHECK_RESULT - Status: {result['status']}")
                    return {"success": True, "health": result}
                except Exception as e:
                    logger.error(f"HEALTH_CHECK_ERROR - Error: {e}")
                    return {"success": False, "error": str(e)}

            if name in all_handlers:
                handler = all_handlers[name]
                try:
                    # プロトコルデバッグモード時の追加ログ
                    if config.protocol_debug:
                        logger.debug(f"TOOL_DEBUG - Executing handler for: {name}")
                        logger.debug(
                            f"TOOL_DEBUG - Handler function: {handler.__name__}"
                        )

                    result = await handler(**arguments)
                    # 詳細な出力ログ（機密情報をマスク）
                    sanitized_result = sanitize_log_output(result)
                    logger.info(
                        f"TOOL_OUTPUT - Tool: {name}, Result: {sanitized_result}"
                    )

                    # プロトコルデバッグモード時の追加ログ
                    if config.protocol_debug:
                        logger.debug(f"TOOL_DEBUG - Raw result type: {type(result)}")
                        if isinstance(result, dict):
                            logger.debug(
                                f"TOOL_DEBUG - Raw result keys: {list(result.keys())}"
                            )
                        else:
                            logger.debug("TOOL_DEBUG - Raw result keys: N/A")

                    return result
                except Exception as e:
                    logger.error(f"TOOL_ERROR - Tool: {name}, Error: {e}")
                    # プロトコルデバッグモード時の詳細なエラー情報
                    if config.protocol_debug:
                        import traceback

                        logger.debug(
                            f"TOOL_DEBUG - Error traceback: {traceback.format_exc()}"
                        )
                    return {"success": False, "error": str(e)}
            else:
                logger.error(f"TOOL_UNKNOWN - Tool: {name}")
                # JSON-RPC 2.0準拠のエラーレスポンスを返す
                return {
                    "success": False,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {name}",
                        "data": {
                            "available_methods": list(all_handlers.keys())
                            + ["health_check"],
                            "server_type": "PostgreSQL MCP Server",
                        },
                    },
                }

        # Register tools via list_tools handler
        # MCP library will automatically filter tools based on concerns
        @server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools including health check."""
            logger = context.logger
            tool_count = len(all_tools) + 1  # +1 for health check
            logger.info(f"TOOL_LIST - Listing {tool_count} available tools")

            # Create health check tool definition
            health_tool = Tool(
                name="health_check",
                description="Check the health status of the PostgreSQL MCP Server",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )

            # MCP library will automatically filter tools based on concerns
            # Return all tools - filtering is handled by MCP
            logger.info(
                f"TOOL_LIST - Returning {tool_count} tools (MCP handles concern filtering)"
            )
            return all_tools + [health_tool]

        # Register resources
        database_resources = get_database_resources()
        resource_handlers = get_resource_handlers()
        table_schema_handler = get_table_schema_resource_handler()

        @server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources."""
            logger = context.logger
            logger.info("RESOURCE_LIST - Listing available resources")
            resources = database_resources.copy()

            # Add dynamic table schema resources
            try:
                db_manager = DatabaseManager(
                    context.config.postgres, context.pool_manager
                )
                db_manager.connect()
                tables_result = db_manager.get_tables()
                db_manager.disconnect()

                if tables_result["success"]:
                    # Convert to List[str] to fix mypy error
                    tables_data = tables_result["tables"]
                    table_list: List[str] = list(tables_data)  # type: ignore[index]
                    table_count = len(table_list)
                    logger.info(
                        f"RESOURCE_LIST - Found {table_count} tables in database"
                    )
                    for table_name in table_list:
                        resource = Resource(
                            uri=f"database://schema/{table_name}",  # type: ignore
                            name=f"Table Schema: {table_name}",
                            description=f"Schema information for table {table_name}",
                            mimeType="text/markdown",
                        )
                        # Add _meta attribute for concerns filtering
                        resource._meta = {}  # type: ignore[attr-defined]
                        resources.append(resource)
                else:
                    logger.warning(
                        f"RESOURCE_LIST - Failed to get tables: {tables_result.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                logger.error(
                    f"RESOURCE_LIST_ERROR - Error listing table resources: {e}"
                )

            # MCP library will automatically filter resources based on concerns
            # Return all resources - filtering is handled by MCP
            total_resources = len(resources)
            logger.info(
                f"RESOURCE_LIST - Returning {total_resources} resources (MCP handles concern filtering)"
            )
            return resources

        @server.list_resource_templates()
        async def handle_list_resource_templates() -> List[types.ResourceTemplate]:
            """List available resource templates"""
            logger = context.logger
            logger.info("RESOURCE_TEMPLATE_LIST - Listing resource templates")
            # Currently no resource templates implemented
            return []

        @server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            logger = context.logger

            # Convert uri to string if it's not already
            uri_str = str(uri)
            logger.info(f"RESOURCE_READ - Reading resource: {uri_str}")

            # Handle static resources
            if uri_str in resource_handlers:
                logger.info(f"RESOURCE_READ - Handling static resource: {uri_str}")
                handler = resource_handlers[uri_str]
                try:
                    content = await handler()
                    content_length = len(content) if content else 0
                    logger.info(
                        f"RESOURCE_READ_SUCCESS - Resource: {uri_str}, Content length: {content_length}"
                    )
                    return content
                except Exception as e:
                    logger.error(
                        f"RESOURCE_READ_ERROR - Resource: {uri_str}, Error: {e}"
                    )
                    return f"Error reading resource {uri_str}: {e}"

            # Handle dynamic table schema resources
            if uri_str.startswith("database://schema/"):
                table_name = uri_str.replace("database://schema/", "")
                logger.info(
                    f"RESOURCE_READ - Handling table schema resource: {table_name}"
                )
                try:
                    content = await table_schema_handler(table_name, "public")
                    content_length = len(content) if content else 0
                    logger.info(
                        f"RESOURCE_READ_SUCCESS - Table schema: {table_name}, Content length: {content_length}"
                    )
                    return content
                except Exception as e:
                    logger.error(
                        f"RESOURCE_READ_ERROR - Table schema: {table_name}, Error: {e}"
                    )
                    return f"Error reading table schema {table_name}: {e}"

            logger.warning(f"RESOURCE_NOT_FOUND - Resource: {uri_str}")
            return f"Resource {uri_str} not found"

        @server.list_prompts()
        async def handle_list_prompts(request: ListPromptsRequest) -> ListPromptsResult:
            """List available prompts."""
            logger = context.logger
            logger.info("PROMPT_LIST - Listing available prompts")
            try:
                prompt_manager = get_prompt_manager()
                prompts = prompt_manager.list_prompts()
                prompt_count = len(prompts)
                logger.info(
                    f"PROMPT_LIST - Found {prompt_count} prompts"
                )

                # MCP library will automatically filter prompts based on concerns
                # Return all prompts - filtering is handled by MCP
                logger.info(
                    f"PROMPT_LIST - Returning {prompt_count} prompts (MCP handles concern filtering)"
                )
                return ListPromptsResult(prompts=prompts)
            except Exception as e:
                logger.error(f"PROMPT_LIST_ERROR - Error listing prompts: {e}")
                return ListPromptsResult(prompts=[])

        @server.get_prompt()
        async def handle_get_prompt(
            name: str, arguments: dict[str, str] | None
        ) -> GetPromptResult:
            """Get prompt content"""
            logger = context.logger

            logger.info(f"PROMPT_GET - Getting prompt: {name}, arguments: {arguments}")
            try:
                prompt_manager = get_prompt_manager()
                # Convert arguments to Dict[str, Any] if needed
                args_dict: Dict[str, Any] = {}
                if arguments:
                    # Convert dict[str, str] to Dict[str, Any]
                    args_dict = {k: v for k, v in arguments.items()}

                prompt = prompt_manager.get_prompt(name, args_dict)

                if prompt:
                    logger.info(f"PROMPT_GET_SUCCESS - Found prompt: {name}")
                    # For now, return empty messages since MCP Prompt doesn't contain message content
                    # In a real implementation, we would need to store the actual message content separately
                    return GetPromptResult(description=prompt.description, messages=[])
                else:
                    logger.warning(f"PROMPT_NOT_FOUND - Prompt not found: {name}")
                    return GetPromptResult(description="", messages=[])
            except Exception as e:
                logger.error(f"PROMPT_GET_ERROR - Error getting prompt {name}: {e}")
                return GetPromptResult(description="", messages=[])

        # Start the server
        logger = context.logger
        config = context.config
        protocol_logger = context.protocol_logger

        logger.info("Starting PostgreSQL MCP Server...")

        try:
            async with stdio_server() as (read_stream, write_stream):
                # プロトコルロギングを有効化
                read_stream, write_stream = await protocol_logging_server(
                    read_stream, write_stream, config, protocol_logger
                )

                # Get initialization options from server
                # Note: If concerns were added to server._declared_concerns earlier,
                # they should already be included in the initialization options
                initialization_options = server.create_initialization_options()

                # Start the server with the options
                await server.run(read_stream, write_stream, initialization_options)

        except Exception as e:
            logger.error(f"Server error: {e}")
            import traceback

            logger.error(f"Server error traceback: {traceback.format_exc()}")
            # 詳細なエラー情報はファイルにのみ出力（sys.stderr/sys.stdoutへの出力なし）
            # 既にlogger.errorでファイルに出力されているため、追加の出力は不要
            raise

        # Note: update_concerns decorator is not available in the current MCP version
        # This functionality would need to be implemented as a custom tool or handler
        # For now, we'll keep the concerns configuration static


def cli_main() -> None:
    """CLI entry point for uv run"""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
