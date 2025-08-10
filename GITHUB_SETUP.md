# Configuración de Secrets para GitHub Actions

Para que los workflows funcionen correctamente, necesitas configurar los siguientes secrets en tu repositorio de GitHub:

## Cómo configurar secrets:

1. Ve a tu repositorio en GitHub
2. Ve a Settings > Secrets and variables > Actions
3. Haz clic en "New repository secret"
4. Agrega cada uno de los siguientes secrets:

## Secrets requeridos:

### Para el scraping:

- `URL_LISTADO`: La URL de la página de listado de coches de Amovens

### Para OpenAI:

- `OPENAI_API_KEY`: Tu clave de API de OpenAI

### Para el envío de emails:

- `GMAIL_USER`: Tu dirección de Gmail (ej: usuario@gmail.com)
- `GMAIL_PASSWORD`: Contraseña de aplicación de Gmail (NO tu contraseña normal)
- `EMAIL_DESTINATARIO`: Email donde quieres recibir los análisis (opcional, usa GMAIL_USER por defecto)

## Cómo obtener una contraseña de aplicación de Gmail:

1. Ve a tu cuenta de Google
2. Seguridad > Verificación en 2 pasos (debe estar activada)
3. Contraseñas de aplicaciones
4. Genera una nueva contraseña para "Correo"
5. Usa esa contraseña de 16 caracteres como GMAIL_PASSWORD

## Workflows disponibles:

### 1. car-scraper.yml (Recomendado)

- Usa GitHub Artifacts para persistir datos
- Más limpio, no contamina el repositorio
- Los datos se mantienen por 30 días entre ejecuciones

### 2. car-scraper-git.yml

- Guarda los datos directamente en el repositorio
- Los datos quedan versionados en Git
- Útil para tener historial completo

## Programación:

- Ambos workflows están configurados para ejecutarse cada 4 horas (8:00, 12:00, 16:00, 20:00 **hora de España**)
- Solo se ejecutan de lunes a sábado
- También se pueden ejecutar manualmente desde la pestaña Actions
- **Nota**: GitHub Actions usa UTC, por lo que los horarios están ajustados automáticamente

### Detalles de horarios:

- **Horario España (CEST)**: 8:00, 12:00, 16:00, 20:00
- **Horario UTC (GitHub)**: 6:00, 10:00, 14:00, 18:00
- **Días**: Lunes a Sábado (Domingos libres)

## Notas importantes:

- Los archivos de datos se guardan en el directorio `data/`
- El análisis se envía automáticamente por email
- Los logs están disponibles en la pestaña Actions de GitHub
