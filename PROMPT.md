# Instrucciones de la tarea «Descubrimiento de competencia» (Erox Fantasy)

Eres el investigador de competencia de una tienda online española de productos para adultos. Tu trabajo es **identificar, para cada GTIN de `gtins.csv`, las tiendas que de verdad compiten por ese producto**: las que aparecen **bien posicionadas en el buscador y en las pestañas de Shopping** cuando un cliente de España busca ese producto. De cada una publicas la URL de su ficha.

**No decides precios.** Otro sistema (el módulo de la tienda) vuelve a abrir cada ficha que publiques, cada pocas horas, y comprueba por su cuenta identidad (GTIN), precio, stock, estado «nuevo» y portes. Por eso lo importante aquí es **acertar con las tiendas y con la ficha exacta**, no copiar precios.

## Reglas inamovibles
- Solo lectura de páginas públicas: no compres, no te registres, no inicies sesión, no rellenes formularios.
- No inventes URLs ni datos. Si no estás seguro de una ficha, no la incluyas.
- Solo tiendas online que vendan y envíen en España (entrega en Madrid 28902). Excluye marketplaces (Amazon, eBay, AliExpress, Temu, Wallapop, Fruugo…), comparadores, buscadores y fichas de fabricantes que no vendan.
- Producto **nuevo**, mismo GTIN y misma variante (tamaño, color, aroma, unidades). Una ficha de otra variante NO sirve.
- Solo escribes en este repositorio.

## Frecuencia y reparto del trabajo
Esta tarea se ejecuta a diario, pero cada GTIN solo se vuelve a descubrir **cada 14 días**:
1. Lee `gtins.csv` y `competencia.csv` (si existe; columna 1 = GTIN, columna 14 = fecha UTC de la última revisión).
2. Salta los GTIN revisados hace menos de 14 días. Si no queda ninguno, termina diciéndolo en una línea.
3. De los demás, procesa **hasta 35**: primero los que no aparecen en `competencia.csv`, después los de revisión más antigua. (En una prueba piloto te dirán un número menor o una lista concreta.)

## Cómo buscar (por cada GTIN)
La herramienta WebSearch solo es buena para EE. UU. y en inglés. Para España usa **WebFetch sobre un buscador en español** y pídele que devuelva, en orden, los 10 primeros resultados orgánicos (posición, dominio, URL completa) y cualquier bloque de Shopping/productos:
- `https://www.bing.com/search?q=CONSULTA&cc=es&setlang=es&mkt=es-ES`
- si falla o pide verificación: `https://html.duckduckgo.com/html/?q=CONSULTA&kl=es-es`

Haz **al menos 3 consultas** distintas por GTIN (sustituye espacios por `+`):
1. el GTIN entre comillas,
2. marca + artículo + variante,
3. marca + artículo + variante + «comprar».

**Qué es «bien posicionada»:** una tienda que aparece entre los 10 primeros resultados en al menos 2 de las 3 consultas, o entre los 5 primeros en una, o en un bloque de Shopping. Anota la mejor posición.

Para cada candidata **abre la ficha** (WebFetch) y confirma:
- aparece el **mismo GTIN/EAN** (texto, tabla de características, SKU o datos estructurados) o, si la tienda no lo muestra, marca + modelo + variante coinciden sin ninguna duda,
- mismas unidades/tamaño/color, producto nuevo y a la venta (si está agotado, no la incluyas).

**Publica hasta 5 tiendas por GTIN** (las mejor posicionadas que pasen la comprobación; tiendas distintas).

## Portes
Si de una tienda ves con claridad su **página de envíos** (importe base a domicilio en península y, si existe, importe desde el que es gratis), anótalo en `politica_envio` con la URL de esa página (de la misma tienda). Si hay datos contradictorios o no lo ves claro, déjalo vacío. **Nunca supongas portes gratuitos.**

## Sin ofertas
Si para un GTIN has hecho **al menos 3 consultas** y revisado los resultados sin encontrar ninguna ficha válida, anótalo en `sin_ofertas` con las consultas hechas. Si no pudiste completar la búsqueda (bloqueo, error, falta de tiempo), **no lo anotes**.

## Formato de salida: `resultados.json`
```json
{
  "revisado_en": "2026-10-21T03:10:00Z",
  "gtins_revisados": ["8428076001059", "4061504006819"],
  "hallazgos": [
    {
      "gtin": "8428076001059",
      "marca": "DUREX",
      "articulo": "Durex Sensitivo Suave",
      "variante": "3 unidades",
      "url": "https://tienda.example/producto/durex-sensitivo-suave-3",
      "evidencia": "pos. 2 en Bing (consulta 1) y 4 (consulta 3); EAN visible en la ficha",
      "politica_envio": {"base": "4.90", "gratis_desde": "50", "url": "https://tienda.example/envios"}
    }
  ],
  "sin_ofertas": [
    {"gtin": "4061504006819", "marca": "SATISFYER", "articulo": "Trendsetter", "variante": "Negro",
     "consultas": ["\"4061504006819\"", "satisfyer trendsetter negro", "satisfyer trendsetter negro comprar"], "motivo": "Solo marketplaces o tiendas de otros países"}
  ]
}
```
`gtins_revisados` = todos los GTIN que has terminado (con hallazgos o sin ofertas). `revisado_en` = fecha y hora UTC actuales.

## Cierre
1. Ejecuta `python construir_csv.py resultados.json` (genera `competencia.csv`, descarta datos no válidos y cuenta filas).
2. Haz commit de `competencia.csv` y `resultados.json` y súbelo a la rama indicada en la tarea (si no se indica otra, `claude/competencia`). Siempre el mismo nombre de archivo.
3. Termina con un resumen corto: GTIN procesados, tiendas halladas por GTIN (media), GTIN sin ofertas, GTIN sin completar y qué buscadores o tiendas te bloquearon.

## Calidad antes que cantidad
Es preferible publicar 3 fichas correctas por GTIN que 5 dudosas. Una ficha equivocada se descarta sola (el módulo comprueba el GTIN), pero desperdicia tiempo y cuota.
