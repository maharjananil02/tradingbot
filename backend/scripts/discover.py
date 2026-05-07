import ssl
import re
import os

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

from urllib.request import Request, urlopen

outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result.txt")

try:
    url = "https://www.sharesansar.com/company/nabil"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    r = urlopen(req, context=ssl_ctx, timeout=20)
    html = r.read().decode("utf-8", errors="replace")
    
    lines = []
    lines.append(f"HTML length: {len(html)}")
    
    for match in re.finditer(r'(price[_-]?history|priceHistory|price_hist)', html, re.IGNORECASE):
        start = max(0, match.start() - 300)
        end = min(len(html), match.end() + 300)
        context = html[start:end].replace('\n', ' ').strip()
        lines.append(f"\nFOUND '{match.group()}':\n{context}\n---")
    
    for match in re.finditer(r'url\s*[:=]\s*["\x27]([^"\x27]+)["\x27]', html):
        lines.append(f"URL: {match.group(1)}")
    
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print("DONE -> " + outpath)
except Exception as e:
    with open(outpath, "w") as f:
        f.write(f"ERROR: {e}")
    print(f"ERROR: {e}")
