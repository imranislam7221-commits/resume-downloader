@echo off
title Resume Downloader Web Server
cd /d "%~dp0"
echo Starting Resume Downloader Web Server at http://localhost:5000 ...
python web_server.py
pause
