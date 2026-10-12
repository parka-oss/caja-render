"""Escena 01 v3 "apertura" (caja-libro MG + "Late la fabrica"): curvas y registro de eventos, todo funcion del cuadro
(t = f / FPS; nunca reloj). Lo usan esc03.py (Blender: keyframes por cuadro) y audio03.py (sonido SOLO desde eventos03.json).
    python curvas03.py   -> eventos03.json, curvas03.json, cuadros03.txt y resumen

v3 (CRITICO_v2 + PACKAGING_v3):
- 1.er latido a 0,30 s (P1-6: sin 0,8 s muertos); intervalos 0,70 / 0,60 / 0,40 s conservados (funcionaban).
- Latido = resorte amortiguado contra el iman (P2-3): 1 cuadro de empuje, vuelve y rebota 4-6 cuadros que decaen (zeta ~0,22).
  Quietud de 0,2 s antes del 4.o.
- EL PULSO ES LA MAQUINA (P0-1): una grilla de golpes (los 4 latidos + la nave que sigue a 0,40 s) mueve la cortadora, las
  planchas, la costura y al que carga. Cada golpe de la maquina es un evento "maquina" (el audio lo toma de ahi).
- Camara: quieta en los latidos; la orbita arranca en el clic del iman (Ajuste A de PACKAGING 15) con ease-in de ~6 cuadros y
  <= 20 grados/s de media. Puerta a 125 (P2-1: el canto libre no sale de cuadro). Foco: de la puerta a la planta de costura.
- Estudio -1 EV siguiendo la puerta (P1-3): al abrir, la fabrica es lo mas claro del cuadro.
v2 en v2_premium/, v1 en v1_carton/.
"""
import json
import math
import os

FPS = 30
N_FR = 150
T_PULSOS = (0.30, 1.00, 1.60)   # intervalos 0,70 / 0,60 / 0,40 (se conserva la aceleracion de la v2)
T_BEAT2 = 2.00                  # 4.o latido: el iman cede
T_SWING = 1.90                  # del 4.o latido al reposo abierto
T_ANCLA = T_BEAT2 + T_SWING     # 3,90 s: puerta en reposo -> 1,1 s de fabrica trabajando a la vista
PERIODO_NAVE = 0.40             # despues del 4.o, la nave sigue al ultimo intervalo
BEATS = T_PULSOS + (T_BEAT2,) + tuple(round(T_BEAT2 + PERIODO_NAVE * k, 4) for k in range(1, 8))   # ... 4,80

# ---------------------------------------------------------------- puerta (grados sobre la bisagra; 0 = contra el iman)
TH0 = 0.10                 # apoyada en el iman: la linea oscura de 0,5-1 mm de PACKAGING 7
AMP = (0.9, 1.2, 1.5)      # 6 / 8 / 10 mm en el canto libre: dentro del alcance del iman (5-10 mm)
AMP4 = 1.8                 # 12,5 mm: se pasa del alcance del iman -> cede
T_UP = 1.0 / FPS           # 1 cuadro de empuje (golpe desde adentro)
T_DN = 2.0 / FPS           # el iman la trae acelerando en 2 cuadros -> golpe
B_AMP = 0.30               # primer rebote (fraccion del empuje)
B_LOBE = 0.060             # medio ciclo del rebote (~2 cuadros)
B_TAU = B_LOBE / 0.71      # zeta ~0,22: cada medio ciclo queda en 0,49 del anterior
TH_ANCLA = 100.0
OVERSHOOT = 3.0
TS1 = T_BEAT2 + 0.86 * T_SWING
SETTLE_W = 2 * math.pi / 0.36
SETTLE_TAU = 0.085
TH_IMAN = TH0 + max(AMP) + 0.5


def _clamp(p):
    return min(1.0, max(0.0, p))


def _smooth(p):
    p = _clamp(p)
    return p * p * p * (p * (6 * p - 15) + 10)


def _ease_io(p):
    p = _clamp(p)
    return 0.5 - 0.5 * math.cos(math.pi * p)


def _ease_out(p):
    p = _clamp(p)
    return 1 - (1 - p) ** 3


def _swing(p):
    return _smooth(_clamp(p) ** 1.3)


