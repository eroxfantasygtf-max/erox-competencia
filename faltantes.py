#!/usr/bin/env python3
"""Lista los productos de la pasada que NO tienen ninguna tienda verificada, con candidatas más flexibles para que las revises.

Uso:  python faltantes.py
Lee work/resultado.json (y work/extra.json) y work/<tienda>.tsv. Para cada producto sin tienda verificada imprime hasta 8 URL de los
catálogos cuya dirección comparte palabras con el producto (umbral bajo). Tú eliges las plausibles y las compruebas con verificar.py.
"""
import csv
import glob
import json
import os
import re

from utiles import tokens


def main():
    verif = set()
    marcas = []
    for ruta in ("work/resultado.json", "work/extra.json"):
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                marcas = d.get("marcas", marcas)
                verif |= {r["gtin"] for r in d.get("verificados", []) if r.get("ok")}
            else:
                verif |= {r["gtin"] for r in d if r.get("ok")}
    ms = {m.lower() for m in marcas}
    cat = {}
    for ruta in glob.glob("work/*.tsv"):
        host = os.path.basename(ruta)[:-4]
        with open(ruta, encoding="utf-8") as f:
            cat[host] = [(l.split("\t")[0], set(tokens(re.sub(r"^https?://[^/]+", "", l.split("\t")[0])))) for l in f if l.strip()]
    falt = 0
    with open("gtins.csv", newline="", encoding="utf-8-sig") as f:
        for p in csv.DictReader(f):
            if p["marca"].lower() not in ms or p["gtin"] in verif:
                continue
            falt += 1
            qt = tokens("%s %s %s" % (p["marca"], p["articulo"], p.get("variante", "")))
            bt = set(tokens(p["marca"]))
            nums = set(re.findall(r"\d+", p.get("variante", "") or ""))
            c = []
            for host, filas in cat.items():
                for u, slug in filas:
                    if not bt <= slug:
                        continue
                    s = sum(1 for t in qt if t in slug) / max(len(qt), 1)
                    if nums and nums & set(re.findall(r"\d+", " ".join(slug))):
                        s += 0.15
                    if s >= 0.2:
                        c.append((s, u))
            c.sort(reverse=True)
            print("%s | %s | %s | %s" % (p["gtin"], p["marca"], p["articulo"], p.get("variante", "")))
            for s, u in c[:8]:
                print("    %.2f %s" % (s, u))
    print("RESUMEN: %d productos sin ninguna tienda verificada" % falt)


if __name__ == "__main__":
    main()