#!/usr/bin/env python3
"""Fase 2 · paso 2: empareja nuestros productos con las fichas de cada tienda y los COMPRUEBA por GTIN.

Uso:  python emparejar.py "DUREX,SATISFYER"
Necesita haber ejecutado antes `python catalogo.py "DUREX,SATISFYER"` (work/<tienda>.tsv).
Para cada producto de esas marcas y cada tienda:
  1. puntúa las fichas candidatas por parecido de palabras (marca + artículo + variante),
  2. abre las 3 mejores y exige que el GTIN figure en un campo de identificación (verificar.py),
  3. se queda con la primera que lo cumple.
Salida: work/resultado.json con  verificados · dudosas (hay candidatas pero ninguna pasó) · sin_candidatas.
"""
import csv
import glob
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from utiles import clave_gtin, tokens
from verificar import verificar

TOP = 3          # fichas que se abren por producto y tienda
UMBRAL = 0.34    # parecido mínimo de palabras
MAX_ABRIR = 1800  # tope de fichas abiertas por pasada


def cargar_productos(marcas, ruta="gtins.csv"):
    ms = {m.lower() for m in marcas}
    with open(ruta, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["marca"].strip().lower() in ms]


def cargar_catalogos():
    cat = {}
    for ruta in glob.glob("work/*.tsv"):
        host = os.path.basename(ruta)[:-4]
        filas = []
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                u, _, m = linea.rstrip("\n").partition("\t")
                if u:
                    filas.append((u, set(tokens(re.sub(r"^https?://[^/]+", "", u))), m))
        cat[host] = filas
    return cat


def candidatas(prod, filas):
    qt = tokens("%s %s %s" % (prod["marca"], prod["articulo"], prod.get("variante", "")))
    # los números de la variante (3, 12, 45 mm…) deben coincidir si aparecen en nuestra variante
    nums = set(re.findall(r"\d+", prod.get("variante", "") or ""))
    bt = set(tokens(prod["marca"]))
    puntuadas = []
    for u, slug, m in filas:
        if not bt <= slug or not qt:
            continue
        acierto = sum(1 for t in qt if t in slug)
        score = acierto / len(qt)
        if nums and not (nums & set(re.findall(r"\d+", " ".join(slug)))):
            score *= 0.5
        if score >= UMBRAL:
            puntuadas.append((score, u))
    puntuadas.sort(reverse=True)
    return puntuadas[:TOP]


def trabajo(args):
    prod, host, cands = args
    for score, url in cands:
        r = verificar(prod["gtin"], url)
        time.sleep(0.4)
        if r.get("ok"):
            r.update(host=host, score=round(score, 2), marca=prod["marca"], articulo=prod["articulo"], variante=prod.get("variante", ""))
            return ("ok", r)
    return ("dudosa", {"gtin": prod["gtin"], "marca": prod["marca"], "articulo": prod["articulo"], "variante": prod.get("variante", ""), "host": host,
                       "candidatas": [u for _, u in cands]})


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    marcas = [m.strip() for m in sys.argv[1].split(",") if m.strip()]
    prods = cargar_productos(marcas)
    cat = cargar_catalogos()
    tareas, sin = [], []
    for p in prods:
        hubo = False
        for host, filas in cat.items():
            c = candidatas(p, filas)
            if c:
                hubo = True
                tareas.append((p, host, c))
        if not hubo:
            sin.append({"gtin": p["gtin"], "marca": p["marca"], "articulo": p["articulo"], "variante": p.get("variante", "")})
    # reparto justo si hay demasiadas: se limita el número de fichas abiertas
    # reparto por rondas: primero la mejor candidata de cada (producto, tienda) y así todos los productos reciben su parte del tope
    tareas.sort(key=lambda t: (-t[2][0][0], t[0]['gtin']))
    abiertas = 0
    recorte = []
    for t in tareas:
        if abiertas + len(t[2]) > MAX_ABRIR:
            break
        abiertas += len(t[2])
        recorte.append(t)
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(trabajo, recorte))
    verificados = [r for k, r in res if k == "ok"]
    dudosas = [r for k, r in res if k == "dudosa"]
    out = {"marcas": marcas, "productos": len(prods), "tiendas_con_catalogo": len([h for h, f in cat.items() if f]), "verificados": verificados,
           "dudosas": dudosas, "sin_candidatas": sin, "pendientes_por_tope": len(tareas) - len(recorte)}
    os.makedirs("work", exist_ok=True)
    with open("work/resultado.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    por_gtin = {}
    for r in verificados:
        por_gtin.setdefault(r["gtin"], set()).add(r["host"])
    print("productos %d · con ≥1 tienda verificada %d · fichas verificadas %d · dudosas %d · sin candidatas %d · pendientes por tope %d" % (
        len(prods), len(por_gtin), len(verificados), len(dudosas), len(sin), out["pendientes_por_tope"]))


if __name__ == "__main__":
    main()
