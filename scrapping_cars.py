from playwright.sync_api import sync_playwright
import json
import sys
import os
from datetime import datetime
import dotenv

dotenv.load_dotenv()

ARCHIVO_COCHES_ELIMINADO = os.getenv("ARCHIVO_COCHES_ELIMINADO", "coches_eliminados.json")
ARCHIVO_COCHES = os.getenv("ARCHIVO_COCHES", "coches.json")
URL_LISTADO = os.getenv("URL_LISTADO", "https://example.com/listing")  # URL configurable

DATE = datetime.now().strftime("%Y-%m-%d")

def extraer_texto(element, default=""):
    return element.inner_text().strip() if element else default

def obtener_detalles_de_coche(page, car: dict) -> dict:
    try:
        url = car.get("url", "")
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_selector("#js-leasing-offer-details", timeout=60000)

        year_div = page.query_selector("#js-leasing-offer-details div.lead.mb5")
        year_text = extraer_texto(year_div)
        car["año"] = year_text.replace("Coche del", "").strip() if year_text else ""

        paragraphs = page.query_selector_all("#js-leasing-offer-details div.grid-row-2 p")
        car["motor_info"] = extraer_texto(paragraphs[0]) if len(paragraphs) > 0 else ""
        car["descripcion"] = extraer_texto(paragraphs[1]) if len(paragraphs) > 1 else ""

        container_selector = (
            "#js-leasing-offer-details "
            "div.grid.grid-template-columns-2.grid-template-columns-3-md.grid-gap4.mb8"
        )
        container = page.query_selector(container_selector)
        if container:
            features = container.query_selector_all("div.flex.flex-align-center")
            for feature in features:
                label_span = feature.query_selector("span")
                name = extraer_texto(label_span).lower()

                value_div = feature.query_selector("div.text-semi-bold.f4.text-nowrap")
                value = extraer_texto(value_div)

                if name and value:
                    car[name] = value
    except Exception as e:
        print(f"⚠️ Error al obtener detalles de {car.get('url', '')}: {e}", file=sys.stderr)
    return car

def coche_ha_cambiado(nuevo, anterior):
    campos_comparables = ["url", "modelo", "precio", "contrato", "uso"]
    return any(nuevo.get(c) != anterior.get(c) for c in campos_comparables)

def calcular_km_por_año(car_data: dict) -> dict:
    km_por_año = None
    km_text = car_data.get("kilometraje", "")
    if km_text:
        km_text = km_text.replace("Menos de ", "").replace(".", "").replace(" kms", "")
        try:
            km = int(km_text)
        except ValueError:
            km = None

        try:
            year = int(car_data.get("año", 0))
        except ValueError:
            year = datetime.now().year

        current_year = datetime.now().year
        years_used = max(1, current_year - year)
        if km is not None:
            km_por_año = round(km / years_used, 0)

    car_data["km_por_año"] = km_por_año
    return car_data

def scrape_coches():
    url = URL_LISTADO

    existing_data = []
    existing_by_url = {}
    try:
        with open(ARCHIVO_COCHES, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if raw:
                existing_data = json.loads(raw)
                for car in existing_data:
                    car["estado_actualizacion"] = "no actualizado"
                    existing_by_url[car["url"]] = car
            else:
                print(f"⚠️ {ARCHIVO_COCHES} existe pero está vacío. Se inicializa limpio.")
    except FileNotFoundError:
        print(f"⚠️ No existe {ARCHIVO_COCHES}. Se creará uno nuevo.")
    except json.JSONDecodeError:
        print(f"⚠️ {ARCHIVO_COCHES} está corrupto. Ignorando contenido.")
        existing_data = []

    nuevos = actualizados = sin_cambios = eliminados = 0
    final_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
        listing_page = browser.new_page()
        details_page = browser.new_page()
        listing_page.set_viewport_size({"width": 1280, "height": 800})
        listing_page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        try:
            listing_page.goto(url, wait_until="load", timeout=60000)
            listing_page.wait_for_selector("a[href^='/leasing/ald/']", timeout=60000)

            car_cards = listing_page.query_selector_all("a[href^='/leasing/ald/']")
            if not car_cards:
                print("⚠️ No se encontraron coches en la página de listado.", file=sys.stderr)

            for card in car_cards:
                try:
                    href = card.get_attribute("href")
                except Exception as e:
                    print(f"⚠️ No pude leer href de un card: {e}", file=sys.stderr)
                    continue
                full_url = f"{url.split('/renting')[0]}{href}"

                title = card.query_selector("h3.mb1.trunc-line")
                title_text = extraer_texto(title)

                price_span = card.query_selector("span.text-bold.text-green-60")
                price_text = extraer_texto(price_span)

                contract_p = card.query_selector("p.mb1.hidden-xs")
                contract_text = extraer_texto(contract_p)

                use_span = card.query_selector("div.text-break-word.hidden-xs span")
                use_text = extraer_texto(use_span)

                car_data = {
                    "url": full_url,
                    "modelo": title_text,
                    "precio": f"{price_text} € al mes" if price_text else "",
                    "contrato": contract_text,
                    "uso": use_text
                }

                if full_url not in existing_by_url:
                    car_data["estado_actualizacion"] = "nuevo"
                    nuevos += 1
                elif coche_ha_cambiado(car_data, existing_by_url[full_url]):
                    car_data["estado_actualizacion"] = "actualizado"
                    actualizados += 1
                else:
                    old_car = existing_by_url[full_url]
                    old_car["estado_actualizacion"] = "sin_cambios"
                    final_data.append(old_car)
                    sin_cambios += 1
                    continue

                try:
                    obtener_detalles_de_coche(details_page, car_data)
                    calcular_km_por_año(car_data)
                except Exception as e:
                    print(f"⚠️ Error enriqueciendo datos de {full_url}: {e}", file=sys.stderr)

                final_data.append(car_data)
                print(f"{'🆕' if car_data['estado_actualizacion']=='nuevo' else '🔁'} {title_text}")

            browser.close()

        except Exception as e:
            print(f"❌ Error al cargar la página de listado: {e}", file=sys.stderr)
            browser.close()
            return

    eliminados_data = [
        {**car, "fecha_eliminación": datetime.now().strftime("%d-%m-%Y %H:%M")}
        for car in existing_data
        if car.get("estado_actualizacion") == "no actualizado"
    ]
    if eliminados_data:
        eliminados_existentes = []
        try:
            with open(ARCHIVO_COCHES_ELIMINADO, "r", encoding="utf-8") as f:
                raw = f.read().strip()
                if raw:
                    eliminados_existentes = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        eliminados_existentes.extend(eliminados_data)
        try:
            with open(ARCHIVO_COCHES_ELIMINADO, "w", encoding="utf-8") as f:
                json.dump(eliminados_existentes, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ No se pudo guardar {ARCHIVO_COCHES_ELIMINADO}: {e}", file=sys.stderr)
        eliminados = len(eliminados_data)

    try:
        with open(ARCHIVO_COCHES, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"❌ No se pudo guardar {ARCHIVO_COCHES}: {e}", file=sys.stderr)

    print("\n✅ Scraping completado.")
    print(f"🆕 Nuevos coches: {nuevos}")
    print(f"🔁 Actualizados: {actualizados}")
    print(f"✔️ Sin cambios: {sin_cambios}")
    print(f"❌ Eliminados y archivados: {eliminados}")

if __name__ == "__main__":
    scrape_coches()
