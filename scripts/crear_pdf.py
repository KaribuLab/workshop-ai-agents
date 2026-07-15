#!/usr/bin/env python3
"""CLI del workshop: genera el PDF de validación de contratos a partir del cruce.

Gemelo de crear_excel.py, pero produce un informe en PDF en vez de un .xlsx. El agente arma
el cruce (PDF vs CRM) como una lista JSON y este CLI lo formatea en un PDF horizontal con la
misma tabla, semáforo de Estado (OK/REVISAR/ERROR) y fila de totales.

Uso:
    python scripts/crear_pdf.py --input cruce.json
    cat cruce.json | python scripts/crear_pdf.py

Por defecto el .pdf se genera en el Escritorio (~/Desktop/resultados.pdf). Rutas fuera del
Escritorio (p. ej. config/contratos) se redirigen automáticamente al Escritorio.

Render: Google Chrome headless (HTML+CSS -> PDF), igual que generar_contratos.py. No requiere
instalar dependencias de Python.

Cada fila del JSON admite estas claves (todas opcionales salvo lo que quieras mostrar):
    archivo, cliente, cliente_existe, estado_cliente, poliza_pdf, poliza_bdd,
    coincide_poliza, monto_pdf, monto_crm, observacion, estado

Si "estado" no viene, se deriva con la precedencia de las reglas del workshop.
"""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata

CHROME = shutil.which("google-chrome") or shutil.which("google-chrome-stable") \
    or shutil.which("chromium") or shutil.which("chromium-browser")

# (clave en el JSON, encabezado en el PDF, ¿es monto?)
COLUMNAS = [
    ("archivo",         "Archivo",          False),
    ("cliente",         "Cliente",          False),
    ("cliente_existe",  "Cliente existe",   False),
    ("estado_cliente",  "Estado cliente",   False),
    ("poliza_pdf",      "Póliza PDF",        False),
    ("poliza_bdd",      "Póliza BDD",        False),
    ("coincide_poliza", "Coincide póliza",  False),
    ("monto_pdf",       "Monto PDF",        True),
    ("monto_crm",       "Monto CRM",        True),
    ("estado",          "Estado",           False),
    ("observacion",     "Observación",      False),
]

NAVY = "#172A4D"
COLOR_ESTADO = {
    "OK":      "#C6EFCE",  # verde
    "REVISAR": "#FFEB9C",  # ámbar
    "ERROR":   "#FFC7CE",  # rojo
}
TEXTO_ESTADO = {
    "OK":      "#1B7A3D",
    "REVISAR": "#9C6500",
    "ERROR":   "#9C0006",
}


def normaliza(valor):
    """Mayúsculas sin acentos: 'Revisar' -> 'REVISAR', 'Sí' -> 'SI'."""
    if valor is None:
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().upper()


def es_no(valor):
    return normaliza(valor) in ("NO", "FALSE", "0", "N")


def a_numero(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return valor
    s = str(valor).replace("$", "").replace(".", "").replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def formato_monto(valor):
    """Número con separador de miles (punto), estilo chileno: 8500000 -> '8.500.000'."""
    n = a_numero(valor)
    if n is None:
        return "" if valor is None else str(valor)
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.2f}".replace(",", "·").replace(".", ",").replace("·", ".")
    return f"{int(n):,}".replace(",", ".")


def derivar_estado(fila):
    """Aplica la precedencia de reglas si la fila no trae 'estado'."""
    if es_no(fila.get("cliente_existe")):
        return "ERROR"
    if es_no(fila.get("coincide_poliza")):
        return "ERROR"
    mp, mc = a_numero(fila.get("monto_pdf")), a_numero(fila.get("monto_crm"))
    if mp is not None and mc is not None and mp != mc:
        return "REVISAR"
    if normaliza(fila.get("estado_cliente")) == "INACTIVO":
        return "REVISAR"
    return "OK"


