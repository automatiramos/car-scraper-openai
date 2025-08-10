#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para enviar el análisis de rentabilidad de coches por email usando Gmail.
Requiere configurar una contraseña de aplicación de Gmail en las variables de entorno.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime
import glob

# Cargar variables de entorno
load_dotenv()

# Configuración de Gmail
GMAIL_USER = os.getenv("GMAIL_USER")  # tu_email@gmail.com
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")  # contraseña de aplicación
DESTINATARIO = os.getenv("EMAIL_DESTINATARIO", GMAIL_USER)  # destinatario por defecto

def buscar_ultimo_analisis():
    """
    Busca el archivo de análisis más reciente.
    """
    archivos = glob.glob("analisis_rentabilidad_*.txt")
    if not archivos:
        return None
    
    # Ordenar por fecha de modificación (más reciente primero)
    archivos.sort(key=os.path.getmtime, reverse=True)
    return archivos[0]

def leer_contenido_analisis(archivo):
    """
    Lee el contenido del archivo de análisis.
    """
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error leyendo archivo {archivo}: {e}")
        return None

def crear_mensaje_email(contenido_analisis, archivo_analisis):
    """
    Crea el mensaje de email con el análisis completo en el cuerpo.
    """
    # Crear mensaje
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = DESTINATARIO
    msg['Subject'] = f"🚗 Análisis Rentabilidad Coches Renting - {datetime.now().strftime('%d/%m/%Y')}"
    
    # Encabezado del email
    encabezado = f"""📧 ANÁLISIS DE RENTABILIDAD - COCHES RENTING
═══════════════════════════════════════════════════════════════════

📅 Generado: {datetime.now().strftime('%d/%m/%Y a las %H:%M')}
📍 Ubicación: Madrid
🎯 Objetivo: Renting + Subalquiler P2P en Amovens

═══════════════════════════════════════════════════════════════════

"""
    
    # Pie del email
    pie = f"""

═══════════════════════════════════════════════════════════════════

📋 Archivo fuente: {os.path.basename(archivo_analisis)}
🤖 Generado automáticamente por el Sistema de Análisis de Rentabilidad

Saludos,
Sistema de Análisis Automático
"""
    
    # Combinar todo el contenido
    cuerpo_completo = encabezado + contenido_analisis + pie
    
    # Solo adjuntar el cuerpo del email (SIN archivo adjunto)
    msg.attach(MIMEText(cuerpo_completo, 'plain', 'utf-8'))
    
    return msg

def enviar_email(mensaje):
    """
    Envía el email usando Gmail SMTP.
    """
    try:
        # Conectar a Gmail
        print("📧 Conectando a Gmail...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Habilitar TLS
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        
        # Enviar email
        print("📤 Enviando email...")
        texto = mensaje.as_string()
        server.sendmail(GMAIL_USER, DESTINATARIO, texto)
        server.quit()
        
        print(f"✅ Email enviado exitosamente a {DESTINATARIO}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de autenticación. Verifica GMAIL_USER y GMAIL_PASSWORD")
        print("💡 Necesitas usar una 'Contraseña de aplicación' de Gmail, no tu contraseña normal")
        return False
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False

def main():
    """
    Función principal del script.
    """
    print("📧 Script de envío de análisis de rentabilidad por email")
    print("=" * 60)
    
    # Verificar configuración
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("❌ Error: Variables de entorno no configuradas")
        print("💡 Configura en tu .env:")
        print("   GMAIL_USER=tu_email@gmail.com")
        print("   GMAIL_PASSWORD=tu_contraseña_de_aplicacion")
        print("   EMAIL_DESTINATARIO=destinatario@email.com (opcional)")
        return
    
    # Buscar archivo de análisis más reciente
    archivo_analisis = buscar_ultimo_analisis()
    if not archivo_analisis:
        print("❌ No se encontró ningún archivo de análisis (analisis_rentabilidad_*.txt)")
        print("💡 Ejecuta primero el script ask_openai_car_evaluation.py")
        return
    
    print(f"📄 Archivo encontrado: {archivo_analisis}")
    
    # Leer contenido
    contenido = leer_contenido_analisis(archivo_analisis)
    if not contenido:
        return
    
    print(f"📝 Contenido leído: {len(contenido)} caracteres")
    
    # Crear mensaje
    mensaje = crear_mensaje_email(contenido, archivo_analisis)
    
    # Enviar email
    if enviar_email(mensaje):
        print(f"🎉 Análisis enviado exitosamente a {DESTINATARIO}")
    else:
        print("💔 Error en el envío del email")

if __name__ == "__main__":
    main()
