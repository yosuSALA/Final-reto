#!/bin/bash
set -e

echo "========================================================"
echo "  Iniciando Miraclex - Auditor Agentico de Siniestros"
echo "========================================================"
echo ""

if command -v python3 >/dev/null 2>&1; then
    python3 scripts/start.py
elif command -v python >/dev/null 2>&1; then
    python scripts/start.py
else
    echo "No se encontro Python 3.10+ en este equipo."
    echo "Instala Python y vuelve a ejecutar ./start.sh"
    exit 1
fi
