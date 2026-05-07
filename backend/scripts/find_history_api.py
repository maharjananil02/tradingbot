"""Find ShareSansar AJAX URL for price history data."""
import ssl
import re
import json
from urllib.request import Request, urlopen

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html",
}

url = "https://www.sharesansar.com/company/nabil"
req = Request(url, headers=headers)
r = urlopen(req, context=ssl_ctx, timeout=15)
html = r.read().decode("utf-8", errors="replace")

# Find all URLs in the page
all_urls = re.findall(r'["\'](/[^"\'>\s]{5,})["\']', html)
# Filter for API-like URLs
api_urls = [u for u in all_urls if any(k in u.lower() for k in ["price", "hist", "ajax", "api", "chart", "data"])]
print("API-like URLs found in page:")
for u in sorted(set(api_urls)):
    print(f"  {u}")

print("\n---\nLooking for AJAX/fetch calls in scripts...")
# Find JS that loads data
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(scripts):
    if any(k in script.lower() for k in ["price", "history", "pricehistory"]):
        # Extract URLs from this script
        urls_in_script = re.findall(r'url\s*[:=]\s*["\']([^"\']+)["\']', script)
        if urls_in_script:
            print(f"\nScript #{i} urls:")
            for u in urls_in_script:
                print(f"  {u}")
        # Also show relevant code context
        for line in script.split("\n"):
            line = line.strip()
            if any(k in line.lower() for k in ["price", "history", "ajax", "url"]) and len(line) < 200:
                print(f"  >> {line}")
