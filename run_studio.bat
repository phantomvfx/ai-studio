@echo off
echo Starting AI Studio App and Telegram Bot...
call venv\Scripts\activate.bat

:: Start Telegram Bot in a new window, activating the venv explicitly for that window
start "AI Studio Telegram Bot" cmd /k "call venv\Scripts\activate.bat & python cli_telegram.py"

:: Start Streamlit in the main window
streamlit run app.py
pause
