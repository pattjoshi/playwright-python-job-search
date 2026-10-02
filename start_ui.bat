@echo off
rem Double-click this file to open the job search web page.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m job_search.web
pause
