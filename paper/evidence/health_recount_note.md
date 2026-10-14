# Recuento de respuestas y solicitudes de cierre

| Configuración | Respuestas | Sin herramientas | Finish válido sin herramientas | SUMMARY_LIMIT sin herramientas | Rechazo FC sin herramientas | Aceptado FC sin herramientas |
| --- | --- | --- | --- | --- | --- | --- |
| C3 | 119 | 16 | 13 | 3 | 11 | 2 |
| C1 | 159 | 25 | 24 | 1 | 20 | 4 |

Las dos columnas finish válido y SUMMARY_LIMIT particionan las respuestas sin herramientas en estas corridas. Las columnas rechazo/aceptación subdividen las solicitudes válidas: 13=11+2 en C3 y 24=20+4 en C1. Son solicitudes, no episodios ni PASS. Los finish mediante herramienta se conservan por separado en el ledger. PENDING_OPERATIONS es un rechazo de política, no una inválida. RUN_APP_BUDGET_EXHAUSTED es una detención ordinaria, tampoco inválida.

| Configuración | Terminal de episodio físico | Episodios |
| --- | --- | --- |
| C3 | finish | 10 |
| C1 | action_budget | 2 |
| C1 | finish | 7 |
| C1 | run_app_budget | 1 |

Evidencia: `response_counts.json`, 470 respuestas de 30 archivos originales (r3 C3/C1 y r2A), con SHA256 de archivo, selector de mensaje/evento/política, bytes y SHA256 del contenido por respuesta. No se copian conversaciones privadas. r2A: 97/192 sin herramientas y 93 no vacías son conteos sintácticos. 86 resúmenes semánticos queda DISCARDED_NOT_FOR_PAPER.
