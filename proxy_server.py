from __future__ import annotations

import argparse
import logging
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from multi_server_loader import MultiServerLayoutLoader

logger = logging.getLogger(__name__)


def create_proxy_app(servers_dict: dict[str, tuple[str, object]]) -> Starlette:
    """
    Create a Starlette app that mounts FastMCP servers on different paths.
    
    Args:
        servers_dict: Dict of {path: (server_name, FastMCP_instance)}
    """
    routes: list = []

    # Add health check endpoint
    async def health_check(request):
        return JSONResponse({"status": "ok"})

    routes.append(Route("/health", health_check))

    # Mount each server at its path
    for path, (server_name, server_instance) in servers_dict.items():
        logger.info(f"Mounting {server_name} at /{path}/mcp")
        
        # Get the ASGI app from FastMCP
        app_asgi = server_instance.http_app()
        routes.append(Mount(f"/{path}", app_asgi))

    app = Starlette(routes=routes)
    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCP servers via unified path-based proxy")
    parser.add_argument("--root", default="mcp_servers", help="Root directory of server folders")
    parser.add_argument("--server", nargs="*", default=None, help="Server directory name(s) to expose (if none specified, expose all)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind to")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Logging level")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    loader = MultiServerLayoutLoader(Path(args.root))

    # Determine which servers to include
    if args.server is None or len(args.server) == 0:
        # No server specified, expose all
        server_names = [p.name for p in loader.discover_servers()]
    else:
        # Validate specified servers
        server_names = args.server
        for server_name in server_names:
            try:
                loader.build_server(server_name)
            except ValueError:
                available = ", ".join(p.name for p in loader.discover_servers()) or "(none)"
                raise SystemExit(f"Unknown server '{server_name}'. Available: {available}")

    # Build all servers
    logger.info(f"Building {len(server_names)} server(s)...")
    servers_dict: dict[str, tuple[str, object]] = {}
    
    for server_name in server_names:
        try:
            build_result = loader.build_server(server_name)
            server_info = build_result.server_info or {}
            
            # Get path from server.json or use server name
            path = server_info.get("path", server_name)
            
            servers_dict[path] = (server_name, build_result.server)
            logger.info(f"Loaded {server_name} → /{path}/mcp")
        except Exception as e:
            logger.error(f"Failed to load {server_name}: {e}")
            raise SystemExit(1)

    if not servers_dict:
        raise SystemExit("No servers available to mount")

    # Create proxy app
    app = create_proxy_app(servers_dict)

    # Run
    logger.info(f"Starting proxy server on {args.host}:{args.port}")
    logger.info(f"Available endpoints:")
    for path in sorted(servers_dict.keys()):
        logger.info(f"  http://{args.host}:{args.port}/{path}/mcp")
    logger.info(f"  http://{args.host}:{args.port}/health")

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
