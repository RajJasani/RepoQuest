from __future__ import annotations

import io
from pathlib import Path
import tarfile
from typing import Optional
import pytest

from app.core.errors import ValidationError
from app.services.archive import (
    MAX_SINGLE_FILE_BYTES,
    extract_tarball_safely,
)


def _create_tarball(files: dict[str, bytes], symlinks: Optional[dict[str, str]] = None) -> bytes:
    """Helper to create an in-memory tarball."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            ti.type = tarfile.REGTYPE
            tar.addfile(ti, io.BytesIO(data))

        if symlinks:
            for name, target in symlinks.items():
                ti = tarfile.TarInfo(name=name)
                ti.type = tarfile.SYMTYPE
                ti.linkname = target
                tar.addfile(ti)

    return buf.getvalue()


def test_safe_tarball_extraction_basic(tmp_path: Path):
    tarball = _create_tarball({
        "owner-repo-commit/src/main.py": b"print('hello world')",
        "owner-repo-commit/README.md": b"# RepoQuest",
    })

    dest = tmp_path / "workspace"
    result = extract_tarball_safely(tarball, dest)

    assert result["extracted_count"] == 2
    assert (dest / "src" / "main.py").exists()
    assert (dest / "src" / "main.py").read_text() == "print('hello world')"
    assert (dest / "README.md").exists()
    assert (dest / "README.md").read_text() == "# RepoQuest"


def test_traversal_rejection_dot_dot(tmp_path: Path):
    tarball = _create_tarball({
        "owner-repo/../escaped.txt": b"evil content",
    })

    with pytest.raises(ValidationError) as exc:
        extract_tarball_safely(tarball, tmp_path)
    assert "path traversal segment '..'" in str(exc.value)


def test_absolute_path_rejection(tmp_path: Path):
    tarball = _create_tarball({
        "/etc/passwd": b"root:x:0:0...",
    })

    with pytest.raises(ValidationError) as exc:
        extract_tarball_safely(tarball, tmp_path)
    assert "prohibited absolute path" in str(exc.value)


def test_symlink_rejection(tmp_path: Path):
    tarball = _create_tarball(
        files={"owner-repo/regular.py": b"# normal code"},
        symlinks={"owner-repo/evil_link": "/etc/passwd"},
    )

    dest = tmp_path / "workspace"
    result = extract_tarball_safely(tarball, dest)

    assert result["extracted_count"] == 1
    assert result["skipped_count"] == 1
    assert (dest / "regular.py").exists()
    assert not (dest / "evil_link").exists()


def test_file_size_limit_300kb(tmp_path: Path):
    oversized = b"a" * (MAX_SINGLE_FILE_BYTES + 100)
    normal = b"b" * 1000

    tarball = _create_tarball({
        "owner-repo/huge.txt": oversized,
        "owner-repo/normal.py": normal,
    })

    dest = tmp_path / "workspace"
    result = extract_tarball_safely(tarball, dest)

    assert result["extracted_count"] == 1
    assert result["skipped_count"] == 1
    assert (dest / "normal.py").exists()
    assert not (dest / "huge.txt").exists()


def test_skip_excluded_folders_lockfiles_and_binaries(tmp_path: Path):
    tarball = _create_tarball({
        "owner-repo/node_modules/lib/index.js": b"console.log('skip');",
        "owner-repo/.git/config": b"[core]\n",
        "owner-repo/build/output.js": b"bundle();",
        "owner-repo/dist/bundle.js": b"bundle();",
        "owner-repo/package-lock.json": b"{}",
        "owner-repo/Cargo.lock": b"lock",
        "owner-repo/image.png": b"\x89PNG\r\n\x1a\nfakeimage",
        "owner-repo/nullbyte.txt": b"some text \x00 with null bytes",
        "owner-repo/app.py": b"def run(): pass",
    })

    dest = tmp_path / "workspace"
    result = extract_tarball_safely(tarball, dest)

    assert result["extracted_count"] == 1
    assert result["skipped_count"] == 8
    assert (dest / "app.py").exists()
    assert not (dest / "node_modules").exists()
    assert not (dest / ".git").exists()
    assert not (dest / "package-lock.json").exists()
    assert not (dest / "image.png").exists()
    assert not (dest / "nullbyte.txt").exists()


def test_total_uncompressed_limit(tmp_path: Path, monkeypatch):
    # Mock limit to 100 bytes for fast test
    monkeypatch.setattr("app.services.archive.MAX_TOTAL_UNCOMPRESSED_BYTES", 100)

    tarball = _create_tarball({
        "owner-repo/file1.py": b"x" * 60,
        "owner-repo/file2.py": b"y" * 60,
    })

    with pytest.raises(ValidationError) as exc:
        extract_tarball_safely(tarball, tmp_path)
    assert "200 MB maximum uncompressed limit" in str(exc.value)
