# gh-render — render repartido de la escena 01 de la caja [XG·792d]

## v3.4 (2026-10-12) — lo nuevo, arriba
- **Escena:** `escenas-caja/esc01/esc034.py` + `curvas04.py` (copias de `../esc034.py` y `../curvas04.py`). Arregla el
  P0-V1 de `CRITICO_v33.md`: cada operario con su ciclo (1,0–1,6 s, fase con semilla), sin saltos de pose; la nave se
  repite de f150 a f212 sin costura. `script` ya viene en `esc034.py`; `esc033.py` y `esc032.py` siguen disponibles.
- **Qué re-renderiza:** `cuadros = 84-212` (129 cuadros). f0–83 no cambian (curva vieja exacta hasta f83). Detalle y
  comando en `../ENTREGA-v34.md`.

## v3.3 (2026-10-12)
- **Escena:** `escenas-caja/esc01/esc033.py` (copia de `../esc033.py`; si se cambia allá, se vuelve a copiar). La v3.2
  (`esc032.py`) queda igual y se puede pedir con `script = esc032.py`.
- **Qué re-renderiza:** f75–212 (138 cuadros). f0–74 se reusan de la v3.2 (f0 idéntico píxel a píxel; f65 y f74 con
  1 y 14 píxeles a 1 nivel). f150–212 es la nave que sigue trabajando, para la fuente de 3–4 s de la IA (PLAN 55).
- **Muestras por tramo:** `muestras` (64) antes de `desde_nave` (84) y `muestras_nave` (128) desde ahí.
- **Máscaras (mismo render, sin costo extra):** artifact `mascara-N` con `fNNNN.png` (blanco = nave vista por la
  abertura; negro = caja, puerta y fondo) y `tela_fNNNN.png` (1 = tela de costura, 0,5 = otras telas).
- `bajar_y_armar.sh` sigue siendo el de la v3.2 (139 cuadros de `cuadros03.txt`): para la v3.3 hay que juntar f0–74 de
  la descarga v3.2 con f75–149 de la v3.3. Detalle en `../ENTREGA-v33.md`.

---

## v3.2 (2026-10-12)

**Qué es.** Todo lo que hace falta para renderizar la escena 01 (la caja carbón que late, se abre y muestra la nave
trabajando) en 10 máquinas de GitHub Actions a la vez, y después bajar los cuadros y armar el video con audio.
**Nada se subió ni se disparó.** Martin decide si va a un repo público o privado.

- **Tamaño:** 90 MB, 49 archivos. El más grande es `ancla-caja/figuras3.blend` (14 MB). No hay archivos de más de
  100 MB: **no hace falta LFS** ni bajar nada aparte en el trabajo.
- **Autocontenido, probado:** desde esta carpeta, Blender usó 20 archivos y los 20 están adentro (`tools/chequeo.py`).
  El cuadro de prueba sale **idéntico píxel por píxel** al de la carpeta original (diferencia máxima 0).
- **Sin rutas `C:/`.** Las carpetas copian la estructura original (`escenas-caja/esc01`, `ancla-caja`, `activos`,
  `assets`), así los scripts encuentran todo con rutas relativas.

## Qué cambió en la escena (v3.2, arreglo del P0 del crítico)
El crítico v3 midió los gestos de la nave en 2–5 px a 1080: "se lee quieto". v3.2 agranda el recorrido de los
**objetos**, no la inclinación de las figuras (sigue en 7–8°). Está en `../esc032.py`; la v3.1 (`../esc03.py`) quedó igual.

Recorrido entre la anticipación (f129) y el golpe (f135), a 1080×1920, medido sobre la geometría (`--mode medir`):

| Objeto | v3.1 | v3.2 | Cambio |
|---|---|---|---|
| Cuchilla | 26,7 px | **34,3 px** | 0,56 → 0,72 m reales (17,5 → 22,5 mm de escena) |
| Plancha | 37–38 px | 37–38 px | ya estaba en 23,75 mm |
| Tela de costura | 0,7 px | **11–13 px** | nueva guía de costado con el golpe (hasta 0,30 m) |
| Caja del que carga | 4,4 px | **35 px** | la caja cae 0,64 m (20 mm) en cada golpe |

Hoja antes/después: `../pruebas_v32/HOJA_gesto_v3_vs_v32.png`.

**Dos cosas que no cumplen el pedido al pie de la letra:**
- **Tela:** 20–25 mm de escena no entran en la mesa (1,2 m reales = 37,5 mm). El paso hacia atrás va en profundidad
  y da 0,75 px por paso: no se ve. Por eso la tela se corre de costado hasta 9,4 mm, sin salir de la mesa.
  Cumple el criterio del crítico (≥ 6 px por golpe).
- **Caja:** las figuras son rígidas. La caja cae casi hasta el piso y **se separa de las manos** en el golpe. Se lee
  como "la deja caer". Tiene que mirarlo el crítico. Si no convence: `--caja_m 0.3` (en el workflow, sumar el flag).

## Calidad del render
La de la etapa A de `../render_noche.sh`, para **todos** los cuadros 0–149 (139 únicos, de `cuadros03.txt`):
1080×1920, Cycles 64 muestras adaptativas 0,01 + OIDN, motion blur 0,5, f/5,6, semilla 1022.

**Render completo en todos los tramos.** `PRESUPUESTO-RENDER.md` aprueba la receta barata solo para la caja cerrada
(f0–65), y con dos reservas: el resultado es inferido (no se corrió Blender) y el logo queda "blando". Además
necesita RIFE con Vulkan en la laptop. La caja cerrada es la parte más fuerte de la pieza: no se arriesga.
Si los minutos aprietan, ese tramo ahorra ~28 % del cómputo (55 de 139 cuadros, los más baratos). Se decide después de ver el primer render.

