#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-----------------------------------
• Envía la lista completa de coches para un ANÁLISIS COMPARATIVO y una RECOMENDACIÓN clara orientada a rentabilidad en Amovens (renting + subalquiler).
"""

import json
import os
import re
import glob
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Optional

# 1) ------------- Cargar clave desde .env -----------------
load_dotenv()
client = OpenAI()

# Crear directorio de datos si no existe
DATA_DIR = os.path.join(os.getcwd(), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

FICHERO_ENTRADA = os.getenv("ARCHIVO_COCHES", os.path.join(DATA_DIR, "coches.json"))
MODELO_ANALISIS = os.getenv("OPENAI_MODEL_ANALISIS", "gpt-4o-mini")

# Archivo para guardar análisis histórico completo
ARCHIVO_ANALISIS = os.path.join(DATA_DIR, "analisis.json")

# 2) ------------- Prompt para análisis --------------------------------

PROMPT_ANALISIS_SYSTEM = """
Eres un analista de rentabilidad para renting + subalquiler P2P en Amovens.
Objetivo: calcular el beneficio neto mensual por coche con reglas fijas.

Parámetros fijos:

Segmento y precio_alquiler_dia:
- Segmento B: 32 €
- Segmento C: 35 €
- SUV compacto: 42 €
Determinar segmento según modelo o descripción.

coste_renting:
- Es el número del campo "precio" (en euros/mes).

puntos_extra (sumar todos los aplicables):
+3 si automático
+3 si etiqueta ECO o 0
+3 si diésel eficiente
+1 si CarPlay o Android Auto
+1 si sensores o cámara
+2 si buen espacio interior/maletero
+1 si aire acondicionado/climatizador
+2 si mantenimiento documentado
+1 si entrega flexible (acceso sin llave)

ponderación: (añadir al campo ponderación)
Si es automático añadir "Es automático"
Si es etiqueta ECO añadir "Es etiqueta ECO"
Si es diésel eficiente añadir "Es diésel eficiente"
Si tiene CarPlay o Android Auto añadir "Tiene CarPlay o Android Auto"
Si tiene sensores o cámara añadir "Tiene sensores o cámara"
Si tiene buen espacio interior/maletero añadir "Tiene buen espacio interior/maletero"
Si tiene aire acondicionado/climatizador añadir "Tiene aire acondicionado/climatizador"
Si tiene mantenimiento documentado añadir "Tiene mantenimiento documentado"
Si tiene entrega flexible (acceso sin llave) añadir "Tiene entrega flexible (acceso sin llave)"

etiqueta_ambiental:
La etiqueta_ambiental SOLO puede ser uno de estos CUATRO valores EXACTOS (nunca otro):
- "0":  BEV, REEV, PHEV >40 km
- "ECO":  híbridos/gas que cumplan C
- "C":  gasolina desde 2006 o diésel desde sept-2015
- "B":  gasolina desde 2001 o diésel desde 2006
No devuelvas nunca ningún otro valor, ni "E", ni "D", ni "A", ni vacío, ni null. Si no puedes determinar la etiqueta, escribe NO DETERMINADO

consumo:
- Usar valor en l/100km si está disponible.
- Si no, estimar = (emisiones_CO2_gkm ÷ 23), redondeado a 1 decimal.

ingresos_mensuales:
- B/C: precio_alquiler_dia × 13 × 0.8
- SUV: precio_alquiler_dia × 10 × 0.8

beneficio_neto:
= ingresos_mensuales - coste_renting

Salida:
Devuelve ÚNICAMENTE un JSON puro, sin texto extra ni marcas de formato, con una lista de objetos.
Cada objeto debe contener:
url, precio_alquiler_dia, ingresos_mensuales, coste_renting, beneficio_neto, etiqueta_ambiental, consumo, puntos_extra, ponderación, segmento
"""
# Plantilla para el mensaje del usuario
PROMPT_ANALISIS_USER_TEMPLATE = """
Lista de coches para analizar rentabilidad.

Datos de entrada por coche:
- url
- modelo
- precio
- motor_info
- km_por_año
- año
- descripcion
- emisiones de co2

Instrucciones:
1. Determinar segmento (B, C o SUV) según el modelo/tipo.
2. Asignar precio_alquiler_dia según segmento (usar reglas del prompt system).
3. Calcular ingresos_mensuales:
   - B/C: precio_alquiler_dia × 13 × 0.8
   - SUV: precio_alquiler_dia × 10 × 0.8
4. Extraer coste_renting (número del campo precio).
5. Calcular beneficio_neto = ingresos_mensuales - coste_renting.
6. Calcular consumo en l/100km (usar valor directo o emisiones/23).
7. Determinar etiqueta_ambiental según reglas.
8. Calcular puntos_extra sumando todos los que correspondan.
9. Añadir ponderación según características del coche.
10. Devolver todos los datos calculados y el segmento detectado.

Salida:
Devolver SOLO un JSON con una lista de objetos, cada uno con:
url, precio_alquiler_dia, ingresos_mensuales, coste_renting, beneficio_neto, etiqueta_ambiental, consumo, puntos_extra, ponderación, segmento

