"""
CRUD tools for PostgreSQL MCP Server
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Coroutine
from mcp import Tool

from ..database import DatabaseError
from ..shared import get_database_manager

logger = logging.getLogger(__name__)


# Tool definitions for CRUD operations
create_entity = Tool(
    name="create_entity",
    description="Create a new entity (row) in a PostgreSQL table",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to insert into",
            },
            "data": {
                "type": "object",
                "description": ("Dictionary of column names and values to insert"),
                "additionalProperties": True,
            },
        },
        "required": ["table_name", "data"],
    },
)
create_entity._meta = {"concerns": {"development": "development", "using": "regular_use"}}  # type: ignore[attr-defined]


read_entity = Tool(
    name="read_entity",
    description="Read entities from a PostgreSQL table with optional conditions and advanced features",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to query",
            },
            "conditions": {
                "type": "object",
                "description": "Optional WHERE conditions as key-value pairs",
                "additionalProperties": True,
            },
            "limit": {
                "type": "integer",
                "description": ("Maximum number of rows to return (default: 100)"),
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
            },
            "offset": {
                "type": "integer",
                "description": "Number of rows to skip (for pagination, default: 0)",
                "default": 0,
                "minimum": 0,
            },
            "order_by": {
                "type": "string",
                "description": "Column name to order by",
            },
            "order_direction": {
                "type": "string",
                "description": "Order direction (ASC or DESC, default: ASC)",
                "enum": ["ASC", "DESC"],
                "default": "ASC",
            },
            "aggregate": {
                "type": "string",
                "description": "Aggregate function (e.g., COUNT(*), SUM(column), AVG(column))",
            },
            "group_by": {
                "type": "string",
                "description": "Column name to group by",
            },
        },
        "required": ["table_name"],
    },
)
read_entity._meta = {"concerns": {"development": "-", "using": "-"}}  # type: ignore[attr-defined]


update_entity = Tool(
    name="update_entity",
    description="Update entities in a PostgreSQL table",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to update",
            },
            "conditions": {
                "type": "object",
                "description": ("WHERE conditions to identify which rows to update"),
                "additionalProperties": True,
            },
            "updates": {
                "type": "object",
                "description": "Dictionary of columns and values to update",
                "additionalProperties": True,
            },
        },
        "required": ["table_name", "conditions", "updates"],
    },
)
update_entity._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}


delete_entity = Tool(
    name="delete_entity",
    description="Delete entities from a PostgreSQL table",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to delete from",
            },
            "conditions": {
                "type": "object",
                "description": ("WHERE conditions to identify which rows to delete"),
                "additionalProperties": True,
            },
        },
        "required": ["table_name", "conditions"],
    },
)
delete_entity._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}


# Batch operation tool definitions
batch_create_entities = Tool(
    name="batch_create_entities",
    description="Create multiple entities in a single operation",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to insert into",
            },
            "data_list": {
                "type": "array",
                "description": "List of dictionaries containing column names and values",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        },
        "required": ["table_name", "data_list"],
    },
)
batch_create_entities._meta = {"concerns": {"development": "-", "using": "-"}}  # type: ignore[attr-defined]

batch_update_entities = Tool(
    name="batch_update_entities",
    description="Update multiple entities with different conditions and updates",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to update",
            },
            "conditions_list": {
                "type": "array",
                "description": "List of WHERE conditions for each entity",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
            "updates_list": {
                "type": "array",
                "description": "List of updates for each entity",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        },
        "required": ["table_name", "conditions_list", "updates_list"],
    },
)
batch_update_entities._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}

batch_delete_entities = Tool(
    name="batch_delete_entities",
    description="Delete multiple entities with different conditions",
    inputSchema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to delete from",
            },
            "conditions_list": {
                "type": "array",
                "description": "List of WHERE conditions for each entity",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        },
        "required": ["table_name", "conditions_list"],
    },
)
batch_delete_entities._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}


# Tool handlers
async def handle_create_entity(table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create entity tool execution"""
    logger.info(
        f"CRUD_TOOL - create_entity - Table: {table_name}, Data keys: {list(data.keys())}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.create_entity(table_name, data)

        logger.info(
            f"CRUD_TOOL_SUCCESS - create_entity - Table: {table_name}, Result: {result.get('success', False)}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - create_entity - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - create_entity - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_read_entity(
    table_name: str,
    conditions: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: Optional[str] = None,
    order_direction: str = "ASC",
    aggregate: Optional[str] = None,
    group_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle read entity tool execution with advanced features"""
    logger.info(
        f"CRUD_TOOL - read_entity - Table: {table_name}, Conditions: {conditions}, Limit: {limit}, Offset: {offset}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.read_entity(
            table_name=table_name,
            conditions=conditions,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_direction=order_direction,
            aggregate=aggregate,
            group_by=group_by,
        )

        row_count = len(result.get("results", [])) if result.get("success") else 0
        logger.info(
            f"CRUD_TOOL_SUCCESS - read_entity - Table: {table_name}, Rows returned: {row_count}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - read_entity - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - read_entity - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_update_entity(
    table_name: str, conditions: Dict[str, Any], updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle update entity tool execution"""
    logger.info(
        f"CRUD_TOOL - update_entity - Table: {table_name}, "
        f"Conditions: {conditions}, Updates keys: {list(updates.keys())}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.update_entity(table_name, conditions, updates)

        logger.info(
            f"CRUD_TOOL_SUCCESS - update_entity - Table: {table_name}, Result: {result.get('success', False)}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - update_entity - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - update_entity - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_delete_entity(
    table_name: str, conditions: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle delete entity tool execution"""
    logger.info(
        f"CRUD_TOOL - delete_entity - Table: {table_name}, Conditions: {conditions}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.delete_entity(table_name, conditions)

        logger.info(
            f"CRUD_TOOL_SUCCESS - delete_entity - Table: {table_name}, Result: {result.get('success', False)}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - delete_entity - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - delete_entity - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Batch operation handlers
async def handle_batch_create_entities(
    table_name: str, data_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Handle batch create entities tool execution"""
    logger.info(
        f"CRUD_TOOL - batch_create_entities - Table: {table_name}, Records: {len(data_list)}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.batch_create_entities(table_name, data_list)

        logger.info(
            f"CRUD_TOOL_SUCCESS - batch_create_entities - Table: {table_name}, Result: {result.get('success', False)}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - batch_create_entities - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - batch_create_entities - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_batch_update_entities(
    table_name: str,
    conditions_list: List[Dict[str, Any]],
    updates_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Handle batch update entities tool execution"""
    logger.info(
        f"CRUD_TOOL - batch_update_entities - Table: {table_name}, Operations: {len(conditions_list)}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.batch_update_entities(
            table_name, conditions_list, updates_list
        )

        logger.info(
            f"CRUD_TOOL_SUCCESS - batch_update_entities - Table: {table_name}, Result: {result.get('success', False)}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - batch_update_entities - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - batch_update_entities - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_batch_delete_entities(
    table_name: str, conditions_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Handle batch delete entities tool execution"""
    logger.info(
        f"CRUD_TOOL - batch_delete_entities - Table: {table_name}, Operations: {len(conditions_list)}"
    )
    try:
        db_manager = get_database_manager()
        result = db_manager.batch_delete_entities(table_name, conditions_list)

        logger.info(
            f"CRUD_TOOL_SUCCESS - batch_delete_entities - Table: {table_name}, Result: {result.get('success', False)}"
        )
        return result

    except DatabaseError as e:
        logger.error(
            f"CRUD_TOOL_ERROR - batch_delete_entities - Table: {table_name}, DatabaseError: {e}"
        )
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(
            f"CRUD_TOOL_ERROR - batch_delete_entities - Table: {table_name}, Unexpected error: {e}"
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# SQL query execution tool
execute_sql_query = Tool(
    name="execute_sql_query",
    description="Execute a SQL query and return results",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query to execute",
            },
            "params": {
                "type": "object",
                "description": "Query parameters for parameterized queries",
                "additionalProperties": True,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of rows to return (default: 1000)",
                "default": 1000,
                "minimum": 1,
                "maximum": 10000,
            },
        },
        "required": ["query"],
    },
)
execute_sql_query._meta = {"concerns": {"development": "-", "using": "-", "tuning": "-"}}  # type: ignore[attr-defined]


# Tool handlers
async def handle_execute_sql_query(
    query: str, params: Optional[Dict[str, Any]] = None, limit: int = 1000
) -> Dict[str, Any]:
    """Handle execute SQL query tool execution"""
    param_keys = list(params.keys()) if params else []
    logger.info(
        f"CRUD_TOOL - execute_sql_query - Query: {query[:100]}..., "
        f"Params keys: {param_keys}, Limit: {limit}"
    )

    try:
        db_manager = get_database_manager()
        result = db_manager.execute_query(query, params, limit)

        row_count = result.get("row_count", 0) if result.get("success") else 0
        logger.info(
            f"CRUD_TOOL_SUCCESS - execute_sql_query - Rows returned: {row_count}"
        )
        return result

    except DatabaseError as e:
        logger.error(f"CRUD_TOOL_ERROR - execute_sql_query - DatabaseError: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"CRUD_TOOL_ERROR - execute_sql_query - Unexpected error: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Concern update tool
update_concerns = Tool(
    name="update_concerns",
    description="Update concern configuration for filtering tools, resources, and prompts",
    inputSchema={
        "type": "object",
        "properties": {
            "concerns": {
                "type": "object",
                "description": "Dictionary of concern keys and values to update",
                "additionalProperties": {
                    "type": "string",
                    "enum": ["planning", "development", "testing", "maintenance", "none", "basic", "advanced", "performance", "exploration", "regular_use", "optimization", "*"],
                },
            },
        },
        "required": ["concerns"],
    },
)
update_concerns._meta = {"concerns": {"development": "development", "using": "regular_use"}}  # type: ignore[attr-defined]


# Concern update handler
async def handle_update_concerns(concerns: Dict[str, str]) -> Dict[str, Any]:
    """Handle update concerns tool execution"""
    logger.info(f"CONCERN_TOOL - update_concerns - Concerns: {concerns}")
    
    try:
        # Import here to avoid circular imports
        from ..context import get_global_context
        
        context = get_global_context()
        if context is None:
            logger.error("CONCERN_TOOL_ERROR - update_concerns - Context not available")
            return {"success": False, "error": "Server context not available"}
        
        # Store old concerns for logging
        old_concerns = context.concerns.copy()
        
        # Update concerns in context
        # Only update provided concerns, keep existing ones
        for key, value in concerns.items():
            if key in context.concerns:
                context.concerns[key] = value
                logger.info(f"CONCERN_UPDATE - Updated {key}: {old_concerns.get(key)} -> {value}")
            else:
                logger.warning(f"CONCERN_UPDATE_WARNING - Unknown concern key: {key}")
        
        logger.info(f"CONCERN_TOOL_SUCCESS - update_concerns - Updated: {old_concerns} -> {context.concerns}")
        return {
            "success": True,
            "message": "Concerns updated successfully",
            "old_concerns": old_concerns,
            "new_concerns": context.concerns,
        }
        
    except Exception as e:
        logger.error(f"CONCERN_TOOL_ERROR - update_concerns - Unexpected error: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Tool registry
def get_crud_tools() -> List[Tool]:
    """Get all CRUD tools including batch operations and SQL query execution"""
    return [
        create_entity,
        read_entity,
        update_entity,
        delete_entity,
        batch_create_entities,
        batch_update_entities,
        batch_delete_entities,
        execute_sql_query,
        update_concerns,
    ]


def get_crud_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for CRUD operations including batch operations and SQL query execution"""
    return {
        "create_entity": handle_create_entity,
        "read_entity": handle_read_entity,
        "update_entity": handle_update_entity,
        "delete_entity": handle_delete_entity,
        "batch_create_entities": handle_batch_create_entities,
        "batch_update_entities": handle_batch_update_entities,
        "batch_delete_entities": handle_batch_delete_entities,
        "execute_sql_query": handle_execute_sql_query,
        "update_concerns": handle_update_concerns,
    }
