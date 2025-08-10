#!/bin/bash

# Script para configurar el entorno de GitHub Actions
# Este script se ejecuta antes de los scripts principales

echo "🔧 Configurando entorno para GitHub Actions..."

# Crear directorio de datos
mkdir -p data

# Verificar si existe data de artifacts anteriores
if [ -d "/tmp/car-data" ]; then
    echo "📥 Restaurando datos de artifacts anteriores..."
    cp -r /tmp/car-data/* data/ 2>/dev/null || true
fi

# Configurar variables de entorno para que los scripts usen el directorio data/
export ARCHIVO_COCHES="data/coches.json"
export ARCHIVO_COCHES_ELIMINADO="data/coches_eliminados.json"

echo "✅ Entorno configurado:"
echo "   - Directorio de datos: $(pwd)/data"
echo "   - Archivo coches: $ARCHIVO_COCHES"
echo "   - Archivo eliminados: $ARCHIVO_COCHES_ELIMINADO"

# Verificar archivos existentes
if [ -f "$ARCHIVO_COCHES" ]; then
    count=$(jq length "$ARCHIVO_COCHES" 2>/dev/null || echo "0")
    echo "   - Coches existentes: $count"
fi

if [ -f "$ARCHIVO_COCHES_ELIMINADO" ]; then
    count=$(jq length "$ARCHIVO_COCHES_ELIMINADO" 2>/dev/null || echo "0")
    echo "   - Coches eliminados: $count"
fi
