#!/usr/bin/env python3
"""
EPG Scraper para izzi.mx/getguia
Genera epg.xml compatible con XMLTV para Televizo y otras apps IPTV
"""

import requests
import json
import time
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ─────────────────────────────────────────────
# MAPEO: canalName de izzi → tvg-id de tu M3U
# ─────────────────────────────────────────────
MAPEO_CANALES = {
    "LAS ESTRELLAS":           "LasEstrellas.mx",
    "AZTECA UNO":              "AztecaUno.mx",
    "CANAL 5":                 "Canal5Nacional.mx",
    "AZTECA 7":                "Azteca7.mx",
    "IMAGEN TELEVISION":       "ImagenTV.mx",
    "IMAGEN TV":               "ImagenTV.mx",
    "CANAL ONCE":              "CanalOnce.mx",
    "CANAL 14":                "CanalCatorce.mx",
    "FORO TV":                 "ForoTv.mx",
    "ADN 40":                  "ADN40.mx",
    "MILENIO TELEVISION":      "MilenioTelevision.mx",
    "BLOOMBERG":               "BloombergTV.mx",
    "MULTIMEDIOS":             "Multimedios.mx",
    "TNT":                     "TNTMexico.mx",
    "SPACE":                   "Space.mx",
    "AMC":                     "AMCLatinAmerica.us",
    "CINECANAL":               "Cinecanal.mx",
    "CINEMAX":                 "Cinemax.mx",
    "E!":                      "EEntertainment.mx",
    "A&E":                     "AandE.mx",
    "SONY CHANNEL":            "SonyChannel.mx",
    "WARNER CHANNEL":          "WarnerChannel.mx",
    "FX":                      "FX.mx",
    "COMEDY CENTRAL":          "ComedyCentral.mx",
    "TNT SERIES":              "TNTSeries.mx",
    "TELEMUNDO":               "Telemundo.mx",
    "UNICABLE":                "Unicable.mx",
    "DISTRITO COMEDIA":        "DistritoComedia.mx",
    "STAR CHANNEL":            "StarChannelMexico.mx",
    "ESPN":                    "ESPN.mx",
    "ESPN 2":                  "ESPN2.mx",
    "ESPN 3":                  "ESPN3.mx",
    "FOX SPORTS":              "FoxSports.mx",
    "FOX SPORTS 2":            "FoxSports2.mx",
    "FOX SPORTS 3":            "FoxSports3.mx",
    "TUDN":                    "TUDN.mx",
    "SKY SPORTS":              "SkySports1.mx",
    "DISCOVERY CHANNEL":       "DiscoveryChannel.mx",
    "ANIMAL PLANET":           "AnimalPlanet.mx",
    "HISTORY":                 "HistoryChannel.mx",
    "HISTORY 2":               "History2.mx",
    "NAT GEO":                 "NatGeo.mx",
    "DISCOVERY TURBO":         "DiscoveryTurboLatinAmerica.pa",
    "INVESTIGATION DISCOVERY": "InvestigationDiscovery.mx",
    "TLC":                     "TLC.mx",
    "HOGAR Y SALUD":           "DiscoveryHomeHealth.mx",
    "MTV":                     "MTV.mx",
    "TELEHIT":                 "TelehitHD.mx",
    "BANDAMAX":                "Bandamax.mx",
    "VIDEO ROLA":              "VideoRola.mx",
    "DISCOVERY KIDS":          "DiscoveryKids.mx",
    "NICKELODEON":             "Nickelodeon.mx",
    "CARTOON NETWORK":         "CartoonNetwork.mx",
    "DISNEY CHANNEL":          "DisneyChannel.mx",
    "DISNEY JUNIOR":           "DisneyJunior.mx",
    "GOLDEN PLUS":             "GoldenPlus.mx",
    "GOLDEN":                  "Golden.mx",
    "GOLDEN EDGE":             "GoldenEdge.mx",
    "PASIONES":                "Pasiones.us",
    "LIFETIME":                "Lifetime.mx",
    "A MAS":                   "APlus.mx",
    "HBO":                     "HBO.mx",
    "HBO 2":                   "HBO2.mx",
    "HBO PLUS":                "HBOPlus.mx",
    "STAR LIFE":               "StarLife.mx",
    "FXM":                     "FXM.mx",
    "UNIVERSAL":               "UniversalChannel.mx",
    "STUDIO UNIVERSAL":        "StudioUniversal.mx",
    "AXN":                     "AXN.mx",
    "PARAMOUNT CHANNEL":       "ParamountChannel.mx",
    "CLARO SPORTS":            "ClaroSports",
    "AFIZZIONADOS":            "Afizzionados.mx",
}

API_URL = "https://www.izzi.mx/webApps/entretenimiento/guia/getguia"
TZ_MEXICO = pytz.timezone("America/Mexico_City")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://www.izzi.mx/webApps/entretenimiento/guia",
    "Origin": "https://www.izzi.mx",
    "Accept": "application/json, text/javascript, */*",
    "X-Requested-With": "XMLHttpRequest",
}

# ─────────────────────────────────────────────
# OBTENER PROGRAMACIÓN
# ─────────────────────────────────────────────
def obtener_guia(timestamp_ms):
    """Hace POST a getguia con el timestamp dado"""
    try:
        resp = requests.post(
            API_URL,
            data=f"inicio={timestamp_ms}",
            headers=HEADERS,
            timeout=20
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ❌ Error en petición: {e}")
        return None

def ts_a_xmltv(ts_ms):
    """Convierte timestamp en ms a formato XMLTV: 20260313143000 +0600"""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=TZ_MEXICO)
    return dt.strftime("%Y%m%d%H%M%S %z")

