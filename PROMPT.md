# Fase 2 · Emparejado de productos con la competencia (Erox Fantasy)

Trabajas para una tienda online española de productos para adultos. Tu misión: para cada producto de `gtins.csv`, encontrar **las fichas de otras tiendas que venden exactamente ese producto (mismo GTIN)** y publicarlas. No decides precios: el módulo de la tienda vuelve a abrir cada ficha cada pocas horas y comprueba stock, precio y portes.

La parte mecánica la hacen **scripts** (rastrear catálogos, puntuar candidatas, comprobar el GTIN en cada ficha). Tu parte es la que necesita criterio: resolver los casos que los scripts no emparejan. **Nunca publicas una ficha cuyo GTIN no haya comprobado `verificar.py`.**

## Reglas inamovibles
- Solo lectura de páginas públicas con los scripts o `curl`: no compres, no te registres, no inicies sesión, no rellenes formularios.
- No inventes URLs ni datos. Si `verificar.py` da `"ok": false`, la ficha NO se publica.
- Garantía de «mismo producto»: el GTIN debe figurar en un campo de identificación de la ficha (lo comprueba `verificar.py`). Un GTIN solo en la URL o en el nombre de una imagen no vale.
- Si el GTIN coincide pero el título de la ficha indica claramente otra cantidad, tamaño o color que nuestra variante, **no la publiques** y anótalo en tu resumen (posible GTIN reutilizado por la tienda).
- No uses marketplaces (Amazon, eBay, AliExpress, Temu, Wallapop, Fruugo…), comparadores ni tiendas fuera de España.
- Solo escribes en este repositorio. Nunca `push --force`.

## Paso 0 · Rama de datos (para acumular lo ya publicado)
```
git fetch origin
git checkout -B claude/competencia-datos origin/claude/competencia-datos 2>/dev/null || git checkout -b claude/competencia-datos
```
Los resultados se acumulan en `competencia.csv` de esa rama.

## Paso 1 · Elegir las marcas de esta pasada
1. Lee `gtins.csv` (gtin, marca, artículo, variante) y `competencia.csv` si existe (columna 1 = GTIN, columna 14 = fecha UTC de la última revisión).
2. Para cada marca calcula la antigüedad de su GTIN **más atrasado** (sin fila = nunca revisado). Cada GTIN solo se revisa de nuevo a los **14 días**.
3. Elige las **2 marcas** con GTIN más atrasados. Si ninguna tiene GTIN atrasados, termina con una línea. (En una prueba piloto te dirán qué marca usar.)

## Paso 2 · Rastrear catálogos
```
python catalogo.py "MARCA1,MARCA2"
```
Lee `tiendas.csv` (tiendas conocidas) y guarda en `work/` las fichas de esas marcas de cada tienda. Puede tardar varios minutos; si una tienda falla, el script sigue con las demás.

## Paso 3 · Emparejar y comprobar
```
python emparejar.py "MARCA1,MARCA2"
```
Genera `work/resultado.json` con `verificados` (ficha + GTIN comprobado), `dudosas` (había candidatas pero ninguna pasó la comprobación) y `sin_candidatas`.

## Paso 4 · Tu parte: resolver lo que los scripts no emparejan
Trabaja sobre `dudosas` y `sin_candidatas` (máximo 30 productos por pasada; empieza por los que no tienen **ninguna** tienda verificada):
1. Mira las URLs candidatas y el catálogo `work/<tienda>.tsv` de esa tienda (`grep -i` con palabras clave del producto, abreviaturas, sinónimos: `ud`/`uds`, `mm`, nombres comerciales distintos…).
2. Elige como máximo 3 URLs plausibles por producto y tienda y ejecuta:
   ```
   python verificar.py GTIN URL1 URL2 URL3
   ```
3. Añade a `work/extra.json` (lista JSON) los resultados con `"ok": true`, completando `host` (dominio de la URL), `marca`, `articulo` y `variante` con los de `gtins.csv`.
4. Si ninguna tienda del catálogo tiene el producto, **no inventes**: déjalo. Opcional, para productos importantes: busca la ficha con Bing desde la terminal, por ejemplo `curl -s -A "Mozilla/5.0" "https://www.bing.com/search?q=site:TIENDA+MARCA+ARTICULO&cc=es&setlang=es&mkt=es-ES"` y comprueba cada URL con `verificar.py`.

## Paso 4b · Políticas de envío de las tiendas que salieron verificadas
El módulo **no usa una ficha si no puede comprobar los portes a domicilio**. Mira `work/resultado.json` (y `work/extra.json`): para cada tienda con fichas verificadas que **no tenga** política en `tiendas.csv` ni en `envios.csv` (máximo 15 tiendas por pasada, las que más fichas tengan):
1. Busca su página de envíos / gastos de envío (enlace del pie de página, «envíos», «condiciones de compra», «entrega»): `curl` a la portada y `grep -i` por esos enlaces.
2. Lee el texto de esa página y localiza el **importe base del envío estándar a domicilio en península** y, si existe, el **pedido mínimo para envío gratis**. Si hay varias tarifas, usa la de un pedido pequeño de un solo artículo ligero. Si no queda claro, no registres esa tienda.
3. Regístrala con el script, que comprueba que los importes están escritos en la página:
   ```
   python politica.py DOMINIO URL_PAGINA_ENVIOS BASE [GRATIS_DESDE]
   ```
   (importes con punto decimal, p. ej. `4.90 50`). Si dice `NO`, corrige o descarta la tienda.
`envios.csv` se sube con el resto (Paso 6).

## Paso 5 · Publicar
```
python publicar.py
```
Elige hasta 5 tiendas por GTIN (las de menor precio visible), añade la política de envíos de `tiendas.csv`, escribe `resultados.json` y genera `competencia.csv` (uniéndolo a lo ya publicado; descarta filas de más de 21 días).

## Paso 6 · Subir
Haz commit de `competencia.csv`, `resultados.json` y `envios.csv` (si existe) y súbelo: `git push origin claude/competencia-datos`. Si lo rechaza, `git pull --rebase origin claude/competencia-datos` y repite; si hay conflicto en `competencia.csv`, rehazlo ejecutando `publicar.py` partiendo de la versión remota.

## Resumen final (corto)
Marcas procesadas · productos · productos con ≥1 tienda verificada · fichas publicadas · tiendas rastreadas con éxito y las que fallaron · casos con título incoherente · tiempo aproximado.

## Si algo falla
- Un script lanza error: léelo, corrígelo con un cambio mínimo en tu copia local y continúa; cuéntalo en el resumen.
- Muchas tiendas devuelven 403/429: reduce el trabajo a una sola marca y avísalo.
- Nunca publiques datos que no hayas comprobado.
