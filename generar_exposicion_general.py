"""
Exposición de la clínica completa, por profesional.

    python generar_exposicion_general.py

Se arma con los 26 gráficos elegidos en el catálogo general. A diferencia de la
exposición de cosmiatras —que sigue las cuatro fases del análisis— esta se
ordena por persona: una sección por profesional, de mayor a menor facturación,
con su retrato en el divisor.

Las lecturas del catálogo son párrafos escritos para leer sentado; aquí se
convierten en bajada y viñetas, que es lo que funciona proyectado.
"""

from __future__ import annotations

import argparse
import base64
import io
import re
import sys
import webbrowser
from pathlib import Path

import pandas as pd

from kpi_body import deck
from kpi_body import general as gen
from kpi_body import tablero_body as tb
from kpi_body.odoo import cargar, explotar_tratamientos

CARPETA_AVATARES = Path("imagenes/personal")
AVATARES = {
    "Doctora": "johana", "Yaselin": "yaselin", "Doctor": "gustavo",
    "Romina": "romina", "Cosmiatras": "cosmiatras", "Oftalmología": "carlos",
}

# La lámina proyectada es más estrecha que la página del catálogo, así que el
# Pareto entra con menos barras: con las de aquel se montaban las etiquetas.
# El acumulado y el «cuántos hacen el 80%» no cambian — se calculan sobre todos
# los tratamientos antes de agrupar el resto.
def _pareto_deck(d, clave):
    return gen.f_pareto(d, clave, tope=7)


def _pareto_conjunto_deck(tr):
    b = gen.f_pareto(gen.solo_estetica(tr), "Doctora", tope=8)
    b["titulo"] = "De qué depende el área estética"
    b["pregunta"] = "¿Cuántos tratamientos hacen el 80% del conjunto?"
    b["insight"] = b["insight"] + " " + gen.NOTA_SIN_OFTALMO
    return b


# Los 26 gráficos elegidos. La clave es el equipo y el valor, qué fábricas se
# usan y en qué orden.
SELECCION_CONJUNTO = [gen.g_peso_equipo, gen.g_top_clinica,
                      _pareto_conjunto_deck]
SELECCION_PERSONA = {
    "Doctor":       [gen.f_mensual, gen.f_tratamientos, _pareto_deck,
                     gen.f_pacientes, gen.f_paquetes],
    "Yaselin":      [gen.f_mensual, gen.f_tratamientos, _pareto_deck,
                     gen.f_pacientes, gen.f_paquetes],
    "Doctora":      [gen.f_mensual, gen.f_tratamientos, _pareto_deck,
                     gen.f_pacientes, gen.f_paquetes],
    "Romina":       [gen.f_mensual, gen.f_pacientes],
    "Cosmiatras":   [gen.f_mensual, gen.f_tratamientos, _pareto_deck,
                     gen.f_pacientes, gen.f_paquetes],
    "Oftalmología": [gen.f_mensual],
}

# Al final de cada consulta, qué se puede mejorar ahí. Cierra la sección con
# algo accionable en vez de dejarla en la última barra.
MEJORAS_TRAS = {"Doctor", "Yaselin", "Doctora", "Cosmiatras"}

# Qué desglose abre cada gráfico al pulsarlo. Todos salen de la facturación:
# esta exposición no usa el registro de atenciones.
CLICS = {
    "Facturación mes a mes": "mes",
    "Cada tratamiento: dinero, sesiones y ventas": "tratamiento",
    "De qué depende: concentración por tratamiento": "tratamiento",
    "Pacientes nuevos y pacientes que vuelven": "mes",
    "Sesión suelta o paquete": "tratamiento",
    "Los 15 tratamientos más grandes del área estética": "tratamiento",
    "De qué depende el área estética": "tratamiento",
    "Cuánto pesa cada profesional": "equipo",
}


def _clic(b: dict, meses) -> dict:
    campo = CLICS.get(b["titulo"].split(" · ")[0].strip())
    if not campo:
        return b
    claves = ({tb.mes_corto(m): pd.Timestamp(m).strftime("%Y-%m") for m in meses}
              if campo == "mes" else {})
    if campo == "equipo":
        claves = {gen.equipo_nombre(k): k for k in gen.EQUIPOS}
    return {**b, "filtro": campo, "fuente": "ventas", "claves": claves}


