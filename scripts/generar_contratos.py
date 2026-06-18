#!/usr/bin/env python3
"""Genera los 20 contratos PDF del workshop con diseños y "sabores" variados.

A partir de datasets/contratos_data.json (fuente de verdad de los datos), renderiza cada
contrato con uno de 7 SABORES distintos (layout, paleta, tipografía, marca ficticia,
vocabulario de etiquetas y orden de secciones), de modo que los 20 documentos se vean y se
lean como emitidos por aseguradoras diferentes. Los DATOS del cliente/póliza/financieros se
mantienen idénticos y siempre aparecen como texto plano para que `pdftotext -layout` los
recupere (el workshop los cruza contra el CRM).

Render: Google Chrome headless (HTML+CSS -> PDF). No requiere instalar dependencias.

Uso:
    python scripts/generar_contratos.py                 # reemplaza datasets/contratos/contrato-NN.pdf
    python scripts/generar_contratos.py --outdir /tmp/out
    python scripts/generar_contratos.py --solo 1,2,15   # solo algunos contratos
"""
import argparse
import colorsys
import html
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DEFAULT = os.path.join(RAIZ, "datasets", "contratos_data.json")
OUTDIR_DEFAULT = os.path.join(RAIZ, "datasets", "contratos")

CHROME = shutil.which("google-chrome") or shutil.which("google-chrome-stable") \
    or shutil.which("chromium") or shutil.which("chromium-browser")

# ─────────────────────────────────────────────────────────────────────────────
# Contenido por tipo de póliza (texto idéntico al de los contratos originales).
# ─────────────────────────────────────────────────────────────────────────────
CONTENIDO = {
    "Auto": {
        "materia": ("el vehículo motorizado individualizado por el Contratante, incluyendo sus "
                    "accesorios de fábrica y equipamiento declarado"),
        "coberturas": [
            "Daño físico al vehículo por colisión, choque o volcamiento.",
            "Robo o hurto total del vehículo y de sus piezas.",
            "Responsabilidad civil por daños a terceros en sus bienes y personas.",
            "Asistencia en ruta, remolque y vehículo de reemplazo según condiciones.",
        ],
        "exclusiones": [
            "Conducción bajo influencia del alcohol, drogas o sin licencia vigente.",
            "Participación del vehículo en competencias o pruebas de velocidad.",
            "Daños derivados de la falta de mantención o desgaste natural.",
            "Uso del vehículo para fines distintos a los declarados en la propuesta.",
        ],
    },
    "Vida": {
        "materia": ("la vida del Asegurado individualizado, conforme a la declaración de salud "
                    "presentada al momento de la contratación"),
        "coberturas": [
            "Pago del capital asegurado por fallecimiento del Asegurado.",
            "Invalidez total y permanente por accidente o enfermedad.",
            "Anticipo del capital ante el diagnóstico de enfermedades graves cubiertas.",
            "Asistencia y orientación para los beneficiarios designados.",
        ],
        "exclusiones": [
            "Suicidio ocurrido dentro del primer año de vigencia de la póliza.",
            "Enfermedades o condiciones preexistentes no declaradas.",
            "Participación en actividades de alto riesgo no informadas.",
            "Siniestros derivados de hechos dolosos del Asegurado.",
        ],
    },
    "Hogar": {
        "materia": ("el inmueble y su contenido individualizados por el Contratante, destinados a "
                    "uso habitacional o comercial según se declare"),
        "coberturas": [
            "Incendio, explosión y daños por humo al inmueble y su contenido.",
            "Daños por agua provenientes de la red interna del inmueble.",
            "Sismo y sus consecuencias directas sobre la estructura asegurada.",
            "Robo con fuerza en las cosas y responsabilidad civil del hogar.",
        ],
        "exclusiones": [
            "Daños preexistentes a la fecha de inicio de vigencia de la póliza.",
            "Vicios de construcción o defectos estructurales conocidos.",
            "Negligencia grave o falta de medidas mínimas de seguridad.",
            "Bienes de valor no declarados expresamente en la propuesta.",
        ],
    },
    "Salud": {
        "materia": ("los gastos médicos del Asegurado individualizado, complementarios a su sistema "
                    "previsional de salud"),
        "coberturas": [
            "Hospitalización, días cama y honorarios del equipo médico.",
            "Intervenciones quirúrgicas y procedimientos cubiertos.",
            "Consultas médicas, exámenes de laboratorio e imagenología.",
            "Medicamentos de uso ambulatorio según el plan contratado.",
        ],
        "exclusiones": [
            "Enfermedades preexistentes no declaradas en la propuesta.",
            "Tratamientos estéticos, cirugías plásticas y de carácter electivo.",
            "Prestaciones durante los períodos de carencia establecidos.",
            "Atenciones no prescritas por un profesional habilitado.",
        ],
    },
}

