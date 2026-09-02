@echo off
rem Japanese Long-form Opportunity Radar - open the dashboard
rem Double-click this file. Close the black window to stop.
cd /d "%~dp0."
echo Starting... a browser tab will open at http://127.0.0.1:8502
start "" http://127.0.0.1:8502
python -m streamlit run app.py --server.port 8502
pause
