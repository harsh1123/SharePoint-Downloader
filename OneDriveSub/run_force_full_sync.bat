@echo off
echo ===================================================
echo OneDrive Sync Tool - Force Full Sync
echo ===================================================
echo.
echo This will perform a full sync, ignoring the existing state file.
echo.
python run.py --force-full-sync
echo.
echo Press any key to exit...
pause > nul
