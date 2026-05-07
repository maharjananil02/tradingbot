"""Test full response format and get all company IDs."""
import ssl
import re
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# 1. Get full response structure for one stock  
url = "https://www.sharesansar.com/company/nabil"
req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
r = urlopen(req, context=ssl_ctx, timeout=20)
html = r.read().decode("utf-8", errors="replace")

csrf = re.search(r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html).group(1)
cookies = {}
cookie_header = r.getheader("Set-Cookie")
if cookie_header:
    for part in cookie_header.split(","):
        m = re.match(r'\s*([^=]+)=([^;]+)', part.strip())
        if m:
            cookies[m.group(1)] = m.group(2)

data = urlencode({
    "draw": "1",
    "start": "0",
    "length": "5",
    "company": "16",
}).encode()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "X-CSRF-Token": csrf,
    "Referer": url,
    "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
}

req2 = Request("https://www.sharesansar.com/company-price-history", data=data, headers=headers)
r2 = urlopen(req2, context=ssl_ctx, timeout=15)
result = json.loads(r2.read().decode("utf-8"))

print("=== RESPONSE STRUCTURE ===")
print(f"Keys: {list(result.keys())}")
print(f"Total records: {result['recordsTotal']}")
print(f"Data entries: {len(result['data'])}")
if result['data']:
    print(f"\nFirst record keys: {list(result['data'][0].keys())}")
    for rec in result['data']:
        print(json.dumps(rec, indent=2))

# 2. Now get the today-share-price page and extract company IDs
print("\n\n=== EXTRACTING COMPANY IDs FROM TODAY-SHARE-PRICE ===")
url2 = "https://www.sharesansar.com/today-share-price"
req3 = Request(url2, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
r3 = urlopen(req3, context=ssl_ctx, timeout=20)
html2 = r3.read().decode("utf-8", errors="replace")

# Look for company links with IDs
# Pattern: <a href="/company/symbol">SYMBOL</a>
# We need the numeric ID from the company page
# Check if today-share-price has any numeric IDs embedded
company_links = re.findall(r'<a[^>]*href=["\'](?:https?://www\.sharesansar\.com)?/company/([^"\']+)["\'][^>]*>([^<]+)</a>', html2)
print(f"Found {len(company_links)} company links")
for slug, name in company_links[:5]:
    print(f"  slug={slug}, name={name}")
