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
ARCHIVO_ANALISIS_HISTORICO = os.path.join(DATA_DIR, "analisis_historico.json")

# 2) ------------- Prompt para análisis --------------------------------

PROMPT_ANALISIS_SYSTEM = """
Eres un analista de movilidad y rentabilidad para renting + subalquiler P2P en Amovens.
Tu objetivo: calcular el beneficio neto mensual EXACTO para cada coche.

PARÁMETROS FIJOS (usar siempre estos valores):
- Ocupación: EXACTAMENTE 13 días/mes (compactos/medianos), 10 días/mes (SUVs)
- Comisión Amovens: EXACTAMENTE 20%
- Ubicación: Madrid centro
- NO incluir vehículos eléctricos (BEV)
- Redondear SIEMPRE hacia abajo (sin decimales)

ESTIMACIÓN DE PRECIO/DÍA (ser conservador):
Usa estos precios base para Madrid y ajusta según características:
- Referencia: Renault Clio 2019 = 38€/día (lunes)
- Segmento B/compacto: base 35-40€/día
- Segmento C/mediano: base 39-41€/día  
- SUV compacto: base 40-45€/día

AJUSTES OBLIGATORIOS:
- Cambio automático: +3€/día
- Híbrido/PHEV: +3€/día (solo si aporta etiqueta ECO o 0)
- Motor diésel eficiente: +3€/día
- CarPlay/Android Auto: +1€/día
- Sensores parking: +1€/día
- Km/año >18.000: -3€/día
- Km/año <13.000: +2€/día

ETIQUETAS AMBIENTALES ESPAÑOLAS (usar solo estas 4):
- ETIQUETA 0 (Azul): Vehículos más eficientes. BEV, REEV, PHEV con >40km autonomía, pila combustible
- ETIQUETA ECO (Verde-Azul): Híbridos, gas. PHEV <40km, HEV, GNC, GNL, GLP + criterios etiqueta C
- ETIQUETA C (Verde): Combustión Euro reciente. Gasolina desde 2006, diésel desde sept-2015
- ETIQUETA B (Amarilla): Combustión Euro anterior. Gasolina desde 2001, diésel desde 2006

CÁLCULO ECONÓMICO EXACTO:
1. Ingresos mensuales = precio_día_estimado x días_ocupación x 0.8 (descuenta comisión 20%)
   - Compactos/Medianos: precio_día x 13 x 0.8
   - SUVs: precio_día x 10 x 0.8
2. Coste renting = extraer número del campo "precio" (ej: "299 € al mes" → 299)
3. Beneficio neto = ingresos_mensuales - coste_renting

FORMATO DE SALIDA OBLIGATORIO:

===========================================
🚗 ANÁLISIS DE RENTABILIDAD - COCHES RENTING
===========================================

📅 Fecha: [FECHA_ACTUAL]
📍 Ubicación: Madrid  
🎯 Objetivo: Renting + Subalquiler P2P

PARÁMETROS FIJOS:
- Ocupación: 13 días/mes (compactos/medianos), 10 días/mes (SUVs)
- Comisión Amovens: 20%
- Filtros: Sin eléctricos, preferencia manual
- Redondeo: hacia abajo, sin decimales

TOP 10 RENTABILIDAD (ordenado por beneficio neto):

Pos | Modelo                    | Renting/mes | Precio/día | Ingresos/mes | Beneficio | Consumo | Etiqueta
----|---------------------------|-------------|------------|--------------|-----------|---------|----------
1   | [Modelo exacto]           | [X]€        | [Y]€       | [Z]€         | [W]€      | [C]l/km | [0/ECO/C/B]
2   | [Modelo exacto]           | [X]€        | [Y]€       | [Z]€         | [W]€      | [C]l/km | [0/ECO/C/B]
...hasta 10

TOP 3 RECOMENDADOS:
🥇 [Modelo] 
   💰 Beneficio neto: [X]€/mes | Renting: [Y]€/mes
   ⛽ Consumo: [C]l/km | 🏷️ Etiqueta: [0/ECO/C/B]
   🔗 [URL completa]
   📝 [Justificación basada en cálculos exactos]

🥈 [Segundo modelo con mismo formato]

🥉 [Tercer modelo con mismo formato]

RECOMENDACIÓN FINAL:
[Recomendación basada en el beneficio neto más alto]

===========================================

INSTRUCCIONES CRÍTICAS:
- Usar SIEMPRE los mismos cálculos y ajustes
- Mostrar números EXACTOS sin rangos
- Ordenar SIEMPRE por beneficio neto (mayor a menor)
- Redondear hacia abajo en todos los cálculos
- NO usar estimaciones variables, usar fórmulas fijas
- NO incluir datos completos JSON - solo URLs en el TOP 3
- IDENTIFICAR SUVs por modelo (ej: Qashqai, Tiguan, Tucson, Kuga, etc.) y usar 10 días ocupación
- Compactos/Medianos usar 13 días ocupación
"""

