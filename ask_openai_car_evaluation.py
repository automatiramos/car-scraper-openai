#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-----------------------------------
• Recopila campos seleccionados de cada coche.
• Envía solo la descripción del equipamiento a la API.
• Guarda cada resultado como archivo JSON en la carpeta "cars".
"""

import json
import pathlib
import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# 1) ------------- Cargar clave desde .env -----------------
load_dotenv()
client = OpenAI()

FICHERO_ENTRADA = os.getenv("ARCHIVO_COCHES")
CARPETA_SALIDA = pathlib.Path("cars")
CARPETA_SALIDA.mkdir(exist_ok=True)

# 2) ------------- Definir prompt optimizado ---------------
PROMPT_SYSTEM = """
Eres un asistente experto en valorar el equipamiento y extras de un coche.
Recibes únicamente un texto con la descripción de equipamiento del vehículo (por ejemplo: pintura, elevalunas eléctricos, faros antiniebla, llantas de aleación, rueda de repuesto, multimedia, etc.).
A partir de esta descripción, genera un objeto JSON con los siguientes campos:
{
    "consumo_eficiencia": string,     // valoración de eficiencia y consumo basado en equipamiento
    "coste_mantenimiento": string,    // estimación de coste de mantenimiento por el equipamiento descrito
    "seguridad_equipo": string,       // elementos de seguridad (faros antiniebla, asistencias, etc.)
    "confort_tecnologia": string,     // elementos de confort y tecnología (aire acondicionado, multimedia, conectividad, etc.)
    "estilo_exterior": string,        // pintura y diseño exterior (color, acabado, llantas)
    "equipo_ruedas": string           // descripción y valor del equipamiento de ruedas (neumáticos, repuesto)
}
Devuelve **solo** el JSON, sin texto adicional ni comentarios.
"""

# 3) ------------- Función de extracción ------------------ ------------- Función de extracción ------------------
def extraer_info_coche(descripcion: str) -> dict:
    """
    Envía la descripción del coche y recibe un JSON con la valoración.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=300,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": descripcion}
        ]
    )

    content = response.choices[0].message.content
    if isinstance(content, str):
        try:
            evaluacion = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Respuesta JSON inválida: {e}\n{content}")
    elif isinstance(content, dict):
        evaluacion = content
    else:
        raise TypeError(f"Formato de respuesta inesperado: {type(content)}")
    return evaluacion

# 4) ------------- Fusionar diccionarios ------------------
def fusionar_datos(original: dict, evaluacion: dict) -> dict:
    """
    Combina el diccionario original con la evaluación, priorizando los valores de evaluación.
    """
    return {**original, **evaluacion}

# 5) ------------- Guardar en archivos JSON ----------------
def guardar_diccionario_en_json(diccionario: dict) -> None:
    """
    Guarda el diccionario completo en cars/<id>.json.
    """
    identificador = diccionario.get("url", "").split("/")[-1] or diccionario.get("modelo", "vehiculo").replace(" ", "_")
    archivo_salida = CARPETA_SALIDA / f"{identificador}.json"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(diccionario, f, ensure_ascii=False, indent=2)
    print(f"✅ Guardado: {archivo_salida}")

# 6) ------------- Carga de datos -------------------------
def cargar_coches(path: str):
    """Generador de dicts coche desde JSON o JSONL."""
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

def guardar_resultado_en_unico_json (diccionario: dict) -> None:
    """
    Guarda el resultado en un único archivo JSON.
    """
    DATE = datetime.now().strftime("%Y-%m-%d")

    archivo_salida = CARPETA_SALIDA / f"resultado_final_{DATE}.json"
    with open(archivo_salida, "a", encoding="utf-8") as f:
        json.dump(diccionario, f, ensure_ascii=False, indent=2)
    print(f"✅ Resultado final guardado: {archivo_salida}")
# 7) ------------- Script principal -----------------------
if __name__ == "__main__":
    total, fallos = 0, 0
    CAMPOS_EXTRAIDOS = [
        "modelo", "motor_info", "año", "km_por_año",
        "descripcion", "emisiones de co2", "neumáticos"
    ]

    for raw in cargar_coches(FICHERO_ENTRADA):
        total += 1
        descripcion = raw.get("descripcion", "")
        print(f"Evaluando coche {total}, descripción: {descripcion}")
        try:
            detalles = extraer_info_coche(descripcion)
            if not isinstance(detalles, dict):
                raise TypeError("La evaluación debe ser un dict, se obtuvo otro tipo.")
            resultado = fusionar_datos(raw, detalles)
            guardar_resultado_en_unico_json(resultado)
            print(f"✓ [{total}] Evaluado correctamente.")
        except Exception as e:
            fallos += 1
            print(f"⚠️  Error en registro {total}: {e}")

    print(f"\nProceso terminado. Evaluados: {total - fallos} | Fallidos: {fallos}")
