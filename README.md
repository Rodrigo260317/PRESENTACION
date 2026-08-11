# Tablero de KPIs — sistema Excel → dashboard

Sistema que lee un libro de Excel, calcula las métricas del negocio y genera un
**tablero interactivo en un solo archivo HTML** listo para proyectar en una junta.
No necesita internet, ni servidor, ni instalar nada en la computadora donde se abre:
se envía por correo o WhatsApp y se abre con doble clic.

---

## 0. Los tres comandos que importan

```bash
python verificar_extraccion.py "Asiento contable (account.move).xlsx"
```
Paso de **verificación**: reconoce los tratamientos en el texto libre de Odoo, cuenta
paquetes y sesiones, contrasta contra el reporte anterior de las cosmiatras y —lo más
importante— lista lo que **no** supo clasificar, para que alguien de la clínica revise si
se escapó algo. Deja todo el detalle en `verificacion_extraccion.xlsx`.

```bash
python generar_tablero_clinica.py junio.xlsx julio.xlsx agosto.xlsx
```
Genera el **tablero real** (`tablero_clinica.html`). Acepta un archivo, varios, o una
carpeta entera (`python generar_tablero_clinica.py datos/`). Si dos archivos traen el
mismo comprobante, el repetido se descarta.

**Con un solo mes** salen 16 gráficos. **Con dos o más** se activan solos otros cuatro:
facturación mes a mes, mezcla de líneas de negocio por mes, pacientes nuevos vs. los que
vuelven, y sesiones vendidas por tratamiento a lo largo del año.

Dos aclaraciones sobre el conteo, para cuando alguien contraste a mano en Excel:

- **Se excluyen los comprobantes anulados.** Contar filas en Excel siempre va a dar un
  número mayor. El listado exacto de lo excluido está en la hoja «Anulados excluidos».
- **Un paquete no es una sesión.** Un `3SS MASCARILLA MANDELICO` es 1 paquete y
  3 sesiones. El tablero muestra las dos cifras por separado.

```bash
python generar_presentacion.py "Asiento contable con campos extra 2026.xlsx"
```
Genera la **presentación para los doctores** (`presentacion.html`) y el **guion para
exponerla** (`guion_exposicion.md`). Son 17 diapositivas a pantalla completa,
organizadas en las cuatro fases del análisis:

| Fase | Pregunta | Qué muestra |
|---|---|---|
| 1 · Descriptivo | ¿Qué pasó? | Cifras del periodo, evolución mensual, de qué vive el área |
| 2 · Diagnóstico | ¿Por qué pasó? | Volumen vs. precio, retención, días flojos, dispersión de precio |
| 3 · Predictivo | ¿Qué es probable que pase? | Proyección a 3 meses con banda, análisis de volatilidad |
| 4 · Prescriptivo | ¿Qué hacemos? | Tres palancas cuantificadas y el plan de acción |

Se navega con las flechas ↓ ↑, la barra espaciadora o los puntos de la derecha.
`Inicio` y `Fin` saltan al principio y al final. El guion se genera con los mismos
números, así que nunca queda desfasado.

```bash
python extraer_datos_video.py
python generar_video.py
```
Genera el **video de presentación** (`presentacion_video.mp4`, 1920×1080 a 30 fps, unos
2 minutos) y su gemelo en HTML (`presentacion_video.html`). Quince escenas encadenadas:
apertura, las cinco cifras del periodo, facturación mes a mes, de qué vive el área,
paquetes, retención, ocupación por cosmiatra, huecos de agenda, tiempo de apoyo, las
cuatro palancas y el cierre.

Los tres archivos sirven para cosas distintas y conviene no confundirlos:

- El **MP4** se manda por WhatsApp o correo, se mete en una diapositiva o se proyecta
  sin nada instalado. No lleva audio: está pensado para narrarlo encima.
- El **HTML** se reproduce solo al abrirlo y además **se puede parar**: espacio pausa,
  las flechas saltan 5 s, `F` pone pantalla completa. Es la versión para la reunión,
  porque si alguien pregunta por una cifra se congela esa escena.
- El **guion** (`guion_video.md`) es lo que se dice encima, **cronometrado**. Cada frase
  trae su marca de tiempo, cuántas palabras tiene, cuántos segundos tarda decirla y
  cuántos le sobran. El generador comprueba que entre en su escena y avisa si no:

  ```
  ! frases que no entran en su escena:
      retencion · «Doscientos sesenta y cinco pacientes en el p…» se pasa 0.0 s
  ```

  Eso importa porque un MP4 no se pausa. Si una frase se pasa de su escena, en la sala
  se descubre tarde. Las duraciones viven en `video.ESCENAS_DUR` y las lee tanto el
  video como el guion, así que no hay dos copias que puedan divergir.

  Los números del guion van **redondeados y escritos como se dicen** —«ochenta y ocho
  mil soles», no «S/ 87,891»— porque nadie pronuncia una cifra exacta en una reunión.
  En pantalla sí sale exacta: por eso cada escena del guion lleva una línea *En
  pantalla* con lo que el espectador está viendo mientras tanto.

