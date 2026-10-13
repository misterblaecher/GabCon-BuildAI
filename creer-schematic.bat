@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title GabCon BuildAI - Creation directe de schematics
echo.
echo   GABCON BUILDAI - CREER UN SCHEMATIC
echo   Sans GabCon Studio
echo.
echo [1] Depuis une description (IA OpenRouter/Ollama configuree)
echo [2] Depuis un fichier Python DSL ChatGPT (aucune API)
echo.
choice /c 12 /n /m "Choix [1/2] : "
if errorlevel 2 goto blueprint

:prompt
echo.
set /p "BUILD_PROMPT=Description de la construction : "
if not defined BUILD_PROMPT goto empty
echo.
echo Mode IA : un modele doit etre configure dans .env.
uv run python tools/create_schematic.py --prompt "%BUILD_PROMPT%" --out "generated/direct-%RANDOM%-%RANDOM%" --preview fast
goto end

:blueprint
echo.
set /p "BLUEPRINT_PATH=Chemin du blueprint .py : "
if not defined BLUEPRINT_PATH goto empty
uv run python tools/create_schematic.py --blueprint "%BLUEPRINT_PATH%" --out "generated/direct-%RANDOM%-%RANDOM%" --preview fast
goto end

:empty
echo Aucun texte ou chemin fourni.
:end
echo.
echo Les fichiers sont dans le dossier generated\.
pause
