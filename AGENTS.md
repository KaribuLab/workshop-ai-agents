# Workshop AI Agents — Validación de contratos

Eres el asistente del workshop. Vas a trabajar **guiado por el expositor**, paso a paso:
sigue las indicaciones de cada prompt y no asumas reglas de validación por tu cuenta.

## Qué tienes disponible

- **Contratos en PDF**: en `datasets/contratos/` (`contrato-01.pdf` … `contrato-20.pdf`).
  Cada uno trae datos del cliente, de la póliza y financieros.
  Para leer su texto: `pdftotext -layout datasets/contratos/contrato-01.pdf -`.

- **CRM (base de datos)**: accesible por el conector MCP **`conector-base-datos`** (solo lectura). Tablas:
  - `clientes(cliente_id, rut, nombre, estado, segmento, fecha_alta)`
  - `polizas(poliza_id, cliente_id, tipo, estado, vigencia, fecha_vencimiento)`
  - `financiera(poliza_id, prima, monto_asegurado)`

- **CLI para el Excel**: `scripts/crear_excel.py` genera el archivo de resultados a partir
  de un JSON. Por defecto lo deja en el **Escritorio** (`~/Desktop/resultados.xlsx`). Ver la
  skill **`crear-excel-contratos`** para su uso.

## Cómo trabajar

Aplica lo que se te pida en cada paso del expositor (extracción, cruce, Excel). Trabaja solo
con datos reales de los PDF y del CRM; no inventes información.
