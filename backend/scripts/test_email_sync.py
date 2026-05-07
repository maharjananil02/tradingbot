import smtplib
import sys
import os
from email.mime.text import MIMEText

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from config import get_settings
settings = get_settings()

print(f"SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
print(f"User: {settings.SMTP_USER}")
print(f"To: {settings.ALERT_EMAIL_TO}")

msg = MIMEText("This is a test stop-loss alert from NEPSE Bot.")
msg["Subject"] = "NEPSE Bot: Stop Loss Test"
msg["From"] = settings.SMTP_USER
msg["To"] = settings.ALERT_EMAIL_TO

try:
    print("Connecting to SMTP server...")
    server = smtplib.SMTP(settings.SMTP_HOST, 587, timeout=10)
    print("Connected. Starting TLS...")
    server.starttls()
    print("TLS started. Logging in...")
    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    print("Logged in. Sending email...")
    server.send_message(msg)
    print("Email sent successfully!")
    server.quit()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