def cargar_filas(args):
    if args.input and args.input != "-":
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = json.load(sys.stdin)
    # Acepta una lista, o un objeto con la lista bajo "contratos"/"filas"/"resultados".
    if isinstance(data, dict):
        for k in ("contratos", "filas", "resultados", "rows"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        raise ValueError("El JSON debe ser una lista de filas (o un objeto que la contenga).")
    return data


def esc(valor):
    return html.escape("" if valor is None else str(valor))


def construir_html(filas):
    """Arma el informe HTML (tabla + semáforo + totales) y devuelve (html, contador)."""
    contador = {"OK": 0, "REVISAR": 0, "ERROR": 0}
    cuerpo = []

    for fila in filas:
        estado = normaliza(fila.get("estado")) or derivar_estado(fila)
        if estado not in contador:
            estado = "REVISAR"  # fallback defensivo
        contador[estado] += 1

        celdas = []
        for clave, _titulo, es_monto in COLUMNAS:
            if clave == "estado":
                fondo, color = COLOR_ESTADO[estado], TEXTO_ESTADO[estado]
                celdas.append(
                    f'<td class="estado" style="background:{fondo};color:{color}">{esc(estado)}</td>'
                )
            elif es_monto:
                celdas.append(f'<td class="num">{esc(formato_monto(fila.get(clave)))}</td>')
            elif clave == "observacion":
                celdas.append(f'<td class="obs">{esc(fila.get(clave, ""))}</td>')
            else:
                celdas.append(f"<td>{esc(fila.get(clave, ''))}</td>")
        cuerpo.append("<tr>" + "".join(celdas) + "</tr>")

    encabezado = "".join(
        f"<th>{esc(titulo)}</th>" for _clave, titulo, _es_monto in COLUMNAS
    )
    resumen = (f"OK={contador['OK']}&nbsp;&nbsp;&nbsp;REVISAR={contador['REVISAR']}"
               f"&nbsp;&nbsp;&nbsp;ERROR={contador['ERROR']}")
    # La fila de totales ocupa: 'TOTALES' + celdas vacías hasta la col. Observación, con el resumen.
    col_obs = next(i for i, c in enumerate(COLUMNAS) if c[0] == "observacion")
    vacias = "".join("<td></td>" for _ in range(col_obs - 1))
    fila_totales = (
        f'<tr class="totales"><td>TOTALES</td>{vacias}'
        f'<td class="obs">{resumen}</td></tr>'
    )

    style = f"""
    @page {{ size: Letter landscape; margin: 12mm; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; font-family: 'DejaVu Sans', Arial, sans-serif;
      color: #1a1a1a; font-size: 10px; }}
    h1 {{ font-size: 15px; letter-spacing: .5px; margin: 0 0 4px; color: {NAVY}; }}
    .sub {{ color: #777; font-size: 10px; margin: 0 0 12px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #D0D0D0; padding: 4px 6px; text-align: center;
      vertical-align: middle; }}
    thead th {{ background: {NAVY}; color: #fff; font-weight: bold;
      text-transform: none; }}
    tbody tr:nth-child(even) td {{ background: #F7F8FA; }}
    td.num {{ text-align: right; white-space: nowrap; }}
    td.obs {{ text-align: left; }}
    td.estado {{ font-weight: bold; }}
    tr.totales td {{ font-weight: bold; background: #ECEFF3; }}
    tr.totales td.obs {{ text-align: left; }}
    """
    documento = (
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        f"<style>{style}</style></head><body>"
        "<h1>INFORME DE VALIDACIÓN DE CONTRATOS</h1>"
        f'<div class="sub">Cruce PDF vs CRM &middot; {len(filas)} contrato(s)</div>'
        "<table><thead><tr>" + encabezado + "</tr></thead><tbody>"
        + "".join(cuerpo) + fila_totales +
        "</tbody></table></body></html>"
    )
    return documento, contador


def render_pdf(html_str, salida):
    with tempfile.TemporaryDirectory() as tmp:
        hpath = os.path.join(tmp, "informe.html")
        with open(hpath, "w", encoding="utf-8") as fh:
            fh.write(html_str)
        cmd = [
            CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--no-pdf-header-footer", "--disable-extensions",
            f"--user-data-dir={os.path.join(tmp, 'profile')}",
            f"--print-to-pdf={salida}", f"file://{hpath}",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(salida):
            raise RuntimeError(f"Chrome falló ({r.returncode}): {r.stderr.strip()[:300]}")


def resolver_escritorio():
    """Ruta del Escritorio del usuario (OpenCode/Karibu usa /config como HOME)."""
    candidatos = []
    home = os.path.expanduser("~")
    candidatos.append(os.path.join(home, "Desktop"))
    candidatos.append(os.path.join(home, "Escritorio"))
    xdg = os.environ.get("XDG_DESKTOP_DIR")
    if xdg:
        candidatos.append(os.path.expanduser(xdg))
    candidatos.append("/config/Desktop")
    for ruta in candidatos:
        if ruta and os.path.isdir(ruta):
            return ruta
    destino = os.path.join(home, "Desktop")
    os.makedirs(destino, exist_ok=True)
    return destino


def resolver_salida(output_arg):
    """Siempre genera el PDF en el Escritorio (~/Desktop/resultados.pdf).

    Solo se respeta --output si la ruta ya está dentro del Escritorio; cualquier
    otra ruta (p. ej. config/contratos, datasets/contratos o el cwd del repo)
    se redirige al Escritorio para que el participante lo encuentre ahí.
    """
    escritorio = os.path.abspath(resolver_escritorio())
    destino = os.path.join(escritorio, "resultados.pdf")
    if not output_arg:
        return destino
    abs_out = os.path.abspath(os.path.expanduser(output_arg))
    if abs_out == escritorio or abs_out.startswith(escritorio + os.sep):
        return abs_out
    print(
        f"Nota: la salida se generará en el Escritorio ({destino}), "
        f"no en {output_arg}.",
        file=sys.stderr,
    )
    return destino


def main():
    ap = argparse.ArgumentParser(description="Genera el PDF de validación de contratos.")
    ap.add_argument("-i", "--input", help="JSON de entrada (default: stdin).")
    ap.add_argument("-o", "--output", default=None,
                    help="Ignorado salvo que la ruta esté en el Escritorio; "
                         "por defecto: ~/Desktop/resultados.pdf.")
    args = ap.parse_args()

    if not CHROME:
        print("Error: no se encontró google-chrome/chromium en el PATH.", file=sys.stderr)
        return 1

    salida = resolver_salida(args.output)

    try:
        filas = cargar_filas(args)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error leyendo el JSON de entrada: {e}", file=sys.stderr)
        return 1

    if not filas:
        print("Advertencia: la lista de filas está vacía; se generará un PDF solo con encabezado.", file=sys.stderr)

    try:
        documento, contador = construir_html(filas)
        render_pdf(documento, salida)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"Error generando el PDF: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"Error generando el PDF: {e}", file=sys.stderr)
        return 1

    print(f"OK: {salida} generado con {len(filas)} fila(s)  "
          f"(OK={contador['OK']}  REVISAR={contador['REVISAR']}  ERROR={contador['ERROR']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
