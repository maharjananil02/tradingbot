"""Fetch historical price data for top NEPSE stocks from ShareSansar.
Run this once to populate the database with enough history for signal generation.
"""
import asyncio
import logging
import sys
import os

# Add parent dir to path
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
        # Step 1: Ensure stocks are loaded
        stock_count = db.query(Stock).count()
        if stock_count == 0:
            logger.info("No stocks in DB. Fetching stock list...")
            stocks_data = await data_fetcher.fetch_all_stocks()
            if stocks_data:
                data_fetcher.save_stocks(db, stocks_data)
                logger.info(f"Saved {len(stocks_data)} stocks")
            stock_count = db.query(Stock).count()

        # Step 2: Find stocks needing history (less than 50 days)
        stocks_need_history = (
            db.query(Stock.symbol, func.count(Price.id).label("cnt"))
            .outerjoin(Price, Stock.symbol == Price.symbol)
            .group_by(Stock.symbol)
            .having(func.count(Price.id) < 50)
            .order_by(func.count(Price.id).asc())
            .all()
        )

        symbols = [s.symbol for s in stocks_need_history]
        logger.info(f"Found {len(symbols)} stocks needing history (out of {stock_count} total)")

        if not symbols:
            logger.info("All stocks have sufficient history!")
            return

        # Step 3: Fetch history in batches
        # Limit to top 50 to avoid too many requests
        batch = symbols[:50]
        logger.info(f"Fetching 100-day history for {len(batch)} stocks...")

        total = await data_fetcher.fetch_and_save_history(db, batch, days=100)
        logger.info(f"Done! Saved {total} new price records")

        # Step 4: Check stats
        stats = (
            db.query(Stock.symbol, func.count(Price.id).label("cnt"))
            .outerjoin(Price, Stock.symbol == Price.symbol)
            .group_by(Stock.symbol)
            .having(func.count(Price.id) >= 50)
            .all()
        )
        logger.info(f"Stocks with 50+ days of history: {len(stats)}")

    finally:
        await data_fetcher.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