# ─────────────────────────────────────────────
# GENERAR XML XMLTV
# ─────────────────────────────────────────────
def generar_xml(canales_data):
    root = ET.Element("tv")
    root.set("generator-info-name", "epg-izzi-scraper")

    # Registrar canales únicos
    canales_vistos = set()
    for canal in canales_data:
        tvg_id = canal.get("tvg_id")
        nombre = canal.get("canalName", "")
        if tvg_id and tvg_id not in canales_vistos:
            canales_vistos.add(tvg_id)
            ch_el = ET.SubElement(root, "channel")
            ch_el.set("id", tvg_id)
            nombre_el = ET.SubElement(ch_el, "display-name")
            nombre_el.set("lang", "es")
            nombre_el.text = nombre
            logo = canal.get("logo", "")
            if logo:
                icon_el = ET.SubElement(ch_el, "icon")
                icon_el.set("src", f"https://www.izzi.mx{logo}" if logo.startswith("/") else logo)

    # Agregar programas
    for canal in canales_data:
        tvg_id = canal.get("tvg_id")
        if not tvg_id:
            continue
        for prog in canal.get("schedule", []):
            try:
                inicio = prog.get("initDate")
                fin = prog.get("endDate")
                titulo = prog.get("title", "Sin título")
                descripcion = prog.get("description", "")
                if not inicio or not fin:
                    continue
                prog_el = ET.SubElement(root, "programme")
                prog_el.set("start", ts_a_xmltv(inicio))
                prog_el.set("stop", ts_a_xmltv(fin))
                prog_el.set("channel", tvg_id)
                tit_el = ET.SubElement(prog_el, "title")
                tit_el.set("lang", "es")
                tit_el.text = titulo
                if descripcion:
                    desc_el = ET.SubElement(prog_el, "desc")
                    desc_el.set("lang", "es")
                    desc_el.text = descripcion
                img = prog.get("image", "")
                if img:
                    icon_el = ET.SubElement(prog_el, "icon")
                    icon_el.set("src", img if img.startswith("http") else f"https://www.izzi.mx/{img}")
            except Exception as e:
                continue

    xml_str = ET.tostring(root, encoding="unicode")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
    return "\n".join(pretty.split("\n")[1:])

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("🔄 EPG Scraper - izzi.mx")
    print(f"📅 {datetime.now(TZ_MEXICO).strftime('%Y-%m-%d %H:%M')}\n")

    # Obtener timestamps para hoy y mañana (bloques de 6 horas)
    ahora = datetime.now(TZ_MEXICO)
    inicio_dia = TZ_MEXICO.localize(datetime(ahora.year, ahora.month, ahora.day, 0, 0, 0))
    
    timestamps = []
    for h in range(0, 48, 6):  # cada 6 horas por 2 días
        ts = int((inicio_dia + timedelta(hours=h)).timestamp() * 1000)
        timestamps.append(ts)

    # Recolectar datos por bloques
    canales_dict = {}  # guideId → canal data

    for ts in timestamps:
        dt = datetime.fromtimestamp(ts/1000, tz=TZ_MEXICO)
        print(f"⏰ Obteniendo bloque: {dt.strftime('%Y-%m-%d %H:%M')}...")
        data = obtener_guia(ts)
        if not data:
            continue

        canales_raw = data if isinstance(data, list) else data.get("canales") or data.get("channels") or []
        
        # Si la respuesta es directamente una lista de canales
        if isinstance(data, list):
            canales_raw = data
        elif isinstance(data, dict):
            # Buscar la lista de canales en el dict
            for key in ["canales", "channels", "guide", "data", "result"]:
                if key in data and isinstance(data[key], list):
                    canales_raw = data[key]
                    break
            if not canales_raw:
                # Puede ser que la respuesta misma sea el canal
                canales_raw = [data]

        for canal in canales_raw:
            if not isinstance(canal, dict):
                continue
            nombre = canal.get("canalName", "").strip().upper()
            tvg_id = MAPEO_CANALES.get(nombre)
            guide_id = canal.get("guideId", nombre)
            
            if guide_id not in canales_dict:
                canales_dict[guide_id] = {
                    "tvg_id": tvg_id,
                    "canalName": canal.get("canalName", nombre),
                    "logo": canal.get("logo", ""),
                    "schedule": []
                }
            
            # Agregar programas evitando duplicados
            schedule = canal.get("schedule", [])
            existentes = {p.get("eventId") for p in canales_dict[guide_id]["schedule"]}
            for prog in schedule:
                if prog.get("eventId") not in existentes:
                    canales_dict[guide_id]["schedule"].append(prog)

        time.sleep(0.5)  # respetar el servidor

    # Filtrar solo canales mapeados
    canales_mapeados = [c for c in canales_dict.values() if c.get("tvg_id")]
    total_programas = sum(len(c["schedule"]) for c in canales_mapeados)

    print(f"\n📊 Canales con datos: {len(canales_mapeados)}")
    print(f"📺 Total programas: {total_programas}")

    if not canales_mapeados:
        print("⚠️  No se obtuvieron datos. Revisa la conexión o el endpoint.")
        # Mostrar canales sin mapear para debug
        sin_mapear = [c["canalName"] for c in canales_dict.values() if not c.get("tvg_id")]
        if sin_mapear:
            print(f"📋 Canales sin mapear: {', '.join(sin_mapear[:10])}")
        return

    print("\n📝 Generando epg.xml...")
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + generar_xml(canales_mapeados)

    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"✅ epg.xml generado: {len(xml_content):,} bytes")
    print(f"📁 Canales incluidos:")
    for c in sorted(canales_mapeados, key=lambda x: x["canalName"]):
        print(f"   {c['canalName']:30} → {c['tvg_id']} ({len(c['schedule'])} programas)")

if __name__ == "__main__":
    main()
