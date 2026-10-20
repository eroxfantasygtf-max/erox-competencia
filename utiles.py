"""Funciones comunes de las herramientas de competencia (solo biblioteca estándar, sin dependencias)."""
import gzip
import re
import time
import unicodedata
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
STOP = {"de", "del", "la", "el", "los", "las", "para", "con", "en", "y", "a", "unidades", "unidad", "uds", "ud", "color", "aroma", "sabor",
        "talla", "tamano", "pack", "caja", "mujer", "hombre", "html", "htm", "producto", "productos", "comprar"}


def descargar(url, intentos=2, espera=1.5, timeout=30, max_bytes=6_000_000):
    """(codigo_http, texto). codigo 0 = fallo de red. Reintenta resets puntuales."""
    ultimo = 0
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9", "Accept": "text/html,application/xml,*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                datos = r.read(max_bytes)
                if datos[:2] == b"\x1f\x8b":
                    datos = gzip.decompress(datos)
                return r.status, datos.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            ultimo = e.code
            if e.code in (403, 404, 410):
                return e.code, ""
        except Exception:
            ultimo = 0
        time.sleep(espera * (i + 1))
    return ultimo, ""


def normalizar(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def tokens(s):
    """Palabras significativas (sin tildes, sin palabras vacías, sin duplicados, en orden)."""
    vistos, out = set(), []
    for t in re.split(r"[^a-z0-9]+", normalizar(s)):
        if len(t) > 1 and t not in STOP and t not in vistos:
            vistos.add(t)
            out.append(t)
    return out


def clave_gtin(g):
    return re.sub(r"\D", "", str(g or "")).lstrip("0")


def gtin_valido(g):
    g = re.sub(r"\D", "", str(g or ""))
    if len(g) not in (8, 12, 13, 14):
        return False
    d = [int(c) for c in g]
    suma = sum(x * (3 if i % 2 == 0 else 1) for i, x in enumerate(reversed(d[:-1])))
    return (10 - suma % 10) % 10 == d[-1]


def host_de(url):
    m = re.match(r"https?://([^/:?#]+)", url or "", re.I)
    return m.group(1).lower() if m else ""
