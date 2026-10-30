from app.services.chunker import (
    MAX_CHUNK_SIZE,
    chunk_file,
    compute_content_hash,
)


def test_empty_and_binary_skipped():
    # Empty string and whitespace
    assert chunk_file("") == []
    assert chunk_file("   \n\n\t  ") == []
    assert chunk_file(b"") == []
    assert chunk_file(b"   \n  ") == []

    # Binary contents
    assert chunk_file(b"\x00\x01\x02\x03some_binary_data") == []
    assert chunk_file("text with null \x00 byte") == []


def test_ast_line_ranges_are_exact():
    py_code = """import os
import sys

def add(a: int, b: int) -> int:
    \"\"\"Adds two numbers.\"\"\"
    return a + b

class Calculator:
    \"\"\"Simple calculator class.\"\"\"

    def multiply(self, x: int, y: int) -> int:
        return x * y
"""
    chunks = chunk_file(py_code, filename="calc.py")

    assert len(chunks) == 3

    # 1. Imports
    chunk_0 = chunks[0]
    assert chunk_0.start_line == 1
    assert chunk_0.end_line == 2
    assert "import os" in chunk_0.content
    assert chunk_0.content_hash == compute_content_hash(chunk_0.content)

    # 2. Function add
    chunk_1 = chunks[1]
    assert chunk_1.start_line == 4
    assert chunk_1.end_line == 6
    assert "def add(" in chunk_1.content
    assert chunk_1.content_hash == compute_content_hash(chunk_1.content)

    # 3. Class Calculator
    chunk_2 = chunks[2]
    assert chunk_2.start_line == 8
    assert chunk_2.end_line == 12
    assert "class Calculator:" in chunk_2.content
    assert "def multiply(" in chunk_2.content
    assert chunk_2.content_hash == compute_content_hash(chunk_2.content)


def test_overlap_behavior():
    # Create paragraphs of ~350 chars each
    p1 = "Paragraph 1: " + "alpha " * 50 + "\n\n"
    p2 = "Paragraph 2: " + "beta " * 50 + "\n\n"
    p3 = "Paragraph 3: " + "gamma " * 50 + "\n\n"
    p4 = "Paragraph 4: " + "delta " * 50 + "\n\n"

    text = p1 + p2 + p3 + p4
    chunks = chunk_file(text, filename="doc.txt")

    assert len(chunks) >= 2

    # Verify overlap exists between consecutive chunks
    # Chunk 0 should contain p1 and p2; chunk 1 should overlap with p2 or p3
    assert len(chunks[0].content) <= MAX_CHUNK_SIZE
    assert len(chunks[1].content) <= MAX_CHUNK_SIZE

    # Both chunks should have valid start and end lines
    assert chunks[0].start_line <= chunks[0].end_line
    assert chunks[1].start_line <= chunks[1].end_line
    assert chunks[1].start_line <= chunks[0].end_line  # Overlaps in line span or content


def test_size_cap_respected():
    # Continuous text of 3,000 characters without blank lines
    long_line = "word " * 600  # ~3,000 characters
    chunks = chunk_file(long_line, filename="huge.md")

    assert len(chunks) > 1
    for c in chunks:
        assert len(c.content) <= MAX_CHUNK_SIZE
        assert len(c.content_hash) == 64


def test_syntax_error_python_fallback():
    # Python code with intentional syntax error
    invalid_py = """def broken_function(
        this is not valid python !!!
        missing colons and brackets
    """

    chunks = chunk_file(invalid_py, filename="broken.py")

    assert len(chunks) >= 1
    assert "broken_function" in chunks[0].content
    assert chunks[0].start_line == 1
