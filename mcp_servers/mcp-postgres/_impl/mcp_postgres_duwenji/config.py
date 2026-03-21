"""
Configuration management for PostgreSQL MCP Server
"""

import os
import logging
from pydantic import BaseModel, Field
from .docker_manager import DockerConfig, load_docker_config


class PostgresConfig(BaseModel):
    """PostgreSQL connection configuration"""

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="postgres", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")

    # Connection options
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Maximum pool overflow")
    connect_timeout: int = Field(
        default=30, description="Connection timeout in seconds"
    )


class ServerConfig(BaseModel):
    """MCP Server configuration"""

    log_level: str = Field(default="INFO", description="Logging level")
    protocol_debug: bool = Field(
        default=False, description="Enable protocol debug mode"
    )
    log_dir: str = Field(default="", description="Log directory path")

    # PostgreSQL configuration
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)

    # Docker auto-setup configuration
    docker: DockerConfig = Field(default_factory=DockerConfig)


def load_config() -> ServerConfig:
    """
    Load configuration from environment variables

    Returns:
        ServerConfig: Loaded configuration

    Raises:
        ValueError: If required configuration is missing
    """
    # Load .env file if it exists
    from dotenv import load_dotenv

    load_dotenv()

    # Load Docker configuration first
    docker_config = load_docker_config()

    # If Docker auto-setup is enabled, use Docker container settings directly
    if docker_config.enabled:
        logger = logging.getLogger(__name__)
        logger.info("Docker auto-setup enabled, using Docker container settings")

        host = "localhost"
        port = docker_config.port
        database = docker_config.database
        username = docker_config.username
        password = docker_config.password
        ssl_mode = os.environ.get("POSTGRES_SSL_MODE", "prefer")
        pool_size = int(os.environ.get("POSTGRES_POOL_SIZE", "5"))
        max_overflow = int(os.environ.get("POSTGRES_MAX_OVERFLOW", "10"))
        connect_timeout = int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "30"))
    else:
        # Load PostgreSQL configuration from environment variables
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
        database = os.environ.get("POSTGRES_DB", "postgres")
        username = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "")
        ssl_mode = os.environ.get("POSTGRES_SSL_MODE", "prefer")
        pool_size = int(os.environ.get("POSTGRES_POOL_SIZE", "5"))
        max_overflow = int(os.environ.get("POSTGRES_MAX_OVERFLOW", "10"))
        connect_timeout = int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "30"))

    # Validate required PostgreSQL configuration
    if not host:
        raise ValueError("POSTGRES_HOST environment variable is required")
    if not database:
        raise ValueError("POSTGRES_DB environment variable is required")
    if not username:
        raise ValueError("POSTGRES_USER environment variable is required")

    # Create PostgresConfig with loaded values
    postgres_config = PostgresConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        ssl_mode=ssl_mode,
        pool_size=pool_size,
        max_overflow=max_overflow,
        connect_timeout=connect_timeout,
    )

    # Load server configuration
    log_level = os.environ.get("MCP_LOG_LEVEL", "INFO")
    protocol_debug = os.environ.get("MCP_PROTOCOL_DEBUG", "false").lower() == "true"
    log_dir = os.environ.get("MCP_LOG_DIR", "")

    # Create ServerConfig with the loaded PostgresConfig and DockerConfig
    config = ServerConfig(
        log_level=log_level,
        protocol_debug=protocol_debug,
        log_dir=log_dir,
        postgres=postgres_config,
        docker=docker_config,
    )

    return config


def get_connection_string(config: PostgresConfig) -> str:
    """
    Generate PostgreSQL connection string from configuration

    Args:
        config: PostgreSQL configuration

    Returns:
        str: PostgreSQL connection string
    """
    base_conn_str = (
        f"postgresql://{config.username}:{config.password}@"
        f"{config.host}:{config.port}/{config.database}"
    )

    # Add SSL mode if specified and not default "prefer"
    if config.ssl_mode and config.ssl_mode != "prefer":
        base_conn_str += f"?sslmode={config.ssl_mode}"

    return base_conn_str
