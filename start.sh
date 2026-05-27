#!/bin/bash
echo "========================================================"
echo "  Iniciando Auditor Agéntico de Facturación de Siniestros"
echo "========================================================"
echo ""

echo "Instalando dependencias..."
pip install -r backend/requirements.txt

echo ""
echo "Iniciando servidor backend y frontend..."
echo "El sistema estara disponible en: http://localhost:8000/app/"
echo ""

python3 -m uvicorn backend.main:app --reload --port 8000
