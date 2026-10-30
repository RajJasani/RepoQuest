import fnmatch
from pathlib import Path
import re

# File patterns that should never be sent to the LLM
SKIP_FILE_PATTERNS = [
    ".env*",
    "*.pem",
    "*.key",
]

SECRET_PATTERNS = [
    # GitHub Tokens
    re.compile(r"\b(ghp_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9_]{20,}|ghu_[A-Za-z0-9_]{20,}|ghs_[A-Za-z0-9_]{20,}|ghr_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    # Bearer Tokens
    re.compile(r"Bearer\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE),
    # OpenAI and OpenAI-like keys
    re.compile(r"\b(sk-[A-Za-z0-9\-_]{20,}|sk-proj-[A-Za-z0-9\-_]{20,})\b"),
    # Google API Keys
    re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b"),
    # Slack Tokens
    re.compile(r"\b(xox[baprs]-[0-9A-Za-z\-]{10,48})\b"),
    # AWS Access Key IDs
    re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    # Private Key blocks
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+)?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z0-9 ]+)?PRIVATE KEY-----"),
]


def should_skip_file(file_path: str) -> bool:
    """Returns True if the file name matches patterns for sensitive files (.env*, *.pem, *.key)."""
    name = Path(file_path).name.lower()
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in SKIP_FILE_PATTERNS)


def redact_secrets(text: str) -> str:
    """Redacts common credentials, tokens, and private keys from the input text."""
    if not text:
        return text

    redacted = text
    for pattern in SECRET_PATTERNS:
        # Special case Bearer to preserve the word Bearer
        if "bearer" in pattern.pattern.lower():
            redacted = pattern.sub("Bearer [REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)

    return redacted


def sanitize_prompt(text: str) -> str:
    """Alias for redact_secrets to sanitize prompt context."""
    return redact_secrets(text)
