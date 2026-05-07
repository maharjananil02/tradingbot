"""Fetch historical price data for actively traded NEPSE stocks.
Targets stocks from the live-trading page that have < 50 days of price data.
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    from models.database import SessionLocal
    from models.tables import Stock, Price
    from services.data_fetcher import data_fetcher
    from sqlalchemy import func

    db = SessionLocal()
    try:
        # Get stocks that have some price data (i.e., actively traded) but < 50 days
        stocks_need_history = (
            db.query(Price.symbol, func.count(Price.id).label("cnt"))
            .group_by(Price.symbol)
            .having(func.count(Price.id) < 50)
            .order_by(func.count(Price.id).desc())
            .all()
        )

        symbols = [s.symbol for s in stocks_need_history]
        logger.info(f"Found {len(symbols)} actively traded stocks needing history")

        if not symbols:
            logger.info("All active stocks have sufficient history!")
            return

        # Process in batches of 30
        batch_size = 30
        total_saved = 0

        for batch_start in range(0, len(symbols), batch_size):
            batch = symbols[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            logger.info(f"\n=== Batch {batch_num}/{total_batches} ({len(batch)} stocks) ===")

            # Close and reopen session between batches to get fresh cookies
            await data_fetcher.close()

            saved = await data_fetcher.fetch_and_save_history(db, batch, days=100)
            total_saved += saved
            logger.info(f"Batch {batch_num} done: saved {saved} records")

        logger.info(f"\n=== TOTAL: Saved {total_saved} historical price records ===")

        # Check stats
        stats = (
            db.query(Price.symbol, func.count(Price.id).label("cnt"))
            .group_by(Price.symbol)
            .having(func.count(Price.id) >= 50)
            .all()
        )
        logger.info(f"Stocks with 50+ days of history: {len(stats)}")

    finally:
        await data_fetcher.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