def _pulso(dt, a):
    """Empuje de 1 cuadro, el iman la trae en 2 (acelerando), golpe y rebote amortiguado que decae en 4-6 cuadros."""
    if dt < 0:
        return 0.0
    if dt < T_UP:
        return a * _ease_out(dt / T_UP)
    dt2 = dt - T_UP
    if dt2 < T_DN:
        return a * (1 - (dt2 / T_DN) ** 2.2)
    db = dt2 - T_DN
    if db > 0.45:
        return 0.0
    return a * B_AMP * abs(math.sin(math.pi * db / B_LOBE)) * math.exp(-db / B_TAU)


def t_golpe(i):
    return T_PULSOS[i] + T_UP + T_DN


def door(t):
    th = TH0
    for ti, a in zip(T_PULSOS, AMP):
        th += _pulso(t - ti, a)
    if t >= T_BEAT2:
        dt = t - T_BEAT2
        bump = AMP4 * _ease_out(dt / (2.0 / FPS))
        if t < TS1:
            sw = (TH_ANCLA + OVERSHOOT - TH0 - AMP4) * _swing(dt / (TS1 - T_BEAT2))
            th = TH0 + bump + sw
        else:
            ds = t - TS1
            th = TH_ANCLA + OVERSHOOT * math.cos(SETTLE_W * ds) * math.exp(-ds / SETTLE_TAU)
    return th


def door_vel(t, h=1e-4):
    return (door(t + h) - door(t - h)) / (2 * h)


def gap_mm(t):
    """Ranura en el canto libre (mm): 0,5 mm de linea de cierre + lo que abre la puerta (400 mm de brazo)."""
    return 0.5 + 400.0 * math.sin(math.radians(max(0.0, min(90.0, door(t)))))


# ---------------------------------------------------------------- latido de la luz
FLARE = (0.7, 0.85, 1.0, 1.1)


def luz(t):
    base = 0.55
    fl = 0.0
    for i, ti in enumerate(T_PULSOS + (T_BEAT2,)):
        base += 0.15 * _smooth((t - ti) / 0.2)
        if t >= ti:
            dt = t - ti
            fl += FLARE[i] * (1 - math.exp(-dt / 0.012)) * math.exp(-dt / 0.10)
    return base + fl


def estudio(t):
    """Multiplicador del estudio (llave, relleno, fondo, mundo): -1 EV siguiendo la puerta (P1-3)."""
    return 1.0 - 0.6 * _smooth(max(0.0, door(t) - 3.0) / (TH_ANCLA * 0.8))


# ---------------------------------------------------------------- cinta de grosgrain (forma "flex", -1..1)
def cinta(t):
    v = 0.0
    for i in range(3):
        dt = t - t_golpe(i)
        if dt > 0:                          # temblor de resorte despues de cada tac: 5 Hz, se apaga en ~0,5 s
            v += (0.5 + 0.2 * i) * math.exp(-dt / 0.14) * math.sin(2 * math.pi * 5.0 * dt)
    v += -max(-1.0, min(1.0, door_vel(t) / 250.0)) * 0.6
    if t > TS1:
        ds = t - TS1
        v += 0.5 * math.exp(-ds / 0.18) * math.sin(2 * math.pi * 3.0 * ds)
    return max(-1.0, min(1.0, v))


# ---------------------------------------------------------------- trabajo en la nave: un golpe por cada beat
def golpe(dt):
    """Un ciclo de trabajo (0 = reposo, 1 = golpe): anticipacion 3 cuadros, accion 2, sosten 1, vuelta con seguimiento."""
    if dt < -0.10 or dt > 0.36:
        return 0.0
    if dt < 0:
        return -0.2 * _ease_io((dt + 0.10) / 0.10)
    if dt < 2.0 / FPS:
        return -0.2 + 1.2 * _ease_out(dt / (2.0 / FPS))
    if dt < 3.0 / FPS:
        return 1.0
    p = (dt - 3.0 / FPS) / (0.36 - 3.0 / FPS)
    return (1.0 - _ease_io(p)) - 0.08 * math.sin(math.pi * p) * p


def trabajo(t, fase=0.0):
    """Suma de golpes en la grilla BEATS (fase en s: los puestos no son un metronomo exacto)."""
    return sum(golpe(t - b - fase) for b in BEATS)


def avance(t, fase=0.0):
    """Tela que avanza un paso por golpe (monotono): cuantos pasos lleva dados."""
    s = 0.0
    for b in BEATS:
        if b < T_VIS:            # v3.1: con la puerta a menos de 20 grados la costura no se ve: no gasta pasos de mesa
            continue
        dt = t - b - fase
        if dt > 0:
            s += _ease_io(dt / 0.12)
    return s


