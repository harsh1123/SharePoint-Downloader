@echo off
echo ===================================================
echo Organizational SharePoint Sync Tool - Reset and Run
echo ===================================================
echo.
echo This will delete the state file and run a full sync.
echo.
python delete_state.py
echo.
echo State file deleted. Running sync...
echo.
python run.py
echo.
echo Press any key to exit...
pause > nul
