"""
Flipkart Seller Hub - Traffic Report Downloader
================================================
Usage:
    python flipkart_report.py                  -> Last 7 Days
    python flipkart_report.py --range 30       -> Last 30 Days
    python flipkart_report.py --from 2026-03-01 --to 2026-03-24  -> Custom Range
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

EMAIL    = os.getenv("FK_EMAIL")
PASSWORD = os.getenv("FK_PASSWORD")

BASE_URL     = "https://seller.flipkart.com"
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Flipkart Traffic Report Downloader")
    parser.add_argument("--range", type=int, choices=[7, 30], default=7)
    parser.add_argument("--from", dest="date_from", type=str)
    parser.add_argument("--to", dest="date_to", type=str)
    return parser.parse_args()


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def check_credentials():
    if not EMAIL or not PASSWORD:
        print("\n❌ ERROR: Credentials not found!")
        print("👉 Create a .env file with FK_EMAIL and FK_PASSWORD\n")
        sys.exit(1)


def dismiss_popups(page):
    for btn_text in ["Don't Allow", "Deny", "No Thanks", "Close", "Skip"]:
        try:
            btn = page.locator(f"button:has-text('{btn_text}')").first
            if btn.is_visible(timeout=2000):
                btn.click()
                log(f"✅ Dismissed popup: '{btn_text}'")
                time.sleep(1)
                break
        except Exception:
            pass


def run(args):
    check_credentials()
    log("🚀 Starting Flipkart Traffic Report Downloader...")
    log(f"📁 Saving reports to: {DOWNLOAD_DIR.resolve()}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 900},
            permissions=[]
        )
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.dismiss())

        try:
            # STEP 1: Open site
            log("🌐 Opening Flipkart Seller Hub...")
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # STEP 2: Click Login on homepage if needed
            try:
                homepage_login = page.locator("a:has-text('Login'), button:has-text('Login')").first
                if homepage_login.is_visible(timeout=5000):
                    homepage_login.click()
                    time.sleep(2)
            except Exception:
                pass

            # STEP 3: Enter email
            log("📧 Entering email/phone...")
            email_field = page.locator(
                "input[name='loginId'], input[placeholder*='Username'], "
                "input[placeholder*='phone'], input[placeholder*='email'], "
                "input[type='email'], input[type='text']"
            ).first
            email_field.wait_for(state="visible", timeout=15000)
            email_field.click()
            email_field.fill(EMAIL)
            time.sleep(1)

            # STEP 4: Click Next
            log("➡️  Clicking Next...")
            next_btn = page.locator("button:has-text('Next')").first
            next_btn.wait_for(state="visible", timeout=10000)
            next_btn.click()
            time.sleep(3)

            # STEP 5: Enter password
            log("🔑 Entering password...")
            password_field = page.locator("input[type='password']").first
            password_field.wait_for(state="visible", timeout=15000)
            password_field.click()
            password_field.fill(PASSWORD)
            time.sleep(1)

            # STEP 6: Submit login
            log("🔓 Submitting login...")
            login_btn = page.locator("button:has-text('Login'), button[type='submit']").first
            login_btn.wait_for(state="visible", timeout=10000)
            login_btn.click()
            log("⏳ Waiting for dashboard...")
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(3)

            # STEP 7: Dismiss popups
            log("🔔 Dismissing any popups...")
            dismiss_popups(page)

            # STEP 8: Click Growth in sidebar
            log("📊 Clicking Growth in sidebar...")
            for selector in ["a[href*='growth']", "text=Growth"]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=5000):
                        el.click()
                        log("✅ Clicked Growth!")
                        break
                except Exception:
                    continue

            dismiss_popups(page)

            # STEP 9: Click Traffic Report tab immediately — don't wait for full page load
            log("📈 Waiting for Traffic Report tab...")
            for attempt in range(20):
                try:
                    traffic_tab = page.locator("text=Traffic Report").first
                    if traffic_tab.is_visible(timeout=1500):
                        traffic_tab.click()
                        log(f"✅ Clicked Traffic Report! (attempt {attempt+1})")
                        break
                except Exception:
                    pass
                time.sleep(1)
            else:
                raise Exception("Traffic Report tab not found after 20 attempts")

            time.sleep(2)
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)

            # STEP 10: Set date range
            if args.date_from and args.date_to:
                log(f"📅 Setting custom range: {args.date_from} to {args.date_to}")
                from datetime import datetime as dt
                import re

                date_from = dt.strptime(args.date_from, "%Y-%m-%d")
                date_to   = dt.strptime(args.date_to,   "%Y-%m-%d")
                MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

                # Click Custom Dates
                page.locator("text=Custom Dates").first.click()
                time.sleep(2)
                try:
                    page.screenshot(path="calendar_open.png")
                    log("📸 Saved calendar_open.png for debugging")
                except Exception:
                    pass

                def nav_to_month(target_year, target_month):
                    """Navigate calendar to the correct month."""
                    for _ in range(24):
                        try:
                            # Read all visible text in calendar header area
                            header_els = page.locator("[class*='caption'], [class*='Caption'], [class*='month'], [class*='Month']").all_text_contents()
                            header_text = " ".join(header_els)
                            m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})", header_text)
                            if m:
                                cur_mon = MONTHS.index(m.group(1)[:3]) + 1
                                cur_yr  = int(m.group(2))
                                log(f"📅 Calendar shows: {m.group(1)} {cur_yr}, need: {MONTHS[target_month-1]} {target_year}")
                                if (cur_yr, cur_mon) == (target_year, target_month):
                                    return True
                                elif (target_year, target_month) < (cur_yr, cur_mon):
                                    page.locator("button[aria-label*='revious'], button[aria-label*='rev month'], .DayPicker-NavButton--prev").first.click()
                                else:
                                    page.locator("button[aria-label*='ext'], button[aria-label*='Next month'], .DayPicker-NavButton--next").first.click()
                                time.sleep(0.5)
                        except Exception as e:
                            log(f"Nav error: {e}")
                            break
                    return False

                def click_day(target_dt):
                    day = target_dt.day
                    log(f"🗓️ Clicking day {day} of {MONTHS[target_dt.month-1]} {target_dt.year}")
                    nav_to_month(target_dt.year, target_dt.month)
                    time.sleep(0.5)

                    # Try aria-label first
                    for fmt in [
                        target_dt.strftime("%a %b %d %Y"),
                        target_dt.strftime("%A, %B %d, %Y"),
                        target_dt.strftime("%B %d, %Y"),
                        f"{day} {MONTHS[target_dt.month-1]} {target_dt.year}",
                    ]:
                        try:
                            el = page.locator(f"[aria-label='{fmt}']").first
                            if el.is_visible(timeout=500):
                                el.click()
                                log(f"✅ Clicked via aria-label: {fmt}")
                                time.sleep(0.5)
                                return True
                        except: pass

                    # Fallback: find all table cells with matching day number
                    try:
                        cells = page.locator("table td, [class*='Day']:not([class*='Outside']):not([class*='disabled'])").all()
                        for cell in cells:
                            try:
                                txt = cell.text_content().strip()
                                aria = cell.get_attribute("aria-label") or ""
                                if txt == str(day) and cell.is_visible():
                                    # Check aria label has right month/year if available
                                    if aria and (MONTHS[target_dt.month-1] not in aria or str(target_dt.year) not in aria):
                                        continue
                                    cell.click()
                                    log(f"✅ Clicked cell with text '{day}'")
                                    time.sleep(0.5)
                                    return True
                            except: pass
                    except: pass

                    log(f"⚠️ Could not find day {day}")
                    try:
                        page.screenshot(path=f"cal_fail_{day}.png")
                    except Exception:
                        pass
                    return False

                # Select dates
                try:
                    click_day(date_from)
                    time.sleep(1)
                    click_day(date_to)
                    time.sleep(1)
                except Exception as e:
                    log(f"⚠️ Date click error: {e}")

                # Click Done
                for btn_text in ["Done", "Apply", "OK", "Confirm"]:
                    try:
                        btn = page.locator(f"button:has-text('{btn_text}')").first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            log(f"✅ Clicked {btn_text}")
                            time.sleep(2)
                            break
                    except: pass

                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(2)

            elif args.range == 30:
                log("📅 Last 30 Days...")
                page.locator("text=Last 30 Days").first.click()
                time.sleep(2)
            else:
                log("📅 Last 7 Days...")
                page.locator("text=Last 7 days").first.click()
                time.sleep(2)

            # STEP 11: Click report button (could say Request or Download)
            log("📋 Looking for report button...")
            report_btn = None
            for btn_text in ["Download Listings Report", "Request Listings Report", "Download Report"]:
                try:
                    btn = page.locator(f"text={btn_text}").first
                    if btn.is_visible(timeout=5000):
                        report_btn_text = btn_text
                        report_btn = btn
                        log(f"✅ Found button: '{btn_text}'")
                        break
                except Exception:
                    continue

            if report_btn is None:
                raise Exception("Could not find report button on page")

            # If already "Download", click and download directly
            if "Download" in report_btn_text:
                log("⬇️  Report already ready! Downloading directly...")
                with page.expect_download(timeout=60000) as download_info:
                    report_btn.click()
                download = download_info.value
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = DOWNLOAD_DIR / f"flipkart_traffic_report_{timestamp}.xlsx"
                download.save_as(save_path)
                log("✅ Report downloaded successfully!")
                log(f"📄 File: {save_path.resolve()}")

                # ── Send Telegram Notification with Full Summary ──
                try:
                    import requests as req
                    import openpyxl as oxl

                    tg_token   = os.getenv("TELEGRAM_TOKEN")
                    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")

                    if tg_token and tg_chat_id:
                        # Read the downloaded report
                        wb = oxl.load_workbook(save_path)
                        ws = wb.active
                        rows = list(ws.iter_rows(values_only=True))
                        headers = [str(h).strip() if h else "" for h in rows[0]]
                        data = [dict(zip(headers, row)) for row in rows[1:] if any(c is not None for c in row)]

                        def sf(v):
                            try: return float(v) if v else 0.0
                            except: return 0.0

                        def fn(n):
                            n = float(n)
                            if n >= 1e7: return f"{n/1e7:.2f}Cr"
                            if n >= 1e5: return f"{n/1e5:.2f}L"
                            if n >= 1e3: return f"{n/1e3:.1f}K"
                            return str(int(n))

                        def fr(n):
                            n = float(n)
                            if n >= 1e7: return f"₹{n/1e7:.2f}Cr"
                            if n >= 1e5: return f"₹{n/1e5:.2f}L"
                            return f"₹{int(n):,}"

                        # Get dates in report
                        dates = sorted(set(str(r.get('Impression Date','')) for r in data if r.get('Impression Date')))
                        latest_date = dates[-1] if dates else "Unknown"
                        prev_date   = dates[-2] if len(dates) >= 2 else None

                        today_data = [r for r in data if str(r.get('Impression Date','')) == latest_date]
                        prev_data  = [r for r in data if str(r.get('Impression Date','')) == prev_date] if prev_date else []

                        total_units   = sum(sf(r.get('Sales',0)) for r in today_data)
                        total_revenue = sum(sf(r.get('Revenue',0)) for r in today_data)
                        avg_cvr       = sum(sf(r.get('Conversion Rate',0)) for r in today_data) / len(today_data) if today_data else 0
                        prev_units    = sum(sf(r.get('Sales',0)) for r in prev_data)
                        prev_revenue  = sum(sf(r.get('Revenue',0)) for r in prev_data)

                        unit_chg = ((total_units - prev_units) / prev_units * 100) if prev_units > 0 else 0
                        rev_chg  = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
                        unit_arr = "📈" if unit_chg >= 0 else "📉"
                        rev_arr  = "📈" if rev_chg >= 0 else "📉"

                        # Top 3 SKUs
                        sku_totals = {}
                        for r in today_data:
                            sku = r.get('SKU Id', 'Unknown')
                            sku_totals[sku] = sku_totals.get(sku, 0) + sf(r.get('Sales', 0))
                        top3 = sorted(sku_totals.items(), key=lambda x: x[1], reverse=True)[:3]
                        top3_text = "\n".join([f"  {i+1}. <code>{s}</code> — {fn(u)} units" for i,(s,u) in enumerate(top3)])

                        # Dead SKUs
                        dead = len([r for r in today_data if sf(r.get('Sales',0)) == 0 and sf(r.get('Product Views',0)) > 0])

                        # Date range info
                        date_range = f"{dates[0]} → {dates[-1]}" if len(dates) > 1 else latest_date

                        msg = (
                            f"📊 <b>Daily Sales Summary</b>\n"
                            f"📅 Latest Date: <b>{latest_date}</b>\n"
                            f"🗓️ Report Range: {date_range}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📦 <b>Units Sold:</b> {fn(total_units)} {unit_arr} {abs(unit_chg):.1f}% vs prev day\n"
                            f"💰 <b>Revenue:</b> {fr(total_revenue)} {rev_arr} {abs(rev_chg):.1f}% vs prev day\n"
                            f"🎯 <b>Avg CVR:</b> {avg_cvr:.2f}%\n"
                            f"💀 <b>Dead SKUs today:</b> {dead}\n"
                            f"\n"
                            f"🏆 <b>Top 3 SKUs:</b>\n"
                            f"{top3_text}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📄 <code>{save_path.name}</code>\n"
                            f"🤖 Flipkart Automation Bot"
                        )

                        req.post(
                            f"https://api.telegram.org/bot{tg_token}/sendMessage",
                            json={"chat_id": tg_chat_id, "text": msg, "parse_mode": "HTML"},
                            timeout=10
                        )
                        log("📱 Telegram summary sent!")
                    else:
                        log("⚠️ Telegram credentials not set in .env")
                except Exception as e:
                    log(f"⚠️ Telegram notification failed: {e}")

                browser.close()
                return

            # Otherwise click Request and wait for generation
            report_btn.click()
            log("⏳ Report is being generated by Flipkart...")

            # STEP 12: Wait for "Generating Report..." to disappear
            # and "Download Report" or similar button to appear
            log("⏳ Waiting for report to be ready (this may take up to 30 minutes)...")
            max_wait = 1800  # wait up to 30 minutes
            check_interval = 5
            elapsed = 0
            download_clicked = False

            while elapsed < max_wait:
                time.sleep(check_interval)
                elapsed += check_interval
                log(f"⏳ Waiting... ({elapsed}s elapsed)")

                # Check if a Download button has appeared
                for dl_text in ["Download Report", "Download", "Download Listings Report"]:
                    try:
                        dl_btn = page.locator(f"text={dl_text}").first
                        if dl_btn.is_visible(timeout=2000):
                            log(f"✅ Download button found: '{dl_text}'")
                            with page.expect_download(timeout=60000) as download_info:
                                dl_btn.click()
                            download = download_info.value
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            save_path = DOWNLOAD_DIR / f"flipkart_traffic_report_{timestamp}.xlsx"
                            download.save_as(save_path)
                            log("✅ Report downloaded successfully!")
                            log(f"📄 File: {save_path.resolve()}")
                            download_clicked = True
                            break
                    except Exception:
                        continue

                if download_clicked:
                    break

                # Also check if "Generating Report" text is gone
                try:
                    still_generating = page.locator("text=Generating Report").first
                    if not still_generating.is_visible(timeout=1000):
                        log("✅ Generation complete! Looking for download link...")
                        # Take screenshot to see what appeared
                        page.screenshot(path="after_generation.png")
                        log("📸 Screenshot saved as after_generation.png")
                except Exception:
                    pass

            if not download_clicked:
                log("⚠️  Could not find download button after waiting. Taking screenshot...")
                page.screenshot(path="error_screenshot.png")
                log("📸 Please share error_screenshot.png so I can see what appeared.")

        except PlaywrightTimeoutError as e:
            log(f"❌ Timeout Error: {e}")
            try:
                page.screenshot(path="error_screenshot.png")
                log("📸 Screenshot saved as error_screenshot.png")
            except Exception:
                log("📸 Could not save screenshot - browser was closed")

        except Exception as e:
            log(f"❌ Error: {e}")
            try:
                page.screenshot(path="error_screenshot.png")
                log("📸 Screenshot saved as error_screenshot.png")
            except Exception:
                log("📸 Could not save screenshot - browser was closed")

        finally:
            browser.close()
            log("🔒 Browser closed.")


if __name__ == "__main__":
    args = parse_args()
    run(args)
