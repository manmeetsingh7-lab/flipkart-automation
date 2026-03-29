"""
Flipkart Telegram Alert System
================================
3 Alert Types:
1. Daily Sales Summary
2. Report Downloaded Confirmation
3. Weekly Performance Summary

Usage:
    python telegram_alerts.py --daily       → Send daily sales summary
    python telegram_alerts.py --weekly      → Send weekly performance summary
    python telegram_alerts.py --downloaded  → Send report downloaded confirmation

Add to .env:
    TELEGRAM_TOKEN=your_bot_token
    TELEGRAM_CHAT_ID=your_chat_id
"""

import os, sys, glob, argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    import openpyxl
except:
    os.system("python -m pip install openpyxl")
    import openpyxl

load_dotenv()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DOWNLOAD_DIR = Path(__file__).parent / "downloads"


# ─────────────────────────────────────────────
# CORE: Send Telegram Message
# ─────────────────────────────────────────────
def send(message):
    if not TOKEN or not CHAT_ID:
        print("❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing in .env!")
        sys.exit(1)
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    r = requests.post(url, json=payload, timeout=10)
    if r.status_code == 200:
        print("✅ Telegram message sent!")
    else:
        print(f"❌ Failed: {r.text}")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_latest_report():
    files = sorted(DOWNLOAD_DIR.glob("flipkart_traffic_report_*.xlsx"), reverse=True)
    if not files:
        raise FileNotFoundError("No report found in downloads folder!")
    return files[0]

def fmt_num(n):
    n = float(n)
    if n >= 1e7: return f"{n/1e7:.2f}Cr"
    if n >= 1e5: return f"{n/1e5:.2f}L"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def fmt_rev(n):
    n = float(n)
    if n >= 1e7: return f"₹{n/1e7:.2f}Cr"
    if n >= 1e5: return f"₹{n/1e5:.2f}L"
    return f"₹{int(n):,}"

