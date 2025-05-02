@echo off
echo ===================================================
echo OneDrive Sync Tool - Root-Only Force Full Sync
echo ===================================================
echo.
echo This will download only files in the root of your OneDrive,
echo ignoring the existing state file.
echo.
python run.py --root-only --force-full-sync
echo.
echo Press any key to exit...
pause > nul
