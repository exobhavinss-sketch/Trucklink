@echo off
title TruckLink Local Server
echo ===================================================
echo   Starting TruckLink 100%% Local Server...
echo   Mode: FSD - DBMS - EDADV Integrated System
echo ===================================================
echo.
echo Opening browser at http://localhost:5000 ...
start http://localhost:5000
echo.
python backend\server.py
if errorlevel 1 (
    echo Python command fallback...
    "%LOCALAPPDATA%\Python\bin\python.exe" backend\server.py
)
pause
