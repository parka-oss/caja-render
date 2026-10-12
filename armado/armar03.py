"""Escena 01 v3: post por cuadro + video final (audio03).
- Cadencia: cada cuadro de salida toma el último render <= f (en los tramos "en dos" se repite el par).
- Post = ancla-caja/post.py (viñeta -0,1 EV en luz lineal, grano monocromo 1,2 %) pero con semilla POR CUADRO (1022 + f):
  un grano fijo sobre una imagen que se mueve se lee como pantalla sucia.
- Video: H.264 yuv420p, matriz BT.709 rango limitado y etiquetas BT.709; audio desde audio03_PROVISORIO.wav.
Uso: python armar01.py frames_dir salida.mp4 [--sin-audio]
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
src, dst = sys.argv[1], sys.argv[2]
N_FR = 150
post_dir = os.path.join(HERE, sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "post")
os.makedirs(post_dir, exist_ok=True)

rendered = sorted(int(n[1:5]) for n in os.listdir(src) if n.startswith("f") and n.endswith(".png"))
assert rendered and rendered[0] == 0, "falta el cuadro 0"
mapa = {}
for f in range(N_FR):
    mapa[f] = max(r for r in rendered if r <= f)


def post(a, seed):
    a = a[..., :3]
    h, w = a.shape[:2]
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    lin *= (2.0 ** (-0.1 * r ** 2.2))[..., None]
    a = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.maximum(lin, 0) ** (1 / 2.4) - 0.055)
    g = np.random.default_rng(seed).normal(0, 1, (h, w))
    gp = np.pad(g, 1, mode="edge")
    g = (gp[1:-1, :-2] + 2 * gp[1:-1, 1:-1] + gp[1:-1, 2:]) / 4
    gp = np.pad(g, 1, mode="edge")
    g = (gp[:-2, 1:-1] + 2 * gp[1:-1, 1:-1] + gp[2:, 1:-1]) / 4
    g /= g.std()
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    amp = 0.012 * (0.6 + 0.4 * (1 - np.abs(lum - 0.5) * 2))
    return np.clip(a + (g * amp)[..., None], 0, 1)


cache = {}
for f in range(N_FR):
    p_out = os.path.join(post_dir, "p%04d.png" % f)
    s = mapa[f]
    if s not in cache:
        cache.clear()
        im = np.asarray(Image.open(os.path.join(src, "f%04d.png" % s))).astype(np.float64)
        cache[s] = im / (65535.0 if im.max() > 255 else 255.0)
    Image.fromarray((post(cache[s], 1022 + f) * 255 + 0.5).astype(np.uint8)).save(p_out)
print("post ok:", N_FR, "cuadros;", len(set(mapa.values())), "renders distintos")

cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "30", "-i", os.path.join(post_dir, "p%04d.png")]
if "--sin-audio" not in sys.argv:
    cmd += ["-i", os.path.join(HERE, "audio03_PROVISORIO.wav")]
cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high", "-movflags", "+faststart",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
if "--sin-audio" not in sys.argv:
    cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest"]
cmd += [dst]
subprocess.run(cmd, check=True)
print("VIDEO_OK", dst)