Coches:
{json_coches}
"""

# ------------- Carga de datos -------------------------
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

def analizar_coches_para_renting(lista_coches: List[Dict]) -> str:
    """
    Envía la lista de coches a OpenAI para un análisis comparativo y una recomendación clara.
    """

    user_msg = PROMPT_ANALISIS_USER_TEMPLATE.format(json_coches=json.dumps(lista_coches, ensure_ascii=False, indent=2))

    resp = client.chat.completions.create(
        model=MODELO_ANALISIS,
        temperature=0.0,  # Máxima consistencia
        messages=[
            {"role": "system", "content": PROMPT_ANALISIS_SYSTEM},
            {"role": "user", "content": user_msg}
        ]
    )
    
    analisis_coches_nuevos = resp.choices[0].message.content.strip()


    return  analisis_coches_nuevos

def ponderar_coches(coches: List[Dict]) -> List[Dict]:
    """
    Pondera los coches según su rentabilidad y otros factores.
    """
    # Reglas si el km_por_año < 10.000
    for coche in coches:
        if coche.get("km_por_año", 0) < 10000:
            coche["puntos_extra"] = coche.get("puntos_extra", 0) + 1
            coche["ponderación"] =  coche.get("ponderación", "") + "* Kms por año menor de 10.000 * "
        if coche.get("beneficio_neto", 0) > 0 < 50:
            coche["puntos_extra"] = coche.get("puntos_extra", 0) + 1
            coche["ponderación"] = coche.get("ponderación", "") + "* Beneficio neto positivo * "
        if coche.get("beneficio_neto") > 50:
            coche["puntos_extra"] = coche.get("puntos_extra", 0) + 1
            coche["ponderación"] = coche.get("ponderación", "") + "* Beneficio neto alto *"
        if coche.get("etiqueta_ambiental") == "0" or coche.get("etiqueta_ambiental") == "ECO":
            coche["puntos_extra"] = coche.get("puntos_extra", 0) + 1
            coche["ponderación"] = coche.get("ponderación", "") + "* Etiqueta ambiental 0 o ECO *"
        if coche.get("consumo", 0) < 5.5:
            coche["puntos_extra"] = coche.get("puntos_extra", 0) + 1
            coche["ponderación"] = coche.get("ponderación", "") + "* Consumo menor de 5.5 l/100km *"
    # Ordenar por beneficio neto
    coches = sorted(coches, key=lambda x: (x.get("beneficio_neto", 0)), reverse=True)

    return coches

def crear_informe(coches: List[Dict]) -> str:
    """
    Crea un informe a partir de la lista de coches ponderados.
    """
    # Cabecera
    informe = (
        "🚗 INFORME DE RENTABILIDAD DE COCHES PARA RENTING + SUBALQUILER 🚗\n"
        "============================================================\n\n"
        "📊 Resumen de los coches analizados y ponderados para rentabilidad en renting + subalquiler (Amovens).\n\n"
    )
    # Tabla principal
    headers = [
        "Modelo", "Año", "Km/año", "Precio/día", "Ingresos", "Renting", "Beneficio", "Etiqueta", "Consumo", "Puntos", "Ponderación"
    ]
    rows = []
    for coche in coches:
        rows.append([
            str(coche.get('modelo', '')),
            str(coche.get('año', '')),
            str(coche.get('km_por_año', '')),
            f"{coche.get('precio_alquiler_dia', 0):.2f}" if coche.get('precio_alquiler_dia') is not None else '',
            f"{coche.get('ingresos_mensuales', 0):.2f}" if coche.get('ingresos_mensuales') is not None else '',
            f"{coche.get('coste_renting', 0):.2f}" if coche.get('coste_renting') is not None else '',
            f"{coche.get('beneficio_neto', 0):.2f}" if coche.get('beneficio_neto') is not None else '',
            str(coche.get('etiqueta_ambiental', '')),
            str(coche.get('consumo', '')),
            str(coche.get('puntos_extra', '')),
            str(coche.get('ponderación', ''))
        ])
    # Ajustar anchos
    col_widths = [max(len(str(x)) for x in [h] + [row[i] for row in rows]) for i, h in enumerate(headers)]
    # Construir tabla
    def format_row(row):
        return " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))
    informe += format_row(headers) + "\n"
    informe += "-+-".join('-' * w for w in col_widths) + "\n"
    for row in rows:
        informe += format_row(row) + "\n"

    informe += "\n🏆 TOP 3 COCHES MÁS RENTABLES 🏆\n==========================\n"
    coches_top = sorted(coches, key=lambda x: (x.get("beneficio_neto", 0), x.get("puntos_extra", 0)), reverse=True)[:3]
    for idx, coche in enumerate(coches_top, 1):
        medalla = "🥇" if idx == 1 else ("🥈" if idx == 2 else "🥉")
        informe += f"\n{medalla} #{idx}: {coche.get('modelo', '')} ({coche.get('año', '')})\n"
        informe += f"🔗 URL: {coche.get('url', '')}\n"
        informe += f"📄 Contrato: {coche.get('contrato', '')}\n"
        informe += f"🛠️ Uso: {coche.get('uso', '')}\n"
        informe += f"🔄 Estado actualización: {coche.get('estado_actualizacion', '')}\n"
        informe += f"🚙 Motor: {coche.get('motor_info', '')}\n"
        informe += f"📝 Descripción: {coche.get('descripcion', '')}\n"
        informe += f"📉 Kilometraje: {coche.get('kilometraje', '')}\n"
        informe += f"🎨 Color: {coche.get('color', '')}\n"
        informe += f"📆 Km/año: {coche.get('km_por_año', '')}\n"
        informe += f"💶 Precio alquiler/día: {coche.get('precio_alquiler_dia', '')}\n"
        informe += f"💰 Ingresos mensuales: {coche.get('ingresos_mensuales', '')}\n"
        informe += f"💸 Coste renting: {coche.get('coste_renting', '')}\n"
        informe += f"📈 Beneficio neto: {coche.get('beneficio_neto', '')}\n"
        informe += f"♻️ Etiqueta ambiental: {coche.get('etiqueta_ambiental', '')}\n"
        informe += f"⛽ Consumo: {coche.get('consumo', '')}\n"
        informe += f"🚦 Segmento: {coche.get('segmento', '')}\n"
        informe += f"⭐ Puntos extra: {coche.get('puntos_extra', '')}\n"
        informe += f"🏷️ Ponderación: {coche.get('ponderación', '')}\n"

    informe += "\n✅ -- Fin del informe -- ✅\n"
    return informe

# 1) ------------- Análisis de coches para renting -----------------------
if __name__ == "__main__":
    print("🚗 Cargando lista de coches...")
    coches = list(cargar_coches(FICHERO_ENTRADA))
    print(f"✅ Lista de coches cargada: {len(coches)} coches encontrados.")

    # Solo se analizan los coches nuevos. Los coches con estado 'sin_cambios' ya han sido analizados previamente
    # y están en la lista de coches ponderados, por lo que no se vuelven a enviar a OpenAI ni a recalcular.
    print("🆕 Filtrando coches nuevos...")
    coches_nuevos = [coche for coche in coches if coche.get("estado_actualizacion") == "nuevo"]
    print(f"✅ Lista de coches nuevos: {len(coches_nuevos)} coches encontrados.")

    print("🤖 Enviando coches nuevos a OpenAI para análisis...")
    analisis_coches_nuevos = analizar_coches_para_renting(coches_nuevos)
    print("✅ Análisis de coches para renting completado de los coches nuevos.")

    print("💾 Guardando análisis de coches nuevos en JSON...")
    with open(ARCHIVO_ANALISIS.split('.')[0] + "_coches_nuevos.json", "w", encoding="utf-8") as f:
        f.write(analisis_coches_nuevos)

    print("🔄 Actualizando información de coches con análisis...")
    coches_nuevos_actualizados = []
    for analisis in json.loads(analisis_coches_nuevos):
        url = analisis.get("url")
        if url:
            for coche in coches_nuevos:
                if coche.get("url") == url:
                    coche.update(analisis)
                    coches_nuevos_actualizados.append(coche)
                    break

    print("💾 Guardando coches actualizados...")
    with open(ARCHIVO_ANALISIS.split('.')[0] + "_coches_nuevos_actualizados.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(coches_nuevos_actualizados, ensure_ascii=False, indent=2))

    print("📊 Ponderando coches según reglas de rentabilidad...")
    coches_nuevos_ponderados = ponderar_coches(coches_nuevos_actualizados)
    print(f"✅ Coches nuevos ponderados: {len(coches_nuevos_ponderados)} coches.")

    
    print("💾 Guardando coches nuevos ponderados...")
    with open(ARCHIVO_ANALISIS.split('.')[0] + "_coches_nuevos_ponderados.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(coches_nuevos_ponderados, ensure_ascii=False, indent=2))

    coches_ponderados = []
    coches_ponderados_anteriormente = list(cargar_coches(ARCHIVO_ANALISIS.split('.')[0] + "_coches_ponderados.json"))

    # Guardar los datos completos del coche que estén en coches_nuevos_ponderados o coches_ponderados_anteriormente
    for coche in coches:
        url = coche.get("url")
        # Buscar primero en los nuevos ponderados
        coche_nuevo = next((c for c in coches_nuevos_ponderados if c.get("url") == url), None)
        if coche_nuevo:
            coches_ponderados.append(coche_nuevo)
            continue
        # Si no está, buscar en los ponderados anteriores
        coche_ant = next((c for c in coches_ponderados_anteriormente if c.get("url") == url), None)
        if coche_ant:
            coches_ponderados.append(coche_ant)

    with open(ARCHIVO_ANALISIS.split('.')[0] + "_coches_ponderados.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(coches_ponderados, ensure_ascii=False, indent=2))

    print("📝 Generando informe final...")
    informe = crear_informe(coches_ponderados)

    print("💾 Guardando informe en TXT...")
    with open(ARCHIVO_ANALISIS.split('.')[0] + "_informe.txt", "w", encoding="utf-8") as f:
        f.write(informe)

    print("🎉 Proceso completado. ¡Consulta los archivos generados en la carpeta data! 🚀")