def read_report(path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows: return [], []
    headers = [str(h).strip() if h else "" for h in rows[0]]
    data = [dict(zip(headers, row)) for row in rows[1:] if any(cell is not None for cell in row)]
    return headers, data

def safe_float(v):
    try: return float(v) if v is not None else 0.0
    except: return 0.0


# ─────────────────────────────────────────────
# ALERT 1: Daily Sales Summary
# ─────────────────────────────────────────────
def daily_summary():
    path = get_latest_report()
    _, data = read_report(path)

    # Get latest date in report
    dates = sorted(set(str(r.get('Impression Date','')) for r in data if r.get('Impression Date')))
    latest_date = dates[-1] if dates else "Unknown"
    prev_date   = dates[-2] if len(dates) >= 2 else None

    # Filter today's data
    today_data = [r for r in data if str(r.get('Impression Date','')) == latest_date]
    prev_data  = [r for r in data if str(r.get('Impression Date','')) == prev_date] if prev_date else []

    # Calculate metrics
    total_units   = sum(safe_float(r.get('Sales', 0)) for r in today_data)
    total_revenue = sum(safe_float(r.get('Revenue', 0)) for r in today_data)
    avg_cvr       = sum(safe_float(r.get('Conversion Rate', 0)) for r in today_data) / len(today_data) if today_data else 0

    prev_units   = sum(safe_float(r.get('Sales', 0)) for r in prev_data)
    prev_revenue = sum(safe_float(r.get('Revenue', 0)) for r in prev_data)

    # Day over day change
    unit_change = ((total_units - prev_units) / prev_units * 100) if prev_units > 0 else 0
    rev_change  = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    unit_arrow  = "📈" if unit_change >= 0 else "📉"
    rev_arrow   = "📈" if rev_change >= 0 else "📉"

    # Top 3 SKUs
    sku_totals = {}
    for r in today_data:
        sku = r.get('SKU Id', 'Unknown')
        sku_totals[sku] = sku_totals.get(sku, 0) + safe_float(r.get('Sales', 0))
    top3 = sorted(sku_totals.items(), key=lambda x: x[1], reverse=True)[:3]

    # Dead SKUs today
    dead_today = len([r for r in today_data if safe_float(r.get('Sales', 0)) == 0 and safe_float(r.get('Product Views', 0)) > 0])

    top3_text = "\n".join([f"  {i+1}. <code>{sku}</code> — {fmt_num(units)} units" for i, (sku, units) in enumerate(top3)])

    message = f"""📊 <b>Daily Sales Summary</b>
📅 Date: <b>{latest_date}</b>
━━━━━━━━━━━━━━━━━━━━━

📦 <b>Units Sold:</b> {fmt_num(total_units)} {unit_arrow} {abs(unit_change):.1f}% vs prev day
💰 <b>Revenue:</b> {fmt_rev(total_revenue)} {rev_arrow} {abs(rev_change):.1f}% vs prev day
🎯 <b>Avg CVR:</b> {avg_cvr:.2f}%
💀 <b>Dead SKUs today:</b> {dead_today}

🏆 <b>Top 3 SKUs:</b>
{top3_text}

━━━━━━━━━━━━━━━━━━━━━
🤖 Flipkart Automation Bot"""

    send(message)


# ─────────────────────────────────────────────
# ALERT 2: Report Downloaded Confirmation
# ─────────────────────────────────────────────
def report_downloaded():
    path = get_latest_report()
    _, data = read_report(path)

    dates = sorted(set(str(r.get('Impression Date','')) for r in data if r.get('Impression Date')))
    skus  = len(set(r.get('SKU Id','') for r in data))
    total_units   = sum(safe_float(r.get('Sales', 0)) for r in data)
    total_revenue = sum(safe_float(r.get('Revenue', 0)) for r in data)
    file_size     = round(path.stat().st_size / 1024, 1)

    message = f"""✅ <b>Report Downloaded Successfully!</b>
━━━━━━━━━━━━━━━━━━━━━

📄 <b>File:</b> <code>{path.name}</code>
📁 <b>Size:</b> {file_size} KB
📅 <b>Date Range:</b> {dates[0]} → {dates[-1]}
📆 <b>Days Covered:</b> {len(dates)} days
📦 <b>Total SKUs:</b> {skus}
🛍️ <b>Total Units:</b> {fmt_num(total_units)}
💰 <b>Total Revenue:</b> {fmt_rev(total_revenue)}

📂 Saved to downloads folder
━━━━━━━━━━━━━━━━━━━━━
🤖 Flipkart Automation Bot"""

    send(message)


# ─────────────────────────────────────────────
# ALERT 3: Weekly Performance Summary
# ─────────────────────────────────────────────
def weekly_summary():
    path = get_latest_report()
    _, data = read_report(path)

    dates = sorted(set(str(r.get('Impression Date','')) for r in data if r.get('Impression Date')))

    # Last 7 days vs previous 7 days
    last7  = dates[-7:]  if len(dates) >= 7  else dates
    prev7  = dates[-14:-7] if len(dates) >= 14 else []

    this_week = [r for r in data if str(r.get('Impression Date','')) in last7]
    prev_week = [r for r in data if str(r.get('Impression Date','')) in prev7]

    # This week metrics
    tw_units   = sum(safe_float(r.get('Sales', 0)) for r in this_week)
    tw_revenue = sum(safe_float(r.get('Revenue', 0)) for r in this_week)
    tw_cvr     = sum(safe_float(r.get('Conversion Rate', 0)) for r in this_week) / len(this_week) if this_week else 0

    # Prev week metrics
    pw_units   = sum(safe_float(r.get('Sales', 0)) for r in prev_week)
    pw_revenue = sum(safe_float(r.get('Revenue', 0)) for r in prev_week)

    # Changes
    unit_chg = ((tw_units - pw_units) / pw_units * 100) if pw_units > 0 else 0
    rev_chg  = ((tw_revenue - pw_revenue) / pw_revenue * 100) if pw_revenue > 0 else 0
    unit_arr = "📈" if unit_chg >= 0 else "📉"
    rev_arr  = "📈" if rev_chg >= 0 else "📉"

    # Best day this week
    day_totals = {}
    for r in this_week:
        d = str(r.get('Impression Date',''))
        day_totals[d] = day_totals.get(d, 0) + safe_float(r.get('Sales', 0))
    best_day  = max(day_totals, key=day_totals.get) if day_totals else "N/A"
    worst_day = min(day_totals, key=day_totals.get) if day_totals else "N/A"

    # Top 5 SKUs this week
    sku_totals = {}
    for r in this_week:
        sku = str(r.get('SKU Id', 'Unknown'))
        sku_totals[sku] = sku_totals.get(sku, 0) + safe_float(r.get('Sales', 0))
    top5 = sorted(sku_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    top5_text = "\n".join([f"  {i+1}. <code>{sku}</code> — {fmt_num(u)} units" for i, (sku, u) in enumerate(top5)])

    # Dead SKUs this week
    sku_units = {}
    for r in this_week:
        sku = str(r.get('SKU Id',''))
        sku_units[sku] = sku_units.get(sku, 0) + safe_float(r.get('Sales', 0))
    dead_count = sum(1 for v in sku_units.values() if v == 0)

    period = f"{last7[0]} → {last7[-1]}" if last7 else "N/A"
    prev_period = f"{prev7[0]} → {prev7[-1]}" if prev7 else "No previous data"

    message = f"""📅 <b>Weekly Performance Summary</b>
🗓️ Period: <b>{period}</b>
━━━━━━━━━━━━━━━━━━━━━

📦 <b>Units Sold:</b> {fmt_num(tw_units)} {unit_arr} {abs(unit_chg):.1f}% vs prev week
💰 <b>Revenue:</b> {fmt_rev(tw_revenue)} {rev_arr} {abs(rev_chg):.1f}% vs prev week
🎯 <b>Avg CVR:</b> {tw_cvr:.2f}%
💀 <b>Dead SKUs:</b> {dead_count}

📅 <b>Best Day:</b> {best_day} ({fmt_num(day_totals.get(best_day,0))} units)
📅 <b>Worst Day:</b> {worst_day} ({fmt_num(day_totals.get(worst_day,0))} units)

🏆 <b>Top 5 SKUs This Week:</b>
{top5_text}

📊 <b>Prev Week:</b> {prev_period}
   Units: {fmt_num(pw_units)} | Revenue: {fmt_rev(pw_revenue)}

━━━━━━━━━━━━━━━━━━━━━
🤖 Flipkart Automation Bot"""

    send(message)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flipkart Telegram Alerts")
    parser.add_argument("--daily",      action="store_true", help="Send daily sales summary")
    parser.add_argument("--weekly",     action="store_true", help="Send weekly performance summary")
    parser.add_argument("--downloaded", action="store_true", help="Send report downloaded confirmation")
    parser.add_argument("--all",        action="store_true", help="Send all alerts")
    args = parser.parse_args()

    if args.all:
        print("📤 Sending all alerts...")
        report_downloaded()
        daily_summary()
        weekly_summary()
    elif args.daily:
        print("📤 Sending daily summary...")
        daily_summary()
    elif args.weekly:
        print("📤 Sending weekly summary...")
        weekly_summary()
    elif args.downloaded:
        print("📤 Sending download confirmation...")
        report_downloaded()
    else:
        print("Usage:")
        print("  python telegram_alerts.py --daily")
        print("  python telegram_alerts.py --weekly")
        print("  python telegram_alerts.py --downloaded")
        print("  python telegram_alerts.py --all")
