@echo off
REM Weather Bot Runner - Sets env vars and runs the bot
REM Edit the values below with your actual keys (or keep them in Windows User Environment Variables)

set GEMINI_API_KEY=AQ.Ab8RN6KNLljwkpHR4Z2rCUvUbq9QhCeGLOYErDdXA3OkTWXPHA
set TG_BOT_TOKEN=8897059207:AAEbm_cl_GSO8J5bD3d6OwTk90b8pGPXGXw
set TG_CHAT_ID=77917638

cd /d "C:\Users\Ebi\workspace\weather_bot"
python weather_bot.py

REM Pause on error so you can see the message
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Bot failed. Check the logs above.
    echo ========================================
    pause
)