`python generar_video.py --solo-html` salta el render (que tarda unos 7 minutos) y deja
solo el HTML. `--prueba 20 35` renderiza un tramo suelto para revisar un cambio sin
esperar el video entero. `--4k` sube a 2160p.

La primera vez hacen falta dos cosas más:

```bash
pip install playwright imageio-ffmpeg pillow
python -m playwright install chromium
python bajar_fuentes.py
```

`bajar_fuentes.py` deja las tipografías incrustadas en `fuentes_video.json`. Se corre una
sola vez: sin eso el HTML no se vería igual en otra computadora y el Chromium que
renderiza —que no tiene fuentes instaladas— caería en la de sistema.

```bash
python generar_dashboard.py --demo
```
Genera el tablero de **demostración** con datos sintéticos. Sirve para probar formas de
gráfico sin tocar datos reales.

> Antes de nada, lee **[EXPORTAR_DE_ODOO.md](EXPORTAR_DE_ODOO.md)**: explica qué export
> falta para que el 100 % del dinero quede atribuido con exactitud (hoy es el 62 %) y
> para tener historia más allá de un mes.

---

## 0.05 Alcance del reporte

El tablero mide **solo los tratamientos que hacen las cosmiatras**:

| Facial | Corporal |
|---|---|
| mascarilla de mandélico · jet peel · Emface · LPG facial | Emsculpt · Emsculpt Neo · Exilis · LPG corporal · carboxiterapia · Uniform · tratamiento corporal genérico |

Lo que hacen el doctor, la doctora, Yaselin y Romina **se reconoce igual** —para no
perder ninguna línea y para poder verificar— pero **no aparece en ninguna cifra del
tablero**. Queda en la hoja «Clasificación» del Excel de verificación, con la columna
`Equipo habitual` y `¿Cuenta en el reporte?`.

Eso se controla con un solo campo en `kpi_body/tratamientos.py`:

```python
Tratamiento("Emsculpt", CORPORAL, [...], equipo=COSMIATRAS)   # cuenta
Tratamiento("Morpheus", FACIAL,   [...], equipo=YASELIN)      # no cuenta
```

**Uniform** y **tratamiento corporal genérico** están dentro del alcance porque el
reporte anterior de las cosmiatras sí los contaba (`4SS Uniform`, `16SS/12SS/10SS
Corporal`), aunque no estaban en la lista que pasó Jazmyn. **Conviene confirmarlo**:
si no son de cosmiatras, basta con cambiarles el `equipo`.

---

## 0.1 Cómo se reconoce un tratamiento

Nadie escribe el tratamiento igual dos veces. En un solo mes aparecen:

```
1SS MASCARILLA MANDELICO          MASCARILLA MANDELICO 1SS
3 SS MASCARILLA MANDELICO         MASCARILLA  MANDELICO
1SS JET PEEL + MASCARILLA MANDELICO
PREPARADO DE MASCARILLA DE MANDELICO   ← no es sesión, es insumo
```

`kpi_body/tratamientos.py` convierte esa sopa en filas limpias: tratamiento · área
(facial/corporal) · sesiones del paquete · si es insumo. Maneja combos con `+`,
la marca de sesiones en cualquier posición (`1SS`, `1 SS`, `6 SS DE`), y da prioridad
a `EMSCULPT NEO` sobre `EMSCULPT` para no contar doble.

**Para agregar una forma de escribirlo**, se agrega un patrón a `CATALOGO` y se
vuelve a correr. Nada más cambia. Así se corrigió el primer hallazgo real: en Odoo
existe `EMSCULP` sin la T final, y esos paquetes no se estaban contando.

---

## 1. Cómo se usa (camino de demostración)

```bash
pip install pandas plotly openpyxl numpy
```

**Ver la demostración** (datos sintéticos, sin necesidad de ningún Excel):

```bash
python generar_dashboard.py --demo
```

**Generar la plantilla de Excel** con las hojas y columnas exactas que espera el sistema:

```bash
python generar_dashboard.py --plantilla
```

**Con los datos reales de la clínica**, una vez llenada la plantilla:

```bash
python generar_dashboard.py --excel "datos_clinica.xlsx" --titulo "Tablero Body"
```

Opciones útiles: `--salida reporte_julio.html`, `--meses 36` (solo demo), `--no-abrir`.

---

## 2. Qué datos necesita (contrato)

Todo vive en un `.xlsx` con estas hojas. Los nombres de columna van **sin acentos y en
minúsculas** a propósito: así el archivo se lee igual desde cualquier sistema.

