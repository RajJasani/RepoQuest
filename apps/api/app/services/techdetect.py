from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Optional

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
}


def detect_languages_from_files(file_paths: list[str]) -> dict[str, int]:
    """
    Detects programming languages and counts occurrences across a list of file paths.
    """
    counts: dict[str, int] = {}
    for fp in file_paths:
        ext = Path(fp).suffix.lower()
        lang = EXTENSION_LANGUAGE_MAP.get(ext)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return counts


def _detect_npm_stack(package_json_str: str) -> list[str]:
    stack = ["Node.js"]
    try:
        data = json.loads(package_json_str)
    except Exception:
        return stack

    deps: dict[str, Any] = {}
    if isinstance(data, dict):
        deps.update(data.get("dependencies", {}))
        deps.update(data.get("devDependencies", {}))

    dep_keys = {k.lower() for k in deps.keys()}

    npm_rules = {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue.js",
        "@angular/core": "Angular",
        "svelte": "Svelte",
        "express": "Express",
        "@nestjs/core": "NestJS",
        "fastify": "Fastify",
        "tailwindcss": "TailwindCSS",
        "prisma": "Prisma",
        "@prisma/client": "Prisma",
        "vite": "Vite",
        "webpack": "Webpack",
        "graphql": "GraphQL",
        "typescript": "TypeScript",
        "jest": "Jest",
        "vitest": "Vitest",
    }

    for dep_key, name in npm_rules.items():
        if dep_key in dep_keys:
            stack.append(name)

    return stack


def _detect_python_stack(content: str) -> list[str]:
    stack = ["Python"]
    content_lower = content.lower()

    py_rules = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "sqlalchemy": "SQLAlchemy",
        "alembic": "Alembic",
        "pydantic": "Pydantic",
        "torch": "PyTorch",
        "tensorflow": "TensorFlow",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "celery": "Celery",
        "redis": "Redis",
        "httpx": "HTTPX",
        "pytest": "pytest",
    }

    for keyword, name in py_rules.items():
        if re.search(rf"\b{re.escape(keyword)}\b", content_lower):
            stack.append(name)

    return stack


def _detect_maven_stack(pom_xml: str) -> list[str]:
    stack = ["Java", "Maven"]
    content_lower = pom_xml.lower()

    if "spring-boot" in content_lower:
        stack.append("Spring Boot")
    elif "springframework" in content_lower:
        stack.append("Spring")
    if "hibernate" in content_lower:
        stack.append("Hibernate")
    if "junit" in content_lower:
        stack.append("JUnit")

    return stack


def _detect_go_stack(go_mod: str) -> list[str]:
    stack = ["Go"]
    content_lower = go_mod.lower()

    if "gin-gonic/gin" in content_lower:
        stack.append("Gin")
    if "gofiber/fiber" in content_lower:
        stack.append("Fiber")
    if "labstack/echo" in content_lower:
        stack.append("Echo")
    if "gorm.io/gorm" in content_lower:
        stack.append("GORM")

    return stack


def _detect_cargo_stack(cargo_toml: str) -> list[str]:
    stack = ["Rust", "Cargo"]
    content_lower = cargo_toml.lower()

    if "tokio" in content_lower:
        stack.append("Tokio")
    if "actix-web" in content_lower:
        stack.append("Actix Web")
    if "axum" in content_lower:
        stack.append("Axum")
    if "serde" in content_lower:
        stack.append("Serde")
    if "diesel" in content_lower:
        stack.append("Diesel")
    if "sqlx" in content_lower:
        stack.append("SQLx")

    return stack


def detect_tech_stack(manifests: dict[str, str]) -> list[str]:
    """
    Detects technology stack frameworks and tools from repository manifest files.
    """
    detected: list[str] = []

    for name, content in manifests.items():
        base_name = Path(name).name.lower()
        if base_name == "package.json":
            detected.extend(_detect_npm_stack(content))
        elif base_name in ("requirements.txt", "pyproject.toml", "pipfile"):
            detected.extend(_detect_python_stack(content))
        elif base_name == "pom.xml":
            detected.extend(_detect_maven_stack(content))
        elif base_name == "go.mod":
            detected.extend(_detect_go_stack(content))
        elif base_name == "cargo.toml":
            detected.extend(_detect_cargo_stack(content))

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for item in detected:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


README_SECTION_PATTERN = re.compile(
    r"(?i)^#{1,3}\s*(quick\s*start|getting\s*started|how\s*to\s*run|running|run|installation|development|setup|usage)\b.*$",
    re.MULTILINE,
)


def extract_run_instructions(
    readme_content: Optional[str] = None,
    manifests: Optional[dict[str, str]] = None,
) -> str:
    """
    Extracts run instructions from the README or infers them from manifest files.
    """
    if readme_content:
        # Look for relevant section in README
        matches = list(README_SECTION_PATTERN.finditer(readme_content))
        if matches:
            first_match = matches[0]
            start_pos = first_match.start()
            # Capture up to next same/higher heading or 2000 chars
            remainder = readme_content[start_pos:]
            next_heading = re.search(r"\n#{1,2}\s+[A-Za-z0-9]", remainder[len(first_match.group(0)) :])
            if next_heading:
                section_text = remainder[: len(first_match.group(0)) + next_heading.start()].strip()
            else:
                section_text = remainder[:2000].strip()
            if section_text:
                return section_text

    # Fallback to manifest-based inference
    if manifests:
        for name, content in manifests.items():
            base_name = Path(name).name.lower()
            if base_name == "package.json":
                try:
                    data = json.loads(content)
                    scripts = data.get("scripts", {})
                    if "dev" in scripts:
                        return "npm install\nnpm run dev"
                    if "start" in scripts:
                        return "npm install\nnpm start"
                except Exception:
                    pass
                return "npm install\nnpm start"

            if base_name == "requirements.txt":
                return "pip install -r requirements.txt\npython main.py"

            if base_name == "pyproject.toml":
                return "poetry install\npoetry run python main.py"

            if base_name == "cargo.toml":
                return "cargo run"

            if base_name == "go.mod":
                return "go run ."

            if base_name == "pom.xml":
                return "mvn clean install\nmvn spring-boot:run"

    return "Refer to project documentation for run instructions."

