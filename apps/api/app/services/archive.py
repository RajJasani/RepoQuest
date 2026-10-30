from __future__ import annotations

import io
import logging
import os
from pathlib import Path
import tarfile
from typing import Any, Union

from app.core.errors import ValidationError

logger = logging.getLogger("app.services.archive")

MAX_TOTAL_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB
MAX_SINGLE_FILE_BYTES = 300 * 1024  # 300 KB

# Folders to skip
SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "out",
    "target",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".gradle",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
}

# Lock files to skip
SKIP_LOCK_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "pipfile.lock",
    "composer.lock",
    "gemfile.lock",
    "flake.lock",
}

# Binary extensions to skip
BINARY_EXTENSIONS = {
    # Images & media
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".tiff",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flv",
    # Documents & archives
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    # Executables & libraries
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".msi",
    ".jar", ".war", ".class", ".pyc", ".pyo", ".pyd", ".whl",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Databases & data
    ".sqlite", ".db", ".parquet", ".arrow",
}


def is_binary_file(filename: str, content_prefix: bytes = b"") -> bool:
    """Checks if a file is binary by extension or null-byte probe."""
    ext = Path(filename).suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True
    if b"\x00" in content_prefix[:1024]:
        return True
    return False


def should_skip_member(rel_path: Path) -> tuple[bool, str]:
    """Determines whether a member path should be excluded according to PRD §6 rules."""
    parts = rel_path.parts

    # Check directory components
    for part in parts[:-1]:
        if part.lower() in SKIP_DIR_NAMES:
            return True, f"directory '{part}' in skip list"

    # Check filename
    filename = parts[-1].lower()
    if filename in SKIP_LOCK_FILES:
        return True, f"lock file '{filename}'"

    ext = rel_path.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True, f"binary extension '{ext}'"

    return False, ""


def extract_tarball_safely(
    tarball_data: Union[bytes, io.BytesIO, Path, str],
    destination_dir: Union[Path, str],
) -> dict[str, Any]:
    """
    Safely extracts a repository tarball into destination_dir.
    Enforces security boundaries from PRD §6 (F1) and §14:
    - Rejects absolute paths and '..' path traversal segments.
    - Skips symlinks and hardlinks.
    - Enforces 200 MB total uncompressed limit.
    - Skips individual files over 300 KB.
    - Skips node_modules, .git, build folders, binaries, and lock files.
    - Strips common top-level prefix if present (GitHub tarball structure).
    """
    dest_path = Path(destination_dir).resolve()
    dest_path.mkdir(parents=True, exist_ok=True)

    if isinstance(tarball_data, (bytes, bytearray)):
        fileobj = io.BytesIO(tarball_data)
        tar = tarfile.open(fileobj=fileobj, mode="r:*")
    elif isinstance(tarball_data, io.BytesIO):
        tar = tarfile.open(fileobj=tarball_data, mode="r:*")
    else:
        tar = tarfile.open(name=str(tarball_data), mode="r:*")

    try:
        members = tar.getmembers()
        if not members:
            return {"extracted_count": 0, "skipped_count": 0, "total_bytes": 0, "files": []}

        # 1. Path traversal and absolute path validation
        for m in members:
            # Check raw member name
            raw_name = m.name
            if raw_name.startswith("/") or os.path.isabs(raw_name):
                raise ValidationError(
                    f"Archive contains prohibited absolute path: {raw_name}",
                    details={"path": raw_name},
                )
            # Check '..' segments
            parts = Path(raw_name).parts
            if ".." in parts:
                raise ValidationError(
                    f"Archive contains path traversal segment '..': {raw_name}",
                    details={"path": raw_name},
                )

        # 2. Determine top-level prefix to strip (e.g. owner-repo-sha/)
        first_parts = [Path(m.name).parts[0] for m in members if Path(m.name).parts]
        common_prefix = ""
        if first_parts and all(p == first_parts[0] for p in first_parts):
            common_prefix = first_parts[0]

        extracted_files: list[str] = []
        skipped_count = 0
        total_uncompressed_bytes = 0

        for m in members:
            # Skip symlinks and hardlinks
            if m.issym() or m.islnk():
                logger.debug("Skipping symlink/link member: %s", m.name)
                skipped_count += 1
                continue

            # Strip common prefix
            rel_parts = Path(m.name).parts
            if common_prefix and len(rel_parts) > 1 and rel_parts[0] == common_prefix:
                clean_rel_path = Path(*rel_parts[1:])
            elif common_prefix and len(rel_parts) == 1 and rel_parts[0] == common_prefix:
                # Top level directory itself
                continue
            else:
                clean_rel_path = Path(*rel_parts)

            # Skip directories from extraction loop (they will be created on demand)
            if m.isdir():
                continue

            # Check skip rules (folders, lock files, binary extensions)
            should_skip, reason = should_skip_member(clean_rel_path)
            if should_skip:
                logger.debug("Skipping %s: %s", m.name, reason)
                skipped_count += 1
                continue

            # Check individual file size limit (300 KB)
            if m.size > MAX_SINGLE_FILE_BYTES:
                logger.info("Skipping large file %s (%d bytes > 300 KB limit)", m.name, m.size)
                skipped_count += 1
                continue

            # Check total uncompressed size limit (200 MB)
            if total_uncompressed_bytes + m.size > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ValidationError(
                    "Archive extraction exceeded 200 MB maximum uncompressed limit",
                    details={"limit_bytes": MAX_TOTAL_UNCOMPRESSED_BYTES},
                )

            # Target destination check (defense in depth against escaping dest_path)
            target_file_path = (dest_path / clean_rel_path).resolve()
            if not str(target_file_path).startswith(str(dest_path)):
                raise ValidationError(
                    f"Resolved path escapes target directory: {clean_rel_path}",
                    details={"target": str(target_file_path)},
                )

            # Extract content and probe for binary content
            file_data = tar.extractfile(m)
            if file_data is None:
                continue

            content = file_data.read()

            if is_binary_file(str(clean_rel_path), content):
                logger.debug("Skipping binary content file: %s", m.name)
                skipped_count += 1
                continue

            # Write file safely
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            target_file_path.write_bytes(content)

            total_uncompressed_bytes += len(content)
            extracted_files.append(str(clean_rel_path))

        return {
            "extracted_count": len(extracted_files),
            "skipped_count": skipped_count,
            "total_bytes": total_uncompressed_bytes,
            "files": extracted_files,
        }

    finally:
        tar.close()
