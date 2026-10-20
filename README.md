# erox-competencia

Datos y herramientas para vigilar la competencia de Erox Fantasy.

**Tres fases**
1. **Mapa de tiendas** (`FASE1_MAPA_TIENDAS.md`, cada ~45 días, a mano o con ChatGPT Plus): mantiene `tiendas.csv`.
2. **Emparejado** (`PROMPT.md`, tarea programada de Claude): rastrea catálogos (`catalogo.py`), empareja y comprueba el GTIN de cada ficha (`emparejar.py`, `verificar.py`) y publica (`publicar.py`, `construir_csv.py`).
3. **Vigilancia** (módulo de la tienda, en el hosting, cada 6 h): vuelve a abrir las fichas y comprueba stock, precio y portes; ordena por precio total con portes.

Archivos: `gtins.csv` (productos de marcas de competencia), `tiendas.csv` (tiendas y políticas de envío), `competencia.csv` (lo publica la tarea en la rama `claude/competencia-datos`).

No contiene costes, precios propios ni datos de clientes.