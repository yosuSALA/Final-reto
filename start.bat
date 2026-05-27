@echo off
echo ========================================================
echo   Iniciando Auditor Agéntico de Facturación de Siniestros
echo ========================================================
echo.

echo Instalando dependencias...
npm install
pip install -r backend\requirements.txt

echo El sistema estara disponible en: http://localhost:8000/app/

python -m uvicorn backend.main:app --reload --port 8000
