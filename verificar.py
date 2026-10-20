#!/usr/bin/env python3
"""Comprueba que una ficha de producto es DE VERDAD el GTIN indicado.

Uso:  python verificar.py GTIN URL [URL ...]      (imprime una línea JSON por URL)

Regla de identidad (garantía de «mismo producto»): el GTIN tiene que aparecer en un campo de identificación de la ficha:
  · estructurado: JSON-LD (gtin, gtin8/12/13/14), datos de producto de PrestaShop (ean13, upc), microdatos (itemprop=gtin…)
  · etiquetado: texto de la ficha precedido de EAN / GTIN / código de barras / Referencia / SKU (también SKU con prefijo de letras)
Si el GTIN solo aparece en la URL, en nombres de imagen o suelto en la página, la ficha NO se acepta.
Además extrae título, precio, moneda y disponibilidad como información (el módulo de la tienda lo vuelve a comprobar todo).
"""
import html as htmllib
import json
import re
import sys

from utiles import clave_gtin, descargar

GT_CAMPOS = ("gtin", "gtin8", "gtin12", "gtin13", "gtin14", "isbn", "ean13", "ean", "upc", "barcode")


def _recorrer(nodo, productos, prof=0):
    if prof > 8:
        return
    if isinstance(nodo, list):
        for n in nodo:
            _recorrer(n, productos, prof + 1)
    elif isinstance(nodo, dict):
        tipos = nodo.get("@type")
        tipos = tipos if isinstance(tipos, list) else [tipos]
        if any(t in ("Product", "ProductGroup", "IndividualProduct") for t in tipos):
            productos.append(nodo)
        for k in ("@graph", "hasVariant"):
            if k in nodo:
                _recorrer(nodo[k], productos, prof + 1)


def _json_ld(texto):
    productos = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', texto, re.S | re.I):
        crudo = htmllib.unescape(m.group(1)).strip()
        try:
            _recorrer(json.loads(crudo), productos)
        except ValueError:
            try:
                _recorrer(json.loads(re.sub(r"[\x00-\x1f]", " ", crudo)), productos)
            except ValueError:
                pass
    return productos


def _ofertas(nodo):
    o = nodo.get("offers")
    lista = o if isinstance(o, list) else [o] if isinstance(o, dict) else []
    out = []
    for x in lista:
        if isinstance(x, dict) and isinstance(x.get("offers"), (list, dict)):
            out.extend(_ofertas(x))
        elif isinstance(x, dict):
            out.append(x)
    return out


def _numero(v):
    if v is None:
        return None
    s = re.sub(r"[^\d.,]", "", str(v))
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def _igual(valor, clave):
    return clave_gtin(valor) == clave and clave != ""


def _con_prefijo(valor, clave):
    """SKU del tipo «DU8428076001059» (1 a 3 letras + GTIN)."""
    return bool(re.fullmatch(r"[A-Za-z]{1,3}[-_ ]?0*" + re.escape(clave), str(valor or "").strip()))


