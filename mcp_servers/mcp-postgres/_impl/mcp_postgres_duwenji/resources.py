"""
Resource management for PostgreSQL MCP Server
"""

import logging
from typing import List, Dict, Any, Callable, Coroutine
from mcp import Resource

from .database import DatabaseManager
from .config import load_config

logger = logging.getLogger(__name__)


class DatabaseResourceManager:
    """Manage database-related resources"""

    def __init__(self) -> None:
        self.config = load_config()
        self.db_manager = DatabaseManager(self.config.postgres)

    async def get_tables_resource(self) -> str:
        """Get tables list as resource content"""
        try:
            self.db_manager.connect()
            result = self.db_manager.get_tables()
            self.db_manager.disconnect()

            if result["success"]:
                tables = result["tables"]
                content = f"# Database Tables in {self.config.postgres.database}\n\n"
                content += f"Total tables: {len(tables)}\n\n"

                for table in tables:
                    content += f"- {table}\n"

                return content
            else:
                return f"Error retrieving tables: {result['error']}"

        except Exception as e:
            logger.error(f"Error in get_tables_resource: {e}")
            return f"Error retrieving tables: {str(e)}"

    async def get_table_schema_resource(
        self, table_name: str, schema: str = "public"
    ) -> str:
        """Get table schema as resource content"""
        try:
            self.db_manager.connect()

            # Get table schema information
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

            columns_result = self.db_manager.execute_query(
                query, {"schema": schema, "table_name": table_name}
            )
            columns = columns_result["data"] if columns_result["success"] else []

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
            WHERE tc.table_schema = %s AND tc.table_name = %s
            ORDER BY tc.constraint_type, tc.constraint_name
            """

            constraints_result = self.db_manager.execute_query(
                constraints_query, {"schema": schema, "table_name": table_name}
            )
            constraints = (
                constraints_result["data"] if constraints_result["success"] else []
            )

            self.db_manager.disconnect()

            # Format content
            content = f"# Table Schema: {schema}.{table_name}\n\n"

            # Columns section
            content += "## Columns\n\n"
            content += (
                "| Column Name | Data Type | Nullable | Default | "
                "Max Length | Precision | Scale |\n"
            )
            content += (
                "|-------------|-----------|----------|---------|"
                "------------|-----------|-------|\n"
            )

            for col in columns:
                content += (
                    f"| {col['column_name']} | {col['data_type']} | "
                    f"{col['is_nullable']} | {col['column_default'] or 'NULL'} | "
                    f"{col['character_maximum_length'] or '-'} | "
                    f"{col['numeric_precision'] or '-'} | "
                    f"{col['numeric_scale'] or '-'} |\n"
                )

            content += "\n"

            # Constraints section
            if constraints:
                content += "## Constraints\n\n"
                content += "| Constraint Name | Type | Column |\n"
                content += "|-----------------|------|--------|\n"

                for constraint in constraints:
                    content += (
                        f"| {constraint['constraint_name']} | "
                        f"{constraint['constraint_type']} | "
                        f"{constraint['column_name'] or '-'} |\n"
                    )

            return content

        except Exception as e:
            logger.error(f"Error in get_table_schema_resource: {e}")
            return f"Error retrieving table schema: {str(e)}"

    async def get_database_info_resource(self) -> str:
        """Get database information as resource content"""
        try:
            self.db_manager.connect()

            # Get database version
            version_result = self.db_manager.execute_query("SELECT version();")
            version = (
                version_result["data"][0]["version"]
                if version_result["success"] and version_result["data"]
                else "Unknown"
            )

            # Get database name and current user
            db_info_result = self.db_manager.execute_query(
                "SELECT current_database(), current_user, current_schema();"
            )
            db_info = (
                db_info_result["data"][0]
                if db_info_result["success"] and db_info_result["data"]
                else {}
            )

            # Get database size
            size_result = self.db_manager.execute_query(
                (
                    "SELECT pg_size_pretty(pg_database_size(current_database())) "
                    "as database_size;"
                )
            )
            database_size = (
                size_result["data"][0]["database_size"]
                if size_result["success"] and size_result["data"]
                else "Unknown"
            )

            # Get number of tables
            tables_count_result = self.db_manager.execute_query(
                (
                    "SELECT COUNT(*) as table_count FROM information_schema.tables "
                    "WHERE table_schema = 'public';"
                )
            )
            table_count = (
                tables_count_result["data"][0]["table_count"]
                if tables_count_result["success"] and tables_count_result["data"]
                else 0
            )

            self.db_manager.disconnect()

            # Format content
            content = "# Database Information\n\n"
            content += (
                f"**Database Name**: {db_info.get('current_database', 'Unknown')}\n"
            )
            content += f"**PostgreSQL Version**: {version}\n"
            content += f"**Current User**: {db_info.get('current_user', 'Unknown')}\n"
            content += (
                f"**Current Schema**: {db_info.get('current_schema', 'Unknown')}\n"
            )
            content += f"**Database Size**: {database_size}\n"
            content += f"**Table Count**: {table_count}\n"

            return content

        except Exception as e:
            logger.error(f"Error in get_database_info_resource: {e}")
            return f"Error retrieving database information: {str(e)}"

    async def get_connection_info_resource(self) -> str:
        """Get database connection information as JSON resource content"""
        try:
            import json

            # Get connection configuration
            config = self.config.postgres

            # Create connection info dictionary
            connection_info = {
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "username": config.username,
                "password": config.password,
                "ssl_mode": config.ssl_mode,
                "pool_size": config.pool_size,
                "max_overflow": config.max_overflow,
                "connect_timeout": config.connect_timeout,
            }

            # Return as formatted JSON
            return json.dumps(connection_info, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in get_connection_info_resource: {e}")
            return f"Error retrieving connection information: {str(e)}"


# Resource definitions
database_tables_resource = Resource(
    uri="database://tables",  # type: ignore
    name="Database Tables",
    description="List of all tables in the database",
    mimeType="text/markdown",
)
database_tables_resource._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}

database_info_resource = Resource(
    uri="database://info",  # type: ignore
    name="Database Information",
    description="Database metadata and version information",
    mimeType="text/markdown",
)
database_info_resource._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}

database_connection_resource = Resource(
    uri="database://connection",  # type: ignore
    name="Database Connection Info",
    description="Database connection parameters (host, port, database, username, password, etc.)",
    mimeType="application/json",
)
database_connection_resource._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "maintenance": "-"}
}


def get_database_resources() -> List[Resource]:
    """Get all database resources"""
    return [
        database_tables_resource,
        database_info_resource,
        database_connection_resource,
    ]


def get_resource_handlers() -> Dict[str, Callable[[], Coroutine[Any, Any, str]]]:
    """Get resource handlers"""
    resource_manager = DatabaseResourceManager()

    return {
        "database://tables": resource_manager.get_tables_resource,
        "database://info": resource_manager.get_database_info_resource,
        "database://connection": resource_manager.get_connection_info_resource,
    }


def get_table_schema_resource_handler() -> (
    Callable[[str, str], Coroutine[Any, Any, str]]
):
    """Get table schema resource handler factory"""
    resource_manager = DatabaseResourceManager()
    return resource_manager.get_table_schema_resource
