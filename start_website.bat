@echo off
cd /d "%~dp0"
title AI Student Engagement Website
echo Starting web-based Student Engagement System...
start http://localhost:5000
python app.py
pause
