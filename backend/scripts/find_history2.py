"""Fetch historical price data from ShareSansar price history tab."""
import ssl
import re
import json
import sys
from urllib.request import Request, urlopen

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
    "X-Requested-With": "XMLHttpRequest",
}

# ShareSansar uses AJAX to load price history via a separate endpoint
# Let's try the known pattern: /api/merolagani/priceHistory/{symbol}
test_urls = [
    "https://www.sharesansar.com/company/price-history/NABIL",
    "https://www.sharesansar.com/api/priceHistory?symbol=NABIL",
    "https://www.sharesansar.com/stock/price-history?symbol=NABIL",
]

for url in test_urls:
    try:
        req = Request(url, headers=headers)
        r = urlopen(req, context=ssl_ctx, timeout=10)
        data = r.read()
        print(f"OK {url}")
        print(f"  Length: {len(data)}")
        print(f"  Content: {data[:300].decode('utf-8', errors='replace')}")
    except Exception as e:
        print(f"FAIL {url} -> {e}")
    print()

# Now try fetching the company page and look for data-loading JS
print("=== Checking company page scripts ===")
url = "https://www.sharesansar.com/company/nabil"
req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
r = urlopen(req, context=ssl_ctx, timeout=15)
html = r.read().decode("utf-8", errors="replace")

# Look for price-history related JavaScript
for match in re.finditer(r'(price[_-]?history|priceHistory|price_hist)', html, re.I):
    start = max(0, match.start() - 200)
    end = min(len(html), match.end() + 200)
    context = html[start:end].replace('\n', ' ').strip()
    print(f"\nFound '{match.group()}' context:")
    print(f"  ...{context}...")
