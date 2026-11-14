
@echo off
cd /d "%~dp0"
title PlatinumPath - Sincronizar trofeus recentes
py -3.14 -c "import psnawp_api" >nul 2>&1
if errorlevel 1 (
  echo A instalar a biblioteca PSNAWP no Python 3.14...
  py -3.14 -m pip install PSNAWP
  if errorlevel 1 (
    echo ERRO: nao foi possivel instalar PSNAWP.
    echo Confirma que tens Python 3.14 com pip e Internet.
    pause
    exit /b 1
  )
)
py -3.14 atualizar_recentes.py
if errorlevel 1 echo A sincronizacao nao ficou totalmente concluida. Verifica as mensagens acima.
echo.
pause
