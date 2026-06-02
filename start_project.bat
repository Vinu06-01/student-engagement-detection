@echo off
cd /d "%~dp0"
title AI Student Engagement System Launcher

echo Starting AI Student Engagement Detection System...
echo.
echo 1. Starting Flask server...
start "Engagement Server" cmd /k "cd /d ""%~dp0"" && python server.py"

timeout /t 3 /nobreak >nul

echo 2. Starting Streamlit dashboard...
start "Engagement Dashboard" cmd /k "cd /d ""%~dp0"" && python -m streamlit run dashboard.py"

timeout /t 5 /nobreak >nul

echo 3. Starting real-time webcam detection...
start "Realtime Detection" cmd /k "cd /d ""%~dp0"" && python realtime_detection.py"

timeout /t 2 /nobreak >nul

echo Opening dashboard in browser...
start http://localhost:8501

echo.
echo All services started.
echo Keep the opened command windows running during class.
echo Press any key to close this launcher window.
pause >nul
