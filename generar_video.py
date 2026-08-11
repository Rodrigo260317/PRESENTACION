"""
Video de presentación de la junta, en un MP4 listo para proyectar o enviar.

    python generar_video.py                  # HTML + MP4 completo (1080p, 30 fps)
    python generar_video.py --solo-html      # solo el HTML, para verlo en vivo
    python generar_video.py --prueba 0 20    # renderiza solo del segundo 0 al 20
    python generar_video.py --4k             # 2160p, para pantalla grande

Se apoya en `datos_video.json` y `fuentes_video.json`; si falta alguno, avisa
qué script lo produce en vez de fallar a medio camino.

Salen dos archivos y los dos sirven:

  · `presentacion_video.html`  se reproduce solo al abrirlo. Espacio pausa,
    las flechas saltan 5 s y F pone pantalla completa. Es la versión para
    proyectar en la reunión, porque se puede detener en una lámina si
    preguntan.
  · `presentacion_video.mp4`   el mismo contenido cuadro a cuadro. Es el que
    se manda por WhatsApp o se mete en una presentación.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from kpi_body import guion_video, video

DATOS = "datos_video.json"
FUENTES = "fuentes_video.json"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Video de presentación de la junta.")
    p.add_argument("--html", default="presentacion_video.html")
    p.add_argument("--mp4", default="presentacion_video.mp4")
    p.add_argument("--guion", default="guion_video.md")
    p.add_argument("--solo-html", action="store_true",
                   help="no renderiza el video, solo escribe el HTML")
    p.add_argument("--prueba", nargs=2, type=float, metavar=("DESDE", "HASTA"),
                   help="renderiza solo ese tramo, en segundos")
    p.add_argument("--fps", type=int, default=video.FPS)
    p.add_argument("--4k", dest="cuatro_k", action="store_true")
    p.add_argument("--crf", type=int, default=16,
                   help="calidad de H.264: 14 es casi sin pérdida, 23 es liviano")
    p.add_argument("--jpeg", type=int, default=95,
                   help="calidad de cada captura antes de comprimir el video")
    p.add_argument("--no-abrir", action="store_true")
    a = p.parse_args(argv)

    faltan = [(r, c) for r, c in ((DATOS, "extraer_datos_video.py"),
                                  (FUENTES, "bajar_fuentes.py"))
              if not Path(r).exists()]
    if faltan:
        for ruta, script in faltan:
            print(f"Falta {ruta} — se genera con:  python {script}")
        return 2

    datos = json.loads(Path(DATOS).read_text(encoding="utf-8"))
    fuentes = json.loads(Path(FUENTES).read_text(encoding="utf-8"))["css"]

    ruta_html = Path(a.html)
    ruta_html.write_text(video.html(datos, fuentes), encoding="utf-8")
    print(f"HTML: {ruta_html.resolve()}  "
          f"({ruta_html.stat().st_size/1_048_576:.1f} MB)")

    # El guion se cronometra contra las mismas duraciones que acaba de usar el
    # video, así que no puede quedar desfasado. Si una frase no entra en su
    # escena, se avisa aquí y no en la sala.
    ruta_guion, avisos = guion_video.escribir(a.guion, datos)
    print(f"Guion: {Path(ruta_guion).resolve()}")
    if avisos:
        print("  ! frases que no entran en su escena:")
        for x in avisos:
            print(f"      {x}")

    if a.solo_html:
        if not a.no_abrir:
            webbrowser.open(ruta_html.resolve().as_uri())
        return 0

    ancho, alto = (3840, 2160) if a.cuatro_k else (video.ANCHO, video.ALTO)
    desde, hasta = a.prueba if a.prueba else (0.0, None)
    salida = Path(a.mp4)
    if a.prueba:
        salida = salida.with_name(salida.stem + "_prueba" + salida.suffix)

    print(f"Renderizando {ancho}x{alto} a {a.fps} fps (crf {a.crf}) ...")
    r = video.renderizar(ruta_html, salida, fps=a.fps, ancho=ancho, alto=alto,
                         desde=desde, hasta=hasta, calidad=a.crf, jpeg=a.jpeg,
                         poster=Path(a.mp4).with_suffix(".png"))
    m, s = divmod(r["duracion"], 60)
    print(f"Listo: {salida.resolve()}")
    print(f"  {int(m)}:{s:04.1f} · {r['cuadros']} cuadros · {r['peso_mb']:.1f} MB")

    if not a.no_abrir:
        webbrowser.open(salida.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