| Hoja | Una fila por… | Columnas |
|---|---|---|
| **Citas** | cita agendada | `fecha`, `paciente_id`, `profesional`, `tratamiento`, `categoria`, `estado`, `ingreso`, `costo_directo`, `es_primera_visita`, `canal`, *(opcional)* `minutos` |
| **Metas** | mes | `mes`, `meta_ingreso`, `capacidad_horas` |
| **Embudo** | mes y etapa comercial | `mes`, `etapa`, `personas` |
| **Marketing** | mes y canal | `mes`, `canal`, `inversion`, `leads` |
| **Encuestas** *(opcional)* | respuesta de NPS | `fecha`, `paciente_id`, `nps` |

`estado` acepta `Atendida`, `No asistio` o `Cancelada`.
Si falta una columna requerida, el sistema lo dice con nombre y hoja en vez de fallar a medias.
La hoja de **Citas** es la que más pesa: casi todos los indicadores salen de ahí.

---

## 3. Qué contiene el tablero

**Cifra principal + 8 tarjetas de KPI** con variación contra el mes anterior y
mini-tendencia de 12 meses: facturación, margen de contribución, pacientes,
ticket promedio, ocupación de agenda, inasistencias, NPS y LTV/CAC.

Después, 13 gráficos agrupados en cinco bloques. Cada uno trae la **pregunta de negocio
que responde**, una **lectura escrita calculada con los datos reales** (no un texto fijo)
y un botón para ver la tabla exacta.

| # | Gráfico | Forma | Responde |
|---|---|---|---|
| 1 | Facturación mensual contra meta | columnas + línea de meta | ¿Vendemos lo que nos propusimos? |
| 2 | De dónde salió el cambio | cascada | ¿Crecimos por volumen o por precio? |
| 3 | Pronóstico a 3 meses | línea + banda de confianza | ¿Qué esperar si todo sigue igual? |
| 4 | Embudo comercial | barras ordinales | ¿Dónde se cae la gente antes de comprar? |
| 5 | Retención por cohorte | mapa de calor | ¿Los pacientes vuelven? |
| 6 | Nuevos vs. recurrentes | barras apiladas | ¿Cuánto depende de comprar pacientes? |
| 7 | Concentración por servicio | Pareto (barras + acumulado) | ¿Qué tratamientos sostienen el negocio? |
| 8 | Dispersión del precio cobrado | cajas horizontales | ¿Cobramos parejo? |
| 9 | Desviación contra objetivo | barras divergentes | ¿Qué servicios arrastran el trimestre? |
| 10 | Ocupación día × hora | mapa de calor | ¿Cuándo se llena y cuándo está vacía? |
| 11 | Facturación diaria y anomalías | carta de control ±2σ | ¿Qué días fueron anormales de verdad? |
| 12 | Producción por profesional | mancuerna (antes → después) | ¿Cómo evolucionó cada quien? |
| 13 | Rentabilidad por canal | dispersión con cuadrantes | ¿Qué canal deja dinero? |

---

## 4. Análisis avanzado que corre por debajo

No son gráficos bonitos sobre sumas: cada bloque aplica una técnica concreta.

- **Descomposición volumen × precio** (gráfico 2). Identidad exacta y sin residuo
  `P₁T₁ − P₀T₀ = (P₁−P₀)T₀ + P₁(T₁−T₀)`, aplicada por separado a pacientes nuevos y
  recurrentes. Se compara contra el mismo mes del año anterior cuando hay historia
  suficiente, para que la estacionalidad no ensucie la lectura.
- **Tendencia + estacionalidad y pronóstico** (gráfico 3). Recta por mínimos cuadrados,
  índice estacional por mes calendario normalizado a suma cero, y banda de ±1.96σ que se
  ensancha con la raíz del horizonte. Deliberadamente simple: se puede reconstruir en una
  hoja de cálculo, que es justo lo que hace que un dueño le crea al pronóstico.
- **Carta de control** (gráfico 11). Media móvil de 14 días ±2σ. Sirve para lo contrario
  de lo que parece: para **no** reaccionar a la variación normal, y reaccionar solo a los
  días marcados.
- **Cohortes de retención** (gráfico 5). Matriz por mes de alta, con las celdas aún no
  maduras dejadas en blanco en vez de contadas como cero.
- **Análisis ABC / Pareto** (gráfico 7) sobre facturación y margen por tratamiento.
- **LTV observado vs. CAC** (gráfico 13). El LTV no se estima: se suma el margen real
  acumulado por paciente de cada canal. Incluye la referencia de 3× y la línea de
  rentabilidad cero.
- **Dispersión del ticket** (gráfico 8) con cuartiles, que es donde aparecen los
  descuentos concedidos en mostrador sin política clara.

