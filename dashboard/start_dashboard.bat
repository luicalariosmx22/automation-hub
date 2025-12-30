@echo off
REM Inicia el dashboard de jobs local
REM
REM Uso: Doble click en este archivo o ejecuta desde terminal

echo ====================================
echo   AUTOMATION HUB - Dashboard Local
echo ====================================
echo.
echo Iniciando servidor Flask en http://localhost:5000
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

cd /d "%~dp0\.."
set PYTHONPATH=src
python dashboard\server.py

pause
