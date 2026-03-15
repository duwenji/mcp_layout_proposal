from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from multi_server_loader import MultiServerLayoutLoader


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCP servers from hierarchical layout")
    parser.add_argument("--root", default="mcp_servers", help="Root directory of server folders")
    parser.add_argument("--server", nargs="*", default=None, help="Server name to run (stdio mode) or servers to expose (sse/streamable-http)")
    parser.add_argument(
        "--transport",
        default="sse",
        choices=["stdio", "sse", "streamable-http"],
        help="FastMCP transport (stdio=debug mode, sse/streamable-http=proxy mode)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind to")
    args = parser.parse_args()

    loader = MultiServerLayoutLoader(Path(args.root))
    
    if args.transport == "stdio":
        # Debug Mode: single server with stdio transport and output capture
        if not args.server or len(args.server) != 1:
            available = ", ".join(p.name for p in loader.discover_servers()) or "(none)"
            raise SystemExit(f"Stdio mode requires exactly one --server. Available: {available}")
        
        server_name = args.server[0]
        
        # Validate server exists
        try:
            loader.build_server(server_name)
        except ValueError:
            available = ", ".join(p.name for p in loader.discover_servers()) or "(none)"
            raise SystemExit(f"Unknown server '{server_name}'. Available: {available}")
        
        # Start subprocess with stdio transport
        print(f"Debug Mode (stdio): Starting {server_name}")
        proc_args = [
            sys.executable,
            "run_server_subprocess.py",
            "--root", args.root,
            "--server", server_name,
            "--transport", "stdio",
        ]
        
        try:
            proc = subprocess.Popen(
                proc_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Real-time output capture and display
            for line in iter(proc.stdout.readline, ''):
                if line:
                    print(f"[{server_name}] {line}", end="")
            
            returncode = proc.wait()
            return returncode
        except KeyboardInterrupt:
            print(f"\nTerminating {server_name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            return 1
    else:
        # Proxy Mode: multiple servers with path-based routing
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
        
        # Start proxy server with specified transport
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
