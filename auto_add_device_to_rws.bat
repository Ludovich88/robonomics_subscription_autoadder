@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
pip install -r requirements.txt
python add_devices_to_rws.py --key-json ********.json --password "YOUR_PASSWORD"
pause