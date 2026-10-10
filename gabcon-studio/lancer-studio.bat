@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo.
echo  GABCON STUDIO - BuildAI
 echo  Interface : http://127.0.0.1:8788
 echo.
uv run python "gabcon-studio\server.py"
echo.
echo  Le programme s'est termine. Verifie les messages ci-dessus.
pause
