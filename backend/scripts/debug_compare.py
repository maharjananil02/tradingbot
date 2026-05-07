"""Debug: compare NABIL (works) vs ADBL (fails)."""
import asyncio
import logging
import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


async def test_stock(symbol):
    import aiohttp
    import ssl

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    conn = aiohttp.TCPConnector(ssl=ssl_ctx)
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    async with aiohttp.ClientSession(connector=conn, timeout=timeout, headers=headers) as session:
        # Step 1: Visit company page
        slug = symbol.lower()
        url = f"https://www.sharesansar.com/company/{slug}"
        print(f"\n{'='*50}")
        print(f"Testing {symbol}: GET {url}")

        async with session.get(url) as resp:
            print(f"  Status: {resp.status}")
            print(f"  Final URL: {resp.url}")
            html = await resp.text()
            
            id_match = re.search(r'id=["\']companyid["\'][^>]*>(\d+)<', html)
            csrf_match = re.search(r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html)
            
            cid = id_match.group(1) if id_match else None
            csrf = csrf_match.group(1) if csrf_match else None
            
            print(f"  Company ID: {cid}")
            print(f"  CSRF: {csrf[:20] if csrf else 'NONE'}...")
            print(f"  Cookie jar: {len(session.cookie_jar)} cookies")

            if not cid:
                # Check if page has the symbol
                if symbol in html:
                    print(f"  Symbol found in page, but no companyid element")
                else:
                    print(f"  Symbol NOT found in page (wrong page?)")
                    # Show title
                    title_match = re.search(r'<title>(.*?)</title>', html)
                    if title_match:
                        print(f"  Page title: {title_match.group(1)}")
                return

        # Step 2: POST for price history
        form_data = {"draw": "1", "start": "0", "length": "3", "company": cid}
        hdrs = {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf,
            "Referer": url,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        
        async with session.post(
            "https://www.sharesansar.com/company-price-history",
            data=form_data,
            headers=hdrs,
        ) as resp:
            print(f"\n  POST Status: {resp.status}")
            text = await resp.text()
            print(f"  Response length: {len(text)}")
            try:
                data = json.loads(text)
                print(f"  recordsTotal: {data.get('recordsTotal')}")
                print(f"  data count: {len(data.get('data', []))}")
                if data.get("data"):
                    print(f"  First record: {data['data'][0]}")
            except Exception as e:
                print(f"  Parse error: {e}")
                print(f"  Raw: {text[:200]}")


async def main():
    for sym in ["NABIL", "ADBL", "NLIC", "SCB"]:
        await test_stock(sym)


asyncio.run(main())
