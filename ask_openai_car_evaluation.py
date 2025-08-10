#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-----------------------------------
• Envía la lista completa de coches para un ANÁLISIS COMPARATIVO y una RECOMENDACIÓN clara orientada a rentabilidad en Amovens (renting + subalquiler).
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict

# 1) ------------- Cargar clave desde .env -----------------
load_dotenv()
client = OpenAI()

# Crear directorio de datos si no existe
DATA_DIR = os.path.join(os.getcwd(), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

FICHERO_ENTRADA = os.getenv("ARCHIVO_COCHES", os.path.join(DATA_DIR, "coches.json"))
MODELO_ANALISIS = os.getenv("OPENAI_MODEL_ANALISIS", "gpt-4o-mini")

# 2) ------------- Prompt para análisis --------------------------------

PROMPT_ANALISIS_SYSTEM = """
Eres un analista de movilidad y rentabilidad para renting + subalquiler P2P en Amovens.
Tu objetivo: elegir el coche que maximize el beneficio neto mensual (ingresos por alquiler - coste renting - comisiones - costes variables), cumpliendo las restricciones dadas.

Contexto clave (usar estrictamente):
- Ubicación: Madrid centro (alta demanda urbana y escapadas). Priorización ambiental: distintivo 0 preferente. Si contradice otras restricciones del usuario (p. ej. descartar eléctricos), entonces prioriza ECO; si no hay ECO válidos, usa C como última opción y justifica.
- El usuario descarta eléctricos puros (BEV). PHEV sólo si encaja con el resto de requisitos (ojo: suelen ser automáticos).
- Transmisión preferida: manual.
- Plazas: mínimo 5. Maletero: razonable para viajes (valóralo si hay datos).
- Extras valorados: CarPlay/Android Auto y sensores.
- Ocupación objetivo: 12-15 días/mes.
- Perfil: particular (no considerar deducciones de IVA).

Estimación de precio/día (cuando no haya datos de mercado explícitos):
- Parte de un precio base por segmento y uso urbano-turismo en Madrid y ajusta:
  • Segmento B/compacto manual: base 27-33 €/día.
  • SUV compacto manual: base 40-45 €/día.
- Ajustes:
  • Cambio automático: +10% (pero el usuario prefiere manual; si es automático y el resto compensa, justifícalo).
  • Híbrido/PHEV: +5-10% si aporta etiqueta y ahorro real.
  • Diésel en ciudad: -5% salvo que sea claramente eficiente para viajes largos.
  • CarPlay/Android Auto y sensores: +5%.
  • Estacionalidad (verano/puentes): +10-15% (aplícalo sólo en tabla de sensibilidad).
- Si alguna estimación es incierta, usa el punto medio del rango y deja claro el supuesto.

Cálculo económico:
- Ingresos por alquiler = precio_día_estimado * días_ocupación * (1 - comisión_amovens)
- Comisión Amovens: si no se indica, asume 20% (expresa este supuesto).
- Costes variables: combustible/energía a cargo del inquilino (ignóralos). Considera un pequeño % de riesgos/limpieza imprevista si lo crees necesario (1-3%).
- Coste renting mensual: usa el campo "precio" (se asume IVA incluido).
- Beneficio neto mensual = ingresos - renting - otros costes asumidos.

FORMATO DE SALIDA ESPECÍFICO (TEXTO PLANO para correo electrónico):

===========================================
🚗 ANÁLISIS DE RENTABILIDAD - COCHES RENTING
===========================================

📅 Fecha: [FECHA_ACTUAL]
📍 Ubicación: Madrid  
🎯 Objetivo: Renting + Subalquiler P2P

SUPUESTOS DE ANÁLISIS:
- Ocupación esperada: 12 a 15 días/mes
- Comisión Amovens: 20%
- Filtros: Manual preferente, descartados eléctricos puros
- Precios base por segmento en Madrid

COMPARATIVA COMPLETA:
[Tabla con formato fijo de columnas usando espacios]

TOP 3 RECOMENDADOS:
🥇 [Modelo] - [Puntuación]/100
   💰 Beneficio neto: [X]€/mes | Precio: [Y]€/mes
   🔗 https://amovens.com/leasing/ald/[ID]
   📝 [Justificación en 3 líneas]
   📋 DATOS COMPLETOS DEL COCHE:
   {JSON completo del coche con todos los datos scrapeados}

🥈 [Modelo] - [Puntuación]/100  
   💰 Beneficio neto: [X]€/mes | Precio: [Y]€/mes
   🔗 https://amovens.com/leasing/ald/[ID]
   📝 [Justificación en 3 líneas]
   📋 DATOS COMPLETOS DEL COCHE:
   {JSON completo del coche con todos los datos scrapeados}

🥉 [Modelo] - [Puntuación]/100
   💰 Beneficio neto: [X]€/mes | Precio: [Y]€/mes
   🔗 https://amovens.com/leasing/ald/[ID]
   📝 [Justificación en 3 líneas]
   📋 DATOS COMPLETOS DEL COCHE:
   {JSON completo del coche con todos los datos scrapeados}

RECOMENDACIÓN FINAL:
[Recomendación clara y justificación económica]

===========================================

Si faltan datos (p. ej. maletero), indícalo y no penalices en exceso; usa inferencias prudentes por segmento.
Usa este formato EXACTO para facilitar el envío por email.
"""

PROMPT_ANALISIS_USER_TEMPLATE = """
Aquí tienes la lista de coches disponibles para renting en Amovens. Cada coche incluye:
- url: enlace directo al anuncio 
- modelo, año, precio (cuota mensual), uso (Seminuevo)
- motor_info, km_por_año, descripcion, emisiones de co2
- localización, kilometraje, color, neumáticos, etc.

Analiza comparativamente y recomienda el más rentable usando el FORMATO ESPECÍFICO indicado en las instrucciones del sistema.

OBLIGATORIO: 
1. Usar el formato exacto con títulos, tablas y emojis especificados
2. Incluir URLs completas en el TOP 3
3. Crear tabla comparativa con columnas alineadas usando espacios (SIN incluir "Coste renting", solo usar precio/mes)
4. Usar separadores visuales (=======) para secciones
5. IMPORTANTE: En cada coche del TOP 3, incluir el JSON completo con TODOS los datos scrapeados bajo "📋 DATOS COMPLETOS DEL COCHE"

El análisis debe ser directo, profesional y listo para enviar por email con toda la información detallada.

COCHES DISPONIBLES:
{json_coches}
"""

# 3) ------------- Análisis comparativo con ChatGPT -------------
def analizar_coches_para_renting(lista_coches: List[Dict]) -> str:
    """
    Envía la lista completa de coches y obtiene un análisis comparativo y una recomendación clara.
    """
    # (Opcional) pre-normalizar campos útiles para el análisis
    coches_norm = []
    for c in lista_coches:
        coches_norm.append({
            **c
        })

    json_coches = json.dumps(coches_norm, ensure_ascii=False, indent=2)
    user_msg = PROMPT_ANALISIS_USER_TEMPLATE.format(json_coches=json_coches)

    resp = client.chat.completions.create(
        model=MODELO_ANALISIS,
        temperature=0.2,
        messages=[
            {"role": "system", "content": PROMPT_ANALISIS_SYSTEM},
            {"role": "user", "content": user_msg}
        ]
    )
    return resp.choices[0].message.content.strip()

# 4) ------------- Carga de datos -------------------------
def cargar_coches(path: str):
    """Generador de dicts coche desde JSON o JSONL."""
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró ARCHIVO_COCHES: {path}")
    with open(path, "r", encoding="utf-8") as f:
        primero = f.read(1)
        f.seek(0)
        if primero == "[":
            for coche in json.load(f):
                yield coche
        else:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

# 5) ------------- Script principal -----------------------
if __name__ == "__main__":
    coches_lista = list(cargar_coches(FICHERO_ENTRADA))
    
    if not coches_lista:
        print("ℹ️ No se encontraron coches para analizar.")
        exit(1)
    
    print(f"📊 Analizando {len(coches_lista)} coches para renting...")
    
    try:
        analisis = analizar_coches_para_renting(coches_lista)
        date_tag = datetime.now().strftime("%Y-%m-%d_%H-%M")
        out_file = os.path.join(DATA_DIR, f"analisis_rentabilidad_{date_tag}.txt")
        
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(analisis)
        
        print(f"\n📈 Análisis comparativo guardado en: {out_file}\n")
        print(analisis)
        
    except Exception as e:
        print(f"❌ Error generando análisis: {e}")
