import requests
import re
import os
import json
from datetime import datetime

# ─────────────────────────────────────────────
# CANALES A RENOVAR
# Agrega más canales aquí con su rokuId y el
# identificador único que aparece en el M3U8
# ─────────────────────────────────────────────
CANALES = [
    {
        "nombre": "FIFA+ Roku",
        "rokuId": "7a033d0101975470a6904c96b6e9bc32",
        "playId": "s-fifa.ZmlmYV9maWZhcGx1c19teA==",
        "marker": "FIFA+ Roku",  # texto único en la línea #EXTINF del canal
    },
    {
        "nombre": "Imagen TV",
        "rokuId": "e71ded29bfc95669961bf907e8e12c26",
        "playId": "s-grupo_imagen.Z3J1cG9pbWFnZW5faW1hZ2VuX3R2X214",
        "marker": "IMAGEN TV",  # texto único en la línea #EXTINF del canal
    },
    {
        "nombre": "Video Rola",
        "rokuId": "070ab968222458f3b7ebbde5b06ab83d",
        "playId": "s-vrplus.ZW50cmV0ZW5pbWllbnRvX3NhdGVsaXRhbF92cnBsdXM=",
        "mediaFormat": "mpeg-dash",  # este canal usa DASH en vez de HLS
        "marker": "VIDEO ROLA",  # texto único en la línea #EXTINF del canal
    },
]

ROKU_API = "https://therokuchannel.roku.com/api/v3/playback"
ROKU_HOME = "https://therokuchannel.roku.com"

# ─────────────────────────────────────────────
# PASO 1: Obtener cookies de sesión anónima
# ─────────────────────────────────────────────
def obtener_sesion():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9",
    }
    session.get(ROKU_HOME, headers=headers, timeout=15)
    print(f"[{datetime.now()}] Sesión iniciada. Cookies: {list(session.cookies.keys())}")
    return session

# ─────────────────────────────────────────────
# PASO 2: Obtener el M3U8 de un canal
# ─────────────────────────────────────────────
def obtener_m3u8(session, canal):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": ROKU_HOME,
        "Origin": ROKU_HOME,
        "X-Requested-With": "XMLHttpRequest",
    }

    # Agregar CSRF si está disponible
    csrf = session.cookies.get("_csrf")
    if csrf:
        headers["X-CSRF-Token"] = csrf

    payload = {
        "rokuId": canal["rokuId"],
        "playId": canal["playId"],
        "mediaFormat": canal.get("mediaFormat", "m3u"),  # usa mpeg-dash si el canal lo requiere
        "quality": "fhd",
        "drmType": "widevine",
        "providerId": "rokuavod",
        "adPolicyId": "",
        "playbackContextParams": f"sessionId={session.cookies.get('_us', 'anon')}&idType=roku-trc&userTag=cultureCode%3Aes_MX&channelStore=mx"
    }

    resp = session.post(ROKU_API, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    print(f"[{datetime.now()}] Respuesta {canal['nombre']}: {json.dumps(data)[:200]}")

    # Buscar el URL del stream en la respuesta
    url = None
    if isinstance(data, dict):
        # Buscar recursivamente el URL m3u8
        url = encontrar_url(data)

    if not url:
        raise ValueError(f"No se encontró URL m3u8 en la respuesta de {canal['nombre']}")

    return url

def encontrar_url(obj):
    """Busca recursivamente un URL de stream en el JSON de respuesta"""
    if isinstance(obj, str) and "osm.sr.roku.com" in obj and ("m3u8" in obj or ".mpd" in obj or "jwt=" in obj):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            result = encontrar_url(v)
            if result:
                return result
    if isinstance(obj, list):
        for item in obj:
            result = encontrar_url(item)
            if result:
                return result
    return None

# ─────────────────────────────────────────────
# PASO 3: Actualizar el archivo M3U8
# ─────────────────────────────────────────────
def actualizar_m3u(contenido_m3u, canal, nuevo_url):
    lineas = contenido_m3u.split("\n")
    nuevo_contenido = []
    i = 0
    actualizado = False

    while i < len(lineas):
        linea = lineas[i]
        # Buscar la línea #EXTINF que corresponde a este canal
        if "#EXTINF" in linea and canal["marker"].lower() in linea.lower():
            nuevo_contenido.append(linea)
            i += 1
            # La siguiente línea no vacía es el URL — la reemplazamos
            while i < len(lineas) and lineas[i].strip() == "":
                nuevo_contenido.append(lineas[i])
                i += 1
            if i < len(lineas):
                print(f"[{datetime.now()}] Reemplazando URL de {canal['nombre']}")
                print(f"  Antes: {lineas[i][:80]}...")
                print(f"  Después: {nuevo_url[:80]}...")
                nuevo_contenido.append(nuevo_url)
                actualizado = True
                i += 1
        else:
            nuevo_contenido.append(linea)
            i += 1

    if not actualizado:
        print(f"⚠️  No se encontró el marcador '{canal['marker']}' en el archivo M3U")

    return "\n".join(nuevo_contenido)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    # Leer el archivo M3U actual (en GitHub Actions estará en el repo clonado)
    m3u_path = os.environ.get("M3U_PATH", "TV.m3u8")

    with open(m3u_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Obtener sesión anónima de Roku
    session = obtener_sesion()

    errores = []

    for canal in CANALES:
        try:
            print(f"\n🔄 Renovando: {canal['nombre']}...")
            nuevo_url = obtener_m3u8(session, canal)
            contenido = actualizar_m3u(contenido, canal, nuevo_url)
            print(f"✅ {canal['nombre']} actualizado")
        except Exception as e:
            print(f"❌ Error en {canal['nombre']}: {e}")
            errores.append(canal["nombre"])

    # Guardar el archivo actualizado
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"\n📝 Archivo guardado: {m3u_path}")

    if errores:
        print(f"⚠️  Canales con error: {', '.join(errores)}")
        exit(1)
    else:
        print("🎉 Todos los canales actualizados correctamente")

if __name__ == "__main__":
    main()
