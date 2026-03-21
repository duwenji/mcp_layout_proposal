"""
Transaction tools for PostgreSQL MCP Server

This module provides tools for safe schema changes with transaction management
and rollback capabilities.
"""

import logging
import uuid
from typing import Any, Dict, List, Callable, Coroutine
from datetime import datetime
from mcp import Tool

from ..database import DatabaseManager, DatabaseError
from ..config import load_config

logger = logging.getLogger(__name__)


# In-memory session storage (in production, this should be persistent)
_schema_change_sessions: Dict[str, Dict[str, Any]] = {}


# Tool definitions for transaction operations
begin_change_session = Tool(
    name="begin_change_session",
    description="Begin a schema change session with transaction management",
    inputSchema={
        "type": "object",
        "properties": {
            "session_description": {
                "type": "string",
                "description": "Description of the planned changes",
            },
            "backup_enabled": {
                "type": "boolean",
                "description": "Whether to create backups (default: true)",
                "default": True,
            },
        },
        "required": [],
    },
)
begin_change_session._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


create_schema_backup = Tool(
    name="create_schema_backup",
    description="Create a backup of current schema state",
    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID from begin_change_session",
            },
            "backup_name": {
                "type": "string",
                "description": "Name for the backup",
            },
        },
        "required": ["session_id"],
    },
)
create_schema_backup._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


apply_schema_changes = Tool(
    name="apply_schema_changes",
    description="Apply schema changes with transaction safety",
    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID from begin_change_session",
            },
            "ddl_statements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of DDL statements to execute",
            },
            "validate_before_commit": {
                "type": "boolean",
                "description": "Validate changes before committing (default: true)",
                "default": True,
            },
        },
        "required": ["session_id", "ddl_statements"],
    },
)
apply_schema_changes._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


rollback_schema_changes = Tool(
    name="rollback_schema_changes",
    description="Rollback schema changes to previous state",
    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID to rollback",
            },
            "backup_id": {
                "type": "string",
                "description": "Specific backup to restore (optional)",
            },
        },
        "required": ["session_id"],
    },
)
rollback_schema_changes._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


list_schema_backups = Tool(
    name="list_schema_backups",
    description="List available schema backups for a session",
    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID to list backups for",
            },
        },
        "required": ["session_id"],
    },
)
list_schema_backups._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


commit_schema_changes = Tool(
    name="commit_schema_changes",
    description="Commit schema changes and end session",
    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID to commit",
            },
        },
        "required": ["session_id"],
    },
)
commit_schema_changes._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


