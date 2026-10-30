from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
import re
from typing import Optional
import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Module, ModuleEdge, Repository
from app.providers.base import LLMProvider, Msg

logger = logging.getLogger("app.services.explorer")

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".tox",
    ".idea",
    ".vscode",
}

COMMON_ENTRY_POINT_NAMES = {
    "main.py",
    "app.py",
    "manage.py",
    "run.py",
    "cli.py",
    "server.py",
    "wsgi.py",
    "asgi.py",
    "__main__.py",
    "index.js",
    "index.ts",
    "server.js",
    "server.ts",
    "app.js",
    "app.ts",
    "main.js",
    "main.ts",
    "main.go",
    "main.rs",
}


def parse_python_imports(code: str) -> list[str]:
    """Extracts imported module names from Python source code."""
    imported_names: list[str] = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.append(node.module)
    except Exception:
        # Regex fallback on syntax error
        for match in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z0-9_.]+)", code, re.MULTILINE):
            imported_names.append(match.group(1))
    return imported_names


def parse_js_ts_imports(code: str) -> list[str]:
    """Extracts imported module names or paths from JS / TS source code."""
    imported_paths: list[str] = []
    patterns = [
        re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"])"""),
        re.compile(r"""(?:require\(\s*['"]([^'"]+)['"]\))"""),
        re.compile(r"""(?:export\s+.*?from\s+['"]([^'"]+)['"])"""),
        re.compile(r"""(?:import\(\s*['"]([^'"]+)['"]\))"""),
    ]
    for pattern in patterns:
        for match in pattern.finditer(code):
            imported_paths.append(match.group(1))
    return imported_paths


def detect_entry_points_in_files(
    rel_paths: list[str],
    manifests: Optional[dict[str, str]] = None,
) -> list[str]:
    """Finds known entry point files among a list of relative file paths."""
    entry_points: list[str] = []
    for p in rel_paths:
        name = Path(p).name.lower()
        if name in COMMON_ENTRY_POINT_NAMES:
            entry_points.append(p)

    if manifests:
        pkg_json = manifests.get("package.json")
        if pkg_json:
            try:
                data = json.loads(pkg_json)
                main_field = data.get("main")
                if main_field and isinstance(main_field, str):
                    clean_main = main_field.lstrip("./")
                    if clean_main not in entry_points:
                        entry_points.append(clean_main)
                bin_field = data.get("bin")
                if isinstance(bin_field, str):
                    clean_bin = bin_field.lstrip("./")
                    if clean_bin not in entry_points:
                        entry_points.append(clean_bin)
                elif isinstance(bin_field, dict):
                    for b_val in bin_field.values():
                        if isinstance(b_val, str):
                            clean_b = b_val.lstrip("./")
                            if clean_b not in entry_points:
                                entry_points.append(clean_b)
            except Exception:
                pass

    return sorted(list(set(entry_points)))


def generate_fallback_summary(
    name: str,
    path: str,
    file_count: int,
    key_files: list[str],
    entry_points: list[str],
) -> str:
    """Generates a deterministic summary if LLM call is unavailable or fails."""
    sample_files = f" including {', '.join(key_files[:4])}" if key_files else ""
    entry_str = f" Primary entry points: {', '.join(entry_points)}." if entry_points else ""
    clean_name = name.replace("_", " ").replace("-", " ")
    return (
        f"The {name} module ({path}) comprises {file_count} files{sample_files}. "
        f"It provides core functionality for {clean_name}.{entry_str}"
    )


class ModuleInfo:
    def __init__(self, path: str, name: str):
        self.path = path
        self.name = name
        self.files: list[str] = []
        self.key_files: list[str] = []
        self.entry_points: list[str] = []
        self.file_count: int = 0
        self.summary: str = ""
        self.id: uuid.UUID = uuid.uuid4()


