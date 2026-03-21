"""
Sampling tools for PostgreSQL MCP Server

This module provides tools that leverage MCP Sampling functionality
for advanced data analysis and quality improvement.
"""

import logging
from typing import Any, Dict, List, Callable, Coroutine
from mcp import Tool

from ..database import DatabaseManager, DatabaseError
from ..shared import get_database_manager

logger = logging.getLogger(__name__)


# Tool definitions for sampling operations
get_multiple_table_schemas = Tool(
    name="get_multiple_table_schemas",
    description="Get schema information for multiple tables at once",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to get schemas for",
            },
            "schema": {
                "type": "string",
                "description": "Schema name (default: 'public')",
                "default": "public",
            },
        },
        "required": ["table_names"],
    },
)
get_multiple_table_schemas._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "maintenance": "-"}
}


analyze_table_relationships = Tool(
    name="analyze_table_relationships",
    description="Analyze relationships and dependencies between multiple tables",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to analyze relationships for",
            },
        },
        "required": ["table_names"],
    },
)
analyze_table_relationships._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "maintenance": "-"}
}


generate_schema_overview = Tool(
    name="generate_schema_overview",
    description="Generate comprehensive overview of database schema",
    inputSchema={
        "type": "object",
        "properties": {
            "include_tables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific tables to include (empty for all)",
                "default": [],
            },
        },
        "required": [],
    },
)
generate_schema_overview._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


analyze_normalization_state = Tool(
    name="analyze_normalization_state",
    description="Analyze current normalization state of tables using LLM",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to analyze",
            },
            "analysis_depth": {
                "type": "string",
                "enum": ["basic", "detailed", "comprehensive"],
                "description": "Depth of normalization analysis",
                "default": "detailed",
            },
        },
        "required": ["table_names"],
    },
)
analyze_normalization_state._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


suggest_normalization_improvements = Tool(
    name="suggest_normalization_improvements",
    description="Suggest normalization improvements using LLM analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to analyze",
            },
            "improvement_focus": {
                "type": "string",
                "enum": ["all", "performance", "maintainability", "data_quality"],
                "description": "Focus area for improvements",
                "default": "all",
            },
        },
        "required": ["table_names"],
    },
)
suggest_normalization_improvements._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "maintenance": "-"}
}


