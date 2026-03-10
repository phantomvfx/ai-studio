@echo off
echo Starting AI Studio (Local) and Telegram Bot...
call venv\Scripts\activate.bat

:: Start Telegram Bot in a new window
start "AI Studio Telegram Bot" cmd /k "call venv\Scripts\activate.bat & python cli_telegram.py"

:: Start Streamlit local version
streamlit run applocal.py
pause
