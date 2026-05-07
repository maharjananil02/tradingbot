"""Test ShareSansar company-price-history - debug company ID."""
import ssl
import re
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# Get the company page
url = "https://www.sharesansar.com/company/nabil"
req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
r = urlopen(req, context=ssl_ctx, timeout=20)
html = r.read().decode("utf-8", errors="replace")

# Find companyid element
matches = re.findall(r'id\s*=\s*["\']companyid["\'][^>]*>([^<]*)<', html, re.IGNORECASE)
print(f"companyid content: {matches}")

# Also check nearby elements
idx = html.find('companyid')
if idx > 0:
    context = html[idx-100:idx+200]
    print(f"\nContext around companyid:\n{context}")

# Get CSRF token
csrf_match = re.search(r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html)
if not csrf_match:
    csrf_match = re.search(r'content=["\']([^"\']{20,})["\'][^>]*name=["\']_token["\']', html)
    if not csrf_match:
        csrf_match = re.search(r'csrf.token["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
csrf = csrf_match.group(1) if csrf_match else None
print(f"\nCSRF: {csrf[:30] if csrf else 'NOT FOUND'}...")

# Get all cookies
cookie_header = r.getheader("Set-Cookie")
cookies = {}
if cookie_header:
    for part in cookie_header.split(","):
        m = re.match(r'\s*([^=]+)=([^;]+)', part.strip())
        if m:
            cookies[m.group(1)] = m.group(2)

# Try with different company values
test_values = matches + ["NABIL", "nabil", "16"]
for cv in test_values:
    cv = cv.strip()
    if not cv:
        continue
    data = urlencode({
        "draw": "1",
        "start": "0",
        "length": "20",
        "company": cv,
    }).encode()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-Token": csrf or "",
        "Referer": "https://www.sharesansar.com/company/nabil",
    }
    
    if cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers["Cookie"] = cookie_str
    
    req2 = Request(
        "https://www.sharesansar.com/company-price-history",
        data=data,
        headers=headers,
    )
    try:
        r2 = urlopen(req2, context=ssl_ctx, timeout=15)
        result = r2.read().decode("utf-8")
        print(f"\ncompany='{cv}' -> {result[:200]}")
    except Exception as e:
        print(f"\ncompany='{cv}' -> ERROR: {e}")
