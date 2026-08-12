@echo off
rem ============================================================
rem  plex_debrid launcher - runs the app in a visible console
rem  window (service mode: no user input needed).
rem ============================================================
cd /d "%~dp0"
py main.py -service
