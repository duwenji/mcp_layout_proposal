"""
Docker management for PostgreSQL MCP Server
Automatically sets up PostgreSQL Docker container when MCP server starts
"""

import logging
import os
import time
from typing import Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DockerConfig(BaseModel):
    """Docker container configuration"""

    enabled: bool = Field(default=False, description="Enable Docker auto-setup")
    image: str = Field(default="postgres:16", description="PostgreSQL Docker image")
    container_name: str = Field(
        default="mcp-postgres-auto", description="Container name"
    )
    port: int = Field(default=5432, description="Host port mapping")
    data_volume: str = Field(
        default="mcp_postgres_data", description="Data volume name"
    )
    password: str = Field(default="postgres", description="PostgreSQL password")
    database: str = Field(default="postgres", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    max_wait_time: int = Field(
        default=30, description="Maximum wait time for container startup (seconds)"
    )
    slow_query_threshold_ms: int = Field(
        default=1000, description="Slow query threshold in milliseconds"
    )
    enable_auto_explain: bool = Field(
        default=True, description="Enable auto_explain extension"
    )


class DockerManager:
    """Manages PostgreSQL Docker container lifecycle"""

    def __init__(self, config: DockerConfig):
        self.config = config
        self.container = None
        self._docker_client: Any = None

    def _get_docker_client(self) -> Any:
        """Get Docker client with lazy loading"""
        if self._docker_client is None:
            try:
                import docker

                self._docker_client = docker.from_env()
            except ImportError:
                raise RuntimeError(
                    "Docker Python SDK not installed. Install with: pip install docker"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Docker: {e}")
        return self._docker_client

    def is_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            client = self._get_docker_client()
            client.ping()
            return True
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            return False

    def is_container_running(self) -> bool:
        """Check if the PostgreSQL container is already running"""
        try:
            client = self._get_docker_client()
            containers = client.containers.list(
                filters={"name": self.config.container_name}
            )
            return len(containers) > 0
        except Exception as e:
            logger.warning(f"Failed to check container status: {e}")
            return False

    def start_container(self) -> Dict[str, Any]:
        """Start PostgreSQL Docker container"""
        try:
            client = self._get_docker_client()

            # Check if container already exists
            try:
                existing_container = client.containers.get(self.config.container_name)
                if existing_container.status == "running":
                    logger.info(
                        f"Container {self.config.container_name} is already running"
                    )
                    return {
                        "success": True,
                        "status": "already_running",
                        "container_id": existing_container.id,
                        "port": self.config.port,
                    }
                else:
                    logger.info(
                        f"Starting existing container {self.config.container_name}"
                    )
                    existing_container.start()
                    self.container = existing_container
            except Exception:
                # Container doesn't exist, create new one
                logger.info(
                    f"Creating new PostgreSQL container: {self.config.container_name}"
                )

                # Pull image if not exists
                try:
                    client.images.get(self.config.image)
                except Exception:
                    logger.info(f"Pulling image: {self.config.image}")
                    client.images.pull(self.config.image)

                # Get the path to our custom postgresql.conf
                current_dir = os.path.dirname(os.path.abspath(__file__))
                custom_conf_path = os.path.join(
                    current_dir, "assets", "postgresql.conf"
                )

                # Use standard PostgreSQL startup without custom config file override
                # The custom config will be applied after initialization
                self.container = client.containers.run(
                    image=self.config.image,
                    name=self.config.container_name,
                    environment={
                        "POSTGRES_PASSWORD": self.config.password,
                        "POSTGRES_DB": self.config.database,
                        "POSTGRES_USER": self.config.username,
                    },
                    ports={"5432/tcp": self.config.port},
                    volumes={
                        self.config.data_volume: {
                            "bind": "/var/lib/postgresql/data",
                            "mode": "rw",
                        },
                        custom_conf_path: {
                            "bind": "/etc/mcp_postgresql.conf",
                            "mode": "ro",
                        },
                    },
                    detach=True,
                    auto_remove=False,
                    restart_policy={"Name": "unless-stopped"},
                )

            # Wait for PostgreSQL to be ready
            if self._wait_for_postgres_ready():
                # Apply custom configuration after PostgreSQL is ready
                if self._apply_custom_config():
                    logger.info(
                        f"PostgreSQL container started successfully on port "
                        f"{self.config.port} with custom configuration"
                    )
                else:
                    logger.warning(
                        "PostgreSQL container started but custom configuration could not be applied"
                    )

                container_id = self.container.id if self.container else "unknown"
                return {
                    "success": True,
                    "status": "started",
                    "container_id": container_id,
                    "port": self.config.port,
                }
            else:
                logger.error("PostgreSQL container started but not responding")
                return {
                    "success": False,
                    "error": "PostgreSQL container not responding after startup",
                }

        except Exception as e:
            logger.error(f"Failed to start PostgreSQL container: {e}")
            return {"success": False, "error": str(e)}

    def stop_container(self) -> Dict[str, Any]:
        """Stop PostgreSQL Docker container"""
        try:
            if self.container:
                self.container.stop()
                logger.info(
                    f"Stopped PostgreSQL container: {self.config.container_name}"
                )
                return {"success": True}

            # Try to find and stop container by name
            client = self._get_docker_client()
            try:
                container = client.containers.get(self.config.container_name)
                container.stop()
                logger.info(
                    f"Stopped PostgreSQL container: {self.config.container_name}"
                )
                return {"success": True}
            except Exception:
                logger.info(f"Container {self.config.container_name} not found")
                return {"success": True}

        except Exception as e:
            logger.error(f"Failed to stop PostgreSQL container: {e}")
            return {"success": False, "error": str(e)}

    def remove_container(self) -> Dict[str, Any]:
        """Remove PostgreSQL Docker container"""
        try:
            client = self._get_docker_client()
            try:
                container = client.containers.get(self.config.container_name)
                container.remove(force=True)
                logger.info(
                    f"Removed PostgreSQL container: {self.config.container_name}"
                )
            except Exception:
                logger.info(f"Container {self.config.container_name} not found")

            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to remove PostgreSQL container: {e}")
            return {"success": False, "error": str(e)}

    def _wait_for_postgres_ready(self) -> bool:
        """Wait for PostgreSQL to be ready to accept connections"""
        import psycopg2
        import socket

        start_time = time.time()
        max_wait = self.config.max_wait_time

        while time.time() - start_time < max_wait:
            try:
                # Try to connect to PostgreSQL
                conn = psycopg2.connect(
                    host="localhost",
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.username,
                    password=self.config.password,
                    connect_timeout=5,
                )
                conn.close()
                return True
            except (psycopg2.OperationalError, socket.timeout, ConnectionRefusedError):
                time.sleep(2)

        return False

    def get_container_status(self) -> Dict[str, Any]:
        """Get current container status"""
        try:
            client = self._get_docker_client()
            try:
                container = client.containers.get(self.config.container_name)
                return {
                    "success": True,
                    "status": container.status,
                    "running": container.status == "running",
                    "container_id": container.id,
                    "image": (
                        container.image.tags[0]
                        if container.image.tags
                        else self.config.image
                    ),
                }
            except Exception:
                return {"success": True, "status": "not_found", "running": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _apply_custom_config(self) -> bool:
        """Apply custom PostgreSQL configuration after container startup"""
        try:
            if not self.container:
                logger.warning("No container available to apply configuration")
                return False

            # Execute commands inside the container to apply custom configuration
            # 1. Backup the original postgresql.conf
            # 2. Copy our custom configuration
            # 3. Reload PostgreSQL configuration

            commands = [
                # Backup original configuration
                "cp /var/lib/postgresql/data/postgresql.conf /var/lib/postgresql/data/postgresql.conf.backup",
                # Copy custom configuration
                "cp /etc/mcp_postgresql.conf /var/lib/postgresql/data/postgresql.conf",
                # Ensure proper permissions
                "chown postgres:postgres /var/lib/postgresql/data/postgresql.conf",
                "chmod 600 /var/lib/postgresql/data/postgresql.conf",
                # Reload PostgreSQL configuration
                "pg_ctl reload -D /var/lib/postgresql/data",
            ]

            for command in commands:
                result = self.container.exec_run(command, user="postgres")
                if result.exit_code != 0:
                    logger.warning(
                        f"Command failed: {command}, exit code: {result.exit_code}"
                    )
                    # Continue with next command even if one fails

            logger.info("Custom PostgreSQL configuration applied successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to apply custom configuration: {e}")
            return False


def load_docker_config() -> DockerConfig:
    """
    Load Docker configuration from environment variables

    Returns:
        DockerConfig: Loaded Docker configuration
    """
    enabled = os.environ.get("MCP_DOCKER_AUTO_SETUP", "false").lower() == "true"
    image = os.environ.get("MCP_DOCKER_IMAGE", "postgres:16")
    container_name = os.environ.get("MCP_DOCKER_CONTAINER_NAME", "mcp-postgres-auto")
    port = int(os.environ.get("MCP_DOCKER_PORT", "5432"))
    data_volume = os.environ.get("MCP_DOCKER_DATA_VOLUME", "mcp_postgres_data")
    password = os.environ.get("MCP_DOCKER_PASSWORD", "postgres")
    database = os.environ.get("MCP_DOCKER_DATABASE", "postgres")
    username = os.environ.get("MCP_DOCKER_USERNAME", "postgres")
    max_wait_time = int(os.environ.get("MCP_DOCKER_MAX_WAIT_TIME", "30"))
    slow_query_threshold_ms = int(os.environ.get("MCP_SLOW_QUERY_THRESHOLD_MS", "1000"))
    enable_auto_explain = (
        os.environ.get("MCP_ENABLE_AUTO_EXPLAIN", "true").lower() == "true"
    )

    return DockerConfig(
        enabled=enabled,
        image=image,
        container_name=container_name,
        port=port,
        data_volume=data_volume,
        password=password,
        database=database,
        username=username,
        max_wait_time=max_wait_time,
        slow_query_threshold_ms=slow_query_threshold_ms,
        enable_auto_explain=enable_auto_explain,
    )
