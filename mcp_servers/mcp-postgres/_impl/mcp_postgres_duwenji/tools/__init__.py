"""
MCP Tools for PostgreSQL operations

This module contains all the MCP tools for database operations.
"""

from .crud_tools import (
    create_entity,
    read_entity,
    update_entity,
    delete_entity,
)

from .sampling_tools import (
    get_multiple_table_schemas,
    analyze_table_relationships,
    generate_schema_overview,
    analyze_normalization_state,
    suggest_normalization_improvements,
)

from .transaction_tools import (
    begin_change_session,
    create_schema_backup,
    apply_schema_changes,
    rollback_schema_changes,
    list_schema_backups,
    commit_schema_changes,
)

from .sampling_integration import (
    request_llm_analysis,
    generate_normalization_plan,
    assess_data_quality,
    optimize_schema_with_llm,
)

__all__ = [
    "create_entity",
    "read_entity",
    "update_entity",
    "delete_entity",
    "get_multiple_table_schemas",
    "analyze_table_relationships",
    "generate_schema_overview",
    "analyze_normalization_state",
    "suggest_normalization_improvements",
    "begin_change_session",
    "create_schema_backup",
    "apply_schema_changes",
    "rollback_schema_changes",
    "list_schema_backups",
    "commit_schema_changes",
    "request_llm_analysis",
    "generate_normalization_plan",
    "assess_data_quality",
    "optimize_schema_with_llm",
]
