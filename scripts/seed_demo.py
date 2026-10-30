#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys

# Ensure apps/api is in sys.path
api_dir = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from app.core.db import get_sessionmaker
from app.routers.system import get_provider
from app.services.demo import load_demo_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed_demo")


async def main():
    logger.info("Seeding demo repository demo/taskboard...")
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        provider = await get_provider(session)
        res = await load_demo_data(session=session, provider=provider)
        print("=" * 60)
        print("DEMO REPOSITORY SEED COMPLETED")
        print(f"Repository: {res['full_name']} (Status: {res['status']})")
        print(f"Files: {res['files_count']}")
        print(f"Chunks: {res['chunks_count']}")
        print(f"Issues: {res['issues_count']}")
        print(f"Pull Requests: {res['prs_count']}")
        print(f"Duration: {res['duration_seconds']}s")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
