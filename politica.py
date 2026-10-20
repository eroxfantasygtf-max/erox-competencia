#!/usr/bin/env python3
"""Registra la política de envíos de una tienda, comprobando que los importes figuran escritos en su página.

Uso:  python politica.py HOST URL_PAGINA_ENVIOS BASE [GRATIS_DESDE]
Ejemplo:  python politica.py hojafresca.com https://hojafresca.com/content/6-envios-gratis 3.85 49.95
Comprueba que URL es del mismo dominio, que BASE (y GRATIS_DESDE si se indica) aparecen en el texto de la página y, si es así,
añade o actualiza la fila de `envios.csv`. Si no aparecen, no escribe nada (código de salida 1).
BASE = envío estándar a domicilio en península para un pedido pequeño; GRATIS_DESDE = pedido mínimo para envío gratis (opcional).
"""
import csv
import html as htmllib
import os
import re
import sys
from datetime import datetime, timezone

from utiles import descargar, host_de

CAMPOS = ["host", "sitemap", "envio_base", "envio_gratis_desde", "envio_url", "comprobado_en"]


def aparece(texto, importe):
    """¿Figura el importe (4,90 / 4.90 / 4,9 / 5) como número independiente?"""
    v = float(importe)
    ent = int(v)
    cts = int(round((v - ent) * 100))
    formas = ["%d[.,]%02d" % (ent, cts)]
    if cts % 10 == 0:
        formas.append("%d[.,]%d" % (ent, cts // 10))
    if cts == 0:
        formas.append(str(ent))
    return any(re.search(r"(?<![\d.,])" + f + r"(?!\d)", texto) for f in formas)


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    host, url, base = sys.argv[1].lower(), sys.argv[2], sys.argv[3]
    gratis = sys.argv[4] if len(sys.argv) > 4 else ""
    h = host_de(url)
    if h.replace("www.", "") != host.replace("www.", ""):
        print("NO: la página de envíos no es del mismo dominio (%s)" % h)
        sys.exit(1)
    cod, txt = descargar(url)
    if cod != 200 or not txt:
        print("NO: no se pudo leer la página (HTTP %s)" % cod)
        sys.exit(1)
    txt = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", txt, flags=re.S | re.I)
    txt = htmllib.unescape(re.sub(r"<[^>]+>", " ", txt)).replace("\xa0", " ")
    faltan = [x for x in (base, gratis) if x and not aparece(txt, x)]
    if faltan:
        print("NO: el importe %s no figura escrito en la página" % ", ".join(faltan))
        sys.exit(1)
    filas = []
    if os.path.exists("envios.csv"):
        with open("envios.csv", newline="", encoding="utf-8") as f:
            filas = [r for r in csv.DictReader(f) if r.get("host", "").lower() != host]
    filas.append({"host": host, "sitemap": "", "envio_base": base, "envio_gratis_desde": gratis, "envio_url": url,
                  "comprobado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    with open("envios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    print("OK: política de %s registrada (base %s, gratis desde %s)" % (host, base, gratis or "—"))


if __name__ == "__main__":
    main()