"""Debug: test price history fetch for NABIL specifically."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")


async def main():
    from services.data_fetcher import data_fetcher

    # Test 1: Get company ID and CSRF for NABIL
    print("=== Test: _get_company_id_and_csrf for NABIL ===")
    cid, csrf = await data_fetcher._get_company_id_and_csrf("NABIL")
    print(f"Company ID: {cid}, CSRF: {csrf[:30] if csrf else 'NONE'}...")

    # Test 2: Fetch price history
    print("\n=== Test: fetch_price_history for NABIL ===")
    history = await data_fetcher.fetch_price_history("NABIL", 5)
    print(f"Records: {len(history)}")
    for rec in history:
        print(f"  {rec['date']}: O={rec['open']} H={rec['high']} L={rec['low']} C={rec['close']} V={rec['volume']}")

    # Test 3: Debug the actual POST response
    print("\n=== Debug: raw POST response ===")
    import aiohttp
    session = await data_fetcher._get_session()
    
    # First visit company page to establish cookies
    async with session.get("https://www.sharesansar.com/company/nabil") as resp:
        html = await resp.text()
        import re
        csrf2 = re.search(r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html)
        csrf_val = csrf2.group(1) if csrf2 else "NONE"
        print(f"CSRF from page: {csrf_val[:30]}...")
        print(f"Cookies in jar: {list(session.cookie_jar)}")

    # Then POST
    form_data = {"draw": "1", "start": "0", "length": "5", "company": "16"}
    hdrs = {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-Token": csrf_val,
        "Referer": "https://www.sharesansar.com/company/nabil",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    async with session.post("https://www.sharesansar.com/company-price-history", data=form_data, headers=hdrs) as resp:
        print(f"Status: {resp.status}")
        text = await resp.text()
        print(f"Response: {text[:500]}")

    await data_fetcher.close()


asyncio.run(main())
