from __future__ import annotations

import argparse
import subprocess
import sys
from multiprocessing import Process
from pathlib import Path

from multi_server_loader import MultiServerLayoutLoader


def run_server(server_name: str, root_dir: str, transport: str) -> None:
    """Run a single server in its own process."""
    loader = MultiServerLayoutLoader(Path(root_dir))
    try:
        build = loader.build_server(server_name)
        build.server.run(transport=transport)
    except ValueError as e:
        print(f"Error running {server_name}: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCP servers from hierarchical layout")
    parser.add_argument("--root", default="mcp_servers", help="Root directory of server folders")
    parser.add_argument("--server", nargs="*", default=None, help="Server directory name(s) to run (if none specified, run all)")
    parser.add_argument(
        "--transport",
        default="sse",
        choices=["stdio", "sse", "streamable-http"],
        help="FastMCP transport (stdio=multi mode, sse/streamable-http=proxy mode)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind to")
    args = parser.parse_args()

    loader = MultiServerLayoutLoader(Path(args.root))
    
    if args.server is None or len(args.server) == 0:
        # No server specified, run all
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

    if args.transport == "stdio":
        # Multi Mode: separate processes with stdio
        print(f"Multi Mode (stdio): Starting {len(server_names)} server(s)")
        processes = []
        for server_name in server_names:
            p = Process(target=run_server, args=(server_name, args.root, args.transport))
            p.start()
            processes.append((server_name, p))
            print(f"  Started {server_name}")

        try:
            for server_name, p in processes:
                p.join()
        except KeyboardInterrupt:
            print("Terminating all servers...")
            for server_name, p in processes:
                p.terminate()
            for server_name, p in processes:
                p.join()
        return 0
    else:
        # Proxy Mode: path-based routing on single port
        print(f"Proxy Mode ({args.transport}): Starting on {args.host}:{args.port}")
        proc_args = [
            sys.executable,
            "proxy_server.py",
            "--root", args.root,
            "--host", args.host,
            "--port", str(args.port),
        ]
        if server_names:
            proc_args.extend(["--server"] + server_names)
        
        proc = subprocess.run(proc_args)
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
