#!/usr/bin/env python3
"""Construye competencia.csv (contrato EROX_COMPETENCIA v1) a partir de los hallazgos de una pasada de investigación.

Uso:  python construir_csv.py resultados.json

Lee `resultados.json` (ver PROMPT.md) y el `competencia.csv` anterior, sustituye las filas de los GTIN revisados en esta pasada,
descarta filas con más de 21 días y escribe un CSV coherente (la fila de control declara el número exacto de filas).
Solo usa la biblioteca estándar. No hace peticiones de red.
"""
import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

DESTINO = "ES-28902"
MAX_DIAS = 21
CSV_SALIDA = "competencia.csv"
FUENTE = "Tarea Claude"
CABECERA = ["GTIN", "Marca", "Articulo", "Variante", "Precio IVA", "Envio IVA", "Moneda", "Destino", "En stock", "Modelo verificado",
            "IVA verificado", "Sin condiciones", "Confianza", "Fecha UTC", "URL", "Estado", "Prueba identidad", "Prueba stock", "Prueba IVA",
            "Prueba envio", "Prueba condiciones", "Fuente"]


def ahora():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def gtin_valido(g):
    """GTIN-8/12/13/14 con dígito de control correcto."""
    if not re.fullmatch(r"\d{8}|\d{12,14}", g or ""):
        return False
    d = [int(c) for c in g]
    suma = sum(x * (3 if i % 2 == 0 else 1) for i, x in enumerate(reversed(d[:-1])))
    return (10 - suma % 10) % 10 == d[-1]


def url_valida(u):
    p = urlparse(u or "")
    return p.scheme == "https" and bool(p.hostname) and "." in p.hostname and not re.fullmatch(r"[\d.]+", p.hostname)


def decimal(v):
    """'4,90' / 4.9 / '4.90' → '4.90' (texto con punto), o None."""
    if v is None or v == "":
        return None
    try:
        return "%.2f" % float(str(v).replace(",", "."))
    except ValueError:
        return None


def fila_pista(h, momento):
    g = str(h.get("gtin", "")).strip()
    if not gtin_valido(g) or not url_valida(h.get("url")):
        return None
    host = urlparse(h["url"]).hostname.lower()
    pol = h.get("politica_envio") or None
    pol_json = ""
    if pol:
        base = decimal(pol.get("base"))
        libre = decimal(pol.get("gratis_desde"))
        if base is not None and url_valida(pol.get("url")) and urlparse(pol["url"]).hostname.lower() == host:
            pol_json = json.dumps({"schema": "erox-shipping/1", "host": host, "destination": DESTINO, "method": "home", "currency": "EUR",
                                   "base": base, "free_from": libre, "source_url": pol["url"], "checked_at": iso(momento), "status": "VERIFICADA"},
                                  ensure_ascii=False)
    ident = (h.get("evidencia") or "")[:300]
    return [g, h.get("marca", ""), h.get("articulo", ""), h.get("variante", ""), "", "", "EUR", DESTINO, "FALSE", "FALSE", "FALSE", "FALSE", 0,
            iso(momento), h["url"], "PENDIENTE", ident, "", "", pol_json, "", FUENTE]


def fila_sin_ofertas(n, momento):
    g = str(n.get("gtin", "")).strip()
    consultas = [str(q)[:120] for q in (n.get("consultas") or [])][:5]
    if not gtin_valido(g) or len(consultas) < 2:
        return None
    ident = json.dumps({"schema": "erox-no-offers/1", "gtin": g, "destination": DESTINO, "checked_at": iso(momento), "queries": consultas,
                        "unresolved": 0, "reason": str(n.get("motivo", ""))[:280]}, ensure_ascii=False)
    return [g, n.get("marca", ""), n.get("articulo", ""), n.get("variante", ""), "", "", "EUR", DESTINO, "FALSE", "FALSE", "FALSE", "FALSE", 0,
            iso(momento), "", "BUSQUEDA_COMPLETA_SIN_OFERTAS", ident, "", "", "", "", FUENTE]


def leer_previo():
    try:
        with open(CSV_SALIDA, newline="", encoding="utf-8-sig") as f:
            filas = list(csv.reader(f))
    except FileNotFoundError:
        return []
    return [r for r in filas[2:] if len(r) >= 22 and r[0]]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        res = json.load(f)
    momento = parse_iso(res.get("revisado_en")) or ahora()
    revisados = {str(g).strip() for g in res.get("gtins_revisados", [])}
    nuevas = []
    descartadas = 0
    for h in res.get("hallazgos", []):
        fila = fila_pista(h, momento)
        if fila:
            nuevas.append(fila)
        else:
            descartadas += 1
    for n in res.get("sin_ofertas", []):
        fila = fila_sin_ofertas(n, momento)
        if fila:
            nuevas.append(fila)
        else:
            descartadas += 1
    # dentro de una pasada, un GTIN con hallazgos no puede figurar también «sin ofertas»
    con_hallazgos = {r[0] for r in nuevas if r[15] == "PENDIENTE"}
    nuevas = [r for r in nuevas if not (r[15] == "BUSQUEDA_COMPLETA_SIN_OFERTAS" and r[0] in con_hallazgos)]
    # sin duplicados (GTIN + URL)
    vistos, unicas = set(), []
    for r in nuevas:
        k = (r[0], r[14])
        if k not in vistos:
            vistos.add(k)
            unicas.append(r)
    limite = ahora() - timedelta(days=MAX_DIAS)
    conservadas = []
    for r in leer_previo():
        f = parse_iso(r[13])
        if r[0] in revisados or f is None or f < limite:
            continue
        conservadas.append(r)
    filas = conservadas + unicas
    pub = "nube_" + ahora().strftime("%Y%m%d%H%M%S")
    with open(CSV_SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["EROX_COMPETENCIA", 1, pub, "COMPLETADA", iso(ahora()), len(filas), DESTINO])
        w.writerow(CABECERA)
        w.writerows(filas)
    print("publicación %s: %d filas (%d nuevas, %d conservadas, %d descartadas por datos no válidos)" % (pub, len(filas), len(unicas), len(conservadas), descartadas))


if __name__ == "__main__":
    main()
