"""Escena 01 v3.4 [XG·792d] (CRITICO_v33 P0-V1): los gestos de la nave SIN diente de sierra. Lo usa esc034.py.
curvas03.py no se toca: hasta f83 (T_CORTE) todo gesto devuelve EXACTAMENTE la curva vieja (f0-83 iguales); desde f84 cada
operario sigue su propia fase, todo funcion del cuadro (t = f / FPS).
    python curvas04.py   -> tabla de fases/duraciones, paso por cuadro normalizado, eventos04.json

Forma de un ciclo (periodo 1 en fase u):
  - accion  u in [0, BETA):  de -a (anticipacion) a 1 (golpe), coseno: arranca y llega con ease, ~12-13 cuadros
  - vuelta  u in [BETA, 1):  de 1 a -a: seguimiento, pasa por el reposo (0) y sigue a la anticipacion (-a)
  La velocidad es continua (0 en el golpe y en la anticipacion), sin pausas: el paso maximo queda <= ~1,6x la mediana.
Fase por operario phi_i(t):
  - f84-149: Hermite desde la fase que reproduce el valor (y la velocidad) de la curva vieja en f83 hasta la fase de bucle,
    con N_i ciclos (semilla fija) -> ciclos de 1,0-1,6 s distintos por operario.
  - f150-212 (bucle de L = 63 cuadros, f212 encadena con f150): exactamente 2 ciclos por operario con una deformacion
    w(s) = s + eps/(2 pi) (sin(2 pi s + rho) - sin rho): duraciones 1,00-1,10 s, distintas por operario; fase de bucle psi_i
    repartida por estratos con semilla fija -> la nave no golpea junta. phi(f213) = phi(f150) + 2 y phi' tambien coincide.
Por que 2 ciclos: 63 cuadros solo admiten un numero entero de ciclos; con ciclos de 1,0-1,6 s el unico entero posible es 2
(31,5 cuadros de media). Fuera del bucle (f84-149) los ciclos si pueden ir de 1,0 a 1,6 s.
"""
import json
import math
import os
import random

import curvas03 as C3

FPS = C3.FPS
F_CORTE = 83                     # ultimo cuadro con la curva vieja (f0-83 no cambian)
T_CORTE = F_CORTE / FPS
F_BUCLE, F_FIN = 150, 212        # bucle f150..f212 (63 cuadros)
T_BUCLE = F_BUCLE / FPS
L_BUCLE = (F_FIN + 1 - F_BUCLE) / FPS
K_BUCLE = 2                      # ciclos por operario en el bucle
BETA = 0.47                      # fraccion del ciclo para la accion (0,40 da paso max/mediana 1,89 a tasa fija: sin margen)
SEMILLA = 7922                   # [XG·792d]
EPS_MAX = 0.045                  # deformacion del bucle: rate 2/L*(1 +- eps) <= 1/1,0 s
R_MIN, R_MAX = 1 / 1.6, 1 / 1.0  # ciclos por segundo admitidos
N_MIN, N_MAX = 1.62, 2.12        # ciclos en f84-149 (2,2 s): tasa 0,72-1,0 ciclo/s; mas lento baja la mediana del paso (max/med > 2)
R0_MIN, R0_MAX = 0.72, 0.98
R0_SEM = None                    # probado (0,64-0,98 sembrada): el primer golpe sigue agrupado y el bucle empeora (7-8 en 5 cuadros)

# operarios: (clave, fase vieja de curvas03 o None para carga, anticipacion a)
# la anticipacion de la costura es mayor (CRITICO pide >= 8 px de recorrido de tela por ciclo)
OPS = [("corte_a_op0", 0.0, 0.25), ("corte_a_op1", 0.10, 0.25), ("op_plancha0", 0.0, 0.25), ("op_plancha1", 0.2, 0.25),
       ("op_caja", None, 0.06), ("op_control", 0.15, 0.25), ("op_rollo", 0.2, 0.25)]
