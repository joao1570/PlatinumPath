@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PlatinumPath - Atualizar trofeus
if not exist ".venv\Scripts\python.exe" goto nao_instalado
".venv\Scripts\python.exe" "atualizar_recentes.py"
if errorlevel 1 goto erro
echo.
echo Sincronizacao terminada. Verifica os resultados acima.
pause
exit /b 0
:nao_instalado
echo FALTA INSTALAR: executa INSTALAR.cmd uma vez antes de iniciar.
goto erro
:erro
echo.
echo Sincronizacao nao concluida. Consulta a mensagem acima.
pause
exit /b 1
