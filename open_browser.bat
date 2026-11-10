@echo off
title Job Applier - Browser Login Setup
echo ===============================================================
echo Launching Google Chrome with your dedicated Job Applier profile...
echo Profile path: %~dp0browser_profile
echo.
echo Please log in to:
echo  1. Wellfound (https://wellfound.com/login)
echo  2. LinkedIn (https://www.linkedin.com/login)
echo  3. Naukri (https://www.naukri.com/nlogin/login)
echo.
echo Once logged in, you can close the browser. Your sessions and cookies
echo will be automatically preserved for the automated watcher.
echo ===============================================================

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0browser_profile" --no-first-run --no-default-browser-check "https://wellfound.com/login" "https://www.linkedin.com/login" "https://www.naukri.com/nlogin/login"
