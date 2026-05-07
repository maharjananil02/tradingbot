"""Debug: call data_fetcher.fetch_price_history directly for ADBL."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")


async def main():
    from services.data_fetcher import data_fetcher

    # Close any existing session
    await data_fetcher.close()

    print("=== Testing data_fetcher.fetch_price_history('ADBL', 5) ===")
    result = await data_fetcher.fetch_price_history("ADBL", 5)
    print(f"Result: {len(result)} records")
    for r in result:
        print(f"  {r}")

    print("\n=== Testing data_fetcher.fetch_price_history('NABIL', 5) ===")
    result2 = await data_fetcher.fetch_price_history("NABIL", 5)
    print(f"Result: {len(result2)} records")
    for r in result2:
        print(f"  {r}")

    await data_fetcher.close()


asyncio.run(main())