N_COSTURA = 12                   # una curva propia por puesto de costura (v3.3: 0,03 * (n % 3) de fase vieja)
A_COSTURA = 0.35
GAN_COSTURA = 16.0 / 14.0         # el giro de la costura pasa de 14 a 16 grados desde f84 (con 14 la tela recorria 7,4-7,7 px)
T_RAMPA = 1.0                    # s: la ganancia entra suave (f84-114); antes de f84 vale 1 (f0-83 iguales)


def _old(t, fase):
    return C3.carga(t) if fase is None else C3.trabajo(t, fase)


def forma(u, a):
    """Ciclo de trabajo en fase u (periodo 1): -a en u=0, 1 en u=BETA."""
    u = u % 1.0
    m, h = (1 - a) / 2, (1 + a) / 2
    if u < BETA:
        th = math.pi + math.pi * u / BETA
    else:
        th = math.pi * (u - BETA) / (1 - BETA)
    return m + h * math.cos(th)


def dforma(u, a):
    u = u % 1.0
    h = (1 + a) / 2
    if u < BETA:
        th = math.pi + math.pi * u / BETA; k = math.pi / BETA
    else:
        th = math.pi * (u - BETA) / (1 - BETA); k = math.pi / (1 - BETA)
    return -h * math.sin(th) * k


def _fase_de_valor(v, a, sube):
    """Fase u con forma(u) = v, en la rama que sube (accion) o baja (vuelta)."""
    m, h = (1 - a) / 2, (1 + a) / 2
    c = max(-1.0, min(1.0, (v - m) / h))
    th = math.acos(c)                 # [0, pi]
    if sube:
        return BETA * (2 * math.pi - th - math.pi) / math.pi   # th en (pi, 2pi) -> u en (0, BETA)
    return BETA + (1 - BETA) * th / math.pi


class Gesto:
    def __init__(self, clave, fase_vieja, a, psi, eps, rho, r0_sem=None, gan=1.0):
        self.clave, self.fv, self.a, self.gan = clave, fase_vieja, a, gan
        dt = 1e-4
        v83 = _old(T_CORTE, fase_vieja)
        dv = (_old(T_CORTE, fase_vieja) - _old(T_CORTE - dt, fase_vieja)) / dt
        sube = dv > 0
        u83 = _fase_de_valor(v83, a, sube)
        d = dforma(u83, a)
        r0 = dv / d if abs(d) > 0.3 else None            # misma velocidad que la curva vieja en f83 (C1 en el empalme)
        if r0 is None or not (R0_MIN <= r0 <= R0_MAX):
            r0 = None
        self.v83, self.u83, self.dv83 = v83, u83, dv
        self.eps, self.rho = eps, rho
        self.r1 = K_BUCLE * (1 + eps * math.cos(rho)) / L_BUCLE
        T = T_BUCLE - T_CORTE
        N = (psi - u83) % 1.0
        while N < N_MIN:
            N += 1.0
        self.N = N
        self.psi = psi
        self.r0 = r0_sem if r0_sem is not None else (r0 if r0 is not None else min(R0_MAX, max(R0_MIN, N / T)))
        self.T = T

    def fase(self, t):
        if t <= T_CORTE:
            return None
        if t < T_BUCLE:
            s = (t - T_CORTE) / self.T
            h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s
            h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
            return self.u83 * h00 + self.r0 * self.T * h10 + (self.u83 + self.N) * h01 + self.r1 * self.T * h11
        dtb = t - T_BUCLE
        k, s = divmod(dtb / L_BUCLE, 1.0)
        w = s + self.eps / (2 * math.pi) * (math.sin(2 * math.pi * s + self.rho) - math.sin(self.rho))
        return self.u83 + self.N + K_BUCLE * (k + w)

    def __call__(self, t):
        if t <= T_CORTE + 1e-9:
            return _old(t, self.fv)
        v = forma(self.fase(t), self.a)
        if self.gan != 1.0:
            p = min(1.0, (t - T_CORTE) / T_RAMPA)
            v *= 1.0 + (self.gan - 1.0) * p * p * (3 - 2 * p)
        return v


