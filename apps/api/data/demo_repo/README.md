# TaskBoard

TaskBoard is a lightweight, modular task management application with a REST API backend and a simple client dashboard.

## Features

- **Authentication:** User registration, password hashing, and token-based session verification.
- **Task Management:** Create, update, filter, assign, and track status across backlog, in-progress, and completed states.
- **REST API:** Clean route structure with modular endpoints for auth and tasks.
- **Client Dashboard:** Vanilla JavaScript single-page client for managing tasks interactively.

## Tech Stack

- **Backend:** Python 3.10+, SQLite database
- **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3

## Run Instructions

### 1. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize Database & Run Migrations
```bash
python cli.py init-db
```

### 3. Start the Server
```bash
python main.py
```
The server will start on `http://127.0.0.1:8000`.

### 4. Running Tests
```bash
python -m unittest discover -s tests
```

