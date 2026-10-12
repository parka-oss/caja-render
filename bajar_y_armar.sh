#!/bin/bash
# Baja los cuadros del render de GitHub Actions, verifica que esten todos y arma el video con audio. [XG·792d] 2026-10-12
# Armado = el de siempre (armado/armar03.py): post por cuadro (vineta -0,1 EV + grano por cuadro), los reposos quietos se
# copian del ultimo render, H.264 BT.709 CRF 14 + audio03_PROVISORIO.wav (AAC 256k).
#
# Uso (desde esta carpeta, con `gh auth login` hecho):
#   bash bajar_y_armar.sh                 -> la ultima corrida de render.yml
#   bash bajar_y_armar.sh 1234567890      -> una corrida puntual (el numero sale en la URL de la corrida)
#   REPO=MAGONTEX/caja-render bash bajar_y_armar.sh   -> si no se corre adentro del clon del repo
#   bash bajar_y_armar.sh descarga/1234567890         -> re-arma una descarga que ya esta en disco
# Necesita: gh, python con numpy y pillow, ffmpeg. NO dispara nada: si faltan cuadros, imprime el comando para pedirlos.
set -euo pipefail
cd "$(dirname "$0")"
R=${REPO:+-R $REPO}
if [ -n "${1:-}" ] && [ -d "$1" ]; then   # re-armar una descarga que ya esta en disco (sin gh)
  D=${1%/}
else
  RUN=${1:-$(gh run list $R --workflow render.yml --limit 1 --json databaseId -q '.[0].databaseId')}
  [ -n "$RUN" ] || { echo "no encontre corridas de render.yml"; exit 1; }
  D=descarga/$RUN
  echo "corrida $RUN -> $D"
  gh run view $R "$RUN" --json status,conclusion -q '"estado: \(.status) / \(.conclusion)"'
  mkdir -p "$D"
  gh run download $R "$RUN" -p 'frames-*' -D "$D"
fi

python - "$D" <<'EOF'
import glob, os, shutil, sys
import numpy as np
from PIL import Image
D = sys.argv[1]
out = os.path.join(D, "frames"); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)   # sin restos de un armado anterior
pedidos = [int(x) for x in open("escenas-caja/esc01/cuadros03.txt").read().split(",")]
hechos = {}
for p in glob.glob(os.path.join(D, "**", "f[0-9][0-9][0-9][0-9].png"), recursive=True):   # frames-*/ y re-renders en subcarpetas
    if os.path.dirname(os.path.abspath(p)) == os.path.abspath(out):
        continue
    hechos.setdefault(int(os.path.basename(p)[1:5]), []).append(p)
for f, ps in sorted(hechos.items()):
    shutil.copy2(ps[0], os.path.join(out, "f%04d.png" % f))
    if len(ps) > 1:   # cuadro testigo: el mismo cuadro en dos maquinas distintas
        a, b = [np.asarray(Image.open(p)).astype(int) for p in ps[:2]]
        dif = np.abs(a - b)
        print("TESTIGO f%d en 2 maquinas: diferencia maxima %d de 255, pixeles distintos %d (%.3f %%)" % (
            f, dif.max(), int((dif > 0).any(-1).sum()), 100.0 * (dif > 0).any(-1).mean()))
falta = [f for f in pedidos if f not in hechos]
print("cuadros: %d de %d" % (len(pedidos) - len(falta), len(pedidos)))
if falta:
    print("FALTAN %d: %s" % (len(falta), ",".join(map(str, falta))))
    print("Para pedirlos (lo decide Martin):  gh workflow run render.yml -f cuadros=%s -f trabajos=%d" % (
        ",".join(map(str, falta)), min(10, len(falta))))
    print("Cuando termine:  gh run download <corrida nueva> -p 'frames-*' -D %s/rerender  y  bash bajar_y_armar.sh %s" % (D, D))
    sys.exit(2)
sz = {Image.open(os.path.join(out, "f%04d.png" % f)).size for f in pedidos}
print("tamanos:", sz)
if len(sz) != 1:
    print("OJO: cuadros de distinta resolucion mezclados"); sys.exit(3)
EOF

python armado/armar03.py "$D/frames" "$D/esc01_caja_v32.mp4" "../$D/post"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of compact "$D/esc01_caja_v32.mp4"
echo "LISTO: $D/esc01_caja_v32.mp4"
