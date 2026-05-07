import socket
import ssl
import sys

# Test port 587 (STARTTLS)
print("Testing smtp.gmail.com:587...")
try:
    s = socket.create_connection(("smtp.gmail.com", 587), timeout=5)
    print("  Port 587: CONNECTED")
    s.close()
except Exception as e:
    print(f"  Port 587: FAILED - {e}")

# Test port 465 (SSL)
print("Testing smtp.gmail.com:465...")
try:
    s = socket.create_connection(("smtp.gmail.com", 465), timeout=5)
    print("  Port 465: CONNECTED (TCP)")
    ctx = ssl.create_default_context()
    ss = ctx.wrap_socket(s, server_hostname="smtp.gmail.com")
    print(f"  Port 465: SSL OK - {ss.version()}")
    ss.close()
except Exception as e:
    print(f"  Port 465: FAILED - {e}")

# Test port 25
print("Testing smtp.gmail.com:25...")
try:
    s = socket.create_connection(("smtp.gmail.com", 25), timeout=5)
    print("  Port 25: CONNECTED")
    s.close()
except Exception as e:
    print(f"  Port 25: FAILED - {e}")