PROMPT_ANALISIS_USER_TEMPLATE = """
Aquí tienes la lista de coches disponibles para renting en Amovens. 

INSTRUCCIONES ESPECÍFICAS:
1. Calcular EXACTAMENTE usando las fórmulas del sistema
2. Mostrar TOP 10 en tabla ordenada por beneficio neto (mayor a menor)
3. Redondear SIEMPRE hacia abajo, sin decimales
4. Usar temperatura 0 - deben salir los MISMOS resultados cada vez
5. Filtrar automáticamente los eléctricos (BEV)
6. Incluir consumo l/km y etiqueta ambiental en tabla y TOP 3
7. IDENTIFICAR SUVs y aplicar ocupación de 10 días (vs 13 días para otros)

DATOS DE CADA COCHE:
- url: enlace directo
- modelo: nombre completo
- precio: cuota mensual de renting (extraer solo el número)
- motor_info: información del motor y transmisión
- km_por_año: kilometraje anual estimado
- consumo: l/km si está disponible
- etiqueta ambiental: 0, ECO, C, B (usar clasificación española)
- Otros: año, descripción, localización, etc.

CÁLCULO OBLIGATORIO PARA CADA COCHE:
1. Determinar precio/día según segmento + ajustes fijos
2. Calcular ingresos según tipo:
   - Compactos/Medianos: precio_día x 13 x 0.8
   - SUVs: precio_día x 10 x 0.8
3. Extraer coste renting del campo "precio"
4. Beneficio = ingresos - coste_renting
5. Mostrar consumo y etiqueta en tabla

COCHES DISPONIBLES:
{json_coches}
"""

# 3) ------------- Análisis comparativo con ChatGPT -------------
def extraer_urls_top3(texto_analisis: str) -> List[str]:
    """
    Extrae las URLs del TOP 3 del análisis generado por la IA.
    """
    urls = []
    
    # Buscar URLs en el texto del análisis
    url_pattern = r'🔗\s*(https?://[^\s\n]+)'
    matches = re.findall(url_pattern, texto_analisis)
    
    return matches[:3]  # Solo las primeras 3

def buscar_datos_coche_por_url(url: str, lista_coches: List[Dict]) -> Dict:
    """
    Busca los datos completos de un coche por su URL en la lista original.
    """
    for coche in lista_coches:
        if coche.get("url") == url:
            return coche
    return {}

def añadir_datos_completos_top3(analisis: str, lista_coches: List[Dict]) -> str:
    """
    Añade los datos completos del JSON al análisis para el TOP 3.
    """
    urls_top3 = extraer_urls_top3(analisis)
    
    if not urls_top3:
        return analisis
    
    # Buscar los datos para cada URL
    datos_completos = []
    for url in urls_top3:
        datos = buscar_datos_coche_por_url(url, lista_coches)
        if datos:
            datos_completos.append(datos)
    
    # Añadir los datos al final del análisis
    if datos_completos:
        analisis += "\n\n" + "="*60 + "\n"
        analisis += "📋 DATOS COMPLETOS DE LOS TOP 3 COCHES:\n"
        analisis += "="*60 + "\n\n"
        
        for i, datos in enumerate(datos_completos, 1):
            analisis += f"🏆 TOP {i} - DATOS COMPLETOS:\n"
            analisis += json.dumps(datos, indent=2, ensure_ascii=False)
            analisis += "\n\n" + "-"*40 + "\n\n"
    
    return analisis

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
        temperature=0.0,  # Máxima consistencia
        messages=[
            {"role": "system", "content": PROMPT_ANALISIS_SYSTEM},
            {"role": "user", "content": user_msg}
        ]
    )
    
    analisis_base = resp.choices[0].message.content.strip()
    
    # Añadir datos completos del TOP 3 desde el JSON local
    analisis_completo = añadir_datos_completos_top3(analisis_base, lista_coches)
    
    return analisis_completo

