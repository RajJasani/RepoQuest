"""Command line interface for TaskBoard management."""

import sys
from db.session import get_db_connection, init_db
from tasks.service import TaskService


def print_help():
    print("Usage: python cli.py [init-db | list-tasks | help]")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "init-db":
        print("Initializing database tables...")
        init_db()
        print("Done.")
    elif cmd == "list-tasks":
        conn = get_db_connection()
        service = TaskService(conn)
        tasks = service.list_tasks()
        print(f"Found {len(tasks)} tasks:")
        for t in tasks:
            print(f"- [{t.status}] #{t.id}: {t.title}")
    else:
        print_help()


if __name__ == "__main__":
    main()

