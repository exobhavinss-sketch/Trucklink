@echo off
title TruckLink EDADV Analysis
echo ===================================================
echo   Running TruckLink Offline EDADV Analysis...
echo ===================================================
echo.
python edadv_analytics\eda_analysis.py
if errorlevel 1 (
    echo Python command fallback...
    "%LOCALAPPDATA%\Python\bin\python.exe" edadv_analytics\eda_analysis.py
)
echo.
echo All high-resolution charts saved in edadv_analytics\charts\
pause