def carga(t):
    """El que carga (v3.1, CRITICO_v3 P0-1): baja la caja en CADA golpe desde el 4.o latido (antes cada 2), con la misma
    forma de golpe (anticipacion -> bajada -> sosten -> vuelta). Solo la bajada: se ignora la anticipacion negativa."""
    return max(0.0, sum(golpe(t - b) for b in BEATS[3:]))


def cuelga(t):
    """Cinta (v3.1, CRITICO_v3 P2-3): cerrada, el iman la pisa en la ranura y sale en S horizontal; cuando el iman cede la
    ranura la suelta y cae por su peso en ~0,3 s (0 = S horizontal, 1 = colgando), con un rebote chico que se apaga."""
    if t <= T_CLIC:              # el clic del iman (f65,6) suelta la ranura
        return 0.0
    dt = t - T_CLIC
    v = _ease_out(min(1.0, dt / 0.30))
    if dt > 0.30:
        v += 0.08 * math.sin(2 * math.pi * (dt - 0.30) / 0.30) * math.exp(-(dt - 0.30) / 0.20)
    return max(0.0, min(1.0, v))


# ---------------------------------------------------------------- eventos (emit al cruzar umbral, t exacto del cruce)
def _cross(fn, thr, t0, t1, up=True, steps=6000):
    prev_t, prev_v = t0, fn(t0)
    for i in range(1, steps + 1):
        t = t0 + (t1 - t0) * i / steps
        v = fn(t)
        if (up and prev_v < thr <= v) or ((not up) and prev_v > thr >= v):
            a, b = prev_t, t
            for _ in range(40):
                m = 0.5 * (a + b)
                vm = fn(m)
                if (up and vm < thr) or ((not up) and vm > thr):
                    a = m
                else:
                    b = m
            return 0.5 * (a + b)
        prev_t, prev_v = t, v
    return None


T_CLIC = _cross(door, TH_IMAN, T_BEAT2, N_FR / FPS)
T_VIS = _cross(door, 20.0, T_BEAT2, N_FR / FPS)   # la nave empieza a verse (primer golpe visible: 2,8 s, f84)

# ---------------------------------------------------------------- camara
CAM0 = (-28.0, 12.0, 2.60, 0.0, -0.05)
CAM1 = (4.0, 11.0, 2.70, -0.08, 0.03)
CAM_DUR = 1.8                   # 32 grados en 1,8 s = 17,8 grados/s de media (<= 20)


def _cam_e(t):
    if t <= T_CLIC:
        return 0.0
    p = (t - T_CLIC) / CAM_DUR
    if p >= 1.0:
        return 1.0
    return _smooth(p ** 0.85)


def cam(f):
    t = f / FPS
    e = _cam_e(t)
    az = CAM0[0] + (CAM1[0] - CAM0[0]) * e
    el = CAM0[1] + (CAM1[1] - CAM0[1]) * e
    d = math.exp(math.log(CAM0[2]) + (math.log(CAM1[2]) - math.log(CAM0[2])) * e)
    tend = T_CLIC + CAM_DUR
    if t > tend:   # respira: sigue acercandose 1 % hasta el final (nunca un cuadro clavado)
        d *= 1.0 - 0.01 * _ease_io((t - tend) / (N_FR / FPS - tend))
    sx = CAM0[3] + (CAM1[3] - CAM0[3]) * e
    sy = CAM0[4] + (CAM1[4] - CAM0[4]) * e
    # persigue a la puerta: cuando el canto libre barre hacia la derecha (f75-90) el cuadro lo acompana y lo suelta
    # (sin esto el canto toca el borde derecho en f78-83; medido con pruebas_v3/encuadre)
    if t > T_CLIC:
        sx += 0.035 * math.sin(math.pi * _clamp((t - T_CLIC) / 1.1)) ** 2
    return az, el, d, sx, sy


def foco(t):
    """0 = foco en la cara de la puerta; 1 = en la planta de costura (medio de la nave)."""
    return _smooth((door(t) - 20.0) / 80.0)