---

## 5. Criterios de diseño (por qué se ve así)

Están aplicados a propósito, no por gusto:

- **Nunca dos ejes Y en un mismo gráfico.** Es el error más común en tableros ejecutivos:
  la alineación entre las dos escalas es arbitraria e inventa correlaciones que no existen.
  Cuando hacen falta dos medidas, van en dos paneles (gráfico 7) o en una dispersión (13).
- **El color tiene un trabajo.** Identidad → paleta categórica en orden fijo; magnitud →
  un solo tono claro a oscuro; polaridad → dos tonos opuestos con gris neutro al centro;
  estado → verde/ámbar/rojo, reservados y nunca usados como serie.
- **Paleta verificada para daltonismo** (protanopia, deuteranopia, tritanopia) contra la
  superficie clara y la oscura. No está elegida a ojo.
- **Etiquetas selectivas**, nunca un número sobre cada punto. El eje, el tooltip y la
  tabla cargan el resto.
- **Todo valor es alcanzable sin el mouse**: cada gráfico tiene su tabla, para quien
  imprime el tablero o lo lee en PDF.
- **Modo claro y oscuro**, ambos con colores elegidos para su fondo (no un invertido
  automático). Botón en la barra superior.
- **Hoja de impresión** incluida: `Ctrl+P → Guardar como PDF` da un documento presentable.

---

## 6. Estructura del código

```
verificar_extraccion.py     verificación de la extracción (correr SIEMPRE primero)
generar_tablero_clinica.py  tablero real, desde el export de Odoo
generar_dashboard.py        tablero de demostración, datos sintéticos
extraer_datos_video.py      vuelca a JSON las cifras que consume el video
bajar_fuentes.py            incrusta las tipografías del video en base64 (una vez)
generar_video.py            arma el HTML del video y lo renderiza a MP4
kpi_body/
  tratamientos.py        catálogo de palabras clave y reconocimiento del texto libre
  odoo.py                lectura del export de Odoo y reparto del importe por línea
  historico.py           serie feb–jun rescatada del PPTX anterior
  tablero_body.py        los 16 gráficos del tablero real
  datos.py               contrato de Excel, generador de datos demo, plantilla
  analitica.py           métricas y análisis avanzado (aquí no hay nada visual)
  graficos.py            los 13 gráficos del tablero de demostración
  tema.py                paleta, escalas y layout base de todas las figuras
  formato.py             formateo de dinero, porcentajes y meses en español
  reporte.py             ensamblado del HTML final (lo usan los dos tableros)
  video.py               las 15 escenas del video, su línea de tiempo y el render
  guion_video.py         el guion hablado, cronometrado contra esa línea de tiempo
```

**Para cambiar algo del video:** todo el movimiento sale de una función `seek(t)` que,
dado un segundo, deja el DOM como debe verse en ese instante. No hay ni una animación de
CSS, y es a propósito: las de CSS corren contra el reloj real, así que el mismo archivo
daría un video distinto en cada máquina según lo que tarde en pintar. Cada escena es un
par `(construir, dibujar)` en `ESCENAS`; para reordenarlas o cambiar cuánto dura una,
se toca el segundo argumento de `escena(...)` y nada más.

**Para agregar un gráfico:** escribir una función `bloque_*` en `graficos.py` que devuelva
`id`, `titulo`, `pregunta`, `fig`, `tabla`, `insight`, `ancho`, y registrarla en `CATALOGO`.
Nada más cambia.

**Para cambiar los colores a los de la marca:** editar `tema.py`. Si se cambian los tonos
de serie, hay que revalidar la separación bajo daltonismo — no basta con que "se vean
distintos".

---

## 7. Archivos generados

| Archivo | Qué es |
|---|---|
| `presentacion_video.mp4` | **el video**, 1920×1080 · 30 fps · ~2 min · sin audio |
| `presentacion_video.html` | el mismo video, reproducible y **pausable**, para la sala |
| `guion_video.md` | **qué decir encima del video**, frase por frase y con marca de tiempo |
| `presentacion_video.png` | primer cuadro, sirve de portada al compartir el MP4 |
| `datos_video.json` | las cifras del video, ya redondeadas y en orden de aparición |
| `fuentes_video.json` | las tipografías del video incrustadas en base64 |
| `tablero_clinica.html` | **el tablero real**, con los datos de Odoo de junio |
| `verificacion_extraccion.xlsx` | auditoría fila por fila: qué se reconoció y qué no |
| `dashboard_demo.html` | tablero con datos sintéticos, para probar formas de gráfico |
| `plantilla_datos.xlsx` | Excel de ejemplo del camino de demostración |
| `EXPORTAR_DE_ODOO.md` | qué pedirle a Odoo y cómo sacarlo |
