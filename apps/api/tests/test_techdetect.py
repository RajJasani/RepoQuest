from app.services.techdetect import (
    detect_languages_from_files,
    detect_tech_stack,
    extract_run_instructions,
)


def test_detect_languages_from_files():
    files = [
        "src/main.py",
        "src/utils.py",
        "app/index.ts",
        "app/components/Button.tsx",
        "lib/server.go",
        "backend/main.rs",
        "styles/main.css",
        "public/index.html",
        "README.md",
    ]

    langs = detect_languages_from_files(files)

    assert langs["Python"] == 2
    assert langs["TypeScript"] == 2
    assert langs["Go"] == 1
    assert langs["Rust"] == 1
    assert langs["CSS"] == 1
    assert langs["HTML"] == 1
    assert langs["Markdown"] == 1


def test_detect_tech_stack_manifests():
    # 1. package.json
    pkg_json = """{
        "dependencies": {
            "react": "^18.2.0",
            "next": "^14.0.0",
            "tailwindcss": "^3.3.0"
        },
        "devDependencies": {
            "typescript": "^5.0.0",
            "jest": "^29.0.0"
        }
    }"""
    npm_stack = detect_tech_stack({"package.json": pkg_json})
    assert "React" in npm_stack
    assert "Next.js" in npm_stack
    assert "TailwindCSS" in npm_stack
    assert "TypeScript" in npm_stack
    assert "Jest" in npm_stack

    # 2. requirements.txt
    req_txt = """
    fastapi==0.115.0
    sqlalchemy>=2.0.0
    alembic>=1.13.0
    pydantic>=2.0.0
    pytest>=8.0.0
    """
    py_stack = detect_tech_stack({"requirements.txt": req_txt})
    assert "FastAPI" in py_stack
    assert "SQLAlchemy" in py_stack
    assert "Alembic" in py_stack
    assert "Pydantic" in py_stack
    assert "pytest" in py_stack

    # 3. pyproject.toml
    pyproject = """
    [tool.poetry.dependencies]
    python = "^3.11"
    celery = "^5.3.0"
    redis = "^5.0.0"
    """
    poetry_stack = detect_tech_stack({"pyproject.toml": pyproject})
    assert "Celery" in poetry_stack
    assert "Redis" in poetry_stack

    # 4. pom.xml
    pom_xml = """<project>
        <dependencies>
            <dependency>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-starter-web</artifactId>
            </dependency>
            <dependency>
                <groupId>org.hibernate.orm</groupId>
                <artifactId>hibernate-core</artifactId>
            </dependency>
        </dependencies>
    </project>"""
    maven_stack = detect_tech_stack({"pom.xml": pom_xml})
    assert "Spring Boot" in maven_stack
    assert "Hibernate" in maven_stack

    # 5. go.mod
    go_mod = """module example.com/app

    go 1.22

    require (
        github.com/gin-gonic/gin v1.9.1
        gorm.io/gorm v1.25.7
    )"""
    go_stack = detect_tech_stack({"go.mod": go_mod})
    assert "Gin" in go_stack
    assert "GORM" in go_stack

    # 6. Cargo.toml
    cargo_toml = """[package]
    name = "rust-app"
    version = "0.1.0"

    [dependencies]
    tokio = { version = "1.0", features = ["full"] }
    axum = "0.7"
    serde = { version = "1.0", features = ["derive"] }
    """
    cargo_stack = detect_tech_stack({"Cargo.toml": cargo_toml})
    assert "Tokio" in cargo_stack
    assert "Axum" in cargo_stack
    assert "Serde" in cargo_stack


def test_extract_run_instructions_from_readme():
    readme = """# My Cool Project

Some description here.

## Quickstart

Run the dev server with:

```bash
docker compose up -d
npm run dev
```

## Architecture
Some details.
"""
    instructions = extract_run_instructions(readme_content=readme)
    assert "docker compose up -d" in instructions
    assert "npm run dev" in instructions


def test_extract_run_instructions_from_manifests_fallback():
    # Fallback to package.json
    pkg_json = '{"scripts": {"dev": "next dev"}}'
    inst = extract_run_instructions(readme_content=None, manifests={"package.json": pkg_json})
    assert "npm run dev" in inst

    # Fallback to requirements.txt
    inst_py = extract_run_instructions(readme_content=None, manifests={"requirements.txt": "fastapi"})
    assert "pip install" in inst_py

