#!/usr/bin/env python3
"""Extrae los datos de los 20 contratos PDF actuales a un JSON (fuente de verdad).

Corre `pdftotext -layout` sobre cada datasets/contratos/contrato-NN.pdf y vuelca una
lista de objetos con los campos que el workshop cruza contra el CRM. Este JSON queda
versionado y es la entrada de scripts/generar_contratos.py, de modo que regenerar los
PDFs (reemplazo en sitio) no pierde los datos originales.

Uso:
    python scripts/extraer_datos_contratos.py            # -> datasets/contratos_data.json
    python scripts/extraer_datos_contratos.py -o otro.json
"""
import argparse
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CONTRATOS = os.path.join(RAIZ, "datasets", "contratos")
SALIDA_DEFAULT = os.path.join(RAIZ, "datasets", "contratos_data.json")

# (clave en el JSON, etiqueta tal como aparece en el PDF original)
CAMPOS = [
    ("nombre",        "Nombre"),
    ("id_cliente",    "ID Cliente"),
    ("rut",           "RUT"),
    ("poliza",        "Número de póliza"),
    ("tipo",          "Tipo de póliza"),
    ("fecha_emision", "Fecha de emisión"),
    ("prima",         "Prima mensual"),
    ("monto",         "Monto asegurado"),
]


def texto_pdf(ruta):
    return subprocess.run(
        ["pdftotext", "-layout", ruta, "-"],
        capture_output=True, text=True, check=True,
    ).stdout


def valor_de(texto, etiqueta):
    """Devuelve lo que sigue a la etiqueta en su línea (colapsando espacios)."""
    patron = re.compile(r"^\s*" + re.escape(etiqueta) + r"\s{2,}(.+?)\s*$", re.MULTILINE)
    m = patron.search(texto)
    if not m:
        raise ValueError(f"No se encontró la etiqueta '{etiqueta}'")
    return m.group(1).strip()


def extraer(n):
    ruta = os.path.join(DIR_CONTRATOS, f"contrato-{n:02d}.pdf")
    texto = texto_pdf(ruta)
    fila = {"n": n}
    for clave, etiqueta in CAMPOS:
        fila[clave] = valor_de(texto, etiqueta)
    return fila


def main():
    ap = argparse.ArgumentParser(description="Extrae datos de los contratos PDF a JSON.")
    ap.add_argument("-o", "--output", default=SALIDA_DEFAULT,
                    help=f"JSON de salida (default: {SALIDA_DEFAULT}).")
    args = ap.parse_args()

    filas = []
    for n in range(1, 21):
        try:
            filas.append(extraer(n))
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"Error en contrato-{n:02d}: {e}", file=sys.stderr)
            return 1

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=2)

    print(f"OK: {args.output} con {len(filas)} contrato(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