def analizar(texto, gtin):
    """Devuelve el diccionario de resultado para una página ya descargada."""
    clave = clave_gtin(gtin)
    res = {"ok": False, "nivel": None, "evidencia": "", "titulo": "", "precio": None, "moneda": None, "disponibilidad": None}
    m = re.search(r"<title[^>]*>(.*?)</title>", texto, re.S | re.I)
    res["titulo"] = re.sub(r"\s+", " ", htmllib.unescape(m.group(1))).strip()[:160] if m else ""

    # 1) JSON-LD
    for p in _json_ld(texto):
        for k in GT_CAMPOS:
            if k in p and _igual(p[k], clave):
                res.update(ok=True, nivel="estructurado", evidencia="JSON-LD " + k)
        for o in _ofertas(p):
            for k in GT_CAMPOS:
                if k in o and _igual(o[k], clave):
                    res.update(ok=True, nivel="estructurado", evidencia="JSON-LD (oferta) " + k)
        sku = p.get("sku")
        if not res["ok"] and sku and (_igual(sku, clave) or _con_prefijo(sku, clave)):
            res.update(ok=True, nivel="etiquetado", evidencia="JSON-LD sku " + str(sku))
        if res["ok"] or res["precio"] is None:
            for o in _ofertas(p):
                pr = _numero(o.get("price")) or _numero((o.get("priceSpecification") or {}).get("price") if isinstance(o.get("priceSpecification"), dict) else None)
                if pr is not None:
                    res["precio"] = pr
                    res["moneda"] = o.get("priceCurrency")
                    res["disponibilidad"] = str(o.get("availability", "")).rsplit("/", 1)[-1] or None
                    break
        if res["ok"]:
            break

    # 2) datos de producto de PrestaShop (atributo data-product)
    m = re.search(r'\sdata-product\s*=\s*"([^"]{20,})"', texto)
    if m:
        try:
            d = json.loads(htmllib.unescape(m.group(1)))
        except ValueError:
            d = {}
        if isinstance(d, dict) and "price_amount" in d:
            if not res["ok"]:
                for k in ("ean13", "upc", "isbn"):
                    if k in d and _igual(d[k], clave):
                        res.update(ok=True, nivel="estructurado", evidencia="PrestaShop " + k)
                ref = d.get("reference")
                if not res["ok"] and ref and (_igual(ref, clave) or _con_prefijo(ref, clave)):
                    res.update(ok=True, nivel="etiquetado", evidencia="PrestaShop referencia " + str(ref))
            if res["precio"] is None:
                res["precio"] = _numero(d.get("price_amount"))
                av = d.get("availability")
                res["disponibilidad"] = {"available": "InStock", "last_remaining_items": "InStock", "unavailable": "OutOfStock"}.get(av, av)
            m2 = re.search(r'property="product:price:currency"[^>]*content="([A-Z]{3})"', texto)
            res["moneda"] = res["moneda"] or (m2.group(1) if m2 else None)

    # 3) microdatos y claves JSON sueltas
    if not res["ok"]:
        for m in re.finditer(r'itemprop\s*=\s*["\'](gtin\d*|sku)["\'][^>]*?(?:content\s*=\s*["\']([^"\']+)["\']|>([^<]+)<)', texto, re.I):
            v = (m.group(2) or m.group(3) or "").strip()
            if _igual(v, clave) or (m.group(1).lower() == "sku" and _con_prefijo(v, clave)):
                res.update(ok=True, nivel="estructurado" if m.group(1).lower() != "sku" else "etiquetado", evidencia="microdatos " + m.group(1))
                break
    if not res["ok"]:
        m = re.search(r'["\'](ean13?|gtin\d*|barcode|upc)["\']\s*:\s*["\']?0*' + re.escape(clave) + r'(?!\d)', texto, re.I)
        if m:
            res.update(ok=True, nivel="estructurado", evidencia="dato «" + m.group(1) + "» en la ficha")

    # 4) texto etiquetado (EAN, GTIN, código de barras, referencia, SKU)
    if not res["ok"]:
        plano = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", texto, flags=re.S | re.I)
        plano = htmllib.unescape(re.sub(r"<[^>]+>", " ", plano))
        plano = re.sub(r"\s+", " ", plano)
        m = re.search(r"(?i)(ean(?:-?13)?|gtin(?:-?1[34]|-?8)?|c[oó]d(?:igo)?\.? ?(?:de )?barras|referencia|ref\.?|sku|upc)\W{0,40}?(?<!\d)[A-Za-z]{0,3}0*" + re.escape(clave) + r"(?!\d)", plano)
        if m:
            res.update(ok=True, nivel="etiquetado", evidencia="texto «" + m.group(0)[:60] + "»")

    # información (no decisiva): meta de precio si aún no hay
    if res["precio"] is None:
        m = re.search(r'property="(?:product|og):price:amount"[^>]*content="([^"]+)"', texto)
        if m:
            res["precio"] = _numero(m.group(1))
        m = re.search(r'property="(?:product|og):price:currency"[^>]*content="([A-Z]{3})"', texto)
        if m:
            res["moneda"] = m.group(1)
    return res


def verificar(gtin, url):
    codigo, texto = descargar(url)
    if codigo != 200 or not texto:
        return {"gtin": gtin, "url": url, "http": codigo, "ok": False, "nivel": None, "evidencia": "no se pudo leer la ficha (HTTP %s)" % codigo}
    r = analizar(texto, gtin)
    r.update(gtin=gtin, url=url, http=codigo)
    if not r["ok"]:
        r["evidencia"] = "el GTIN no figura en ningún campo de identificación de la ficha"
    return r


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    for u in sys.argv[2:]:
        print(json.dumps(verificar(sys.argv[1], u), ensure_ascii=False))
