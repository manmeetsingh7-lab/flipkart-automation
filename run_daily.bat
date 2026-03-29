@echo off
title Flipkart Daily Automation — Running...
cd /d "%~dp0"

echo ============================================
echo   Flipkart Daily Report Automation
echo   %date% %time%
echo ============================================
echo.

:: Flipkart report has 2-day delay
:: Today = 29th → Download report for 27th
for /f %%i in ('python -c "from datetime import date, timedelta; print((date.today()-timedelta(days=2)).strftime('%%Y-%%m-%%d'))"') do set REPORT_DATE=%%i

echo [%time%] Today: %date%
echo [%time%] Downloading report for: %REPORT_DATE% (2 days ago)
echo.

:: Step 1: Download report for 2 days ago
echo [%time%] Step 1/3: Downloading Report for %REPORT_DATE%...
python flipkart_report.py --from %REPORT_DATE% --to %REPORT_DATE%
if %errorlevel% neq 0 (
    echo [ERROR] Report download failed!
    python -c "import requests,os; from dotenv import load_dotenv; load_dotenv(); t=os.getenv('TELEGRAM_TOKEN'); c=os.getenv('TELEGRAM_CHAT_ID'); requests.post(f'https://api.telegram.org/bot{t}/sendMessage', json={'chat_id':c,'text':'❌ Daily report for %REPORT_DATE% FAILED! Please check manually.','parse_mode':'HTML'}, timeout=10) if t and c else None" 2>nul
    goto :end
)

echo.
:: Step 2: Generate dashboard with all merged data
echo [%time%] Step 2/3: Updating Dashboard...
python generate_dashboard.py
if %errorlevel% neq 0 (
    echo [ERROR] Dashboard update failed!
    goto :end
)

echo.
:: Step 3: Send daily Telegram summary
echo [%time%] Step 3/3: Sending Daily Summary to Telegram...
python telegram_alerts.py --daily

echo.
echo ============================================
echo   Done! Report for %REPORT_DATE% downloaded.
echo   Dashboard updated. Check Telegram!
echo ============================================

:end
timeout /t 5
