@echo off
setlocal
set "APP_DIR=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%APP_DIR%start_plex_debrid.bat"

echo.
echo Installing plex_debrid auto-start (visible console at logon) ...
echo.

rem remove the old hidden launcher if present
if exist "%STARTUP%\plex_debrid.vbs" del /q "%STARTUP%\plex_debrid.vbs"

%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $lnk=$ws.CreateShortcut('%STARTUP%\plex_debrid.lnk'); $lnk.TargetPath='%TARGET%'; $lnk.WorkingDirectory='%APP_DIR%'; $lnk.WindowStyle=1; $lnk.Save()"
if errorlevel 1 (
    echo Failed to create the Startup shortcut.
) else (
    echo Done! plex_debrid will open in a visible console every time you log in.
    echo   - Remove auto-start: delete "%STARTUP%\plex_debrid.lnk"
)
echo.
endlocal
