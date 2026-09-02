@echo off
chcp 65001 > nul
cd /d "%~dp0."
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "LOG=C:\ia-codyssey\assignments\M1-1\Japanese-Longform-Opportunity-Radar\data\raw\run_log.txt"

echo [%date% %time%] --- collect start --- >> "%LOG%"
"C:\Users\UserK\AppData\Local\Programs\Python\Python311\python.exe" -m src.collector >> "%LOG%" 2>&1
"C:\Users\UserK\AppData\Local\Programs\Python\Python311\python.exe" -m src.snapshot_collector >> "%LOG%" 2>&1
echo [%date% %time%] --- done (exit %errorlevel%) --- >> "%LOG%"
