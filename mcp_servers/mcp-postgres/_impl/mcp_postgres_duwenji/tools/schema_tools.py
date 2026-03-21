"""
Schema tools for PostgreSQL MCP Server
"""

import logging
from typing import Any, Dict, List, Callable, Coroutine
from mcp import Tool

from ..database import DatabaseError
from ..shared import get_database_manager

logger = logging.getLogger(__name__)


# Tool definitions for schema operations
get_tables = Tool(
    name="get_tables",
    description="Get list of all tables in the PostgreSQL database",
    inputSchema={
        "type": "object",
        "properties": {
            "schema": {
                "type": "string",
                "description": ("Schema name to filter tables (default: 'public')"),
                "default": "public",
            }
        },
        "required": [],
    },
)
get_tables._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}


get_table_schema = Tool(
    name="get_table_schema",
    description="Get detailed schema information for a specific table",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to get schema for",
            },
            "schema": {
                "type": "string",
                "description": "Schema name (default: 'public')",
                "default": "public",
            },
        },
        "required": ["table_name"],
    },
)
get_table_schema._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}


get_database_info = Tool(
    name="get_database_info",
    description="Get database metadata and version information",
    inputSchema={"type": "object", "properties": {}, "required": []},
)
get_database_info._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}


# Tool handlers
async def handle_get_tables(schema: str = "public") -> Dict[str, Any]:
    """Handle get_tables tool execution"""
    try:
        db_manager = get_database_manager()
        # Use existing get_tables method
        result = db_manager.get_tables()
        return result

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_tables: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_get_table_schema(
    table_name: str, schema: str = "public"
) -> Dict[str, Any]:
    """Handle get_table_schema tool execution"""
    try:
        db_manager = get_database_manager()

        # Query to get table schema information
        query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %(schema)s AND table_name = %(table_name)s
        ORDER BY ordinal_position
        """

        logger.info(f"Executing table schema query for table: {table_name}")
        try:
            results = db_manager._execute_query(
                query, {"schema": schema, "table_name": table_name}
            )
            logger.info(
                f"Query results type: {type(results)}, "
                f"length: {len(results) if isinstance(results, list) else 'N/A'}, "
                f"results: {results}"
            )
        except Exception as query_error:
            logger.error(f"Query execution failed: {query_error}")
            raise

        # Get table constraints
        constraints_query = """
        SELECT
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
            AND tc.table_name = kcu.table_name
        WHERE tc.table_schema = %(schema)s AND tc.table_name = %(table_name)s
        ORDER BY tc.constraint_type, tc.constraint_name
        """

        logger.info(f"Executing constraints query for table: {table_name}")
        try:
            constraints = db_manager._execute_query(
                constraints_query, {"schema": schema, "table_name": table_name}
            )
            logger.info(
                f"Constraints results type: {type(constraints)}, "
                f"length: {len(constraints) if isinstance(constraints, list) else 'N/A'}, "
                f"results: {constraints}"
            )
        except Exception as constraints_error:
            logger.error(f"Constraints query execution failed: {constraints_error}")
            constraints = []

        # Ensure results are properly formatted as lists
        columns_list = []
        if isinstance(results, list):
            columns_list = results
        elif isinstance(results, dict):
            columns_list = [results]
        else:
            try:
                columns_list = list(results) if hasattr(results, "__iter__") else []
            except Exception as e:
                logger.warning(f"Failed to convert results to list: {e}")
                columns_list = []

        constraints_list = []
        if isinstance(constraints, list):
            constraints_list = constraints
        elif isinstance(constraints, dict):
            constraints_list = [constraints]
        else:
            try:
                constraints_list = (
                    list(constraints) if hasattr(constraints, "__iter__") else []
                )
            except Exception as e:
                logger.warning(f"Failed to convert constraints to list: {e}")
                constraints_list = []

        logger.info(
            f"Final columns_list type: {type(columns_list)}, length: {len(columns_list)}"
        )
        logger.info(
            f"Final constraints_list type: {type(constraints_list)}, length: {len(constraints_list)}"
        )

        return {
            "success": True,
            "table_name": table_name,
            "schema": schema,
            "columns": columns_list,
            "constraints": constraints_list,
        }

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_table_schema: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_get_database_info() -> Dict[str, Any]:
    """Handle get_database_info tool execution"""
    try:
        db_manager = get_database_manager()

        # Get database version
        version_result = db_manager._execute_query("SELECT version();")
        version = version_result[0]["version"] if version_result else "Unknown"

        # Get database name and current user
        db_info_result = db_manager._execute_query(
            "SELECT current_database(), current_user, current_schema();"
        )
        db_info = db_info_result[0] if db_info_result else {}

        # Get database size
        size_result = db_manager._execute_query(
            (
                "SELECT pg_size_pretty(pg_database_size(current_database())) "
                "as database_size;"
            )
        )
        database_size = size_result[0]["database_size"] if size_result else "Unknown"

        # Get number of tables
        tables_count_result = db_manager._execute_query(
            (
                "SELECT COUNT(*) as table_count FROM information_schema.tables "
                "WHERE table_schema = 'public';"
            )
        )
        table_count = (
            tables_count_result[0]["table_count"] if tables_count_result else 0
        )

        return {
            "success": True,
            "database_info": {
                "version": version,
                "database_name": db_info.get("current_database", "Unknown"),
                "current_user": db_info.get("current_user", "Unknown"),
                "current_schema": db_info.get("current_schema", "Unknown"),
                "database_size": database_size,
                "table_count": table_count,
            },
        }

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_database_info: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Tool registry
def get_schema_tools() -> List[Tool]:
    """Get all schema tools"""
    return [
        get_tables,
        get_table_schema,
        get_database_info,
    ]


def get_schema_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for schema operations"""
    return {
        "get_tables": handle_get_tables,
        "get_table_schema": handle_get_table_schema,
        "get_database_info": handle_get_database_info,
    }
