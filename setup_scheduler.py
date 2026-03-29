"""
Windows Task Scheduler Setup — Full Automation
================================================
Sets up TWO tasks:
  1. DAILY at 11:00 AM  → Download report + update dashboard
  2. WEEKLY Monday 11AM → Weekly performance summary on Telegram

Run ONCE as Administrator.
"""

import subprocess, os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR  = Path(__file__).parent.resolve()
BAT_DAILY   = SCRIPT_DIR / "run_daily.bat"
BAT_WEEKLY  = SCRIPT_DIR / "run_weekly.bat"
TASK_DAILY  = "FlipkartDailyReport"
TASK_WEEKLY = "FlipkartWeeklyReport"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check_requirements():
    log("🔍 Checking requirements...")
    env_file = SCRIPT_DIR / ".env"
    if not env_file.exists():
        log("❌ .env file not found!")
    else:
        content = env_file.read_text()
        missing = [k for k in ["FK_EMAIL","FK_PASSWORD","TELEGRAM_TOKEN","TELEGRAM_CHAT_ID"] if k not in content]
        if missing:
            log(f"⚠️  Missing in .env: {', '.join(missing)}")
        else:
            log("✅ .env looks good!")
    if not BAT_DAILY.exists():
        log("⚠️  run_daily.bat not found — will be created")
    if not BAT_WEEKLY.exists():
        log("⚠️  run_weekly.bat not found!")
    py = subprocess.run(["python","--version"], capture_output=True, text=True)
    log(f"✅ Python: {py.stdout.strip()}" if py.returncode==0 else "❌ Python not found!")

def create_task(task_name, bat_file, schedule, day=None, time="11:00"):
    """Create a Windows scheduled task"""
    # Delete existing
    subprocess.run(f'schtasks /delete /tn "{task_name}" /f',
                   shell=True, capture_output=True)
    if schedule == "DAILY":
        cmd = (f'schtasks /create /tn "{task_name}" '
               f'/tr "cmd /c \\"{bat_file}\\"" '
               f'/sc DAILY /st {time} /rl HIGHEST /f')
    else:  # WEEKLY
        cmd = (f'schtasks /create /tn "{task_name}" '
               f'/tr "cmd /c \\"{bat_file}\\"" '
               f'/sc WEEKLY /d {day} /st {time} /rl HIGHEST /f')

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        log(f"✅ Task '{task_name}' created! ({schedule} at {time})")
        return True
    else:
        log(f"❌ Failed: {result.stderr or result.stdout}")
        log("💡 Right-click setup_scheduler.py → Run as Administrator")
        return False

def verify_task(task_name):
    result = subprocess.run(f'schtasks /query /tn "{task_name}" /fo LIST',
                            shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if any(k in line for k in ["Next Run","Status","Last Run"]):
                log(f"   {line.strip()}")

def send_test_telegram():
    try:
        from dotenv import load_dotenv
        import requests
        load_dotenv(SCRIPT_DIR / ".env")
        token   = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            log("⚠️  Telegram credentials not found — skipping test")
            return
        msg = (
            "🤖 <b>Flipkart Automation Setup Complete!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Daily scheduler active\n"
            "📅 Runs <b>every day at 11:00 AM</b>\n\n"
            "What happens automatically:\n"
            "1️⃣ Downloads Flipkart traffic report\n"
            "2️⃣ Updates dashboard with new data\n"
            "3️⃣ Deploys to Netlify\n"
            "4️⃣ Sends daily summary here\n\n"
            "📊 Weekly summary every Monday 11 AM\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Keep laptop ON at 11 AM daily!"
        )
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        if r.status_code == 200:
            log("📱 Test Telegram message sent!")
        else:
            log(f"⚠️  Telegram failed: {r.text[:100]}")
    except Exception as e:
        log(f"⚠️  Telegram error: {e}")

if __name__ == "__main__":
    print("=" * 55)
    print("   Flipkart Automation — Scheduler Setup")
    print("=" * 55)
    print()

    check_requirements()
    print()

    run_time = input("⏰ Run time [default: 11:00]: ").strip() or "11:00"
    print()

    log("🔧 Creating DAILY task (report + dashboard)...")
    ok1 = create_task(TASK_DAILY, BAT_DAILY, "DAILY", time=run_time)

    print()
    log("🔧 Creating WEEKLY task (summary on Telegram)...")
    ok2 = create_task(TASK_WEEKLY, BAT_WEEKLY, "WEEKLY", day="MON", time=run_time)

    if ok1 and ok2:
        print()
        log("📋 Task status:")
        verify_task(TASK_DAILY)
        verify_task(TASK_WEEKLY)
        print()
        log("📱 Sending test Telegram message...")
        send_test_telegram()
        print()
        print("=" * 55)
        log("🎉 Setup complete! Schedule:")
        log(f"   📅 Every day at {run_time} → Download + Dashboard + Telegram")
        log(f"   📊 Every Monday at {run_time} → Weekly summary on Telegram")
        log("")
        log("   ⚠️  Keep laptop ON at 11 AM daily!")
        log("   💡 Run manually anytime: python run_daily.bat")
        print("=" * 55)
    else:
        log("❌ Setup failed. Try running as Administrator.")
