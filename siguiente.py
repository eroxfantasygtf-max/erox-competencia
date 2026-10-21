#!/usr/bin/env python3
"""Elige las marcas de esta pasada (y no lo calcula la IA): las que más productos tienen sin revisar en los últimos 14 días.

Uso:  python siguiente.py [N=2]      → imprime «MARCA1,MARCA2» (o NADA_ATRASADO)
Un producto cuenta como revisado cuando figura en `revisados.csv` (lo escribe publicar.py, haya o no hallado fichas) o, si ese archivo
no existe, cuando tiene fila en `competencia.csv`. Pasados 14 días vuelve a estar pendiente.
Si existe `repasar_desde.txt` (una fecha AAAA-MM-DD), todo lo revisado antes de esa fecha cuenta como pendiente.
"""
import csv
import os
import sys
from datetime import datetime, timedelta, timezone

DIAS = 14


def leer_revisados():
    ult = {}
    if os.path.exists("revisados.csv"):
        with open("revisados.csv", newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                try:
                    ult[r["gtin"]] = datetime.strptime(r["fecha"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except (ValueError, KeyError):
                    pass
    elif os.path.exists("competencia.csv"):
        with open("competencia.csv", newline="", encoding="utf-8-sig") as f:
            for r in list(csv.reader(f))[2:]:
                try:
                    t = datetime.strptime(r[13], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    ult[r[0]] = max(ult.get(r[0], t), t)
                except (ValueError, IndexError):
                    pass
    return ult


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    ult = leer_revisados()
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS)
    # Orden del propietario: «repasar desde AAAA-MM-DD». Lo revisado antes de esa fecha vuelve a estar pendiente
    # (útil al subir tiendas nuevas a tiendas.csv: así se repasan todas las marcas sin esperar 14 días).
    if os.path.exists("repasar_desde.txt"):
        try:
            with open("repasar_desde.txt", encoding="utf-8-sig") as f:
                desde = datetime.strptime(f.read().strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            limite = max(limite, desde)
        except ValueError:
            pass
    pend = {}
    with open("gtins.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = ult.get(r["gtin"])
            if t is None or t < limite:
                pend.setdefault(r["marca"], []).append(t)
    if not pend:
        print("NADA_ATRASADO")
        return
    orden = sorted(pend.items(), key=lambda kv: (-len(kv[1]), min((t or datetime(1970, 1, 1, tzinfo=timezone.utc)) for t in kv[1])))
    print(",".join(m for m, _ in orden[:n]))
    for m, v in orden:
        sys.stderr.write("%s: %d productos pendientes\n" % (m, len(v)))


if __name__ == "__main__":
    main()