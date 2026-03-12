from __future__ import annotations

import argparse
from pathlib import Path

from multi_server_loader import MultiServerLayoutLoader


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCP server from hierarchical layout")
    parser.add_argument("--root", default="mcp_servers", help="Root directory of server folders")
    parser.add_argument("--server", required=True, help="Server directory name to run")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="FastMCP transport",
    )
    args = parser.parse_args()

    loader = MultiServerLayoutLoader(Path(args.root))
    try:
        target = loader.build_server(args.server)
    except ValueError:
        available = ", ".join(p.name for p in loader.discover_servers()) or "(none)"
        raise SystemExit(f"Unknown server '{args.server}'. Available: {available}")

    target.server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
