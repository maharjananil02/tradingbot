import smtplib
import ssl
import sys
import os
from email.mime.text import MIMEText

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from config import get_settings
settings = get_settings()

print(f"User: {settings.SMTP_USER}")

msg = MIMEText("Test email from NEPSE Bot")
msg["Subject"] = "NEPSE Bot Test"
msg["From"] = settings.SMTP_USER
msg["To"] = settings.ALERT_EMAIL_TO

# Try port 465 with SMTP_SSL
print("\n--- Try 1: SMTP_SSL port 465 ---")
try:
    ctx = ssl.create_default_context()
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10, context=ctx)
    server.set_debuglevel(1)
    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    server.send_message(msg)
    print("SUCCESS via port 465!")
    server.quit()
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

# Try port 587 with STARTTLS and debug
print("\n--- Try 2: SMTP+STARTTLS port 587 ---")
try:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    server.send_message(msg)
    print("SUCCESS via port 587!")
    server.quit()
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
