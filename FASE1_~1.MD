# Fase 1 · Mapa de tiendas de la competencia (cada ~45 días, a mano)

`tiendas.csv` es la lista de tiendas españolas que la nube rastrea (con su dominio, su sitemap y, si se conoce, su envío). Sin tiendas nuevas la competencia se queda estancada. El módulo te avisa cuando toca renovarla (*Competencia → Mapa de tiendas*).

## Paso a paso (unos 10 minutos)

1. Abre ChatGPT Plus, elige **Investigación profunda** y pega el texto de abajo.
2. Cuando termine, **copia solo el CSV** (la parte que empieza por `host,sitemap,envio_base,…`).
3. **Pégamelo en el chat de Claude** y escribe «integra el mapa de tiendas». Yo reviso los dominios, **añado las tiendas nuevas sin tocar las que ya tienes** (conservo sus portes y sitemaps) y te devuelvo un `tiendas.csv` listo.
4. En GitHub (repositorio `erox-competencia`, rama `main`): **Add file → Upload files**, arrastra el `tiendas.csv` nuevo y pulsa **Commit changes**.
5. En el módulo: **Competencia → Mapa de tiendas → «Ya lo he actualizado»**. Eso reinicia el contador del aviso.

No hay que hacer nada más: la nube usa la lista nueva en su próxima pasada.

## Texto para pegar en ChatGPT (Investigación profunda)

> Eres analista de competencia de una tienda online española de productos para adultos (sexshop, preservativos, lubricantes, juguetes). Necesito el **mapa de tiendas competidoras en España** para estas marcas: DUREX, CONTROL, SATISFYER, LELO, WOMANIZER, FLESHLIGHT, TENGA, PJUR, SHUNGA, MISTER SIZE, MY SIZE PRO.
>
> 1. Localiza hasta **40 tiendas online que vendan esas marcas y envíen a España peninsular**, priorizando las que aparecen bien posicionadas en Google (búsquedas de «comprar <marca> <producto>») y en Google Shopping. Incluye sexshops, parafarmacias y farmacias online y grandes minoristas. Excluye marketplaces (Amazon, eBay, AliExpress, Temu, Miravia, Fruugo), comparadores, tiendas fuera de España y tiendas de Canarias/Ceuta/Melilla (precios sin IVA).
> 2. De cada tienda aporta: **dominio** (sin https://), la **URL de su sitemap** si la conoces (suele estar en `dominio/robots.txt`, línea «Sitemap:»), y su **política de envíos a domicilio en península**: importe base del envío estándar y pedido mínimo para envío gratis, **copiando los importes tal como están escritos** y dando la **URL de la página donde aparecen**. Si no lo ves con claridad, deja esos campos vacíos; no supongas nada.
> 3. Entrega el resultado **solo como CSV** con esta cabecera exacta y una tienda por línea:
> `host,sitemap,envio_base,envio_gratis_desde,envio_url,notas`
> (importes con punto decimal, por ejemplo `4.90`; sin símbolo €).
> 4. Después del CSV, añade una lista breve con las tiendas descartadas y por qué.

## Reglas de calidad
- Menos tiendas pero reales es mejor que muchas dudosas. Un envío con importes inventados o sin URL se descarta solo: la nube y el módulo vuelven a abrir esa página y exigen ver los importes escritos.
- Tiendas que no publican su envío: no pasa nada, se dejan vacías. Si quieres usarlas, mira el envío en su carrito y añádelo en el módulo (*Ajustes → Competencia → Tarifas de envío manuales*).
- Amazon no entra en el mapa (sus precios no se usan para igualar).
