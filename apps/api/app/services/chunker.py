from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Optional, Union

TARGET_CHUNK_SIZE = 800
MAX_CHUNK_SIZE = 1000
OVERLAP_SIZE = 100


@dataclass
class Chunk:
    chunk_index: int
    start_line: int
    end_line: int
    content: str
    content_hash: str


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_binary_string_or_bytes(content: Union[str, bytes]) -> bool:
    if isinstance(content, bytes):
        if b"\x00" in content[:1024]:
            return True
        try:
            content.decode("utf-8")
            return False
        except UnicodeDecodeError:
            return True
    return "\x00" in content[:1024]


def _split_oversized_line(line: str, max_size: int) -> list[str]:
    """Splits a single line exceeding max_size into pieces of at most max_size."""
    pieces: list[str] = []
    words = line.split(" ")
    curr_piece: list[str] = []
    curr_len = 0

    for w in words:
        w_len = len(w) + (1 if curr_piece else 0)
        if curr_len + w_len > max_size:
            if curr_piece:
                pieces.append(" ".join(curr_piece))
                curr_piece = []
                curr_len = 0
            if len(w) > max_size:
                for idx in range(0, len(w), max_size):
                    pieces.append(w[idx : idx + max_size])
            else:
                curr_piece.append(w)
                curr_len = len(w)
        else:
            curr_piece.append(w)
            curr_len += w_len

    if curr_piece:
        pieces.append(" ".join(curr_piece))
    return pieces


def _generic_chunk_lines(
    lines: list[str],
    base_line_offset: int = 1,
    target_size: int = TARGET_CHUNK_SIZE,
    max_size: int = MAX_CHUNK_SIZE,
    overlap_size: int = OVERLAP_SIZE,
) -> list[Chunk]:
    """
    Chunks a list of lines using blank-line-aware windows of about target_size chars
    with overlap_size chars overlap. Strictly enforces max_size cap.
    """
    if not lines:
        return []

    # Identify blocks separated by blank lines
    blocks: list[tuple[int, int, str]] = []  # (start_line, end_line, text)
    curr_block_lines: list[str] = []
    curr_block_start = base_line_offset

    for idx, line in enumerate(lines):
        line_no = base_line_offset + idx
        if not line.strip():  # blank line
            if curr_block_lines:
                block_text = "".join(curr_block_lines)
                blocks.append((curr_block_start, line_no - 1, block_text))
                curr_block_lines = []
            curr_block_start = line_no + 1
        else:
            if not curr_block_lines:
                curr_block_start = line_no
            curr_block_lines.append(line)

    if curr_block_lines:
        blocks.append((curr_block_start, base_line_offset + len(lines) - 1, "".join(curr_block_lines)))

    if not blocks:
        # File is all empty/blank lines
        return []

    # If any single block exceeds max_size, split that block by lines/sentences
    sub_blocks: list[tuple[int, int, str]] = []
    for b_start, b_end, b_text in blocks:
        if len(b_text) <= max_size:
            sub_blocks.append((b_start, b_end, b_text))
        else:
            # Split oversized block line-by-line
            b_lines = b_text.splitlines(keepends=True)
            chunk_buf: list[str] = []
            chunk_start = b_start
            curr_len = 0
            for l_idx, bline in enumerate(b_lines):
                cur_line_no = b_start + l_idx
                if len(bline) <= max_size:
                    if curr_len + len(bline) > max_size and chunk_buf:
                        sub_blocks.append((chunk_start, cur_line_no - 1, "".join(chunk_buf)))
                        chunk_buf = [bline]
                        chunk_start = cur_line_no
                        curr_len = len(bline)
                    else:
                        chunk_buf.append(bline)
                        curr_len += len(bline)
                else:
                    if chunk_buf:
                        sub_blocks.append((chunk_start, cur_line_no - 1, "".join(chunk_buf)))
                        chunk_buf = []
                        curr_len = 0
                    pieces = _split_oversized_line(bline, max_size)
                    for p in pieces:
                        sub_blocks.append((cur_line_no, cur_line_no, p))
                    chunk_start = cur_line_no + 1
            if chunk_buf:
                sub_blocks.append((chunk_start, b_end, "".join(chunk_buf)))

    # Now assemble sub_blocks into chunks with target_size and overlap
    chunks: list[Chunk] = []
    i = 0
    chunk_idx = 0

    while i < len(sub_blocks):
        c_start, c_end, c_text = sub_blocks[i]
        curr_text = c_text
        curr_start = c_start
        curr_end = c_end
        next_i = i + 1

        while next_i < len(sub_blocks):
            nxt_start, nxt_end, nxt_text = sub_blocks[next_i]
            if len(curr_text) + len(nxt_text) <= max_size:
                curr_text += "\n\n" + nxt_text
                curr_end = nxt_end
                next_i += 1
                if len(curr_text) >= target_size:
                    break
            else:
                break

        chunks.append(
            Chunk(
                chunk_index=chunk_idx,
                start_line=curr_start,
                end_line=curr_end,
                content=curr_text,
                content_hash=compute_content_hash(curr_text),
            )
        )
        chunk_idx += 1

        # Calculate overlap for next iteration
        if next_i >= len(sub_blocks):
            break

        # Move forward, but step back if overlap is possible
        overlap_acc = 0
        back_i = next_i - 1
        while back_i > i:
            overlap_acc += len(sub_blocks[back_i][2])
            if overlap_acc >= overlap_size:
                break
            back_i -= 1

        i = max(i + 1, back_i)

    return chunks