PRINCIPALES = ("corte_a_op0", "op_plancha0", "op_plancha1", "op_caja")   # los gestos que se leen: se reparten primero


def u_golpe(a):
    """Fase en que la accion cruza 0,5 (el golpe que suena)."""
    return _fase_de_valor(0.5, a, True)


def _armar():
    """psi (fase de cada operario al entrar al bucle, f150): cada uno tiene una ventana admitida [u83 + N_MIN, u83 + N_MAX]
    (mod 1). En orden sembrado, cada operario toma, dentro de su ventana, la fase mas lejana de las ya elegidas (desempate
    con ruido sembrado): los golpes quedan repartidos en el ciclo y no caen juntos."""
    rng = random.Random(SEMILLA)
    claves = [(c, f, a) for c, f, a in OPS] + [("costura_%d" % i, 0.03 * (i % 3), A_COSTURA) for i in range(N_COSTURA)]
    orden = list(range(len(claves))); rng.shuffle(orden)
    orden = [i for i in orden if claves[i][0] in PRINCIPALES] + [i for i in orden if claves[i][0] not in PRINCIPALES]
    G, elegidas = {}, []
    for i in orden:
        c, f, a = claves[i]
        eps = rng.uniform(-EPS_MAX, EPS_MAX); rho = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(R0_SEM[0], R0_SEM[1]) if R0_SEM else None   # None: la tasa de arranque copia la velocidad vieja en f83
        g0 = Gesto(c, f, a, 0.0, eps, rho, r0)
        best = None
        for k in range(101):
            psi = (g0.u83 + N_MIN + (N_MAX - N_MIN) * k / 100) % 1.0
            rmin, rmax = tasa_rango(Gesto(c, f, a, psi, eps, rho, r0), paso=2)
            if rmin < R_MIN or rmax > R_MAX:
                continue
            h = (psi + u_golpe(a)) % 1.0
            dmin = min([min(abs(h - e), 1 - abs(h - e)) for e in elegidas] or [1.0])
            score = dmin + 0.004 * rng.random()
            if best is None or score > best[0]:
                best = (score, psi, h)
        elegidas.append(best[2])
        G[c] = Gesto(c, f, a, best[1], eps, rho, r0, GAN_COSTURA if c.startswith("costura_") else 1.0)
    return {c: G[c] for c, _, _ in claves}, 0


def tasa_rango(g, f0=F_CORTE + 1, f1=F_FIN + 1, paso=10):
    rs = []
    for k in range((f1 - f0) * paso):
        t = (f0 + k / paso) / FPS; h = 1e-4
        rs.append((g.fase(t + h) - g.fase(t - h)) / (2 * h))
    return min(rs), max(rs)


GESTOS, _INTENTO = _armar()


def gesto(clave):
    return GESTOS[clave]


def costura(i):
    """Puesto de costura i (el mismo indice n_cos de esc033): fase vieja 0,03 * (i % 3) hasta f83, ciclo propio despues."""
    return GESTOS["costura_%d" % i]


def duraciones(g):
    """Tiempos (s) en que la fase cruza cada entero (golpe de anticipacion) en f84-213, y las duraciones de ciclo."""
    ts, prev = [], None
    for k in range((F_FIN + 1 - F_CORTE) * 20 + 1):
        t = T_CORTE + 1e-6 + k / (20 * FPS)
        p = g.fase(t)
        if prev is not None and math.floor(p) > math.floor(prev):
            ts.append(t)
        prev = p
    return ts, [b - a for a, b in zip(ts, ts[1:])]


