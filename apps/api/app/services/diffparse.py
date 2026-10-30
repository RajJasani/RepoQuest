from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Optional


@dataclass
class ParsedHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)
    valid_new_lines: set[int] = field(default_factory=set)


@dataclass
class ParsedFileDiff:
    path: str
    old_path: Optional[str] = None
    is_binary: bool = False
    is_deleted: bool = False
    is_created: bool = False
    patch: str = ""
    hunks: list[ParsedHunk] = field(default_factory=list)
    valid_lines: set[int] = field(default_factory=set)
    added_lines_count: int = 0
    deleted_lines_count: int = 0

    @property
    def changed_lines(self) -> int:
        return self.added_lines_count + self.deleted_lines_count


HUNK_HEADER_REGEX = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)")


def _clean_path(path: str) -> str:
    path = path.strip()
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def parse_unified_diff(diff_text: str) -> list[ParsedFileDiff]:
    """
    Parses a unified diff into a list of ParsedFileDiff objects,
    extracting files, hunks, added/deleted line counts, and valid new-side line numbers.
    """
    if not diff_text or not diff_text.strip():
        return []

    lines = diff_text.splitlines()
    files: list[ParsedFileDiff] = []
    
    current_file: Optional[ParsedFileDiff] = None
    current_hunk: Optional[ParsedHunk] = None
    file_patch_lines: list[str] = []

    def finalize_file():
        nonlocal current_file, current_hunk, file_patch_lines
        if current_file:
            if current_hunk:
                current_file.hunks.append(current_hunk)
                current_file.valid_lines.update(current_hunk.valid_new_lines)
                current_hunk = None
            current_file.patch = "\n".join(file_patch_lines).strip()
            files.append(current_file)
            current_file = None
            file_patch_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for diff header: diff --git a/path b/path
        if line.startswith("diff --git "):
            finalize_file()
            parts = line.split(" ")
            old_p = _clean_path(parts[2]) if len(parts) > 2 else "unknown"
            new_p = _clean_path(parts[3]) if len(parts) > 3 else old_p
            current_file = ParsedFileDiff(path=new_p, old_path=old_p)
            file_patch_lines = [line]
            i += 1
            continue

        if current_file is None:
            # Standalone unified diff without diff --git
            if line.startswith("--- "):
                current_file = ParsedFileDiff(path="")
                file_patch_lines = [line]
            else:
                i += 1
                continue

        file_patch_lines.append(line)

        # Check file modes and metadata
        if line.startswith("--- "):
            raw = line[4:].strip()
            if raw == "/dev/null":
                current_file.is_created = True
            else:
                current_file.old_path = _clean_path(raw)
        elif line.startswith("+++ "):
            raw = line[4:].strip()
            if raw == "/dev/null":
                current_file.is_deleted = True
                if not current_file.path and current_file.old_path:
                    current_file.path = current_file.old_path
            else:
                current_file.path = _clean_path(raw)
        elif line.startswith("Binary files ") or "GIT binary patch" in line:
            current_file.is_binary = True

        # Check hunk header
        match = HUNK_HEADER_REGEX.match(line)
        if match:
            if current_hunk:
                current_file.hunks.append(current_hunk)
                current_file.valid_lines.update(current_hunk.valid_new_lines)

            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) is not None else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) is not None else 1

            current_hunk = ParsedHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                lines=[],
                valid_new_lines=set(),
            )

            current_new_line = new_start
            current_old_line = old_start

            i += 1
            # Read hunk content lines
            while i < len(lines):
                hunk_line = lines[i]
                if hunk_line.startswith("diff --git ") or HUNK_HEADER_REGEX.match(hunk_line):
                    # Next file or next hunk
                    break

                file_patch_lines.append(hunk_line)
                current_hunk.lines.append(hunk_line)

                if hunk_line.startswith("+"):
                    # Added line on the new side
                    current_hunk.valid_new_lines.add(current_new_line)
                    current_file.added_lines_count += 1
                    current_new_line += 1
                elif hunk_line.startswith("-"):
                    # Deleted line on old side
                    current_file.deleted_lines_count += 1
                    current_old_line += 1
                elif hunk_line.startswith(" "):
                    # Context line present on both sides
                    current_hunk.valid_new_lines.add(current_new_line)
                    current_new_line += 1
                    current_old_line += 1
                elif hunk_line.startswith("\\"):
                    # \ No newline at end of file
                    pass
                else:
                    # In case of malformed diff line, advance cautiously
                    break

                i += 1
            continue

        i += 1

    finalize_file()
    return files
