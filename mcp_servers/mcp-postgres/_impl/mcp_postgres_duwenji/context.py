"""
Application context for PostgreSQL MCP Server

This module provides centralized context management for all server resources,
replacing global variables with explicit context-based resource management.
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from .config import ServerConfig
from .database import ConnectionPoolManager
from .docker_manager import DockerManager


class AppContext:
    """
    Application context that holds all server resources.

    This class centralizes resource management and provides type-safe access
    to all server components.
    """

    def __init__(self):
        # Core resources
        self.config: Optional[ServerConfig] = None
        self.logger: Optional[logging.Logger] = None
        self.protocol_logger: Optional[logging.Logger] = None
        self.pool_manager: Optional[ConnectionPoolManager] = None
        self.docker_manager: Optional[DockerManager] = None

        # Concerns management for MCP filtering
        self.concerns: dict = {
            "development": "-",
            "maintenance": "-",
            "using": "-",
            "tuning": "-",
        }

        # Derived resources (initialized on-demand)
        self._initialized: bool = False
        self._shutdown_requested: bool = False

    def is_initialized(self) -> bool:
        """Check if context has been properly initialized."""
        return self._initialized

    def mark_initialized(self) -> None:
        """Mark context as initialized."""
        self._initialized = True

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_requested = True

    def validate(self) -> None:
        """
        Validate that all required resources are initialized.

        Raises:
            RuntimeError: If any required resource is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Context has not been initialized")

        required_resources = [
            ("config", self.config),
            ("logger", self.logger),
            ("protocol_logger", self.protocol_logger),
            ("pool_manager", self.pool_manager),
        ]

        for name, resource in required_resources:
            if resource is None:
                raise RuntimeError(f"Required resource '{name}' is not initialized")

    @staticmethod
    def _validate_concerns(concerns: dict) -> tuple[bool, str]:
        """
        Validate concerns dictionary.

        Args:
            concerns: Dictionary of concerns to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_concerns = {"development", "maintenance", "using", "tuning"}
        valid_values = {"-", "low", "medium", "high"}

        for key, value in concerns.items():
            if key not in valid_concerns:
                return (
                    False,
                    f"Invalid concern key: {key}. Valid keys are: {', '.join(valid_concerns)}",
                )

            if value not in valid_values:
                return (
                    False,
                    f"Invalid concern value for {key}: {value}. Valid values are: {', '.join(valid_values)}",
                )

        return True, ""

    async def shutdown(self) -> None:
        """
        Perform graceful shutdown of all resources.

        This method should be called during server shutdown to clean up
        all resources properly.
        """
        if not self._initialized:
            return

        if self.logger:
            self.logger.info("Starting context shutdown...")

        # Close database connections
        if self.pool_manager:
            try:
                self.pool_manager.disconnect()
                if self.logger:
                    self.logger.info("Database connection pool closed")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error closing database connection pool: {e}")

        # Stop Docker container if enabled
        if self.docker_manager and self.config and self.config.docker.enabled:
            try:
                result = self.docker_manager.stop_container()
                if self.logger:
                    if result.get("success"):
                        self.logger.info("Docker container stopped")
                    else:
                        self.logger.warning(
                            f"Failed to stop Docker container: {result.get('error')}"
                        )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error stopping Docker container: {e}")

        if self.logger:
            self.logger.info("Context shutdown completed")

        self._initialized = False


# Global context instance (for backward compatibility during migration)
# Note: This will be removed once migration is complete
_global_context: Optional[AppContext] = None


def get_global_context() -> Optional[AppContext]:
    """
    Get the global context instance.

    This is a temporary function for backward compatibility during migration.
    New code should pass context explicitly rather than using global state.

    Returns:
        The global AppContext instance, or None if not set.
    """
    return _global_context


def set_global_context(context: AppContext) -> None:
    """
    Set the global context instance.

    This is a temporary function for backward compatibility during migration.

    Args:
        context: The AppContext instance to set as global.
    """
    global _global_context
    _global_context = context


@asynccontextmanager
async def create_lifespan_context():
    """
    Create a lifespan context manager for MCP server.

    This context manager handles the complete lifecycle of server resources:
    1. Initializes all resources during startup
    2. Yields control to server runtime
    3. Cleans up all resources during shutdown

    Yields:
        AppContext: The initialized application context
    """
    context = AppContext()

    try:
        # Startup phase
        await _initialize_context(context)
        context.mark_initialized()

        # Set global context for backward compatibility
        set_global_context(context)

        # Yield control to server runtime
        yield context

    except Exception as e:
        if context.logger:
            context.logger.error(f"Server runtime error: {e}")
        raise
    finally:
        # Shutdown phase
        if context.logger:
            context.logger.info("Starting server shutdown...")
        await context.shutdown()
        if context.logger:
            context.logger.info("Server shutdown completed")


async def _initialize_context(context: AppContext) -> None:
    """
    Initialize all resources in the context.

    Args:
        context: The AppContext to initialize.

    Raises:
        RuntimeError: If initialization fails.
    """
    from .config import load_config
    from .shared import setup_logging

    # Load configuration
    context.config = load_config()

    # Setup logging
    context.logger, context.protocol_logger = setup_logging(
        log_level=context.config.log_level, log_dir=context.config.log_dir
    )

    context.logger.info(f"Configuration loaded successfully. config={context.config}")

    # Handle Docker auto-setup if enabled
    if context.config.docker.enabled:
        context.logger.info(
            "Docker auto-setup enabled, starting PostgreSQL container..."
        )
        context.docker_manager = DockerManager(context.config.docker)

        if context.docker_manager.is_docker_available():
            result = context.docker_manager.start_container()
            if result["success"]:
                context.logger.info(
                    f"PostgreSQL container started successfully: {result}"
                )
            else:
                context.logger.error(
                    f"Failed to start PostgreSQL container: {result.get('error', 'Unknown error')}"
                )
                # Continue without Docker setup - user might have external PostgreSQL
        else:
            context.logger.warning(
                "Docker auto-setup enabled but Docker is not available. Using existing PostgreSQL connection."
            )

    # Initialize connection pool manager
    context.logger.info("Initializing connection pool manager...")
    context.pool_manager = ConnectionPoolManager(context.config.postgres)

    # Test database connection
    if context.pool_manager.test_connection():
        context.logger.info("Connection pool manager initialized successfully")
    else:
        context.logger.error("Failed to initialize connection pool manager")
        raise RuntimeError("Database connection failed")

    context.logger.info("Application context initialization completed")