def _suavizar(hex_color: str, hacia: str = "#f4f2ee", parte: float = 0.55) -> str:
    """
    Acerca un color al papel base. Los tintes del catálogo se ven bien en una
    pantalla a un palmo; proyectados en una pared llenan la sala. Se mezclan a
    mitad de camino con el fondo para que digan «cambió la sección» y nada más.
    """
    def _t(c):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    a, b = _t(hex_color), _t(hacia)
    m = tuple(round(x + (y - x) * parte) for x, y in zip(a, b))
    return "#%02x%02x%02x" % m


def _detalle_ventas(tr: pd.DataFrame) -> list[dict]:
    """Las ventas que alimentan el panel, de toda la clínica y no solo de un área."""
    c = tr.copy()
    d = pd.DataFrame({
        "fecha": c["fecha"].dt.strftime("%d/%m/%Y"),
        "mes": c["mes"].dt.strftime("%Y-%m"),
        "cliente": c["cliente"],
        "descripcion": c["descripcion"].astype(str).str.title(),
        "tratamiento": c["tratamiento"],
        "equipo": c["equipo"],
        "sesiones": c["sesiones"].astype(int),
        "ingreso": c["ingreso"].round(2),
    })
    return d.to_dict("records")


def avatar(clave: str, lado: int = 260) -> str:
    nombre = AVATARES.get(clave)
    if not nombre:
        return ""
    p = CARPETA_AVATARES / f"{nombre}_avatar.png"
    if not p.exists():
        p = CARPETA_AVATARES / f"{nombre}.png"
    if not p.exists():
        return ""
    try:
        from PIL import Image
        im = Image.open(p).convert("RGBA")
        im.thumbnail((lado, lado), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        return ("data:image/png;base64,"
                + base64.b64encode(buf.getvalue()).decode())
    except Exception:                                            # noqa: BLE001
        return ""


def _frases(texto: str) -> list[str]:
    """
    Parte la lectura en frases completas.

    Los dos puntos no cierran una frase —introducen lo que viene después— y un
    punto entre dígitos tampoco: «S/ 1,234.50» se rompería por la mitad. Solo
    se corta en punto seguido de espacio y mayúscula.
    """
    t = re.sub(r"\s+", " ", texto).strip()
    partes = [f.strip() for f in
              re.split(r"(?<=[.!?])\s+(?=[«¿A-ZÁÉÍÓÚÑ])", t) if f.strip()]
    salida, pendiente = [], ""
    for f in partes:
        f = f"{pendiente} {f}".strip() if pendiente else f
        pendiente = ""
        if len(f) < 55:
            pendiente = f
            continue
        salida.append(f)
    if pendiente:
        if salida:
            salida[-1] = f"{salida[-1]} {pendiente}"
        else:
            salida.append(pendiente)
    return salida


def a_lamina(b: dict, fase: int, max_puntos: int = 3) -> dict:
    fr = _frases(b.get("insight", ""))
    if not fr:
        return {**b, "fase": fase, "bajada": "", "puntos": []}
    bajada, resto, total = fr[0], [], 0
    for f in fr[1:]:
        if len(resto) >= max_puntos or total + len(f) > 420:
            break
        if len(f) > 220:
            continue
        resto.append(f)
        total += len(f)
    return {"fase": fase, "titulo": b["titulo"], "bajada": bajada,
            "fig": b["fig"], "puntos": resto}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Exposición de la clínica completa.")
    p.add_argument("excel", nargs="?",
                   default="Asiento contable con campos extra 2026.xlsx")
    p.add_argument("--salida", default="exposicion_general.html")
    p.add_argument("--no-abrir", action="store_true")
    a = p.parse_args(argv)

    if not Path(a.excel).exists():
        print(f"No encuentro el archivo: {a.excel}")
        return 2

    print(f"Leyendo {a.excel} ...")
    tr = explotar_tratamientos(cargar(a.excel))
    tr = tr[~tr["es_insumo"]]
    est = gen.solo_estetica(tr)
    tot = float(est["ingreso"].sum())
    meses = sorted(est["mes"].unique())
    ult = tb.ultimo_mes(meses)
    print(f"  conjunto estético: S/ {tot:,.0f} · {est['cliente'].nunique():,} "
          f"pacientes · {len(meses)} meses")

    # Orden por facturación: en una junta, primero quien más pesa.
    peso = tr.groupby("equipo")["ingreso"].sum()
    personas = [k for k in sorted(SELECCION_PERSONA, key=lambda k: -peso.get(k, 0))
                if k in peso.index]

    # Fase 1 es el conjunto; a partir de la 2, una por profesional.
    fases = {1: ("El conjunto", "¿Cómo se reparte la clínica?",
                 "Los cinco profesionales del área estética juntos. "
                 "Oftalmología va aparte al final.")}
    laminas: list[dict] = []

    print("\nConjunto ...")
    fases["fondo1"] = "#f6f5f2"
    for fn in SELECCION_CONJUNTO:
        try:
            laminas.append(_clic(a_lamina(fn(tr), 1), meses))
            print(f"  · {laminas[-1]['titulo']}"
                  + ("   ▸ clic" if laminas[-1].get("filtro") else ""))
        except Exception as e:                                   # noqa: BLE001
            print(f"  ! {fn.__name__}: {type(e).__name__}: {e}")

    for i, clave in enumerate(personas, start=2):
        meta = gen.EQUIPOS[clave]
        d = tr[tr["equipo"] == clave]
        imp = float(d["ingreso"].sum())
        fases[i] = (meta["nombre"], meta["rol"],
                    f"{tb.sol(imp, True)} en el periodo · "
                    f"{tb.pc(imp/tot)} del área estética · "
                    f"{d['cliente'].nunique():,} pacientes"
                    if clave not in gen.FUERA_DEL_CONJUNTO else
                    f"{tb.sol(imp, True)} en el periodo · "
                    f"{d['cliente'].nunique():,} pacientes · fuera del conjunto")
        fases[f"avatar{i}"] = avatar(clave)
        # El fondo de toda la lámina cambia con la persona. Se aclara el tinte
        # del catálogo hacia el papel base: proyectado, el mismo color que
        # funciona en una web resulta demasiado presente.
        fases[f"fondo{i}"] = _suavizar(meta["tinte"])
        print(f"\n{meta['nombre']} · S/ {imp:,.0f} ...")
        for fn in SELECCION_PERSONA[clave]:
            try:
                laminas.append(_clic(a_lamina(fn(d, clave), i), meses))
                print(f"  · {laminas[-1]['titulo']}"
                      + ("   ▸ clic" if laminas[-1].get("filtro") else ""))
            except Exception as e:                               # noqa: BLE001
                print(f"  ! {fn.__name__}: {type(e).__name__}: {e}")
        if clave in MEJORAS_TRAS:
            try:
                b = gen.f_mejoras(d, clave, tr)
                laminas.append({**b, "fase": i})
                print(f"  · {b['titulo']} ({len(b['mejoras'])} observaciones)")
            except Exception as e:                               # noqa: BLE001
                print(f"  ! mejoras: {type(e).__name__}: {e}")

    deck.FASES = fases

    # ---- portada y cifras -------------------------------------------------- #
    g = est.groupby("mes")["ingreso"].sum()
    v = est.groupby("cliente").agg(eq=("equipo", "nunique"),
                                   m=("mes", "nunique"), g=("ingreso", "sum"))
    cruzan = int((v["eq"] > 1).sum())
    t = est.groupby("tratamiento")["ingreso"].sum().sort_values(ascending=False)
    n80 = int(((t.cumsum() / tot * 100) < 80).sum()) + 1
    lider = peso.drop(index=list(gen.FUERA_DEL_CONJUNTO), errors="ignore").idxmax()

    cifras = [
        deck._cifra(tot, tb.sol(tot, True), "Facturado en el periodo",
                    f"{len(meses)} meses · solo estética", pre="S/ "),
        # Compacto como el de al lado: «S/ 1,303,186» obligaba a encoger las
        # cinco tarjetas para que cupiera, y el número exacto está en el
        # gráfico de la sección siguiente.
        deck._cifra(float(g.iloc[-1]), tb.sol(float(g.iloc[-1]), True),
                    f"Facturado en {ult}",
                    f"{tb.pc(float(g.iloc[-1]/g.iloc[-2]-1), signo=True)} "
                    f"contra el mes anterior", pre="S/ "),
        deck._cifra(len(v), f"{len(v):,}", "Pacientes distintos",
                    f"{tb.pc(cruzan/len(v))} pasa por más de un profesional"),
        deck._cifra(float(peso[lider] / tot * 100),
                    tb.pc(float(peso[lider] / tot)),
                    f"Peso de {gen.equipo_nombre(lider)}",
                    "el resto se reparte entre cuatro", suf="%", dec=1),
        deck._cifra(n80, f"{n80}", "Tratamientos hacen el 80%",
                    f"de {len(t)} que se facturan"),
    ]

    portada = {
        "eyebrow": "Junta médica · OftalmoLáser",
        "titulo": "La clínica, profesional por profesional",
        "sub": ("Toda la facturación de enero a julio de 2026, repartida entre "
                "los cinco del área estética. Qué factura cada uno, de qué "
                "vive y con cuántos pacientes."),
        "chips": [f"{len(meses)} meses", f"{len(laminas)} láminas",
                  f"{len(personas)} profesionales"],
        "marca": "OftalmoLáser",
        "periodo": (f"{tb.LARGOS[min(meses).month - 1]} – "
                    f"{tb.LARGOS[max(meses).month - 1]} de {max(meses).year}"),
        "titulo_cifras": "La clínica en cinco números",
        "bajada_cifras": (f"Facturación registrada en Odoo, comprobante por "
                          f"comprobante. <b>Oftalmología va aparte</b>: se "
                          f"factura por el mismo sistema pero es otro negocio."),
    }

    g1 = float(v[v["eq"] == 1]["g"].mean())
    g2 = float(v[v["eq"] > 1]["g"].mean())
    cierre = {
        "titulo": "Lo que se lleva de esta reunión",
        "puntos": [
            f"<b>El año va en subida.</b> De {tb.sol(float(g.iloc[0]))} en "
            f"{tb.mes_corto(g.index[0])} a {tb.sol(float(g.iloc[-1]))} en "
            f"{ult}: <b>{tb.pc(float(g.iloc[-1]/g.iloc[0]-1))} más</b>. "
            f"El último mes fue el mejor de los siete.",

            f"<b>Casi la mitad depende de una persona.</b> "
            f"{gen.equipo_nombre(lider)} es el "
            f"{tb.pc(float(peso[lider]/tot))} de todo lo que factura el área. "
            f"Es la fortaleza y el riesgo a la vez: si esa agenda se detiene, "
            f"no hay nada detrás que lo compense.",

            f"<b>Y diez tratamientos hacen el 80%.</b> De los {len(t)} que se "
            f"facturan, diez sostienen cuatro de cada cinco soles. "
            f"«{t.index[0]}» y «{t.index[1]}» solos ya son el "
            f"{tb.pc(float(t.iloc[0]+t.iloc[1])/tot)}.",

            f"<b>El paciente que cruza vale tres veces más.</b> "
            f"{cruzan} de {len(v)} pacientes pasan por más de un profesional y "
            f"dejan {tb.sol(g2)} de media, contra {tb.sol(g1)} del que ve solo "
            f"a uno. Ese paciente ya está dentro: no hay que captarlo, hay que "
            f"presentarle lo que no conoce.",

            f"<b>Pero {tb.pc(float((v['m'] == 1).mean()))} vino un solo mes.</b> "
            f"{int((v['m'] == 1).sum()):,} de {len(v):,} pacientes no han "
            f"vuelto. La derivación interna y la recuperación de esos pacientes "
            f"son la misma conversación, y ninguna cuesta publicidad.",
        ],
    }

    print("\nRenderizando ...")
    ventas = _detalle_ventas(tr)
    print(f"  desglose: {len(ventas):,} ventas")
    html = deck.render(portada, cifras, laminas, cierre, ventas=ventas)
    Path(a.salida).write_text(html, encoding="utf-8")
    destino = Path(a.salida).resolve()
    print(f"Listo: {destino}  ({destino.stat().st_size/1_048_576:.1f} MB)")
    print(f"  {len(laminas)} láminas de contenido + portada + cifras + "
          f"{len(personas) + 1} divisores + cierre")
    if not a.no_abrir:
        webbrowser.open(destino.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
