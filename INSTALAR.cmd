@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PlatinumPath - Instalacao automatica
echo.
echo =========================================
echo        PLATINUMPATH - INSTALACAO
echo =========================================
echo.

if not exist "app.py" goto falta_arquivos
if not exist "requirements.txt" goto falta_arquivos
if not exist "preparar_instalacao.py" goto falta_arquivos

where py >nul 2>&1
if errorlevel 1 goto falta_python
py -3.14 -c "import sys;sys.exit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
if errorlevel 1 goto falta_python

echo [1/3] A preparar ambiente virtual Python 3.14...
if not exist ".venv\Scripts\python.exe" (
  py -3.14 -m venv ".venv"
  if errorlevel 1 goto falha
)
set "PYTHON_LOCAL=%CD%\.venv\Scripts\python.exe"
"%PYTHON_LOCAL%" -c "import sys;sys.exit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
if errorlevel 1 (
  echo ERRO: a pasta .venv existente nao utiliza Python 3.14.
  echo Guarda os teus dados, elimina apenas a pasta .venv e repete a instalacao.
  goto falha
)

echo.
echo [2/3] A instalar dependencias...
"%PYTHON_LOCAL%" -m pip install --disable-pip-version-check -r "requirements.txt"
if errorlevel 1 goto falha

echo.
echo [3/3] A guardar backup e preparar base de dados...
"%PYTHON_LOCAL%" "preparar_instalacao.py"
if errorlevel 1 goto falha

echo.
echo =========================================
echo        INSTALACAO CONCLUIDA!
echo =========================================
echo.
echo Para iniciar, abre INICIAR_COM_PSN.cmd ou INICIAR_OFFLINE.cmd.
echo O programa abre automaticamente no navegador.
echo Fecha a janela de comandos para parar o servidor.
echo.
pause
exit /b 0

:falta_python
echo ERRO: Python 3.14 e/ou o Python Launcher nao foi encontrado.
echo Instala Python 3.14 para Windows com o launcher py e tenta novamente.
goto falha

:falta_arquivos
echo ERRO: faltam ficheiros do PlatinumPath nesta pasta.
echo Extrai o ZIP e copia o conteudo para a pasta original do projeto.
goto falha

:falha
echo.
echo A instalacao nao ficou concluida. Le as mensagens acima.
pause
exit /b 1
