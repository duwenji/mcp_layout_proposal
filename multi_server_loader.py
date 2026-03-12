from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from mcp.server.fastmcp import FastMCP


@dataclass
class ModuleLoadResult:
    server_name: str
    category: str
    file: Path
    ok: bool
    error: str | None


@dataclass
class ServerBuildResult:
    server_name: str
    server: FastMCP
    module_results: list[ModuleLoadResult]


class MultiServerLayoutLoader:
    """Build FastMCP servers from hierarchical folders.

    Expected layout:
      root/
        server_a/
          Tools/*.py
          Prompts/*.py
          Resource/*.py
    """

    CATEGORY_DIRS = {
        "tools": {"tools", "tool"},
        "prompts": {"prompts", "prompt"},
        "resources": {"resource", "resources"},
    }

    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)

    def discover_servers(self) -> list[Path]:
        if not self.root_dir.exists():
            return []
        return sorted([p for p in self.root_dir.iterdir() if p.is_dir()])

    def _import_module(self, module_file: Path) -> ModuleType:
        module_name = f"ms_{module_file.parent.name}_{module_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {module_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _category_paths(self, server_dir: Path) -> dict[str, Path | None]:
        lowered = {p.name.lower(): p for p in server_dir.iterdir() if p.is_dir()}
        out: dict[str, Path | None] = {}
        for category, aliases in self.CATEGORY_DIRS.items():
            hit = next((lowered[a] for a in aliases if a in lowered), None)
            out[category] = hit
        return out

    def _load_category(self, server: FastMCP, server_name: str, category: str, dir_path: Path | None) -> list[ModuleLoadResult]:
        if dir_path is None:
            return []

        results: list[ModuleLoadResult] = []
        for py_file in sorted(dir_path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                module = self._import_module(py_file)
                register = getattr(module, "register", None)
                if not callable(register):
                    raise ValueError("Missing callable register(server)")
                register(server)
                results.append(
                    ModuleLoadResult(
                        server_name=server_name,
                        category=category,
                        file=py_file,
                        ok=True,
                        error=None,
                    )
                )
            except Exception as exc:
                results.append(
                    ModuleLoadResult(
                        server_name=server_name,
                        category=category,
                        file=py_file,
                        ok=False,
                        error=str(exc),
                    )
                )
        return results

    def build_all(self) -> list[ServerBuildResult]:
        builds: list[ServerBuildResult] = []
        for server_dir in self.discover_servers():
            builds.append(self.build_server(server_dir.name))

        return builds

    def build_server(self, server_name: str) -> ServerBuildResult:
        server_dir = self.root_dir / server_name
        if not server_dir.exists() or not server_dir.is_dir():
            raise ValueError(f"Server directory does not exist: {server_name}")

        server = FastMCP(server_name)
        category_paths = self._category_paths(server_dir)
        module_results: list[ModuleLoadResult] = []
        for category in ("tools", "prompts", "resources"):
            module_results.extend(
                self._load_category(
                    server=server,
                    server_name=server_name,
                    category=category,
                    dir_path=category_paths.get(category),
                )
            )

        self._attach_admin_interfaces(server, module_results)
        return ServerBuildResult(
            server_name=server_name,
            server=server,
            module_results=module_results,
        )

    def _attach_admin_interfaces(self, server: FastMCP, module_results: list[ModuleLoadResult]) -> None:
        @server.resource("layout://load-report")
        def load_report() -> str:
            lines: list[str] = []
            for item in module_results:
                status = "OK" if item.ok else "ERROR"
                lines.append(
                    f"[{status}] {item.server_name}/{item.category}/{item.file.name} err={item.error}"
                )
            return "\n".join(lines)

        @server.tool(name="layout_list")
        def layout_list() -> list[dict[str, Any]]:
            return [
                {
                    "server_name": item.server_name,
                    "category": item.category,
                    "file": item.file.name,
                    "ok": item.ok,
                    "error": item.error,
                }
                for item in module_results
            ]
