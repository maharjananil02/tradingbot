"""Test ShareSansar company-price-history endpoint."""
import ssl
import re
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# Step 1: Get the company page to extract CSRF token and company ID
url = "https://www.sharesansar.com/company/nabil"
req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
r = urlopen(req, context=ssl_ctx, timeout=20)
html = r.read().decode("utf-8", errors="replace")

# Extract CSRF token
csrf_match = re.search(r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html)
if not csrf_match:
    csrf_match = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']_token["\']', html)
csrf_token = csrf_match.group(1) if csrf_match else "NONE"
print(f"CSRF Token: {csrf_token[:20]}...")

# Extract company ID
cid_match = re.search(r'id=["\']companyid["\'][^>]*>(\d+)<', html)
if not cid_match:
    cid_match = re.search(r"companyid['\"]>[^<]*?(\d+)", html)
company_id = cid_match.group(1) if cid_match else None
print(f"Company ID: {company_id}")

# Also get cookies
cookies = r.getheader("Set-Cookie")
print(f"Cookies: {cookies[:100] if cookies else 'None'}...")

# Step 2: POST to get price history
if company_id:
    # DataTables server-side processing params
    data = urlencode({
        "draw": "1",
        "start": "0",
        "length": "100",  # Get 100 records
        "company": company_id,
    }).encode()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-Token": csrf_token,
        "Referer": "https://www.sharesansar.com/company/nabil",
    }
    
    if cookies:
        # Extract session cookie
        cookie_parts = []
        for c in cookies.split(","):
            m = re.match(r'([^=]+=[^;]+)', c.strip())
            if m:
                cookie_parts.append(m.group(1))
        headers["Cookie"] = "; ".join(cookie_parts)
    
    req2 = Request(
        "https://www.sharesansar.com/company-price-history",
        data=data,
        headers=headers,
    )
    r2 = urlopen(req2, context=ssl_ctx, timeout=20)
    result = r2.read().decode("utf-8", errors="replace")
    print(f"\nResponse length: {len(result)}")
    print(f"First 1000 chars:\n{result[:1000]}")
else:
    print("Could not find company ID!")
