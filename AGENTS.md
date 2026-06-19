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
  de un JSON. **Siempre** lo deja en el **Escritorio** (`~/Desktop/resultados.xlsx`); no uses
  `-o` ni guardes en `config/contratos` ni en carpetas del repo. Ver la skill
  **`crear-excel-contratos`** para su uso.

## Cómo trabajar

Aplica lo que se te pida en cada paso del expositor (extracción, cruce, Excel). Trabaja solo
con datos reales de los PDF y del CRM; no inventes información.

## Reglas del cruce (PDF vs CRM)

Para **cada** contrato realiza las 4 comprobaciones siguientes, en este orden de precedencia
(la primera que falle determina el resultado). **La clave para identificar al cliente es el
RUT**, no el "ID Cliente" del PDF (que puede ser ficticio).

1. **Cliente existe**: busca el RUT del PDF en `clientes`. Si no está → `ERROR` (Cliente no encontrado).
2. **Póliza coincide**: busca el número de póliza del PDF en `polizas`. Si **no existe**, o existe
   pero su `cliente_id` **no corresponde** al cliente del RUT → `ERROR` (Póliza no coincide).
   ⚠️ Haz esta comprobación **siempre**, aunque el monto coincida: hay contratos cuyo RUT, estado
   y monto están correctos pero citan una póliza inexistente (p. ej. `990112` en vez de `112`).
3. **Monto coincide**: compara el monto asegurado del PDF con `financiera.monto_asegurado` de esa
   póliza. Si difieren → `REVISAR` (Monto PDF ≠ CRM).
4. **Cliente activo**: si `clientes.estado` es `Inactivo` → `REVISAR` (Cliente inactivo).

Si las 4 pasan → `OK` (Coincide). Nota: un nombre escrito distinto pero con el **mismo RUT** se
considera coincidente (no es error).

## Cómo redactar la columna "Observación"

Cuando generes el Excel, escribe en `Observación` el motivo concreto de cada resultado, no un
texto genérico:

- Cliente no existe en el CRM → `Cliente no encontrado`
- El nº de póliza no corresponde al cliente → `Póliza no coincide`
- El monto del PDF difiere del CRM → `Monto PDF ≠ CRM` (cita ambos, p. ej. `$15.000.000 vs $13.000.000`)
- Cliente inactivo → `Cliente inactivo`
- Todo correcto → `Coincide`
