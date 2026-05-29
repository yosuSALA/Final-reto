@echo off
setlocal
chcp 65001 >nul
echo ========================================================
echo   Iniciando Miraclex - Auditor Agentico de Siniestros
echo ========================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 scripts\start.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python scripts\start.py
    goto :end
)

echo No se encontro Python 3.10+ en este equipo.
echo Instala Python desde https://www.python.org/downloads/ y vuelve a ejecutar start.bat

:end
endlocal