OBLIGACIONES = [
    "Declarar con veracidad la información requerida en la propuesta de seguro.",
    "Mantener las medidas de seguridad y cuidado razonables sobre la materia asegurada.",
    "Informar a la Compañía toda circunstancia que agrave el riesgo cubierto.",
    "Denunciar los siniestros dentro de los plazos y forma establecidos.",
]

FORMA_PAGO = ("La prima se paga mensualmente mediante el medio de pago acordado por el Asegurado. "
              "Los valores podrán reajustarse en cada período anual de renovación conforme a las "
              "condiciones de la póliza y a la variación de los índices pactados.")

CLAUSULAS = [
    "Perfeccionamiento: el presente contrato se perfecciona con la aceptación de la propuesta y las declaraciones del Contratante, que se entienden incorporadas a la póliza.",
    "Pago de la prima y mora: la falta de pago oportuno de la prima faculta a la Compañía para suspender la cobertura y, en su caso, terminar el contrato conforme a la ley.",
    "Denuncia de siniestros: el Asegurado deberá denunciar todo siniestro dentro de los plazos establecidos, entregando los antecedentes que permitan su liquidación.",
    "Liquidación: los siniestros serán liquidados conforme a la normativa vigente y a las condiciones de esta póliza, pudiendo intervenir un liquidador designado al efecto.",
    "Terminación anticipada: cualquiera de las partes podrá poner término al contrato en los casos y con los efectos previstos en las condiciones generales y en la ley.",
    "Jurisdicción y normativa: este contrato se rige por la legislación chilena y queda sujeto a la fiscalización de la Comisión para el Mercado Financiero (CMF).",
    "Datos personales: el tratamiento de los datos del Contratante se realiza conforme a la Ley N° 19.628 sobre protección de la vida privada.",
]

INTRO = ("SEGUROS_BRAND, en adelante la Compañía, y el Contratante individualizado en este documento, "
         "en adelante el Asegurado, acuerdan celebrar el presente contrato de seguro, que se rige por "
         "las Condiciones Particulares y Generales que siguen. La Compañía se obliga a indemnizar los "
         "siniestros amparados, dentro de los límites y condiciones pactados.")

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s))


def vigencia_hasta(fecha_emision):
    """Suma un año a la fecha de emisión (YYYY-MM-DD)."""
    y, m, d = (int(x) for x in fecha_emision.split("-"))
    try:
        fin = date(y + 1, m, d)
    except ValueError:  # 29-feb
        fin = date(y + 1, m, d - 1)
    return fin.isoformat()


def hsl(h, s, l):
    return f"hsl({h % 360}, {s}%, {l}%)"


def tinte(base_hue, grupo):
    """Color de acento que rota el tono según el grupo, para que dos contratos del mismo
    sabor base no se vean idénticos. Determinista."""
    return base_hue + grupo * 47


def barras(seed):
    """Pseudo 'código de barras' determinista en CSS a partir de un número."""
    n = int("".join(ch for ch in str(seed) if ch.isdigit()) or "7")
    stops, x = [], 0
    rng = n
    for _ in range(34):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        w = 1 + (rng >> 8) % 3
        color = "#000" if x % 2 == 0 else "#fff"
        stops.append(f"{color} {x}px {x + w}px")
        x += w
    return f"repeating-linear-gradient(90deg, {', '.join(stops)})", x


def li(items):
    return "".join(f"<li>{esc(t)}</li>" for t in items)


PAGE_CSS = "@page { size: Letter; margin: 14mm 14mm; }"


def doc(style, body, lang_font):
    return (f"<!doctype html><html lang=es><head><meta charset=utf-8>"
            f"<style>{PAGE_CSS}*{{box-sizing:border-box}}"
            f"html,body{{margin:0;padding:0;font-family:{lang_font};color:#1a1a1a}}"
            f"{style}</style></head><body>{body}</body></html>")


