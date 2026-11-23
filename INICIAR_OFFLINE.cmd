@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PlatinumPath - Iniciar offline
if not exist ".venv\Scripts\python.exe" goto nao_instalado
".venv\Scripts\python.exe" "abrir_platinumpath.py" --offline
if errorlevel 1 goto erro
exit /b 0
:nao_instalado
echo FALTA INSTALAR: executa INSTALAR.cmd uma vez antes de iniciar.
goto erro
:erro
echo.
echo Nao foi possivel iniciar o PlatinumPath. Consulta a mensagem acima.
pause
exit /b 1
