# Diagnóstico posterior al primer recuento — sin cambiar el filtro principal

El primer recuento conserva `sound == 1`: **114/129**. La reconstrucción literal a partir de `empty_resolved == 0`, `gold_resolved == 1` y ambos flags de error en cero produce **117**, con tres discrepancias. No se modificó el CSV ni se sustituyó el criterio principal.

En `task_soundness.csv` v8, `rich_3480`, `rich_3772` y `rich_4006` tienen `status=control_error`, `sound=0`, los cuatro flags que satisfacen esa reconstrucción y `empty_exit_code=124`. Su `exclusion_reason` declara expresamente que el protocolo excluye el control vacío por timeout fijo de 300 segundos aun cuando gold pasa. `data_dictionary.json` también identifica 124 como timeout, pero la definición breve de `sound` no explicita este guard y `empty_control_error` vale cero en esos registros.

Se agrega una comprobación **suplementaria**, separada y rotulada como tal: el predicado de los cuatro flags y ningún `empty_exit_code`/`gold_exit_code` igual a 124. Se aplica a todas las filas, no solamente a esos tres IDs. Su justificación es el criterio textual publicado en `exclusion_reason`, no alcanzar 114. Se informarán ambos recuentos y cualquier discrepancia restante. Los códigos faltantes no se imputan y el predicado original permanece registrado en `CRITERIOS_RECUENTO.md/json`.

Esto permite explicar el set publicado con datos explícitos; no reconstruye el código ni los raws privados del auditor. Queda una inconsistencia de documentación/semántica de los flags de error que debe señalarse al citar. No se contactó al autor ni se alteró su recurso.