## Tiempo estimado
- **Medido:** 1 cuadro (f135) a 540×960 y 16 muestras, con 4 hilos en la laptop: **70,8 s**.
  Con la laptop entera, la calidad final tardó entre 345 y 751 s por cuadro (stills v3).
- **Supuesto, no medido:** un runner de 4 núcleos EPYC rinde como 4 hilos de la laptop, con un margen de ±30 %.
  Eso da entre 700 y 1100 s por cuadro "caro".
- **Por trabajo:** 14 cuadros → **entre 3,4 y 5,5 h**. Todo junto: unas 35 h de máquina, o sea ~2100 minutos.
- El tope de GitHub es 6 h por trabajo. Para no perder nada, Blender no arranca un cuadro que terminaría después de
  las 5 h 10 min. Lo que no llegó queda listado y se pide de nuevo.
- **Por eso el paso 6 de abajo es una prueba corta antes del render grande.**

## Cómo se sube y se dispara (cuando Martin decida)
1. **Elegir público o privado.** Diferencias que importan (datos de GitHub que conozco; verificarlos en
   github.com/pricing antes de decidir):
   - Público: máquinas de 4 núcleos y 16 GB, minutos gratis, los cuadros (~1 GB) se guardan sin costo.
   - Privado (plan gratis): máquinas de **2 núcleos**, **2000 minutos por mes** (este render usa ~2100) y
     **500 MB** para guardar los cuadros (este render produce ~1 GB). Con privado gratis **no alcanza**.
2. Crear el repo vacío en github.com/organizations/MAGONTEX → **New repository** → nombre, por ejemplo,
   `caja-render`. Sin README.
3. En la laptop, en una terminal (Git Bash), pegar:
   ```
   cd "C:/Users/Usuario/Desktop/Magontex_IA/Remotion/nobrand-fabrica-bloques/escenas-caja/esc01/gh-render"
   git init -b main && git add . && git commit -m "Render caja esc01 v3.2"
   git remote add origin https://github.com/MAGONTEX/caja-render.git && git push -u origin main
   ```
   Tiene que aparecer `main -> main` al final.
4. En el repo, ir a la pestaña **Actions**. Tiene que aparecer **Render caja esc01** a la izquierda.
5. Si GitHub pide habilitar Actions, hacer clic en el botón verde para habilitarlas.
6. **Prueba corta (unos 20–30 min):** clic en **Render caja esc01** → **Run workflow** → poner
   `cuadros` = `0,81,135`, `trabajos` = `3`, dejar lo demás → **Run workflow**. Cuando termine, abrir cualquier
   trabajo de render: cada línea `FRAME_OK <cuadro> <segundos>` dice cuánto tardó un cuadro de verdad.
   Con eso se recalcula: si pasa de 1300 s por cuadro, usar `trabajos` = `16` (o hasta 20) en el render grande.
7. **Render grande:** **Run workflow** con los valores por defecto (`todos`, `64`, `1`, `10`).
8. Cuando termine (el trabajo **verificar** dice qué cuadros faltan y si el cuadro 135, que se hace en dos máquinas,
   salió igual), en la terminal:
   ```
   gh auth login        (una sola vez)
   bash bajar_y_armar.sh
   ```
   Al final tiene que decir `cuadros: 139 de 139` y `LISTO: descarga/<número>/esc01_caja_v32.mp4`.
9. Si faltan cuadros, el script imprime el comando exacto para pedirlos (no lo lanza solo) y cómo re-armar.

## Qué hay adentro
- `.github/workflows/render.yml`: 3 trabajos. `plan` reparte los cuadros por costo (apertura y nave pesan 1,4,
  caja cerrada 1,0) y baja Blender 5.1.0 una vez, con verificación SHA-256 y cache. `render` (10 en paralelo)
  chequea el paquete, renderiza y sube los cuadros siempre, aunque falle o corte. `verificar` cuenta faltantes y
  compara el cuadro testigo.
- `tools/repartir.py` (reparto), `tools/chequeo.py` (falla si falta un archivo: Blender sola pinta de rosa y sigue).
- `bajar_y_armar.sh`: baja con `gh run download`, verifica que estén los 139, compara el testigo y arma con
  `armado/armar03.py` + `armado/audio03_PROVISORIO.wav` (el mismo armado de siempre).
- `escenas-caja/esc01/esc032.py` es una **copia**: si se cambia `../esc032.py`, hay que volver a copiarla acá.

## Qué NO verifiqué
- **El workflow nunca corrió en GitHub.** El YAML es válido, pero no se probaron el Blender de Linux, las librerías
  de apt, la cache ni la subida de cuadros.
- **El tiempo por cuadro en el runner** es un supuesto (ver arriba). Tampoco medí la RAM máxima de la escena.
- **Determinismo entre máquinas:** en la laptop, 4 hilos y todos los hilos dan el mismo cuadro exacto. Entre dos
  runners con CPU distinta, el denoiser puede variar un poco. Lo mide el cuadro testigo.
- `bajar_y_armar.sh` se probó con cuadros falsos (139 copias de la prueba, con un faltante y un re-render); la parte
  de `gh` no se probó.
- **Abierto del crítico v3, sin tocar:** P1-1 (congelar la maqueta de la nave o marcar f90–149 provisorio), P1-2
  (la nave "acuarela" a 64 muestras), P1-4 (escala de placard). La caída de la caja y la guía de la tela solo las vi
  a 540 y 16 muestras.
