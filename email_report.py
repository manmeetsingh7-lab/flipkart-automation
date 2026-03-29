"""
Flipkart Traffic Report - Gmail Emailer
========================================
Sends the latest downloaded traffic report via Gmail.

Setup:
1. Add these to your .env file:
   GMAIL_SENDER=your_gmail@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   GMAIL_RECIPIENT=recipient@gmail.com

How to get Gmail App Password:
   1. Go to myaccount.google.com
   2. Security → 2-Step Verification (enable it)
   3. Security → App Passwords
   4. Create a new app password for "Mail"
   5. Copy the 16-character password into .env
"""

import os
import smtplib
import glob
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

GMAIL_SENDER     = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASS   = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT  = os.getenv("GMAIL_RECIPIENT")
DOWNLOAD_DIR     = Path(__file__).parent / "downloads"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_latest_report():
    files = sorted(DOWNLOAD_DIR.glob("flipkart_traffic_report_*.xlsx"), reverse=True)
    if not files:
        raise FileNotFoundError("No report found in downloads folder! Run flipkart_report.py first.")
    return files[0]


def send_email(report_path):
    log(f"📧 Preparing email with: {report_path.name}")

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = GMAIL_RECIPIENT
    msg["Subject"] = f"📊 Flipkart Traffic Report — {datetime.now().strftime('%d %b %Y')}"

    body = f"""
Hi,

Please find attached the latest Flipkart Traffic Report.

📅 Report Date : {datetime.now().strftime('%d %B %Y')}
📄 File        : {report_path.name}
📁 Downloaded  : Weekly Auto-Report

This email was sent automatically by your Flipkart Automation Script.

Regards,
Flipkart Automation Bot
    """
    msg.attach(MIMEText(body, "plain"))

    # Attach the Excel report
    with open(report_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={report_path.name}")
        msg.attach(part)

    # Send via Gmail SMTP
    log("📤 Connecting to Gmail SMTP...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_SENDER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())

    log(f"✅ Email sent successfully to {GMAIL_RECIPIENT}!")


if __name__ == "__main__":
    if not all([GMAIL_SENDER, GMAIL_APP_PASS, GMAIL_RECIPIENT]):
        print("\n❌ Missing Gmail credentials in .env file!")
        print("Add these to your .env:")
        print("  GMAIL_SENDER=your_gmail@gmail.com")
        print("  GMAIL_APP_PASSWORD=your_16char_app_password")
        print("  GMAIL_RECIPIENT=recipient@gmail.com\n")
    else:
        report = get_latest_report()
        send_email(report)