def _ast_chunk_python(text: str) -> list[Chunk]:
    """Chunks Python files by function and class using the standard ast module."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Fall back to generic chunker on syntax errors
        return _generic_chunk_lines(text.splitlines(keepends=True))

    lines = text.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    chunks: list[Chunk] = []
    chunk_index = 0

    # Collect top-level definitions and standalone blocks
    nodes: list[ast.AST] = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    if not nodes:
        # No functions or classes -> generic chunker
        return _generic_chunk_lines(lines)

    # Sort nodes by start line
    def get_node_range(node: ast.AST) -> tuple[int, int]:
        start = node.lineno
        if hasattr(node, "decorator_list") and node.decorator_list:
            dec_starts = [d.lineno for d in node.decorator_list if hasattr(d, "lineno")]
            if dec_starts:
                start = min(start, min(dec_starts))
        end = getattr(node, "end_lineno", node.lineno)
        return start, end

    nodes.sort(key=lambda n: get_node_range(n)[0])

    last_covered_line = 0

    for node in nodes:
        start_line, end_line = get_node_range(node)

        # 1. Any code between last node and this node (e.g. imports, global constants)
        if start_line > last_covered_line + 1:
            gap_lines = lines[last_covered_line : start_line - 1]
            gap_text = "".join(gap_lines).strip()
            if gap_text:
                gap_chunks = _generic_chunk_lines(gap_lines, base_line_offset=last_covered_line + 1)
                for gc in gap_chunks:
                    chunks.append(
                        Chunk(
                            chunk_index=chunk_index,
                            start_line=gc.start_line,
                            end_line=gc.end_line,
                            content=gc.content,
                            content_hash=compute_content_hash(gc.content),
                        )
                    )
                    chunk_index += 1

        # 2. Node content
        node_lines = lines[start_line - 1 : end_line]
        node_content = "".join(node_lines)

        if len(node_content) <= MAX_CHUNK_SIZE:
            chunks.append(
                Chunk(
                    chunk_index=chunk_index,
                    start_line=start_line,
                    end_line=end_line,
                    content=node_content,
                    content_hash=compute_content_hash(node_content),
                )
            )
            chunk_index += 1
        else:
            # If a class or function exceeds MAX_CHUNK_SIZE, sub-chunk its inner body
            sub_chunks = _generic_chunk_lines(node_lines, base_line_offset=start_line)
            for sc in sub_chunks:
                chunks.append(
                    Chunk(
                        chunk_index=chunk_index,
                        start_line=sc.start_line,
                        end_line=sc.end_line,
                        content=sc.content,
                        content_hash=compute_content_hash(sc.content),
                    )
                )
                chunk_index += 1

        last_covered_line = max(last_covered_line, end_line)

    # 3. Any trailing code after the last node
    if last_covered_line < total_lines:
        trailing_lines = lines[last_covered_line:]
        trailing_text = "".join(trailing_lines).strip()
        if trailing_text:
            trail_chunks = _generic_chunk_lines(trailing_lines, base_line_offset=last_covered_line + 1)
            for tc in trail_chunks:
                chunks.append(
                    Chunk(
                        chunk_index=chunk_index,
                        start_line=tc.start_line,
                        end_line=tc.end_line,
                        content=tc.content,
                        content_hash=compute_content_hash(tc.content),
                    )
                )
                chunk_index += 1

    return chunks


def chunk_file(
    content: Union[str, bytes],
    filename: Optional[str] = None,
) -> list[Chunk]:
    """
    Chunks a file's content based on file type and PRD §6 rules:
    - Empty and whitespace-only files are skipped (return []).
    - Binary files are skipped (return []).
    - Python files are chunked by function and class using standard ast module with exact line numbers.
    - Other text files use blank-line-aware windows of ~800 chars with ~100 chars overlap.
    - No chunk may exceed MAX_CHUNK_SIZE (1000 chars).
    - Every chunk receives a SHA-256 content_hash.
    """
    if not content:
        return []

    if is_binary_string_or_bytes(content):
        return []

    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return []
    else:
        text = content

    if not text.strip():
        return []

    ext = Path(filename).suffix.lower() if filename else ""

    if ext == ".py":
        return _ast_chunk_python(text)

    lines = text.splitlines(keepends=True)
    return _generic_chunk_lines(lines)
