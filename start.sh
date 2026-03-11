#!/bin/bash

echo "========================================"
echo "  API Backend - Consolidador REM"
echo "========================================"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 no instalado"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Verificar dependencias
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 Instalando dependencias..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: No se pudieron instalar dependencias"
        exit 1
    fi
fi

echo "✅ Dependencias instaladas"
echo ""

# Verificar .env
if [ ! -f .env ]; then
    echo "⚠️  ADVERTENCIA: Archivo .env no encontrado"
    echo "📋 Copiando .env.example a .env"
    cp .env.example .env
    echo ""
    echo "⚡ IMPORTANTE: Editar .env con credenciales de SQL Server"
    echo "Presiona Enter para continuar..."
    read
fi

# Crear carpetas
mkdir -p uploads logs

echo ""
echo "========================================"
echo "  Iniciando API en http://localhost:8000"
echo "  Documentación: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