def eventos():
    ev = []

    def emit(t, tipo, mag, nota, **kw):
        if t is not None:
            d = {"t": round(t, 5), "cuadro": round(t * FPS, 2), "tipo": tipo, "magnitud": round(mag, 3), "nota": nota}
            d.update(kw)
            ev.append(d)

    fin = N_FR / FPS
    for i, ti in enumerate(T_PULSOS):
        emit(_cross(door, TH0 + 0.05, ti - 0.05, ti + 0.1), "latido", 0.5 + 0.17 * i, "la fabrica late: la puerta se despega del iman", n=i + 1)
        emit(_cross(door, TH0 + 0.02, ti + T_UP, ti + 0.3, up=False), "golpe_iman", 0.55 + 0.15 * i, "la puerta golpea contra el iman", n=i + 1)
    emit(_cross(door, TH0 + 0.05, T_BEAT2 - 0.05, T_BEAT2 + 0.1), "latido", 1.0, "4.o latido", n=4)
    emit(T_CLIC, "iman_cede", 0.8, "el iman suelta (clic seco)")
    emit(_cross(door_vel, 40.0, T_BEAT2 + T_UP, fin), "bisagra", 0.6, "la bisagra de papel toma el peso")
    emit(_cross(door, 30.0, 0, fin), "nave_entra", 1.0, "el sonido de la nave entra de golpe")
    emit(_cross(door_vel, 0.0, TS1 - 0.2, fin, up=False), "asiento", 0.3, "la puerta frena y se asienta")
    # la maquina: el golpe de trabajo cruza 0,5 subiendo (mismo reloj que el latido: el pulso ES la maquina)
    for k, b in enumerate(BEATS):
        tm = _cross(trabajo, 0.5, b - 0.02, b + 0.08)
        emit(tm, "maquina", 0.45 if k < 4 else 0.7, "golpe de la nave (cortadora/plancha/costura)", n=k + 1)
    ev.sort(key=lambda e: e["t"])
    return ev


def curvas():
    out = []
    for f in range(N_FR):
        t = f / FPS
        az, el, d, sx, sy = cam(f)
        out.append({"f": f, "t": round(t, 4), "door": round(door(t), 4), "door_vel": round(door_vel(t), 2), "gap_mm": round(gap_mm(t), 3),
                    "luz": round(luz(t), 4), "estudio": round(estudio(t), 4), "cinta": round(cinta(t), 4),
                    "trabajo": round(trabajo(t), 4), "avance": round(avance(t), 4), "carga": round(carga(t), 4), "cuelga": round(cuelga(t), 4),
                    "foco": round(foco(t), 4),
                    "az": round(az, 4), "el": round(el, 4), "dist": round(d, 5), "sx": round(sx, 5), "sy": round(sy, 5)})
    return out


def estado(c):
    abierta = c["door"] > 3.0      # con la puerta cerrada la nave no se ve: su trabajo no cambia el cuadro
    w = (round(c["trabajo"], 3), round(c["avance"], 3), round(c["carga"], 3)) if abierta else ()
    return (round(c["door"], 3), round(c["luz"] / 0.02), round(c["cinta"] / 0.04), round(c["cuelga"] / 0.02), round(c["az"], 3), round(c["dist"], 4)) + w


def cuadros_a_render(cv):
    fr, prev = [], None
    for c in cv:
        k = estado(c)
        if k != prev:
            fr.append(c["f"])
        prev = k
    return fr


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    ev = eventos()
    json.dump({"fps": FPS, "cuadros": N_FR, "eventos": ev}, open(os.path.join(here, "eventos03.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    cv = curvas()
    json.dump(cv, open(os.path.join(here, "curvas03.json"), "w", encoding="utf-8"), indent=0)
    FR = cuadros_a_render(cv)
    open(os.path.join(here, "cuadros03.txt"), "w").write(",".join(str(f) for f in FR))
    for e in ev:
        print("%6.3f s  f%6.2f  %-11s %.2f  %s" % (e["t"], e["cuadro"], e["tipo"], e["magnitud"], e["nota"]))
    for f in (0, 8, 9, 10, 11, 12, 13, 14, 15, 30, 48, 60, 62, 66, 70, 75, 80, 85, 90, 100, 110, 117, 125, 135, 149):
        c = cv[f]
        print("f%3d door %7.2f gap %5.1f vel %7.1f luz %.2f est %.2f cinta %+.2f trab %+.2f cam az %6.1f d %.3f foco %.2f" % (
            f, c["door"], c["gap_mm"], c["door_vel"], c["luz"], c["estudio"], c["cinta"], c["trabajo"], c["az"], c["dist"], c["foco"]))
    print("clic del iman %.3f s (f%.1f)" % (T_CLIC, T_CLIC * FPS))
    print("renders unicos: %d de %d cuadros" % (len(FR), N_FR))