class ExplorerService:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    def partition_files_into_modules(self, rel_paths: list[str]) -> list[ModuleInfo]:
        """
        Groups relative file paths into architectural modules.
        Modules are top-level directories and packages.
        """
        # Filter ignored directories
        valid_paths = [
            p for p in rel_paths
            if not any(part in IGNORED_DIRS for part in Path(p).parts)
        ]

        if not valid_paths:
            return []

        module_map: dict[str, ModuleInfo] = {}

        for p in valid_paths:
            parts = Path(p).parts
            if len(parts) == 1:
                # Root level file
                mod_path = "."
                mod_name = "root"
            elif parts[0] in ("src", "app", "packages", "apps", "lib") and len(parts) > 2:
                # Sub-package under standard source directory (e.g. app/routers, packages/api)
                mod_path = f"{parts[0]}/{parts[1]}"
                mod_name = parts[1]
            else:
                # Top-level directory (e.g. src, routers, tests, docs, config)
                mod_path = parts[0]
                mod_name = parts[0]

            if mod_path not in module_map:
                module_map[mod_path] = ModuleInfo(path=mod_path, name=mod_name)
            module_map[mod_path].files.append(p)

        modules = list(module_map.values())

        # If only root module and no directories, return root module
        for m in modules:
            m.file_count = len(m.files)
            m.entry_points = detect_entry_points_in_files(m.files)
            # Pick key files: entry points first, then others up to 8
            sorted_files = sorted(
                m.files,
                key=lambda f: (
                    0 if f in m.entry_points else 1,
                    0 if Path(f).name.startswith("__init__") else 1,
                    f,
                ),
            )
            m.key_files = sorted_files[:8]

        return modules

    def extract_module_edges(
        self,
        modules: list[ModuleInfo],
        workspace_dir: Path,
    ) -> list[tuple[uuid.UUID, uuid.UUID, int]]:
        """
        Computes directed edges between modules with weights based on parsed imports.
        Falls back to a folder-tree graph (parent to child edges) if no imports exist.
        """
        if len(modules) <= 1:
            return []

        # Mapping of module path prefix to ModuleInfo
        # Sort by path length descending for accurate prefix matching
        sorted_modules = sorted(modules, key=lambda m: len(m.path), reverse=True)

        def find_module_for_path(target_path: str) -> Optional[ModuleInfo]:
            norm_target = target_path.strip("/")
            for m in sorted_modules:
                if m.path == ".":
                    continue
                if norm_target == m.path or norm_target.startswith(f"{m.path}/"):
                    return m
            # If not in sub-module, check root module
            root_m = next((m for m in sorted_modules if m.path == "."), None)
            return root_m

        def find_module_for_python_import(import_name: str) -> Optional[ModuleInfo]:
            dotted = import_name.strip(".")
            slashed = dotted.replace(".", "/")
            for m in sorted_modules:
                if m.path == ".":
                    continue
                # e.g. "app.routers" or "routers" matching module path "app/routers" or "routers"
                m_dotted = m.path.replace("/", ".")
                if dotted == m_dotted or dotted.startswith(f"{m_dotted}."):
                    return m
                # match last part of module path
                if dotted == m.name or dotted.startswith(f"{m.name}."):
                    return m
                if slashed == m.path or slashed.startswith(f"{m.path}/"):
                    return m
            return None

        edge_weights: dict[tuple[uuid.UUID, uuid.UUID], int] = {}

        for mod in modules:
            for rel_file in mod.files:
                file_path = workspace_dir / rel_file
                if not file_path.is_file():
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                ext = file_path.suffix.lower()
                imported_items: list[str] = []

                if ext in (".py", ".pyw"):
                    imported_items = parse_python_imports(content)
                    for imp in imported_items:
                        target_mod = find_module_for_python_import(imp)
                        if target_mod and target_mod.id != mod.id:
                            pair = (mod.id, target_mod.id)
                            edge_weights[pair] = edge_weights.get(pair, 0) + 1

                elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
                    imported_items = parse_js_ts_imports(content)
                    for imp in imported_items:
                        target_mod: Optional[ModuleInfo] = None
                        if imp.startswith("."):
                            # Relative path from current file
                            try:
                                resolved = (file_path.parent / imp).resolve()
                                rel_to_ws = resolved.relative_to(workspace_dir.resolve()).as_posix()
                                target_mod = find_module_for_path(rel_to_ws)
                            except Exception:
                                pass
                        else:
                            # Package or alias import
                            target_mod = find_module_for_path(imp)

                        if target_mod and target_mod.id != mod.id:
                            pair = (mod.id, target_mod.id)
                            edge_weights[pair] = edge_weights.get(pair, 0) + 1

        # Fallback to folder-tree graph when zero imports are detected
        if not edge_weights:
            logger.info("Zero cross-module imports detected; falling back to folder-tree graph")
            # Connect parent to child modules
            for mod in modules:
                for other in modules:
                    if mod.id == other.id:
                        continue
                    if other.path.startswith(f"{mod.path}/") or (mod.path == "." and other.path != "."):
                        # mod is parent of other
                        # Direct parent check: no intermediate module in between
                        intermediate = any(
                            mid.id != mod.id and mid.id != other.id
                            and other.path.startswith(f"{mid.path}/")
                            and mid.path.startswith(f"{mod.path}/")
                            for mid in modules
                        )
                        if not intermediate:
                            edge_weights[(mod.id, other.id)] = 1

            # If still no edges (all siblings, no root module)
            if not edge_weights and len(modules) > 1:
                # Star or sequential graph from the first module
                first = modules[0]
                for other in modules[1:]:
                    edge_weights[(first.id, other.id)] = 1

        return [(src, tgt, w) for (src, tgt), w in edge_weights.items()]

    async def summarize_module(
        self,
        module: ModuleInfo,
        workspace_dir: Path,
    ) -> str:
        """
        Generates a one-paragraph summary for a module using the LLM.
        Uses map-then-reduce for large modules.
        Falls back to a deterministic summary on failure.
        """
        fallback = generate_fallback_summary(
            name=module.name,
            path=module.path,
            file_count=module.file_count,
            key_files=module.key_files,
            entry_points=module.entry_points,
        )

        if not self.provider:
            return fallback

        # Gather sample excerpts
        excerpts: list[str] = []
        for kf in module.key_files[:4]:
            fpath = workspace_dir / kf
            if fpath.is_file():
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")[:600]
                    excerpts.append(f"File {kf}:\n{text}")
                except Exception:
                    pass

        sample_text = "\n\n".join(excerpts)

        try:
            # If large module (>15 files), use map-then-reduce
            if module.file_count > 15:
                # Map step
                chunk_summaries: list[str] = []
                for i in range(0, len(module.key_files), 4):
                    batch_files = module.key_files[i:i + 4]
                    map_prompt = (
                        f"Summarize the technical role of files: {', '.join(batch_files)} "
                        f"in module '{module.name}' in 2 sentences."
                    )
                    map_res = await self.provider.chat([
                        {"role": "system", "content": "You are RepoQuest assistant."},
                        {"role": "user", "content": map_prompt},
                    ], options={"temperature": 0.2})
                    if map_res and map_res.content:
                        chunk_summaries.append(map_res.content.strip())

                reduce_prompt = (
                    f"Combine these file summaries into one cohesive, concise paragraph (under 80 words) "
                    f"describing the architecture and role of the '{module.name}' module ({module.path}):\n"
                    + "\n".join(chunk_summaries)
                )
                reduce_res = await self.provider.chat([
                    {"role": "system", "content": "You are RepoQuest assistant."},
                    {"role": "user", "content": reduce_prompt},
                ], options={"temperature": 0.2})
                if reduce_res and reduce_res.content:
                    return reduce_res.content.strip()

            else:
                prompt = (
                    f"Write a single concise paragraph (under 75 words) summarizing the purpose, architecture, "
                    f"and key components of the '{module.name}' module ({module.path}).\n"
                    f"Files: {', '.join(module.key_files)}\n"
                    f"Entry points: {', '.join(module.entry_points)}\n"
                    f"Code samples:\n{sample_text}"
                )
                messages: list[Msg] = [
                    {
                        "role": "system",
                        "content": "You are RepoQuest. Write one concise factual paragraph about the code module.",
                    },
                    {"role": "user", "content": prompt},
                ]
                res = await self.provider.chat(messages, options={"temperature": 0.2})
                if res and res.content.strip():
                    return res.content.strip()

        except Exception as exc:
            logger.warning("LLM summarization failed for module %s, using fallback: %s", module.name, exc)

        return fallback

    async def build_and_save_module_graph(
        self,
        session: AsyncSession,
        repo: Repository,
        workspace_dir: Path,
    ) -> list[Module]:
        """
        Partitions repository files, computes import graph edges, generates module summaries,
        and saves Module and ModuleEdge records to the database.
        """
        # Discover files in workspace
        all_files: list[Path] = [p for p in workspace_dir.rglob("*") if p.is_file()]
        rel_paths = [p.relative_to(workspace_dir).as_posix() for p in all_files]

        modules = self.partition_files_into_modules(rel_paths)
        if not modules:
            return []

        # Summarize modules one at a time
        for mod in modules:
            mod.summary = await self.summarize_module(mod, workspace_dir)

        # Compute edges
        edges = self.extract_module_edges(modules, workspace_dir)

        # Delete old modules and module_edges for idempotency
        await session.execute(delete(Module).where(Module.repo_id == repo.id))
        await session.flush()

        module_objs: list[Module] = []
        for mod in modules:
            m_obj = Module(
                id=mod.id,
                repo_id=repo.id,
                path=mod.path,
                name=mod.name,
                summary=mod.summary,
                key_files=mod.key_files,
                entry_points=mod.entry_points,
                file_count=mod.file_count,
            )
            module_objs.append(m_obj)

        session.add_all(module_objs)
        await session.flush()

        edge_objs: list[ModuleEdge] = []
        for src_id, tgt_id, weight in edges:
            edge_obj = ModuleEdge(
                repo_id=repo.id,
                source_id=src_id,
                target_id=tgt_id,
                weight=weight,
            )
            edge_objs.append(edge_obj)

        session.add_all(edge_objs)
        await session.commit()

        logger.info(
            "Saved %d modules and %d module edges for repo %s",
            len(module_objs),
            len(edge_objs),
            repo.full_name,
        )
        return module_objs
