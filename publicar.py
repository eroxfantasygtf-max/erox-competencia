#!/usr/bin/env python3
"""Fase 2 · paso final: convierte los resultados comprobados en `resultados.json` y llama a construir_csv.py.

Uso:  python publicar.py
Lee   work/resultado.json   (de emparejar.py)  y, si existe, work/extra.json (fichas añadidas por la IA y comprobadas con verificar.py,
      mismo formato que los elementos de «verificados»).
Aplica:
  · como máximo 5 tiendas por GTIN (las de menor precio visible),
  · la política de envíos de cada tienda desde tiendas.csv (el módulo la vuelve a comprobar leyendo su página),
  · «sin ofertas» solo si hay catálogos de ≥ 8 tiendas rastreados y ninguna candidata.
Nunca publica una ficha cuyo GTIN no haya sido comprobado.
"""
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

MAX_TIENDAS = 5
MIN_TIENDAS_SIN_OFERTAS = 8


def politicas(ruta="tiendas.csv"):
    out = {}
    if not os.path.exists(ruta):
        return out
    with open(ruta, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            base = (r.get("envio_base") or "").strip()
            url = (r.get("envio_url") or "").strip()
            if base and url:
                out[r["host"].strip().lower()] = {"base": base, "gratis_desde": (r.get("envio_gratis_desde") or "").strip(), "url": url}
    return out


def main():
    with open("work/resultado.json", encoding="utf-8") as f:
        res = json.load(f)
    verificados = list(res.get("verificados", []))
    if os.path.exists("work/extra.json"):
        with open("work/extra.json", encoding="utf-8") as f:
            verificados += [x for x in json.load(f) if x.get("ok")]
    pol = politicas()
    por_gtin = {}
    for r in verificados:
        if r.get("ok") and r.get("nivel") in ("estructurado", "etiquetado"):
            por_gtin.setdefault(r["gtin"], {})[r["host"]] = r
    hallazgos = []
    for gtin, tiendas in por_gtin.items():
        orden = sorted(tiendas.values(), key=lambda r: (r.get("precio") is None, r.get("precio") or 0))[:MAX_TIENDAS]
        for r in orden:
            h = {"gtin": gtin, "marca": r.get("marca", ""), "articulo": r.get("articulo", ""), "variante": r.get("variante", ""), "url": r["url"],
                 "evidencia": "GTIN comprobado por código (%s: %s); %s" % (r["nivel"], r["evidencia"], (r.get("titulo") or "")[:80])}
            if r["host"] in pol:
                h["politica_envio"] = pol[r["host"]]
            hallazgos.append(h)
    pendientes = {d["gtin"] for d in res.get("dudosas", [])} - set(por_gtin)
    sin_ofertas = []
    if res.get("tiendas_con_catalogo", 0) >= MIN_TIENDAS_SIN_OFERTAS:
        for s in res.get("sin_candidatas", []):
            if s["gtin"] not in por_gtin:
                sin_ofertas.append({"gtin": s["gtin"], "marca": s["marca"], "articulo": s["articulo"], "variante": s["variante"],
                                    "consultas": ["catálogos de %d tiendas rastreados (sitemaps)" % res["tiendas_con_catalogo"], "emparejado por marca, artículo y variante"],
                                    "motivo": "Ninguna ficha candidata en las tiendas rastreadas"})
    # GTIN revisados = los de las marcas procesadas, salvo los que quedaron pendientes por tope de fichas
    import csv as _csv
    marcas = {m.lower() for m in res.get("marcas", [])}
    with open("gtins.csv", newline="", encoding="utf-8") as f:
        todos = [r["gtin"] for r in _csv.DictReader(f) if r["marca"].strip().lower() in marcas]
    if res.get("pendientes_por_tope"):
        vistos = set(por_gtin) | {d["gtin"] for d in res.get("dudosas", [])} | {s["gtin"] for s in res.get("sin_candidatas", [])}
        todos = [g for g in todos if g in vistos]
    out = {"revisado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "gtins_revisados": todos, "hallazgos": hallazgos, "sin_ofertas": sin_ofertas}
    with open("resultados.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("GTIN revisados %d · con tiendas %d · fichas publicadas %d · sin ofertas %d · dudosas sin resolver %d" % (
        len(todos), len(por_gtin), len(hallazgos), len(sin_ofertas), len(pendientes)))
    subprocess.check_call([sys.executable, "construir_csv.py", "resultados.json"])


if __name__ == "__main__":
    main()