# 4) ------------- Funciones para análisis incremental -------------------------

def cargar_analisis_historico() -> Dict:
    """
    Carga el análisis histórico desde archivo JSON.
    """
    if not os.path.exists(ARCHIVO_ANALISIS_HISTORICO):
        return {"coches_analizados": {}, "top_3_actual": [], "ultimo_analisis": ""}
    
    try:
        with open(ARCHIVO_ANALISIS_HISTORICO, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"coches_analizados": {}, "top_3_actual": [], "ultimo_analisis": ""}

def guardar_analisis_historico(datos: Dict):
    """
    Guarda el análisis histórico en archivo JSON.
    """
    try:
        with open(ARCHIVO_ANALISIS_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error guardando análisis histórico: {e}")

def extraer_datos_coche_de_analisis(analisis_texto: str) -> List[Dict]:
    """
    Extrae los datos de rentabilidad de cada coche desde el texto del análisis.
    Retorna lista de diccionarios con: modelo, beneficio, precio_dia, ingresos, renting, url.
    """
    coches_data = []
    
    # Buscar la tabla TOP 10
    tabla_pattern = r'TOP 10 RENTABILIDAD.*?\n(.*?)(?=\n\nTOP 3|$)'
    tabla_match = re.search(tabla_pattern, analisis_texto, re.DOTALL)
    
    if tabla_match:
        tabla_content = tabla_match.group(1)
        # Buscar cada línea de coche en la tabla
        lineas = tabla_content.split('\n')
        for linea in lineas:
            if '|' in linea and not linea.startswith('-') and not linea.startswith('Pos'):
                partes = [p.strip() for p in linea.split('|')]
                if len(partes) >= 7:  # Pos, Modelo, Renting/mes, Precio/día, Ingresos/mes, Beneficio, Consumo, Etiqueta
                    try:
                        modelo = partes[1]
                        renting = int(re.search(r'(\d+)', partes[2]).group(1)) if re.search(r'(\d+)', partes[2]) else 0
                        precio_dia = int(re.search(r'(\d+)', partes[3]).group(1)) if re.search(r'(\d+)', partes[3]) else 0
                        ingresos = int(re.search(r'(\d+)', partes[4]).group(1)) if re.search(r'(\d+)', partes[4]) else 0
                        beneficio = int(re.search(r'(\d+)', partes[5]).group(1)) if re.search(r'(\d+)', partes[5]) else 0
                        
                        coches_data.append({
                            "modelo": modelo,
                            "beneficio": beneficio,
                            "precio_dia": precio_dia,
                            "ingresos": ingresos,
                            "renting": renting
                        })
                    except (AttributeError, ValueError, IndexError):
                        continue
    
    return coches_data

def filtrar_coches_nuevos(lista_coches: List[Dict]) -> List[Dict]:
    """
    Filtra solo los coches con estado_actualizacion: 'nuevo'.
    """
    coches_nuevos = [coche for coche in lista_coches if coche.get("estado_actualizacion") == "nuevo"]
    print(f"🆕 Encontrados {len(coches_nuevos)} coches nuevos para analizar")
    return coches_nuevos

def combinar_con_analisis_previo(nuevos_resultados: str, analisis_historico: Dict, todos_los_coches: List[Dict]) -> str:
    """
    Combina los resultados de coches nuevos con el análisis histórico y actualiza el TOP 3 si es necesario.
    """
    # Extraer datos de rentabilidad de los coches nuevos
    datos_nuevos = extraer_datos_coche_de_analisis(nuevos_resultados)
    
    # Recuperar datos del análisis previo
    coches_previos = analisis_historico.get("coches_analizados", {})
    top_3_previo = analisis_historico.get("top_3_actual", [])
    
    # Añadir los nuevos coches analizados
    for dato in datos_nuevos:
        # Buscar URL del coche en la lista completa
        coche_completo = next((c for c in todos_los_coches if c.get("modelo") == dato["modelo"]), None)
        if coche_completo:
            clave_coche = coche_completo.get("url", dato["modelo"])
            coches_previos[clave_coche] = {
                **dato,
                "url": coche_completo.get("url", ""),
                "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
    
    # Crear lista completa ordenada por beneficio
    todos_analizados = list(coches_previos.values())
    todos_analizados.sort(key=lambda x: x.get("beneficio", 0), reverse=True)
    
    # Tomar TOP 10 y TOP 3
    top_10 = todos_analizados[:10]
    top_3_nuevo = todos_analizados[:3]
    
    # Generar análisis combinado
    analisis_combinado = generar_analisis_combinado(top_10, top_3_nuevo, todos_los_coches, len(datos_nuevos))
    
    # Actualizar análisis histórico
    analisis_historico.update({
        "coches_analizados": coches_previos,
        "top_3_actual": top_3_nuevo,
        "ultimo_analisis": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_coches_analizados": len(coches_previos)
    })
    
    return analisis_combinado

def generar_analisis_combinado(top_10: List[Dict], top_3: List[Dict], todos_los_coches: List[Dict], coches_nuevos_count: int) -> str:
    """
    Genera un análisis completo con el TOP 10 y TOP 3 actualizados.
    """
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    
    analisis = f"""===========================================
🚗 ANÁLISIS DE RENTABILIDAD - COCHES RENTING
===========================================

📅 Fecha: {fecha_actual}
📍 Ubicación: Madrid  
🎯 Objetivo: Renting + Subalquiler P2P

PARÁMETROS FIJOS:
- Ocupación: 13 días/mes (compactos/medianos), 10 días/mes (SUVs)
- Comisión Amovens: 20%
- Filtros: Sin eléctricos, preferencia manual
- Redondeo: hacia abajo, sin decimales

🆕 COCHES NUEVOS ANALIZADOS: {coches_nuevos_count}
📊 TOTAL COCHES EN BASE DE DATOS: {len(top_10)}

TOP 10 RENTABILIDAD (ordenado por beneficio neto):

Pos | Modelo                    | Renting/mes | Precio/día | Ingresos/mes | Beneficio | Consumo | Etiqueta
----|---------------------------|-------------|------------|--------------|-----------|---------|----------"""
    
    for i, coche in enumerate(top_10, 1):
        # Buscar datos completos del coche
        coche_completo = next((c for c in todos_los_coches if c.get("url") == coche.get("url")), {})
        consumo = coche_completo.get("emisiones de co2", "N/A")
        etiqueta = "C"  # Valor por defecto
        
        analisis += f"\n{i:<3} | {coche['modelo']:<25} | {coche['renting']:<11}€ | {coche['precio_dia']:<10}€ | {coche['ingresos']:<12}€ | {coche['beneficio']:<9}€ | {consumo:<7} | {etiqueta}"
    
    analisis += "\n\nTOP 3 RECOMENDADOS:\n"
    
    for i, coche in enumerate(top_3, 1):
        coche_completo = next((c for c in todos_los_coches if c.get("url") == coche.get("url")), {})
        
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        analisis += f"{emoji} {coche['modelo']}\n"
        analisis += f"   💰 Beneficio neto: {coche['beneficio']}€/mes | Renting: {coche['renting']}€/mes\n"
        analisis += f"   ⛽ Consumo: {coche_completo.get('emisiones de co2', 'N/A')} | 🏷️ Etiqueta: C\n"
        analisis += f"   🔗 {coche.get('url', 'URL no disponible')}\n"
        analisis += f"   📝 Excelente rentabilidad basada en cálculos exactos\n\n"
    
    analisis += f"""RECOMENDACIÓN FINAL:
El {top_3[0]['modelo']} ofrece el mejor beneficio neto de {top_3[0]['beneficio']}€/mes, siendo la opción más rentable para renting + subalquiler en Amovens.

==========================================="""
    
    # Añadir datos completos del TOP 3
    analisis = añadir_datos_completos_top3(analisis, todos_los_coches)
    
    return analisis

# 5) ------------- Carga de datos -------------------------
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

# 6) ------------- Script principal con análisis incremental -----------------------
if __name__ == "__main__":
    coches_lista = list(cargar_coches(FICHERO_ENTRADA))
    
    if not coches_lista:
        print("ℹ️ No se encontraron coches para analizar.")
        exit(1)
    
    print(f"📊 Total de coches en archivo: {len(coches_lista)}")
    
    # Cargar análisis histórico
    analisis_historico = cargar_analisis_historico()
    print(f"🗃️ Coches ya analizados: {len(analisis_historico.get('coches_analizados', {}))}")
    
    # Filtrar solo coches nuevos
    coches_nuevos = filtrar_coches_nuevos(coches_lista)
    
    if not coches_nuevos:
        print("✅ No hay coches nuevos para analizar.")
        
        # Mostrar el último análisis si existe
        if analisis_historico.get("top_3_actual"):
            print("📋 Mostrando análisis más reciente con datos existentes...")
            analisis_final = generar_analisis_combinado(
                list(analisis_historico["coches_analizados"].values())[:10],
                analisis_historico["top_3_actual"][:3],
                coches_lista,
                0
            )
        else:
            print("⚠️ No hay análisis histórico. Ejecutando análisis completo...")
            analisis_final = analizar_coches_para_renting(coches_lista)
            # Extraer y guardar datos en histórico
            datos_extraidos = extraer_datos_coche_de_analisis(analisis_final)
            for dato in datos_extraidos:
                coche_completo = next((c for c in coches_lista if c.get("modelo") == dato["modelo"]), None)
                if coche_completo:
                    clave_coche = coche_completo.get("url", dato["modelo"])
                    analisis_historico.setdefault("coches_analizados", {})[clave_coche] = {
                        **dato,
                        "url": coche_completo.get("url", ""),
                        "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
            
            # Actualizar TOP 3
            todos_analizados = list(analisis_historico["coches_analizados"].values())
            todos_analizados.sort(key=lambda x: x.get("beneficio", 0), reverse=True)
            analisis_historico["top_3_actual"] = todos_analizados[:3]
            analisis_historico["ultimo_analisis"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            guardar_analisis_historico(analisis_historico)
    else:
        print(f"🤖 Consultando OpenAI para {len(coches_nuevos)} coches nuevos...")
        
        try:
            # Analizar solo los coches nuevos
            analisis_nuevos = analizar_coches_para_renting(coches_nuevos)
            
            # Combinar con análisis previo
            analisis_final = combinar_con_analisis_previo(analisis_nuevos, analisis_historico, coches_lista)
            
            # Guardar análisis histórico actualizado
            guardar_analisis_historico(analisis_historico)
            
            print(f"✅ Análisis actualizado con {len(coches_nuevos)} coches nuevos")
            
        except Exception as e:
            print(f"❌ Error generando análisis para coches nuevos: {e}")
            exit(1)
    
    # Guardar análisis final
    try:
        out_file = os.path.join(DATA_DIR, "analisis_rentabilidad.txt")
        
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(analisis_final)
        
        print(f"\n📈 Análisis guardado en: {out_file}")
        print(f"💰 Mostrando TOP 3 actual:")
        
        # Mostrar solo el TOP 3 en consola para ahorrar espacio
        lineas = analisis_final.split('\n')
        en_top3 = False
        for linea in lineas:
            if "TOP 3 RECOMENDADOS:" in linea:
                en_top3 = True
                print(f"\n{linea}")
            elif en_top3 and "RECOMENDACIÓN FINAL:" in linea:
                print(f"\n{linea}")
                en_top3 = False
            elif en_top3:
                print(linea)
            elif "RECOMENDACIÓN FINAL:" in linea:
                break
        
        # Mostrar estadísticas
        total_analizados = len(analisis_historico.get("coches_analizados", {}))
        print(f"\n📊 Estadísticas:")
        print(f"   🆕 Coches nuevos analizados: {len(coches_nuevos)}")
        print(f"   📋 Total en base de datos: {total_analizados}")
        print(f"   💸 Consultas OpenAI ahorradas: {len(coches_lista) - len(coches_nuevos)}")
        
    except Exception as e:
        print(f"❌ Error guardando análisis: {e}")
