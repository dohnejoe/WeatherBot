@echo off
REM Local Weather Bot Runner
REM Keep secrets in Windows environment variables, not in this file.

if not defined GEMINI_API_KEY (
    echo ERROR: GEMINI_API_KEY is not set.
    exit /b 1
)
if not defined TG_BOT_TOKEN (
    echo ERROR: TG_BOT_TOKEN is not set.
    exit /b 1
)

cd /d "C:\Users\Ebi\workspace\weather_bot"
python weather_bot.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Bot failed. Check the logs above.
    echo ========================================
    pause
    exit /b 1
)
