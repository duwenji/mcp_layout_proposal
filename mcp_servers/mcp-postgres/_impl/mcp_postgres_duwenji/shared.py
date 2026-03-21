"""
Shared utilities and global state management for PostgreSQL MCP Server

This module provides centralized storage for global variables and utilities
to avoid circular imports and enable sharing across all tool modules.
"""

import logging
import os
from typing import Optional
from .database import ConnectionPoolManager, DatabaseManager
from .config import ServerConfig
from .context import AppContext, get_global_context


def setup_logging(
    log_level: str = "INFO", log_dir: str = ""
) -> tuple[logging.Logger, logging.Logger]:
    """
    Setup logging with custom directory and log level

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Custom log directory path. If empty, uses current directory.

    Returns:
        Tuple of (general logger, protocol logger)
    """
    # ログレベルを数値に変換
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # ログディレクトリが指定されている場合は使用
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        general_log_path = os.path.join(log_dir, "mcp_postgres.log")
        protocol_log_path = os.path.join(log_dir, "mcp_protocol.log")
    else:
        general_log_path = "mcp_postgres.log"
        protocol_log_path = "mcp_protocol.log"

    # ルートロガーのリセット
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 基本ログ設定 - ファイルのみに出力（sys.stdout/sys.stderrへの出力なし）
    logger = logging.getLogger(__name__)
    logger.setLevel(numeric_level)

    # ファイルハンドラー
    file_handler = logging.FileHandler(general_log_path)
    file_handler.setLevel(numeric_level)

    # フォーマッター - ファイル名と行番号を追加
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # ファイルハンドラーのみ追加
    logger.addHandler(file_handler)
    logger.propagate = False  # 重複ログを防ぐ

    # プロトコルロガー設定 - ファイル名と行番号を追加
    protocol_logger = logging.getLogger("mcp_protocol")
    protocol_logger.setLevel(numeric_level)
    protocol_handler = logging.FileHandler(protocol_log_path)
    protocol_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
    )
    protocol_logger.addHandler(protocol_handler)
    protocol_logger.propagate = False  # Prevent duplicate logging

    return logger, protocol_logger


# Legacy global variables for backward compatibility
# These will be deprecated in favor of context-based management
_global_pool_manager: Optional[ConnectionPoolManager] = None
_global_config: Optional[ServerConfig] = None


def set_global_db_connection(
    pool_manager: ConnectionPoolManager, config: ServerConfig
) -> None:
    """
    Set global connection pool manager and configuration for sharing across tools

    Note: This is a legacy function for backward compatibility.
    New code should use context-based resource management.
    """
    global _global_pool_manager, _global_config
    _global_pool_manager = pool_manager
    _global_config = config


def get_global_pool_manager() -> Optional[ConnectionPoolManager]:
    """
    Get the global connection pool manager

    Note: This is a legacy function for backward compatibility.
    New code should use context-based resource management.
    """
    # First try to get from global context
    context = get_global_context()
    if context and context.pool_manager:
        return context.pool_manager

    # Fall back to legacy global variable
    return _global_pool_manager


def get_global_config() -> Optional[ServerConfig]:
    """
    Get the global configuration

    Note: This is a legacy function for backward compatibility.
    New code should use context-based resource management.
    """
    # First try to get from global context
    context = get_global_context()
    if context and context.config:
        return context.config

    # Fall back to legacy global variable
    return _global_config


def get_database_manager() -> DatabaseManager:
    """
    Get a DatabaseManager instance using context, global connection, or create new one

    Returns:
        DatabaseManager instance ready for use
    """
    # First try to get from global context
    context = get_global_context()
    if context and context.is_initialized():
        # Ensure config is not None
        if context.config is None:
            raise RuntimeError("Context configuration is not initialized")
        db_manager = DatabaseManager(context.config.postgres, context.pool_manager)
        db_manager._is_connected = True
        return db_manager

    # Fall back to legacy global variables
    _global_pool_manager = get_global_pool_manager()
    _global_config = get_global_config()

    if _global_pool_manager is None or _global_config is None:
        from .config import load_config

        config = load_config()
        db_manager = DatabaseManager(config.postgres)
        db_manager.connect()
        return db_manager
    else:
        db_manager = DatabaseManager(_global_config.postgres, _global_pool_manager)
        db_manager._is_connected = True
        return db_manager


def get_context_database_manager(context: AppContext) -> DatabaseManager:
    """
    Get a DatabaseManager instance from a specific context

    Args:
        context: The AppContext instance to get resources from

    Returns:
        DatabaseManager instance ready for use

    Raises:
        RuntimeError: If context is not properly initialized
    """
    if not context or not context.is_initialized():
        raise RuntimeError("Context is not properly initialized")

    # Ensure config is not None
    if context.config is None:
        raise RuntimeError("Context configuration is not initialized")

    db_manager = DatabaseManager(context.config.postgres, context.pool_manager)
    db_manager._is_connected = True
    return db_manager
