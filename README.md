# erox-competencia

Datos para la investigación de precios de competencia de Erox Fantasy.

- `gtins.csv`: artículos de marcas de competencia (GTIN, marca, artículo, variante). Se regenera desde la tienda cuando cambie el catálogo.
- `PROMPT.md`: instrucciones de la tarea programada de Claude.
- `construir_csv.py`: genera `competencia.csv` (el módulo de la tienda lo lee).
- `competencia.csv` / `resultados.json`: los publica la tarea en la rama `claude/competencia`.

No contiene costes, precios propios ni datos de clientes.