@echo off
rem Double-click this file to open the job search web page.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat

rem Build the web page the first time (needs Node.js 20+).
if not exist frontend\out\index.html (
  echo Building the web page the first time, this takes a minute...
  pushd frontend
  call npm install || goto build_failed
  call npm run build || goto build_failed
  popd
)

python -m job_search
pause
exit /b

:build_failed
popd
echo.
echo Could not build the web page. Install Node.js 20 or newer from https://nodejs.org and try again.
pause
