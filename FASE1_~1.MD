# Fase 1 · Mapa de tiendas de la competencia (cada ~45 días, a mano o con IA)

Objetivo: mantener `tiendas.csv`, la lista de tiendas españolas que compiten con Erox Fantasy en nuestras marcas, con su **política de envíos**. La Fase 2 rastrea esas tiendas.

**Quién la hace:** ChatGPT Plus con «Investigación profunda» (una vez cada ~45 días, sin coste extra), o una tarea de Claude. El resultado se pega en `tiendas.csv`.

## Texto para pegar en ChatGPT (Investigación profunda)

> Eres analista de competencia de una tienda online española de productos para adultos (sexshop, preservativos, lubricantes, juguetes). Necesito el **mapa de tiendas competidoras en España** para estas marcas: DUREX, CONTROL, SATISFYER, LELO, WOMANIZER, FLESHLIGHT, TENGA, PJUR, SHUNGA, MISTER SIZE, MY SIZE PRO.
>
> 1. Localiza hasta **40 tiendas online que vendan esas marcas y envíen a España peninsular**, priorizando las que aparecen bien posicionadas en Google (búsquedas de «comprar <marca> <producto>») y en Google Shopping. Incluye sexshops, parafarmacias y farmacias online y grandes minoristas. Excluye marketplaces (Amazon, eBay, AliExpress, Temu, Miravia, Fruugo), comparadores, tiendas fuera de España y tiendas de Canarias/Ceuta/Melilla (precios sin IVA).
> 2. De cada tienda aporta: **dominio** (sin https://), la **URL de su sitemap** si la conoces (suele estar en `dominio/robots.txt`, línea «Sitemap:»), y su **política de envíos a domicilio en península**: importe base del envío estándar y pedido mínimo para envío gratis, **copiando los importes tal como están escritos** y dando la **URL de la página donde aparecen**. Si no lo ves con claridad, deja esos campos vacíos; no supongas nada.
> 3. Entrega el resultado **solo como CSV** con esta cabecera exacta y una tienda por línea:
> `host,sitemap,envio_base,envio_gratis_desde,envio_url,notas`
> (importes con punto decimal, por ejemplo `4.90`; sin símbolo €).
> 4. Después del CSV, añade una lista breve con las tiendas descartadas y por qué.

## Qué hacer con el resultado
1. Revisa por encima las filas (¿dominios reales y españoles?).
2. Sustituye el contenido de `tiendas.csv` en GitHub (editar el archivo con el lápiz y pegar, o subir uno nuevo con el mismo nombre). Conserva las tiendas que ya tuvieran política si la nueva investigación no las repite.
3. No hace falta tocar nada más: la Fase 2 la usará en su próxima pasada.

## Reglas de calidad
- Una política de envíos con importes inventados o sin URL se descarta sola: el módulo vuelve a abrir esa página y exige encontrar los importes escritos.
- Menos tiendas, pero reales, es mejor que muchas dudosas.