def eventos():
    """Eventos viejos hasta f83 + un 'maquina' por gesto cuando la accion cruza 0,5 subiendo (t exacto del cruce)."""
    ev = [e for e in C3.eventos() if e["t"] <= T_CORTE]
    fin = (F_FIN + 1) / FPS
    for c, g in GESTOS.items():
        t, prev_t, prev_v = T_CORTE, T_CORTE, g(T_CORTE)
        while t < fin:
            t += 1.0 / (FPS * 40)
            v = g(t)
            if prev_v < 0.5 <= v:
                a_, b_ = prev_t, t
                for _ in range(40):
                    mm = 0.5 * (a_ + b_)
                    if g(mm) < 0.5: a_ = mm
                    else: b_ = mm
                tm = 0.5 * (a_ + b_)
                prim = c in PRINCIPALES
                ev.append({"t": round(tm, 5), "cuadro": round(tm * FPS, 2), "tipo": "maquina", "magnitud": 0.7 if prim else 0.35,
                           "nota": "golpe propio de %s (v3.4: cada operario a su ciclo)" % c, "gesto": c})
            prev_t, prev_v = t, v
    ev.sort(key=lambda e: e["t"])
    return ev


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    print("permutacion valida en el intento %d (semilla %d)" % (_INTENTO, SEMILLA))
    print("%-13s %6s %6s %6s %6s %5s %6s %6s  %s" % ("gesto", "v83", "u83", "r0", "N", "psi", "eps", "r1", "ciclos (s)"))
    for c, g in GESTOS.items():
        ts, ds = duraciones(g)
        rmin, rmax = tasa_rango(g)
        print("%-13s %+6.3f %6.3f %6.3f %6.3f %5.3f %+6.3f %6.3f  %s  tasa %.3f-%.3f -> %.2f-%.2f s" % (
            c, g.v83, g.u83, g.r0, g.N, g.psi, g.eps, g.r1, " ".join("%.2f" % d for d in ds), rmin, rmax, 1 / rmax, 1 / rmin))
    # paso por cuadro normalizado (unidades de la curva; x amplitud en px = paso en px)
    print("\npaso por cuadro normalizado f84-212 (y el empalme f83->84 y el bucle f212->f150):")
    for c, g in GESTOS.items():
        st = [abs(g((f + 1) / FPS) - g(f / FPS)) for f in range(F_CORTE, F_FIN)]
        st84 = st[1:]
        srt = sorted(st84); med = srt[len(srt) // 2]
        seam = abs(g(F_BUCLE / FPS) - g(F_FIN / FPS))
        loop0 = abs(g((F_FIN + 1) / FPS) - g(F_BUCLE / FPS))
        print("%-13s max %.4f mediana %.4f max/med %.2f | f83->84 %.4f (f82->83 vieja %.4f) | f212->f150 %.4f (phi(f213)-phi(f150) err %.1e) | rango %.2f..%.2f" % (
            c, max(st84), med, max(st84) / med, st[0], abs(g(T_CORTE) - g((F_CORTE - 1) / FPS)), seam, loop0,
            min(g(f / FPS) for f in range(84, 213)), max(g(f / FPS) for f in range(84, 213))))
    # f0-83 identicos a la curva vieja
    dif = max(abs(GESTOS[c](f / FPS) - _old(f / FPS, GESTOS[c].fv)) for c in GESTOS for f in range(0, F_CORTE + 1))
    print("\nf0-83 contra curvas03: diferencia maxima %.3g" % dif)
    # golpes simultaneos: cuantos gestos cruzan 0,5 en el mismo cuadro
    ev = eventos()
    m = [e for e in ev if e["tipo"] == "maquina"]
    from collections import Counter
    cnt = Counter(int(e["cuadro"]) for e in m)
    print("golpes en f84-212: %d; maximo en un mismo cuadro: %d; en +-2 cuadros: %d" % (
        len(m), max(cnt.values()), max(sum(cnt.get(f + d, 0) for d in range(-2, 3)) for f in range(84, 213))))
    json.dump({"fps": FPS, "cuadros": F_FIN + 1, "eventos": ev}, open(os.path.join(here, "eventos04.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("eventos04.json: %d eventos" % len(ev))