# Tool handlers
async def handle_get_multiple_table_schemas(
    table_names: List[str], schema: str = "public"
) -> Dict[str, Any]:
    """Handle get_multiple_table_schemas tool execution"""
    try:
        db_manager = get_database_manager()

        schemas = {}
        for table_name in table_names:
            try:
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
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """
                results = db_manager.execute_query(
                    query, {"schema": schema, "table_name": table_name}
                )
                schemas[table_name] = (
                    results["data"]
                    if results["success"]
                    else [{"error": "Failed to execute query"}]
                )
            except Exception as e:
                logger.warning(f"Failed to get schema for table {table_name}: {e}")
                schemas[table_name] = [{"error": str(e)}]

        # Get table relationships
        relationships = await _analyze_relationships(table_names, db_manager)

        return {
            "success": True,
            "schemas": schemas,
            "relationships": relationships,
            "total_tables": len(table_names),
            "successful_tables": len(
                [
                    s
                    for s in schemas.values()
                    if isinstance(s, list)
                    and not any(
                        isinstance(item, dict) and "error" in item for item in s
                    )
                ]
            ),
        }

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_multiple_table_schemas: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_analyze_table_relationships(table_names: List[str]) -> Dict[str, Any]:
    """Handle analyze_table_relationships tool execution"""
    try:
        db_manager = get_database_manager()
        relationships = await _analyze_relationships(table_names, db_manager)

        return {
            "success": True,
            "relationships": relationships,
            "table_count": len(table_names),
        }

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in analyze_table_relationships: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_generate_schema_overview(
    include_tables: List[str] = [],
) -> Dict[str, Any]:
    """Handle generate_schema_overview tool execution"""

    try:
        db_manager = get_database_manager()

        # Get all tables if not specified
        if not include_tables:
            tables_result = db_manager.get_tables()
            if tables_result["success"]:
                include_tables = tables_result["tables"]
            else:
                return {"success": False, "error": "Failed to get table list"}

        # Get schemas for all tables
        schemas_result = await handle_get_multiple_table_schemas(include_tables)

        # Get database statistics
        stats_query = """
        SELECT
            COUNT(*) as total_tables,
            SUM(pg_relation_size(schemaname||'.'||tablename)) as total_size_bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        """
        stats_result = db_manager.execute_query(stats_query)

        return {
            "success": True,
            "overview": {
                "table_count": len(include_tables),
                "total_size_bytes": (
                    stats_result["data"][0]["total_size_bytes"]
                    if stats_result["success"] and stats_result["data"]
                    else 0
                ),
                "schemas": schemas_result.get("schemas", {}),
                "relationships": schemas_result.get("relationships", {}),
            },
        }

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in generate_schema_overview: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_analyze_normalization_state(
    table_names: List[str], analysis_depth: str = "detailed"
) -> Dict[str, Any]:
    """Handle analyze_normalization_state tool execution"""
    try:
        # First get the schema information
        schemas_result = await handle_get_multiple_table_schemas(table_names)

        if not schemas_result["success"]:
            return schemas_result

        # Prepare data for LLM analysis
        analysis_data = {
            "table_schemas": schemas_result["schemas"],
            "relationships": schemas_result["relationships"],
            "analysis_depth": analysis_depth,
        }

        # This would normally use MCP Sampling to request LLM analysis
        # For now, we'll return the prepared data structure
        return {
            "success": True,
            "analysis_data": analysis_data,
            "message": "Normalization analysis data prepared. Use MCP Sampling for LLM analysis.",
            "next_step": "Use suggest_normalization_improvements with LLM integration",
        }

    except Exception as e:
        logger.error(f"Unexpected error in analyze_normalization_state: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_suggest_normalization_improvements(
    table_names: List[str], improvement_focus: str = "all"
) -> Dict[str, Any]:
    """Handle suggest_normalization_improvements tool execution"""
    try:
        # Get current state analysis
        analysis_result = await handle_analyze_normalization_state(table_names)

        if not analysis_result["success"]:
            return analysis_result

        # Prepare prompt for LLM analysis
        prompt_data = {
            "current_state": analysis_result["analysis_data"],
            "improvement_focus": improvement_focus,
            "tables": table_names,
        }

        # This would use MCP Sampling to send the analysis to LLM
        # For now, return the prepared prompt structure
        return {
            "success": True,
            "prompt_data": prompt_data,
            "message": "Improvement analysis data prepared. Ready for MCP Sampling LLM integration.",
            "next_step": "Integrate with MCP Sampling for LLM-powered suggestions",
        }

    except Exception as e:
        logger.error(f"Unexpected error in suggest_normalization_improvements: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Helper functions
async def _analyze_relationships(
    table_names: List[str], db_manager: DatabaseManager
) -> Dict[str, Any]:
    """Analyze relationships between tables"""
    relationships: Dict[str, Any] = {
        "foreign_keys": [],
        "potential_relationships": [],
        "data_dependencies": [],
    }

    try:
        # Analyze foreign key relationships
        fk_query = """
        SELECT
            tc.table_schema,
            tc.table_name,
            kcu.column_name,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = ANY(%(table_names)s)
        """

        fk_results = db_manager.execute_query(fk_query, {"table_names": table_names})
        relationships["foreign_keys"] = (
            fk_results["data"] if fk_results["success"] else []
        )

        # Analyze potential relationships based on column names
        for table_name in table_names:
            # Get column names for potential relationship analysis
            column_query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %(table_name)s
            """
            columns_result = db_manager.execute_query(
                column_query, {"table_name": table_name}
            )
            columns = columns_result["data"] if columns_result["success"] else []

            # Simple heuristic: look for common naming patterns
            for column in columns:
                col_name = column["column_name"].lower()
                if col_name.endswith("_id") or col_name.endswith("_code"):
                    relationships["potential_relationships"].append(
                        {
                            "table": table_name,
                            "column": column["column_name"],
                            "type": column["data_type"],
                            "reason": "Common foreign key naming pattern",
                        }
                    )

    except Exception as e:
        logger.warning(f"Error analyzing relationships: {e}")
        relationships["analysis_error"] = str(e)

    return relationships


# Tool registry
def get_sampling_tools() -> List[Tool]:
    """Get all sampling tools"""
    return [
        get_multiple_table_schemas,
        analyze_table_relationships,
        generate_schema_overview,
        analyze_normalization_state,
        suggest_normalization_improvements,
    ]


def get_sampling_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for sampling operations"""
    return {
        "get_multiple_table_schemas": handle_get_multiple_table_schemas,
        "analyze_table_relationships": handle_analyze_table_relationships,
        "generate_schema_overview": handle_generate_schema_overview,
        "analyze_normalization_state": handle_analyze_normalization_state,
        "suggest_normalization_improvements": handle_suggest_normalization_improvements,
    }