# ─────────────────────────────────────────────────────────────────────────────
# SABORES — cada función recibe (d, c, acc) y devuelve HTML completo.
#   d   = fila de datos (nombre, rut, poliza, tipo, fecha_emision, prima, monto, id_cliente)
#   c   = CONTENIDO[d["tipo"]]
#   acc = color de acento (string CSS) calculado por grupo
# ─────────────────────────────────────────────────────────────────────────────
SANS = "'DejaVu Sans', Arial, sans-serif"
SERIF = "'Latin Modern Roman', 'DejaVu Serif', Georgia, serif"
MONO = "'DejaVu Sans Mono', 'Liberation Mono', monospace"
COND = "'DejaVu Sans Condensed', 'DejaVu Sans', Arial Narrow, sans-serif"


def intro_html(brand, fecha):
    return ("En Santiago de Chile, con fecha " + esc(fecha) + ", "
            + INTRO.replace("SEGUROS_BRAND", "<b>" + esc(brand) + "</b>"))


# ---- Sabor A: grilla con bordes + código de barras (estilo certificado Consorcio) ----
def sabor_grilla(d, c, acc):
    brand = "ANDESUR Seguros Generales"
    bg, _ = barras(d["poliza"])
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:11px/1.35 {SANS};padding:0}}
    .wrap{{border:2px solid #111}}
    .topbar{{display:flex;justify-content:space-between;align-items:stretch;border-bottom:2px solid #111}}
    .topbar .seg{{padding:6px 10px;border-right:1px solid #111}}
    .brand{{font-weight:bold;font-size:15px;color:{acc}}}
    .brand small{{display:block;color:#444;font-size:9px;font-weight:normal}}
    .barcode{{width:120px;background:{bg};border-left:1px solid #111}}
    .cert{{text-align:center;font-weight:bold;font-size:11px;line-height:1.2;flex:1;padding:6px}}
    table{{width:100%;border-collapse:collapse}}
    td,th{{border:1px solid #111;padding:4px 7px;vertical-align:top}}
    td{{white-space:nowrap}}
    th{{background:#f0f0f0;text-align:left;width:32%;font-size:10px;text-transform:uppercase;letter-spacing:.3px;white-space:normal}}
    h3{{margin:12px 0 4px;font-size:11px;text-transform:uppercase;border-bottom:1px solid #999;padding-bottom:2px}}
    ul{{margin:4px 0;padding-left:18px}} li{{margin:2px 0}}
    .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:0}}
    .ribbon{{background:#111;color:#fff;padding:3px 8px;font-size:10px;letter-spacing:1px}}
    .firmas{{display:flex;justify-content:space-around;margin-top:34px;text-align:center}}
    .firmas div{{border-top:1px solid #111;width:38%;padding-top:4px;font-size:10px}}
    .small{{font-size:9px;color:#555}}
    """
    body = f"""
    <div class=ribbon>ORIGINAL: ASEGURADO &nbsp;·&nbsp; N° Folio {esc(d['poliza'])}-{d['n']:02d}</div>
    <div class=wrap>
      <div class=topbar>
        <div class=seg><div class=brand>ANDESUR<small>Seguros Generales S.A.</small></div></div>
        <div class="seg cert">CERTIFICADO DE PÓLIZA<br>CONDICIONES PARTICULARES<br>
          <span class=small>Póliza N° {esc(d['poliza'])} · CMF</span></div>
        <div class=barcode></div>
      </div>
      <table>
        <tr><th>Asegurado / Contratante</th><td>{esc(d['nombre'])}</td></tr>
        <tr><th>R.U.T.</th><td>{esc(d['rut'])}</td></tr>
        <tr><th>Código cliente</th><td>{esc(d['id_cliente'])}</td></tr>
      </table>
      <table>
        <tr><th>Ramo / Tipo</th><td>{esc(d['tipo'])}</td><th>Póliza N°</th><td>{esc(d['poliza'])}</td></tr>
        <tr><th>Rige desde</th><td>{esc(d['fecha_emision'])}</td><th>Rige hasta</th><td>{esc(vig)}</td></tr>
        <tr><th>Prima mensual</th><td>{esc(d['prima'])}</td><th>Suma asegurada</th><td>{esc(d['monto'])}</td></tr>
      </table>
    </div>
    <p class=small>{intro_html(brand, d['fecha_emision'])}</p>
    <div class=grid2>
      <div>
        <h3>Materia asegurada y coberturas</h3>
        <p>La materia asegurada corresponde a {esc(c['materia'])}. La Compañía ampara:</p>
        <ul>{li(c['coberturas'])}</ul>
      </div>
      <div>
        <h3>Exclusiones</h3>
        <ul>{li(c['exclusiones'])}</ul>
      </div>
    </div>
    <h3>Obligaciones del asegurado</h3><ul>{li(OBLIGACIONES)}</ul>
    <h3>Forma de pago y reajuste</h3><p>{esc(FORMA_PAGO)}</p>
    <h3>Cláusulas generales</h3>
    <ol class=small>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
    <div class=firmas><div>Por la Compañía</div><div>Contratante / Asegurado</div></div>
    """
    return doc(style, body, SANS)


# ---- Sabor B: dos columnas con etiquetas de color (estilo Vida Security) ----
def sabor_doscol(d, c, acc):
    brand = "Vértice Vida & Salud"
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:12px/1.5 {SANS};padding:0}}
    header{{display:flex;justify-content:space-between;align-items:center;
      background:linear-gradient(90deg,{acc} 0 38%, #2b2150 38% 100%);color:#fff;padding:14px 22px}}
    header .logo{{font-weight:bold;font-size:20px;letter-spacing:1px}}
    header .logo span{{opacity:.85;font-weight:300}}
    .folio{{text-align:right;font-size:12px}}
    main{{padding:18px 26px}}
    h1{{text-align:center;font-weight:600;font-size:16px;letter-spacing:1px;margin:6px 0 14px}}
    h2{{color:{acc};font-size:12px;letter-spacing:1px;border-bottom:1px solid #ccc;padding-bottom:3px;margin:18px 0 10px}}
    .campos{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px 20px}}
    .campo .k{{color:{acc};font-size:10.5px;letter-spacing:.5px;text-transform:uppercase}}
    .campo .v{{font-size:13px;white-space:nowrap}}
    ul{{margin:6px 0;padding-left:18px}} li{{margin:3px 0}}
    p{{margin:6px 0}}
    .intro{{color:#444;font-size:11px}}
    """
    def campo(k, v):
        return f"<div class=campo><div class=k>{esc(k)}</div><div class=v>{esc(v)}</div></div>"
    body = f"""
    <header>
      <div class=logo>VÉRTICE <span>vida&amp;salud</span></div>
      <div class=folio>FOLIO: {esc(d['poliza'])}<br><small>Póliza N° {esc(d['poliza'])}</small></div>
    </header>
    <main>
      <h1>CONDICIONES PARTICULARES DE LA PÓLIZA</h1>
      <p class=intro>{intro_html(brand, d['fecha_emision'])}</p>
      <h2>RESUMEN DE TU INFORMACIÓN</h2>
      <div class=campos>
        {campo('Nombre del Asegurado', d['nombre'])}
        {campo('Rut', d['rut'])}
        {campo('Código cliente', d['id_cliente'])}
        {campo('N° de póliza', d['poliza'])}
        {campo('Cobertura', d['tipo'])}
        {campo('Inicio vigencia', d['fecha_emision'])}
        {campo('Término vigencia', vig)}
        {campo('Valor cuota mensual', d['prima'])}
        {campo('Capital asegurado', d['monto'])}
      </div>
      <h2>MATERIA ASEGURADA Y COBERTURAS</h2>
      <p>La materia asegurada corresponde a {esc(c['materia'])}. La Compañía ampara los siguientes riesgos:</p>
      <ul>{li(c['coberturas'])}</ul>
      <h2>EXCLUSIONES</h2><ul>{li(c['exclusiones'])}</ul>
      <h2>OBLIGACIONES DEL ASEGURADO</h2><ul>{li(OBLIGACIONES)}</ul>
      <h2>FORMA DE PAGO Y REAJUSTE</h2><p>{esc(FORMA_PAGO)}</p>
      <h2>CLÁUSULAS GENERALES</h2>
      <ol>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
    </main>
    """
    return doc(style, body, SANS)


# ---- Sabor C: minimalista monocromo ----
def sabor_minimal(d, c, acc):
    brand = "Clara Seguros"
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:12px/1.7 {SANS};padding:8mm 4mm;color:#222}}
    .mark{{font-size:22px;font-weight:300;letter-spacing:6px;color:{acc}}}
    .rule{{height:2px;background:{acc};width:46px;margin:6px 0 26px}}
    .meta{{display:flex;flex-wrap:wrap;gap:2px 40px;margin:10px 0 8px}}
    .meta div{{min-width:150px}}
    .meta .k{{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#999}}
    .meta .v{{font-size:14px;font-weight:500;white-space:nowrap}}
    h2{{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#999;margin:26px 0 6px;font-weight:600}}
    ul{{margin:4px 0;padding-left:16px}} li{{margin:4px 0}}
    p{{margin:6px 0;color:#333}}
    """
    def m(k, v):
        return f"<div><div class=k>{esc(k)}</div><div class=v>{esc(v)}</div></div>"
    body = f"""
    <div class=mark>clara</div><div class=rule></div>
    <p>{intro_html(brand, d['fecha_emision'])}</p>
    <div class=meta>
      {m('Contratante', d['nombre'])}{m('RUT', d['rut'])}{m('Cliente', d['id_cliente'])}
    </div>
    <div class=meta>
      {m('Póliza', d['poliza'])}{m('Plan', d['tipo'])}{m('Emisión', d['fecha_emision'])}{m('Vigencia hasta', vig)}
    </div>
    <div class=meta>
      {m('Prima mensual', d['prima'])}{m('Monto asegurado', d['monto'])}
    </div>
    <h2>Materia y coberturas</h2>
    <p>La materia asegurada corresponde a {esc(c['materia'])}.</p>
    <ul>{li(c['coberturas'])}</ul>
    <h2>Exclusiones</h2><ul>{li(c['exclusiones'])}</ul>
    <h2>Obligaciones</h2><ul>{li(OBLIGACIONES)}</ul>
    <h2>Forma de pago</h2><p>{esc(FORMA_PAGO)}</p>
    <h2>Cláusulas generales</h2><ol>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
    """
    return doc(style, body, SANS)


# ---- Sabor D: carta corporativa clásica (serif + sello) ----
def sabor_clasico(d, c, acc):
    brand = "Compañía de Seguros La Araucana"
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:12.5px/1.6 {SERIF};padding:4mm}}
    .membrete{{text-align:center;border-bottom:3px double {acc};padding-bottom:10px;margin-bottom:14px}}
    .membrete .co{{font-size:22px;font-weight:bold;color:{acc};letter-spacing:1px}}
    .membrete .sub{{font-size:11px;color:#555;font-style:italic}}
    h1{{text-align:center;font-size:15px;margin:8px 0 4px}}
    .no{{text-align:center;font-size:12px;color:#666;margin-bottom:14px}}
    .datos{{margin:14px auto;border:1px solid {acc};padding:10px 16px;width:92%}}
    .datos table{{width:100%;border-collapse:collapse}}
    .datos td{{padding:3px 6px;white-space:nowrap}} .datos td.k{{font-style:italic;color:#444;width:34%;white-space:normal}}
    h2{{font-size:13px;color:{acc};margin:18px 0 4px;border-bottom:1px solid #ddd}}
    ul{{margin:4px 0;padding-left:22px}} li{{margin:3px 0}}
    .sello{{float:right;border:2px solid {acc};color:{acc};border-radius:50%;width:96px;height:96px;
      display:flex;align-items:center;justify-content:center;text-align:center;font-size:9px;
      transform:rotate(-12deg);opacity:.8;margin:10px}}
    .firmas{{clear:both;display:flex;justify-content:space-around;margin-top:40px;text-align:center}}
    .firmas div{{border-top:1px solid #333;width:40%;padding-top:5px;font-style:italic}}
    """
    body = f"""
    <div class=membrete><div class=co>La Araucana</div>
      <div class=sub>Compañía de Seguros · Fundada en Santiago de Chile</div></div>
    <h1>Condiciones Particulares de la Póliza de Seguro</h1>
    <div class=no>N° de contrato CT-2026-{d['n']:02d} &nbsp;—&nbsp; Póliza N° {esc(d['poliza'])}</div>
    <p>{intro_html(brand, d['fecha_emision'])}</p>
    <div class=datos><table>
      <tr><td class=k>Contratante / Asegurado</td><td>{esc(d['nombre'])}</td>
          <td class=k>R.U.T.</td><td>{esc(d['rut'])}</td></tr>
      <tr><td class=k>Código de cliente</td><td>{esc(d['id_cliente'])}</td>
          <td class=k>Tipo de póliza</td><td>{esc(d['tipo'])}</td></tr>
      <tr><td class=k>N° de póliza</td><td>{esc(d['poliza'])}</td>
          <td class=k>Emisión</td><td>{esc(d['fecha_emision'])}</td></tr>
      <tr><td class=k>Vigencia</td><td>hasta {esc(vig)}</td>
          <td class=k>Prima mensual</td><td>{esc(d['prima'])}</td></tr>
      <tr><td class=k>Monto asegurado</td><td colspan=3>{esc(d['monto'])}</td></tr>
    </table></div>
    <h2>Materia Asegurada y Coberturas</h2>
    <p>La materia asegurada corresponde a {esc(c['materia'])}. Bajo las coberturas contratadas, la
    Compañía ampara los siguientes riesgos:</p><ul>{li(c['coberturas'])}</ul>
    <h2>Exclusiones</h2><ul>{li(c['exclusiones'])}</ul>
    <h2>Obligaciones del Asegurado</h2><ul>{li(OBLIGACIONES)}</ul>
    <h2>Forma de Pago y Reajuste</h2><p>{esc(FORMA_PAGO)}</p>
    <h2>Cláusulas Generales</h2><ol>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
    <div class=sello>LA ARAUCANA<br>SEGUROS<br>CHILE</div>
    <div class=firmas><div>Por la Compañía</div><div>Contratante / Asegurado</div></div>
    """
    return doc(style, body, SERIF)


# ---- Sabor E: moderno con barra lateral de color (tipografía condensada) ----
def sabor_sidebar(d, c, acc):
    brand = "Nordic Risk Insurance"
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:12px/1.5 {COND};padding:0}}
    .layout{{display:flex;min-height:100%}}
    aside{{width:34mm;background:{acc};color:#fff;padding:16px 12px;flex:0 0 auto}}
    aside .logo{{font-size:18px;font-weight:bold;letter-spacing:1px;line-height:1.05}}
    aside .logo span{{font-weight:300}}
    aside .k{{margin-top:16px;font-size:9px;letter-spacing:2px;text-transform:uppercase;opacity:.8}}
    aside .v{{font-size:14px;font-weight:bold}}
    main{{padding:16px 20px;flex:1}}
    h1{{font-size:17px;letter-spacing:1px;margin:0 0 2px;color:{acc}}}
    .sub{{color:#777;font-size:11px;margin-bottom:12px}}
    h2{{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:{acc};margin:16px 0 5px;
       border-left:4px solid {acc};padding-left:7px}}
    ul{{margin:4px 0;padding-left:18px}} li{{margin:3px 0}}
    .fila{{display:flex;gap:24px;flex-wrap:wrap;margin:6px 0}}
    .fila div{{white-space:nowrap}}
    .fila div b{{display:block;color:{acc};font-size:10px;text-transform:uppercase}}
    """
    body = f"""
    <div class=layout>
      <aside>
        <div class=logo>NORDIC<br><span>risk</span></div>
        <div class=k>Póliza</div><div class=v>{esc(d['poliza'])}</div>
        <div class=k>Ramo</div><div class=v>{esc(d['tipo'])}</div>
        <div class=k>Prima mensual</div><div class=v>{esc(d['prima'])}</div>
        <div class=k>Suma asegurada</div><div class=v>{esc(d['monto'])}</div>
        <div class=k>Cliente</div><div class=v>{esc(d['id_cliente'])}</div>
      </aside>
      <main>
        <h1>Póliza de Seguro</h1>
        <div class=sub>Condiciones Particulares · Contrato CT-2026-{d['n']:02d}</div>
        <div class=fila>
          <div><b>Contratante</b>{esc(d['nombre'])}</div>
          <div><b>RUT</b>{esc(d['rut'])}</div>
          <div><b>Emisión</b>{esc(d['fecha_emision'])}</div>
          <div><b>Vigencia hasta</b>{esc(vig)}</div>
        </div>
        <p>{intro_html(brand, d['fecha_emision'])}</p>
        <h2>Materia y coberturas</h2>
        <p>La materia asegurada corresponde a {esc(c['materia'])}.</p><ul>{li(c['coberturas'])}</ul>
        <h2>Exclusiones</h2><ul>{li(c['exclusiones'])}</ul>
        <h2>Obligaciones</h2><ul>{li(OBLIGACIONES)}</ul>
        <h2>Forma de pago</h2><p>{esc(FORMA_PAGO)}</p>
        <h2>Cláusulas generales</h2><ol>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
      </main>
    </div>
    """
    return doc(style, body, COND)


# ---- Sabor F: formulario / ticket condensado (monoespaciada) ----
def sabor_formulario(d, c, acc):
    brand = "PuntoSeguro Express"
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:11px/1.45 {MONO};padding:4mm}}
    .hd{{border:2px dashed {acc};padding:8px 10px;text-align:center;margin-bottom:10px}}
    .hd .b{{font-size:16px;font-weight:bold;color:{acc};letter-spacing:2px}}
    .box{{border:1px solid #444;margin:8px 0}}
    .box .t{{background:{acc};color:#fff;padding:3px 8px;font-weight:bold;letter-spacing:1px}}
    .row{{display:flex;border-top:1px dotted #999}}
    .row:first-child{{border-top:none}}
    .row .k{{width:42%;padding:3px 8px;background:#f5f5f5;border-right:1px dotted #999}}
    .row .v{{padding:3px 8px;font-weight:bold;white-space:nowrap}}
    ul{{margin:4px 0;padding-left:18px}} li{{margin:2px 0}}
    h3{{margin:10px 0 3px;font-size:11px;color:{acc};letter-spacing:1px}}
    .stars{{letter-spacing:2px;color:{acc}}}
    """
    def row(k, v):
        return f"<div class=row><div class=k>{esc(k)}</div><div class=v>{esc(v)}</div></div>"
    body = f"""
    <div class=hd><div class=b>PUNTOSEGURO EXPRESS</div>
      <div class=stars>* * * COMPROBANTE DE PÓLIZA * * *</div>
      <div>CONTRATO CT-2026-{d['n']:02d} · POLIZA N {esc(d['poliza'])}</div></div>
    <div class=box><div class=t>DATOS DEL ASEGURADO</div>
      {row('NOMBRE', d['nombre'])}{row('RUT', d['rut'])}{row('CLIENTE NRO', d['id_cliente'])}
    </div>
    <div class=box><div class=t>DETALLE DE LA POLIZA</div>
      {row('POLIZA N', d['poliza'])}{row('RAMO', d['tipo'])}
      {row('EMISION', d['fecha_emision'])}{row('VIGENCIA HASTA', vig)}
      {row('PRIMA MENSUAL', d['prima'])}{row('MONTO ASEGURADO', d['monto'])}
    </div>
    <p>{intro_html(brand, d['fecha_emision'])}</p>
    <h3>>> MATERIA Y COBERTURAS</h3>
    <p>La materia asegurada corresponde a {esc(c['materia'])}.</p><ul>{li(c['coberturas'])}</ul>
    <h3>>> EXCLUSIONES</h3><ul>{li(c['exclusiones'])}</ul>
    <h3>>> OBLIGACIONES</h3><ul>{li(OBLIGACIONES)}</ul>
    <h3>>> FORMA DE PAGO</h3><p>{esc(FORMA_PAGO)}</p>
    <h3>>> CLAUSULAS GENERALES</h3><ol>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
    """
    return doc(style, body, MONO)


# ---- Sabor G: editorial con bloque de color y tarjetas ----
def sabor_editorial(d, c, acc):
    brand = "Marea Aseguradora"
    vig = vigencia_hasta(d["fecha_emision"])
    style = f"""
    body{{font:12px/1.6 {SANS};padding:0;color:#222}}
    .hero{{background:{acc};color:#fff;padding:22px 26px}}
    .hero .logo{{font-size:13px;letter-spacing:4px;text-transform:uppercase;opacity:.9}}
    .hero h1{{margin:4px 0 0;font-size:24px;font-weight:800}}
    .hero .sub{{opacity:.9;font-size:12px;margin-top:4px}}
    main{{padding:18px 26px}}
    .cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:4px 0 10px}}
    .card{{border:1px solid #e3e3e3;border-top:3px solid {acc};border-radius:6px;padding:8px 11px}}
    .card.full{{grid-column:1 / -1}}
    .card .k{{font-size:9.5px;letter-spacing:1px;text-transform:uppercase;color:#999}}
    .card .v{{font-size:15px;font-weight:700;color:#222;white-space:nowrap}}
    h2{{font-size:13px;color:{acc};margin:20px 0 6px}}
    h2:before{{content:'';display:inline-block;width:9px;height:9px;background:{acc};
      border-radius:50%;margin-right:7px;vertical-align:middle}}
    ul{{margin:5px 0;padding-left:20px}} li{{margin:3px 0}}
    .intro{{color:#555;font-size:11.5px}}
    """
    def card(k, v, full=False):
        cls = "card full" if full else "card"
        return f"<div class='{cls}'><div class=k>{esc(k)}</div><div class=v>{esc(v)}</div></div>"
    body = f"""
    <div class=hero><div class=logo>Marea · Aseguradora</div>
      <h1>Tu Póliza de {esc(d['tipo'])}</h1>
      <div class=sub>Condiciones Particulares · Contrato CT-2026-{d['n']:02d} · Póliza N° {esc(d['poliza'])}</div>
    </div>
    <main>
      <div class=cards>
        {card('Asegurado', d['nombre'], full=True)}
        {card('RUT', d['rut'])}{card('Código cliente', d['id_cliente'])}{card('N° de póliza', d['poliza'])}
        {card('Tipo de póliza', d['tipo'])}{card('Emisión', d['fecha_emision'])}{card('Vigencia hasta', vig)}
        {card('Prima mensual', d['prima'])}{card('Suma asegurada', d['monto'])}
      </div>
      <p class=intro>{intro_html(brand, d['fecha_emision'])}</p>
      <h2>Materia asegurada y coberturas</h2>
      <p>La materia asegurada corresponde a {esc(c['materia'])}. La Compañía ampara los siguientes riesgos:</p>
      <ul>{li(c['coberturas'])}</ul>
      <h2>Exclusiones</h2><ul>{li(c['exclusiones'])}</ul>
      <h2>Obligaciones del asegurado</h2><ul>{li(OBLIGACIONES)}</ul>
      <h2>Forma de pago y reajuste</h2><p>{esc(FORMA_PAGO)}</p>
      <h2>Cláusulas generales</h2><ol>{''.join(f'<li>{esc(x)}</li>' for x in CLAUSULAS)}</ol>
    </main>
    """
    return doc(style, body, SANS)


SABORES = [
    {"id": "grilla",     "render": sabor_grilla,     "hue": 218},
    {"id": "doscol",     "render": sabor_doscol,     "hue": 22},
    {"id": "minimal",    "render": sabor_minimal,    "hue": 174},
    {"id": "clasico",    "render": sabor_clasico,    "hue": 348},
    {"id": "sidebar",    "render": sabor_sidebar,    "hue": 152},
    {"id": "formulario", "render": sabor_formulario, "hue": 28},
    {"id": "editorial",  "render": sabor_editorial,  "hue": 268},
]


def html_de(d):
    idx = (d["n"] - 1) % len(SABORES)
    grupo = (d["n"] - 1) // len(SABORES)
    sabor = SABORES[idx]
    acc = hsl(tinte(sabor["hue"], grupo), 62, 42)
    return sabor["id"], sabor["render"](d, CONTENIDO[d["tipo"]], acc)


def render_pdf(html_str, salida):
    with tempfile.TemporaryDirectory() as tmp:
        hpath = os.path.join(tmp, "c.html")
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


def main():
    ap = argparse.ArgumentParser(description="Genera los contratos PDF con sabores variados.")
    ap.add_argument("-i", "--input", default=INPUT_DEFAULT, help=f"JSON de datos (default: {INPUT_DEFAULT}).")
    ap.add_argument("-o", "--outdir", default=OUTDIR_DEFAULT, help=f"Directorio de salida (default: {OUTDIR_DEFAULT}).")
    ap.add_argument("--solo", help="Lista de números a generar, p. ej. '1,2,15'.")
    args = ap.parse_args()

    if not CHROME:
        print("Error: no se encontró google-chrome/chromium en el PATH.", file=sys.stderr)
        return 1

    import json
    with open(args.input, encoding="utf-8") as fh:
        filas = json.load(fh)

    if args.solo:
        quiere = {int(x) for x in args.solo.split(",")}
        filas = [f for f in filas if f["n"] in quiere]

    os.makedirs(args.outdir, exist_ok=True)
    for d in filas:
        sid, html_str = html_de(d)
        salida = os.path.join(args.outdir, f"contrato-{d['n']:02d}.pdf")
        try:
            render_pdf(html_str, salida)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"Error en contrato-{d['n']:02d}: {e}", file=sys.stderr)
            return 1
        print(f"OK  contrato-{d['n']:02d}.pdf  [{sid:10}] {d['nombre']}")

    print(f"\nListo: {len(filas)} contrato(s) en {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
