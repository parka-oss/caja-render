"""Reparte los cuadros entre N trabajos equilibrando el COSTO, no la cantidad [XG·792d].
Pesos medidos en la laptop (stills v3 a 1080, 64 muestras): caja cerrada f0-65 = 1,0 (373-395 s); apertura f66-95 = 1,4
(513-546 s, puerta en movimiento + motion blur); nave f96-149 = 1,4 (345-751 s, promedio). Reparto LPT: el cuadro mas caro va
al trabajo menos cargado. Un cuadro testigo (por defecto 135, nave en el golpe) va a DOS trabajos para medir determinismo.

  python tools/repartir.py --cuadros todos --trabajos 10            -> JSON de la matriz en stdout
  python tools/repartir.py --cuadros 66,67,140 --trabajos 3 --testigo -1   (re-render de faltantes, sin testigo)
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--cuadros", default="todos")
ap.add_argument("--trabajos", type=int, default=10)
ap.add_argument("--testigo", type=int, default=135)
ap.add_argument("--resumen", action="store_true")
ap.add_argument("--lista", action="store_true")   # solo imprime la lista de cuadros pedidos (para verificar)
A = ap.parse_args()

def leer(spec):
    """"todos" = los unicos de cuadros03.txt (0-149) + 150..212 (v3.3: la nave sigue). Lista "66,67,140" o rangos "84-212"."""
    if spec.strip() in ("", "todos"):
        fr = [int(x) for x in open(os.path.join(HERE, "..", "escenas-caja", "esc01", "cuadros03.txt")).read().split(",") if x.strip()]
        return sorted(set(fr) | set(range(150, 213)))
    out = set()
    for tok in spec.replace(" ", "").split(","):
        if "-" in tok:
            a, b = tok.split("-"); out |= set(range(int(a), int(b) + 1))
        elif tok:
            out.add(int(tok))
    return sorted(out)


FR = leer(A.cuadros)
if A.lista:
    print(",".join(map(str, FR))); sys.exit(0)


def peso(f):
    # v3.3: la nave (f84+) va a 128 muestras (el doble que la v3.2) -> ~1,7x el costo de la apertura a 64
    return 1.0 if f < 66 else (1.4 if f < 84 else 2.4)


n = max(1, min(A.trabajos, len(FR)))
carga = [0.0] * n
listas = [[] for _ in range(n)]
for f in sorted(FR, key=lambda f: (-peso(f), f)):
    i = min(range(n), key=lambda k: (carga[k], k))
    listas[i].append(f); carga[i] += peso(f)
if A.testigo in FR and n > 1:
    dueno = next(i for i in range(n) if A.testigo in listas[i])
    otro = min((i for i in range(n) if i != dueno), key=lambda k: (carga[k], k))
    listas[otro].append(A.testigo); carga[otro] += peso(A.testigo)
# dentro de cada trabajo, el mas caro primero: si el tiempo se acaba, lo que queda sin hacer es lo barato
inc = [{"trabajo": i, "cuadros": ",".join(str(f) for f in sorted(l, key=lambda f: (-peso(f), f))), "n": len(l), "costo": round(carga[i], 1)}
       for i, l in enumerate(listas)]
if A.resumen:
    for d in inc:
        print("trabajo %d: %d cuadros, costo %.1f" % (d["trabajo"], d["n"], d["costo"]), file=sys.stderr)
    print("total %d cuadros unicos (+%d testigo), costo max %.1f / medio %.1f" % (
        len(FR), int(A.testigo in FR and n > 1), max(carga), sum(carga) / n), file=sys.stderr)
print(json.dumps({"include": inc}, separators=(",", ":")))
