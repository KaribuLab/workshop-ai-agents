---
name: "crear-pdf-contratos"
description: >-
  Genera el PDF de validación de contratos del workshop a partir de un JSON de "cruce"
  (PDF vs CRM). Úsalo en el paso final cuando el deliverable pedido es un PDF (en vez del Excel).
  Produce un informe .pdf con la misma tabla, semáforo de Estado (OK/REVISAR/ERROR) y fila de
  totales. Es el gemelo de crear-excel-contratos y usa el mismo JSON de entrada.
---

# crear-pdf-contratos

CLI del workshop para generar el **PDF** final del cruce de contratos. El agente arma las
filas (resultado de leer los PDFs con `pdftotext` y consultar el CRM por el MCP `conector-base-datos`)
y este CLI las formatea en un informe `.pdf`. Es el equivalente en PDF de `crear-excel-contratos`:
mismo formato de entrada, misma tabla y mismo semáforo; solo cambia el formato de salida.

## Cuándo usar

En el **paso 3** del flujo (extracción → cruce → deliverable), cuando ya tienes el resultado de
validar cada contrato y el deliverable pedido es un **PDF**. No armes el PDF a mano: usa este CLI.
Si en cambio te piden un Excel, usa `crear-excel-contratos`. Puedes generar ambos con el mismo
`cruce.json`.

## Uso

```bash
# desde un archivo JSON (el .pdf SIEMPRE se genera en el Escritorio)
python scripts/crear_pdf.py --input cruce.json

# o por stdin
cat cruce.json | python scripts/crear_pdf.py
```

- `-i, --input`  : JSON de entrada (o `-`/omitir para leer de stdin).
- **Salida fija**: el `.pdf` se escribe **siempre** en `~/Desktop/resultados.pdf`
  (en OpenCode/Karibu: `/config/Desktop/resultados.pdf`). **No uses `-o/--output`**
  ni rutas como `config/contratos`, `Desktop/contratos` o `datasets/contratos`.
- **Requiere Google Chrome/Chromium** en el PATH (igual que `generar_contratos.py`): el PDF se
  renderiza con Chrome headless (HTML+CSS → PDF). No hay dependencias de Python que instalar.

## Formato de entrada (JSON)

Idéntico al de `crear-excel-contratos`. Una lista de objetos, uno por contrato. Claves admitidas:

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

**Siempre** en `~/Desktop/resultados.pdf` (OpenCode: `/config/Desktop/resultados.pdf`).

Informe en PDF horizontal (Letter landscape) con la tabla de columnas:
`Archivo | Cliente | Cliente existe | Estado cliente | Póliza PDF | Póliza BDD |
Coincide póliza | Monto PDF | Monto CRM | Estado | Observación`

La columna **Estado** va con semáforo (OK=verde, REVISAR=ámbar, ERROR=rojo) y al final hay
una fila de **TOTALES** con los conteos.

## Notas para el agente

1. Escribe el JSON del cruce a un archivo (p. ej. `cruce.json` en `/config/workshop`) y pásalo con `-i`.
2. **No pases `-o/--output`**. El PDF va **siempre** al Escritorio: `~/Desktop/resultados.pdf`.
   No lo guardes en `config/contratos`, `Desktop/contratos` ni en carpetas del repo.
3. Verifica el exit code (0 = ok) y que exista `~/Desktop/resultados.pdf` al terminar.
4. Incluye una `observacion` breve y útil (p. ej. `"Monto PDF $15.000.000 vs CRM $13.000.000"`).
5. Puedes reusar el mismo `cruce.json` con `crear-excel-contratos` para producir además el `.xlsx`.
