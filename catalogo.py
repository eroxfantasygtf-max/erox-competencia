#!/usr/bin/env python3
"""Fase 2 · paso 1: rastrea el catálogo público (sitemaps) de las tiendas de `tiendas.csv` y se queda solo con las
fichas cuyas URL mencionan alguna de las marcas indicadas.

Uso:  python catalogo.py "DUREX,SATISFYER" [tiendas.csv]
Salida: work/<tienda>.tsv  (url<TAB>marca)  y una línea de resumen por tienda en work/resumen_catalogo.json
Solo lectura de páginas públicas. Educado: ≤ 1 petición cada 0,4 s por tienda; 6 tiendas en paralelo.
"""
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from utiles import descargar, tokens

OMITIR = re.compile(r"(blog|post|page|cms|image|imagen|categor|collection|article|tag|brand|manufactur|pagina|news|video|attribute)", re.I)
MAX_ARCHIVOS = 60
MAX_SEGUNDOS = 150   # tope de tiempo por tienda (una tienda enorme no debe frenar a las demás)


def _locs(xml):
    return re.findall(r"<loc>\s*(?:<!\[CDATA\[)?\s*([^<\s\]]+)", xml)


def hojas_sitemap(host, sitemap_pista=""):
    """Recorre robots.txt / sitemap.xml y devuelve las URL de fichas (sin filtrar)."""
    raiz = []
    if sitemap_pista:
        raiz.append(sitemap_pista)
    _, robots = descargar("https://%s/robots.txt" % host, intentos=2)
    raiz += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots or "")
    if not raiz:
        raiz = ["https://%s/sitemap.xml" % host, "https://%s/sitemap_index.xml" % host]
    cola, vistos, urls, leidos = list(dict.fromkeys(raiz)), set(), [], 0
    inicio = time.time()
    while cola and leidos < MAX_ARCHIVOS and time.time() - inicio < MAX_SEGUNDOS:
        sm = cola.pop(0)
        if sm in vistos:
            continue
        vistos.add(sm)
        cod, xml = descargar(sm, intentos=2)
        time.sleep(0.4)
        if cod != 200 or not xml:
            continue
        leidos += 1
        hijos = [x for x in _locs(xml)]
        xmls = [x for x in hijos if re.search(r"\.xml(\.gz)?(\?.*)?$", x, re.I)]
        if xmls:
            prod = [x for x in xmls if re.search(r"(product|producto|item|articulo)", x, re.I)]
            cola.extend(prod if prod else [x for x in xmls if not OMITIR.search(x)])
            urls.extend(x for x in hijos if x not in xmls)
        else:
            urls.extend(hijos)
    return urls, leidos


def cargar_marcas(ruta="gtins.csv"):
    with open(ruta, newline="", encoding="utf-8") as f:
        return sorted({r["marca"].strip() for r in csv.DictReader(f) if r.get("marca")})


def filtrar(urls, marcas):
    """URL cuyo texto contiene TODAS las palabras de alguna marca."""
    mt = [(m, set(tokens(m))) for m in marcas]
    out = []
    for u in urls:
        slug = set(tokens(re.sub(r"^https?://[^/]+", "", u)))
        for m, ts in mt:
            if ts and ts <= slug:
                out.append((u, m))
                break
    return out


def procesar(args):
    host, pista, marcas = args
    try:
        urls, n = hojas_sitemap(host, pista)
        sel = filtrar(urls, marcas)
        with open(os.path.join("work", host + ".tsv"), "w", encoding="utf-8") as f:
            for u, m in sel:
                f.write("%s\t%s\n" % (u, m))
        return {"tienda": host, "sitemaps": n, "urls": len(urls), "de_nuestras_marcas": len(sel)}
    except Exception as e:  # una tienda que falla no debe parar a las demás
        return {"tienda": host, "error": str(e)[:120]}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    marcas = [m.strip() for m in sys.argv[1].split(",") if m.strip()]
    ruta = sys.argv[2] if len(sys.argv) > 2 else "tiendas.csv"
    os.makedirs("work", exist_ok=True)
    with open(ruta, newline="", encoding="utf-8") as f:
        tiendas = [(r["host"].strip().lower(), (r.get("sitemap") or "").strip(), marcas) for r in csv.DictReader(f) if r.get("host")]
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(procesar, tiendas))
    with open("work/resumen_catalogo.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for r in res:
        print(json.dumps(r, ensure_ascii=False))
    con = sum(1 for r in res if r.get("de_nuestras_marcas"))
    print("RESUMEN: %d tiendas leídas, %d con fichas de las marcas pedidas" % (len(res), con))


if __name__ == "__main__":
    main()
