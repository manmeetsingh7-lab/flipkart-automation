@echo off
title Flipkart Weekly Summary — Running...
cd /d "%~dp0"

echo ============================================
echo   Flipkart Weekly Performance Summary
echo   %date% %time%
echo ============================================
echo.

echo [%time%] Sending Weekly Summary to Telegram...
python telegram_alerts.py --weekly

echo.
echo ============================================
echo   Weekly Summary Sent! Check Telegram.
echo ============================================

timeout /t 5
