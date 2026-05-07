"""Fetch historical price data for actively traded NEPSE stocks."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    from models.database import SessionLocal
    from models.tables import Price
    from services.data_fetcher import data_fetcher
    from sqlalchemy import func

    db = SessionLocal()
    try:
        # Get stocks that have price data but < 50 days
        stocks_need = (
            db.query(Price.symbol, func.count(Price.id).label("cnt"))
            .group_by(Price.symbol)
            .having(func.count(Price.id) < 50)
            .order_by(func.count(Price.id).desc())
            .limit(50)
            .all()
        )
        symbols = [s.symbol for s in stocks_need]
        logger.info(f"Fetching history for {len(symbols)} stocks...")

        # Directly call fetch_and_save_history (no close() call beforehand)
        saved = await data_fetcher.fetch_and_save_history(db, symbols, days=100)
        logger.info(f"Done! Saved {saved} records")

        # Check result
        ready = (
            db.query(Price.symbol, func.count(Price.id).label("cnt"))
            .group_by(Price.symbol)
            .having(func.count(Price.id) >= 50)
            .all()
        )
        logger.info(f"Stocks with 50+ days of history: {len(ready)}")

    finally:
        await data_fetcher.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
