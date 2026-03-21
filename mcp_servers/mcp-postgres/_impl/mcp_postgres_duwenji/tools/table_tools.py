"""
Table management tools for PostgreSQL MCP Server
"""

import logging
from typing import Any, Dict, List, Callable, Coroutine
from mcp import Tool

from ..database import DatabaseError
from ..shared import get_database_manager

logger = logging.getLogger(__name__)


# Table management tools
create_table = Tool(
    name="create_table",
    description="Create a new table in PostgreSQL database",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to create",
            },
            "columns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Column name"},
                        "type": {
                            "type": "string",
                            "description": (
                                "Data type (e.g., VARCHAR(255), INTEGER, TEXT)"
                            ),
                        },
                        "nullable": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether column can be NULL",
                        },
                        "primary_key": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether column is primary key",
                        },
                        "unique": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether column has unique constraint",
                        },
                        "default": {
                            "type": "string",
                            "description": "Default value for the column",
                        },
                    },
                    "required": ["name", "type"],
                },
                "description": "Array of column definitions",
            },
            "if_not_exists": {
                "type": "boolean",
                "default": True,
                "description": "Create table only if it doesn't exist",
            },
        },
        "required": ["table_name", "columns"],
    },
)
create_table._meta = {"concerns": {"development": "-"}}  # type: ignore[attr-defined]


alter_table = Tool(
    name="alter_table",
    description="Modify table structure in PostgreSQL database",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to modify",
            },
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "add_column",
                                "drop_column",
                                "alter_column",
                                "rename_column",
                            ],
                            "description": "Type of operation to perform",
                        },
                        "column_name": {
                            "type": "string",
                            "description": "Name of the column to operate on",
                        },
                        "new_column_name": {
                            "type": "string",
                            "description": (
                                "New name for the column (for rename operations)"
                            ),
                        },
                        "data_type": {
                            "type": "string",
                            "description": (
                                "Data type for the column (for add/alter operations)"
                            ),
                        },
                        "nullable": {
                            "type": "boolean",
                            "description": (
                                "Whether column can be NULL (for add/alter operations)"
                            ),
                        },
                        "default": {
                            "type": "string",
                            "description": (
                                "Default value for the column (for add/alter operations)"
                            ),
                        },
                    },
                    "required": ["type", "column_name"],
                },
                "description": "Array of operations to perform",
            },
        },
        "required": ["table_name", "operations"],
    },
)
alter_table._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


drop_table = Tool(
    name="drop_table",
    description="Delete a table from PostgreSQL database",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to delete",
            },
            "cascade": {
                "type": "boolean",
                "default": False,
                "description": "Also delete objects that depend on this table",
            },
            "if_exists": {
                "type": "boolean",
                "default": True,
                "description": "Don't throw error if table doesn't exist",
            },
        },
        "required": ["table_name"],
    },
)
drop_table._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


# Table management tool handlers
async def handle_create_table(
    table_name: str, columns: List[Dict[str, Any]], if_not_exists: bool = True
) -> Dict[str, Any]:
    """Handle create table tool execution"""
    try:
        db_manager = get_database_manager()
        result = db_manager.create_table(table_name, columns, if_not_exists)
        return result

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in create_table: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_alter_table(
    table_name: str, operations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Handle alter table tool execution"""
    try:
        db_manager = get_database_manager()
        result = db_manager.alter_table(table_name, operations)
        return result

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in alter_table: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_drop_table(
    table_name: str, cascade: bool = False, if_exists: bool = True
) -> Dict[str, Any]:
    """Handle drop table tool execution"""
    try:
        db_manager = get_database_manager()
        result = db_manager.drop_table(table_name, cascade, if_exists)
        return result

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in drop_table: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Tool registry
def get_table_tools() -> List[Tool]:
    """Get all table management tools"""
    return [
        create_table,
        alter_table,
        drop_table,
    ]


def get_table_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for table management operations"""
    return {
        "create_table": handle_create_table,
        "alter_table": handle_alter_table,
        "drop_table": handle_drop_table,
    }
