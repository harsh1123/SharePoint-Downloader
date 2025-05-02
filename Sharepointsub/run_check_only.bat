@echo off
echo ===================================================
echo Organizational SharePoint Sync Tool - Check Only Mode
echo ===================================================
echo.
echo This will check for changes in your organization's SharePoint site
echo without downloading any files.
echo.
python run.py --check-only
echo.
echo Press any key to exit...
pause > nul
