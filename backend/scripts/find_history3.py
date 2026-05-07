import ssl
import re
from urllib.request import Request, urlopen

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

with open("scripts/output.txt", "w") as f:
    # Fetch company page
    url = "https://www.sharesansar.com/company/nabil"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    r = urlopen(req, context=ssl_ctx, timeout=15)
    html = r.read().decode("utf-8", errors="replace")
    
    # Find price-history references
    for match in re.finditer(r'(price[_-]?history|priceHistory|price_hist)', html, re.IGNORECASE):
        start = max(0, match.start() - 300)
        end = min(len(html), match.end() + 300)
        context = html[start:end].replace('\n', ' ').strip()
        f.write(f"Found '{match.group()}':\n{context}\n\n---\n\n")
    
    # Find all url patterns in scripts
    for match in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', html):
        f.write(f"URL: {match.group(1)}\n")
    
    f.write(f"\nDone. HTML length: {len(html)}\n")
    
print("Done - check scripts/output.txt")
