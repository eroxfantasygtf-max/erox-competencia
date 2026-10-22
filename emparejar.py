#!/usr/bin/env python3
"""Fase 2 · paso 2: empareja nuestros productos con las fichas de cada tienda y los COMPRUEBA por GTIN.

Uso:  python emparejar.py "DUREX,SATISFYER" [--pendientes]
      --pendientes: salta los productos que ya tienen fichas publicadas en competencia.csv (para completar solo lo que falta)
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

from utiles import clave_gtin, descargar, firma_articulo, tokens
from verificar import analizar

TOP = 3          # fichas que se abren por producto y tienda
UMBRAL = 0.34    # parecido mínimo de palabras
MAX_ABRIR = 3000  # tope de PÁGINAS DISTINTAS abiertas por pasada (repartido por rondas entre todos los productos)


def cargar_productos(marcas, ruta="gtins.csv"):
    ms = {m.lower() for m in marcas}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r["marca"].strip().lower() in ms]


def cargar_catalogos():
    cat = {}
    for ruta in glob.glob("work/*.tsv"):
        host = os.path.basename(ruta)[:-4]
        filas = []
        with open(ruta, encoding="utf-8-sig") as f:
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
    firma = firma_articulo(prod["marca"], prod["articulo"])      # fichas cuya URL no lleva la marca pero sí el nombre de la línea
    puntuadas = []
    for u, slug, m in filas:
        if not (bt <= slug or (firma and firma <= slug)) or not qt:
            continue
        acierto = sum(1 for t in qt if t in slug)
        score = acierto / len(qt)
        if nums and not (nums & set(re.findall(r"\d+", " ".join(slug)))):
            score *= 0.5
        if score >= UMBRAL:
            puntuadas.append((score, u))
    puntuadas.sort(reverse=True)
    return puntuadas[:TOP]


def abrir(args):
    """Abre UNA página y la comprueba contra TODOS los GTIN que la tienen como candidata (las variantes de un mismo producto comparten fichas)."""
    url, gtins = args
    codigo, texto = descargar(url)
    time.sleep(0.4)
    out = {}
    for g in gtins:
        if codigo == 200 and texto:
            r = analizar(texto, g)
            r.update(gtin=g, url=url, http=codigo)
            if not r["ok"]:
                r["evidencia"] = "el GTIN no figura en ningún campo de identificación de la ficha"
        else:
            r = {"gtin": g, "url": url, "http": codigo, "ok": False, "nivel": None, "evidencia": "no se pudo leer la ficha (HTTP %s)" % codigo}
        out[g] = r
    return url, out


def resolver(prod, host, cands, abiertas):
    """Primera candidata (por orden de parecido) cuyo GTIN se ha comprobado en la ficha."""
    for score, url in cands:
        r = abiertas.get(url, {}).get(prod["gtin"])
        if r and r.get("ok"):
            r = dict(r)
            r.update(host=host, score=round(score, 2), marca=prod["marca"], articulo=prod["articulo"], variante=prod.get("variante", ""))
            return ("ok", r)
    return ("dudosa", {"gtin": prod["gtin"], "marca": prod["marca"], "articulo": prod["articulo"], "variante": prod.get("variante", ""), "host": host,
                       "candidatas": [u for _, u in cands]})

EXPLORADOS = "explorados.csv"   # (gtin, tienda, fecha, resultado) de lo ya abierto en pasadas anteriores: así cada noche se exploran pares NUEVOS
DIAS_EXPLORADO = 12


def cargar_explorados(ruta=EXPLORADOS, dias=DIAS_EXPLORADO):
    """{(gtin, tienda): fecha} de lo explorado hace menos de `dias` días."""
    from datetime import datetime, timedelta, timezone
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    out = {}
    if os.path.exists(ruta):
        with open(ruta, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                try:
                    d = datetime.strptime(r["fecha"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except (ValueError, KeyError):
                    continue
                if d >= limite:
                    out[(r["gtin"], r["tienda"])] = r
    return out


def guardar_explorados(res, ruta=EXPLORADOS):
    """Añade lo explorado en esta pasada (conserva lo anterior de los últimos 30 días)."""
    from datetime import datetime, timezone
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    previo = cargar_explorados(ruta, 30)
    for k, r in res:
        g = r["gtin"]
        h = r["host"]
        previo[(g, h)] = {"gtin": g, "tienda": h, "fecha": ahora, "resultado": "ok" if k == "ok" else "dudosa"}
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["gtin", "tienda", "fecha", "resultado"])
        for (g, h), r in sorted(previo.items()):
            w.writerow([g, h, r["fecha"], r["resultado"]])

def repartir(tareas, tope, vistas=None):
    """Reparte el tope de fichas abiertas por RONDAS entre productos: primero la mejor tienda candidata de cada producto, luego la segunda…
    Así ningún producto se queda sin revisar porque otros tengan muchas candidatas (antes se ordenaba solo por parecido)."""
    por_gtin = {}
    for t in tareas:
        por_gtin.setdefault(t[0]["gtin"], []).append(t)
    for lst in por_gtin.values():
        lst.sort(key=lambda t: -t[2][0][0])
    gtins = sorted(por_gtin)
    orden = []
    ronda = 0
    while True:
        hubo = False
        for g in gtins:
            if ronda < len(por_gtin[g]):
                orden.append(por_gtin[g][ronda])
                hubo = True
        if not hubo:
            break
        ronda += 1
    recorte = []
    vistas = set() if vistas is None else vistas
    for t in orden:
        nuevas = [u for _, u in t[2] if u not in vistas]       # el tope cuenta PÁGINAS DISTINTAS: una ficha compartida por varias variantes se abre una sola vez
        if len(vistas) + len(nuevas) > tope:
            continue
        vistas.update(nuevas)
        recorte.append(t)
    return recorte


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    marcas = [m.strip() for m in sys.argv[1].split(",") if m.strip()]
    prods = cargar_productos(marcas)
    if "--pendientes" in sys.argv and os.path.exists("competencia.csv"):
        with open("competencia.csv", newline="", encoding="utf-8-sig") as f:
            con_fichas = {r[0] for r in list(csv.reader(f))[2:] if len(r) > 15 and r[15] == "PENDIENTE"}
        prods = [p for p in prods if p["gtin"] not in con_fichas]
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
    # si hay demasiadas, se limita el número de fichas abiertas repartiéndolo entre TODOS los productos
    explorados = cargar_explorados()
    nuevas = [t for t in tareas if (t[0]["gtin"], t[1]) not in explorados]
    viejas = [t for t in tareas if (t[0]["gtin"], t[1]) in explorados]
    vistas = set()
    recorte = repartir(nuevas, MAX_ABRIR, vistas) + repartir(viejas, MAX_ABRIR, vistas)    # primero los pares aún no explorados
    pares = {}
    for p, host, cands in recorte:
        for _, url in cands:
            pares.setdefault(url, set()).add(p["gtin"])
    with ThreadPoolExecutor(max_workers=6) as ex:
        abiertas = dict(ex.map(abrir, [(u, sorted(gs)) for u, gs in pares.items()]))
    res = [resolver(p, host, cands, abiertas) for p, host, cands in recorte]
    guardar_explorados([(k, r if k == "ok" else r) for k, r in res])
    verificados = [r for k, r in res if k == "ok"]
    dudosas = [r for k, r in res if k == "dudosa"]
    out = {"marcas": marcas, "productos": len(prods), "tiendas_con_catalogo": len([h for h, f in cat.items() if f]), "verificados": verificados,
           "dudosas": dudosas, "sin_candidatas": sin, "pendientes_por_tope": len(tareas) - len(recorte), "procesados": [p["gtin"] for p in prods]}
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
