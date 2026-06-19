---
name: "crear-excel-contratos"
description: >-
  Genera el Excel de validación de contratos del workshop a partir de un JSON de "cruce"
  (PDF vs CRM). Úsalo en el paso final, en vez de escribir openpyxl a mano. Produce un .xlsx
  con columnas estándar, semáforo de Estado (OK/REVISAR/ERROR) y fila de totales.
---

# crear-excel-contratos

CLI del workshop para generar el Excel final del cruce de contratos. El agente arma las
filas (resultado de leer los PDFs con `pdftotext` y consultar el CRM por el MCP `conector-base-datos`)
y este CLI las formatea en un `.xlsx`.

## Cuándo usar

En el **paso 3** del flujo (extracción → cruce → Excel), cuando ya tienes el resultado de
validar cada contrato y necesitas el archivo `.xlsx`. No escribas openpyxl a mano: usa este CLI.

## Uso

```bash
# desde un archivo JSON (el .xlsx SIEMPRE se genera en el Escritorio)
python scripts/crear_excel.py --input cruce.json

# o por stdin
cat cruce.json | python scripts/crear_excel.py
```

- `-i, --input`  : JSON de entrada (o `-`/omitir para leer de stdin).
- **Salida fija**: el `.xlsx` se escribe **siempre** en `~/Desktop/resultados.xlsx`
  (en OpenCode/Karibu: `/config/Desktop/resultados.xlsx`). **No uses `-o/--output`**
  ni rutas como `config/contratos`, `Desktop/contratos` o `datasets/contratos`.

## Formato de entrada (JSON)

Una lista de objetos, uno por contrato. Claves admitidas:

```json
[
  {
    "archivo": "contrato-01.pdf",
    "cliente": "María González",
    "cliente_existe": "Sí",
    "estado_cliente": "Activo",
    "poliza_pdf": "101",
    "poliza_bdd": "101",
    "coincide_poliza": "Sí",
    "monto_pdf": 8500000,
    "monto_crm": 8500000,
    "observacion": "Coincide",
    "estado": "OK"
  }
]
```

- `estado` es **opcional**: si no lo incluyes, el CLI lo deriva con esta precedencia:
  `cliente_existe=No`→ERROR · `coincide_poliza=No`→ERROR · `monto_pdf≠monto_crm`→REVISAR ·
  `estado_cliente=Inactivo`→REVISAR · resto→OK.
- Los montos aceptan número o texto con `$`/puntos (`"$8.500.000"`).

## Salida

**Siempre** en `~/Desktop/resultados.xlsx` (OpenCode: `/config/Desktop/resultados.xlsx`).

`.xlsx` con las columnas:
`Archivo | Cliente | Cliente existe | Estado cliente | Póliza PDF | Póliza BDD |
Coincide póliza | Monto PDF | Monto CRM | Estado | Observación`

La columna **Estado** va con semáforo (OK=verde, REVISAR=ámbar, ERROR=rojo) y al final hay
una fila de **TOTALES** con los conteos.

## Notas para el agente

1. Escribe el JSON del cruce a un archivo (p. ej. `cruce.json` en `/config/workshop`) y pásalo con `-i`.
2. **No pases `-o/--output`**. El Excel va **siempre** al Escritorio: `~/Desktop/resultados.xlsx`.
   No lo guardes en `config/contratos`, `Desktop/contratos` ni en carpetas del repo.
3. Verifica el exit code (0 = ok) y que exista `~/Desktop/resultados.xlsx` al terminar.
4. Incluye una `observacion` breve y útil (p. ej. `"Monto PDF $15.000.000 vs CRM $13.000.000"`).
