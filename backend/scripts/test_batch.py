"""Minimal test: call fetch_and_save_history for just 3 stocks."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


async def main():
    from models.database import SessionLocal
    from services.data_fetcher import data_fetcher

    db = SessionLocal()
    try:
        symbols = ["ADBL", "NABIL", "NLIC"]
        print(f"Testing fetch_and_save_history with {symbols}")
        saved = await data_fetcher.fetch_and_save_history(db, symbols, days=5)
        print(f"Saved: {saved}")
    finally:
        await data_fetcher.close()
        db.close()


asyncio.run(main())