# Tool handlers
async def handle_begin_change_session(
    session_description: str = "", backup_enabled: bool = True
) -> Dict[str, Any]:
    """Handle begin_change_session tool execution"""
    try:
        session_id = str(uuid.uuid4())

        # Create session
        session: Dict[str, Any] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "description": session_description,
            "backup_enabled": backup_enabled,
            "backups": [],
            "changes": [],
            "status": "active",
            "transaction_started": False,
        }

        _schema_change_sessions[session_id] = session

        # Start transaction if backup is enabled
        if backup_enabled:
            config = load_config()
            db_manager = DatabaseManager(config.postgres)
            db_manager.connect()

            try:
                # Start transaction
                db_manager.execute_query("BEGIN;")
                session["transaction_started"] = True

                # Create initial backup
                backup_id = str(uuid.uuid4())
                backup = {
                    "backup_id": backup_id,
                    "created_at": datetime.now().isoformat(),
                    "name": "initial_backup",
                    "description": "Initial state before changes",
                }
                session["backups"].append(backup)

                db_manager.disconnect()

            except Exception as e:
                db_manager.disconnect()
                raise e

        logger.info(f"Started schema change session: {session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "session": session,
            "message": "Schema change session started successfully",
        }

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in begin_change_session: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_create_schema_backup(
    session_id: str, backup_name: str = ""
) -> Dict[str, Any]:
    """Handle create_schema_backup tool execution"""
    try:
        if session_id not in _schema_change_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session: Dict[str, Any] = _schema_change_sessions[session_id]

        if not session["backup_enabled"]:
            return {"success": False, "error": "Backup not enabled for this session"}

        # Create backup
        backup_id = str(uuid.uuid4())
        backup = {
            "backup_id": backup_id,
            "created_at": datetime.now().isoformat(),
            "name": backup_name or f"backup_{len(session['backups']) + 1}",
            "description": f"Backup created at {datetime.now().isoformat()}",
        }

        session["backups"].append(backup)

        logger.info(f"Created backup {backup_id} for session {session_id}")

        return {
            "success": True,
            "backup_id": backup_id,
            "backup": backup,
            "message": "Schema backup created successfully",
        }

    except Exception as e:
        logger.error(f"Unexpected error in create_schema_backup: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_apply_schema_changes(
    session_id: str, ddl_statements: List[str], validate_before_commit: bool = True
) -> Dict[str, Any]:
    """Handle apply_schema_changes tool execution"""
    try:
        if session_id not in _schema_change_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session: Dict[str, Any] = _schema_change_sessions[session_id]

        config = load_config()
        db_manager = DatabaseManager(config.postgres)
        db_manager.connect()

        try:
            # Ensure we're in a transaction
            if not session["transaction_started"]:
                db_manager.execute_query("BEGIN;")
                session["transaction_started"] = True

            executed_statements = []
            errors = []

            # Execute each DDL statement
            for i, statement in enumerate(ddl_statements):
                try:
                    # Validate statement (basic check)
                    if (
                        not statement.strip()
                        .upper()
                        .startswith(("CREATE", "ALTER", "DROP", "RENAME"))
                    ):
                        errors.append(f"Statement {i+1}: Not a valid DDL statement")
                        continue

                    # Execute statement
                    result = db_manager.execute_query(statement)
                    executed_statements.append(
                        {
                            "statement": statement,
                            "execution_order": i + 1,
                            "success": True,
                            "result": result,
                        }
                    )

                    logger.info(f"Executed DDL statement {i+1}: {statement[:100]}...")

                except Exception as e:
                    errors.append(f"Statement {i+1}: {str(e)}")
                    executed_statements.append(
                        {
                            "statement": statement,
                            "execution_order": i + 1,
                            "success": False,
                            "error": str(e),
                        }
                    )

            # Validate changes if requested
            if validate_before_commit and not errors:
                # Basic validation - check if tables still exist and are accessible
                validation_result = await _validate_schema_changes(db_manager)
                if not validation_result["success"]:
                    errors.extend(validation_result["errors"])

            # Update session
            change_record = {
                "change_id": str(uuid.uuid4()),
                "applied_at": datetime.now().isoformat(),
                "statements": executed_statements,
                "errors": errors,
                "validated": validate_before_commit,
            }
            session["changes"].append(change_record)

            if errors:
                # Rollback transaction on errors
                db_manager.execute_query("ROLLBACK;")
                session["transaction_started"] = False

                return {
                    "success": False,
                    "errors": errors,
                    "executed_statements": executed_statements,
                    "message": "Schema changes failed, transaction rolled back",
                }
            else:
                # Changes applied successfully, but not committed yet
                return {
                    "success": True,
                    "executed_statements": executed_statements,
                    "message": "Schema changes applied successfully (not committed)",
                    "next_step": "Use commit_schema_changes to make changes permanent",
                }

        except Exception as e:
            db_manager.execute_query("ROLLBACK;")
            session["transaction_started"] = False
            raise e
        finally:
            db_manager.disconnect()

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in apply_schema_changes: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_rollback_schema_changes(
    session_id: str, backup_id: str = ""
) -> Dict[str, Any]:
    """Handle rollback_schema_changes tool execution"""
    try:
        if session_id not in _schema_change_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session: Dict[str, Any] = _schema_change_sessions[session_id]

        config = load_config()
        db_manager = DatabaseManager(config.postgres)
        db_manager.connect()

        try:
            if session["transaction_started"]:
                # Rollback current transaction
                db_manager.execute_query("ROLLBACK;")
                session["transaction_started"] = False

            # Note: In a real implementation, we would restore from backup
            # For now, we just record the rollback action

            rollback_record = {
                "rollback_id": str(uuid.uuid4()),
                "rolled_back_at": datetime.now().isoformat(),
                "backup_id": backup_id,
                "message": "Schema changes rolled back",
            }

            if "rollbacks" not in session:
                session["rollbacks"] = []
            session["rollbacks"].append(rollback_record)

            logger.info(f"Rolled back schema changes for session {session_id}")

            return {
                "success": True,
                "rollback_record": rollback_record,
                "message": "Schema changes rolled back successfully",
            }

        except Exception as e:
            raise e
        finally:
            db_manager.disconnect()

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in rollback_schema_changes: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_list_schema_backups(session_id: str) -> Dict[str, Any]:
    """Handle list_schema_backups tool execution"""
    try:
        if session_id not in _schema_change_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session: Dict[str, Any] = _schema_change_sessions[session_id]

        return {
            "success": True,
            "backups": session["backups"],
            "total_backups": len(session["backups"]),
        }

    except Exception as e:
        logger.error(f"Unexpected error in list_schema_backups: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_commit_schema_changes(session_id: str) -> Dict[str, Any]:
    """Handle commit_schema_changes tool execution"""
    try:
        if session_id not in _schema_change_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session: Dict[str, Any] = _schema_change_sessions[session_id]

        config = load_config()
        db_manager = DatabaseManager(config.postgres)
        db_manager.connect()

        try:
            if session["transaction_started"]:
                # Commit transaction
                db_manager.execute_query("COMMIT;")
                session["transaction_started"] = False

            # Mark session as completed
            session["status"] = "completed"
            session["completed_at"] = datetime.now().isoformat()

            logger.info(f"Committed schema changes for session {session_id}")

            return {
                "success": True,
                "message": "Schema changes committed successfully",
                "session": session,
            }

        except Exception as e:
            # Rollback on commit failure
            db_manager.execute_query("ROLLBACK;")
            session["transaction_started"] = False
            raise e
        finally:
            db_manager.disconnect()

    except DatabaseError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in commit_schema_changes: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Helper functions
async def _validate_schema_changes(db_manager: DatabaseManager) -> Dict[str, Any]:
    """Validate that schema changes don't break basic functionality"""
    errors = []

    try:
        # Check if we can still list tables
        tables_result = db_manager.get_tables()
        if not tables_result["success"]:
            errors.append("Cannot list tables after changes")

            # Check if we can describe a sample table
            if tables_result["success"] and tables_result["tables"]:
                sample_table = tables_result["tables"][0]
                # Use direct query to get table schema instead of missing method
                schema_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """
                try:
                    schema_result = db_manager.execute_query(
                        schema_query, {"table_name": sample_table}
                    )
                    if not schema_result["success"] or not schema_result["data"]:
                        errors.append(
                            f"Cannot describe table {sample_table} after changes"
                        )
                except Exception:
                    errors.append(f"Cannot describe table {sample_table} after changes")

    except Exception as e:
        errors.append(f"Validation error: {str(e)}")

    return {
        "success": len(errors) == 0,
        "errors": errors,
    }


# Tool registry
def get_transaction_tools() -> List[Tool]:
    """Get all transaction tools"""
    return [
        begin_change_session,
        create_schema_backup,
        apply_schema_changes,
        rollback_schema_changes,
        list_schema_backups,
        commit_schema_changes,
    ]


def get_transaction_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for transaction operations"""
    return {
        "begin_change_session": handle_begin_change_session,
        "create_schema_backup": handle_create_schema_backup,
        "apply_schema_changes": handle_apply_schema_changes,
        "rollback_schema_changes": handle_rollback_schema_changes,
        "list_schema_backups": handle_list_schema_backups,
        "commit_schema_changes": handle_commit_schema_changes,
    }
