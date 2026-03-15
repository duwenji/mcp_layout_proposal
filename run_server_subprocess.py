"""Run a single MCP server in subprocess mode (for debug/stdio transport)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from multi_server_loader import MultiServerLayoutLoader


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single MCP server in subprocess")
    parser.add_argument("--root", required=True, help="Root directory of server folders")
    parser.add_argument("--server", required=True, help="Server name to run")
    parser.add_argument("--transport", required=True, choices=["stdio", "sse", "streamable-http"], help="Transport mode")
    args = parser.parse_args()

    loader = MultiServerLayoutLoader(Path(args.root))
    
    try:
        build = loader.build_server(args.server)
        build.server.run(transport=args.transport)
    except ValueError as e:
        print(f"Error: Unknown server '{args.server}'", file=sys.stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"Error running {args.server}: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
