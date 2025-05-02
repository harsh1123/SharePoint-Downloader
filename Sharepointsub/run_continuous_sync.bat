@echo off
echo ===================================================
echo Organizational SharePoint Sync Tool - Continuous Mode
echo ===================================================
echo.
echo This will continuously sync files from your organization's SharePoint site.
echo Press Ctrl+C to stop the sync process.
echo.
python run.py --continuous
echo.
echo Press any key to exit...
pause > nul
