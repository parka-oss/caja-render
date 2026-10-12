"""Escena 01 "apertura" v3: caja-libro MG (caja03.py) + "Late la fabrica" con la nave TRABAJANDO en fase con los latidos.
Blender 5.1 / Cycles CPU. Arma la nave con ancla-caja/build3.py (sin tocarlo, por runpy) y encima:
  - luz de punto medio v2/v3 (luz.args), luz de la boca, cuna (spot en la planta baja), tarjeta de reflejo del foil
  - estudio -1 EV siguiendo la puerta (P1-3), profundidad de campo f/5,6 con foco que pasa de la puerta a la nave (P1-4)
  - trabajo: cortadora, planchas, costura (tela que avanza + operarias que acompanan el pedal), el que carga (P0-1)
v3.2 (2026-10-12, [XG·792d], CRITICO_v3 P0-1): recorrido de los OBJETOS en metros reales de la maqueta 1:32, no la
inclinacion de las figuras (esa queda en 7-8 grados):
  - cuchilla 0,72 m (22,5 mm de escena; v3.1 0,56 = 17,5 mm), plancha 0,76 m (23,75 mm, igual que v3.1)
  - tela: ademas del paso de transporte (va en profundidad: 0,75 px por paso a 1080, no se lee) se guia de costado con
    el golpe, hasta 0,30 m (9,4 mm) y nunca fuera de la tapa de la mesa (1,2 m): 20-25 mm no entran en la mesa
  - caja: CAE en cada golpe (curva carga), hasta 0,64 m (20 mm) y nunca por debajo del piso
  - sin rutas absolutas: las maquinas reales (--props 1) se buscan en $PROPS43_DIR; semilla por --seed (1022)
v3.1 sigue en esc03.py, sin tocar. Curvas: curvas03.py (no cambian; cambia solo la amplitud).
Uso:
  blender -b --factory-startup --python esc03.py -- --mode still --frame 135 --res 1 --samples 64 --out x.png  $(cat luz.args)
  blender -b --factory-startup --python esc03.py -- --mode anim --frames auto --res 0.25 --samples 6 --out dir/
"""
import sys, os, math, runpy, argparse, time

HERE = os.path.dirname(os.path.abspath(__file__))
ANCLA = os.path.normpath(os.path.join(HERE, "..", "..", "ancla-caja"))
sys.path.insert(0, HERE)
import curvas03 as CV

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="still")
ap.add_argument("--frame", type=int, default=135)
ap.add_argument("--frames", default="")
ap.add_argument("--res", type=float, default=1.0)
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--thr", type=float, default=0.01)
ap.add_argument("--out", default="")
ap.add_argument("--blend", default="")
ap.add_argument("--prac", type=float, default=2.6)
ap.add_argument("--amb", type=float, default=3.0)
ap.add_argument("--kint", type=float, default=0.4)
ap.add_argument("--wash", type=float, default=0.8)
ap.add_argument("--tkreb", type=float, default=4300.0)
ap.add_argument("--rebk", type=float, default=0.8)
ap.add_argument("--spot", type=float, default=72.0)
ap.add_argument("--sblend", type=float, default=0.35)
ap.add_argument("--pfrac", type=float, default=0.5)
ap.add_argument("--boca", type=float, default=3.0)
ap.add_argument("--tkboca", type=float, default=3600.0)
ap.add_argument("--rebtapa", type=float, default=0.0)
ap.add_argument("--mblur", type=int, default=1)
ap.add_argument("--cuna", type=float, default=8.0)
ap.add_argument("--cunay", type=float, default=0.10)
ap.add_argument("--cunaz", type=float, default=0.11)
ap.add_argument("--tkcuna", type=float, default=2900.0)
ap.add_argument("--linea", type=float, default=40.0)   # (v2) se ignora: la v3 usa --lin3
ap.add_argument("--lin3", type=float, default=5.0)     # emision de la linea v3 con luz(t) = 1 (a 6: R 246, luma 234 en f010)
ap.add_argument("--foil", type=float, default=60.0)    # W de la tarjeta de reflejo del foil
ap.add_argument("--fstop", type=float, default=5.6)
ap.add_argument("--pracboost", type=float, default=2.0)  # practicas al abrir (P1-3)
ap.add_argument("--props", type=int, default=0)   # 1 = maquinas de coser reales del bloque 43
ap.add_argument("--border", default="")
ap.add_argument("--kobj", type=float, default=2.0)    # v3.1: recorrido de los OBJETOS (cuchilla, plancha) x2 (CRITICO_v3 P0-1)
ap.add_argument("--ktela", type=float, default=2.0)   # v3.1: paso de la tela por golpe x2
ap.add_argument("--hasta", default="")                # v3.1: "06:50" -> no arranca un cuadro que terminaria despues (hora local)
ap.add_argument("--lista", default="")                # v3.1: --mode anim con lista explicita "0,9,10,..." (render_noche.sh)
ap.add_argument("--look", default="")
ap.add_argument("--corte_m", type=float, default=0.72)    # v3.2: recorrido de la cuchilla (m reales; x S = escena)
ap.add_argument("--plancha_m", type=float, default=0.76)  # v3.2: pasada de la plancha
ap.add_argument("--telax_m", type=float, default=0.30)    # v3.2: guia lateral de la tela por golpe (tope: la mesa)
ap.add_argument("--caja_m", type=float, default=0.0)      # v3.2: caida de la caja por golpe. 0 [XG·792d 10-12]: con figuras rigidas la caja se separaba de las manos y caia al piso en cada golpe (f135); queda en las manos, como v3.1
ap.add_argument("--seed", type=int, default=1022)         # v3.2: semilla fija de Cycles (igual que v3.1)
A = ap.parse_args(argv)

BUILD_ARGS = ["--stage", "full", "--variant", "pared", "--elev", "8", "--azim", "10", "--dist", "1.95", "--shiftx", "-0.05",
              "--door", "140", "--reb", "2", "--wash", str(A.wash), "--prac", str(A.prac), "--amb", str(A.amb),
              "--kint", str(A.kint), "--desat", "0.45", "--tkamb", "5600", "--tkreb", str(A.tkreb),
              "--res", str(A.res), "--samples", str(A.samples)]
t0 = time.time()
_old = sys.argv
sys.argv = [_old[0], "--"] + BUILD_ARGS
G = runpy.run_path(os.path.join(ANCLA, "build3.py"), run_name="__main__")
sys.argv = _old
print("BUILD_S %.1f" % (time.time() - t0))

import bpy
from mathutils import Vector, Matrix

sc = bpy.context.scene
coll = G["coll"]; light_col = G["light_col"]
PW, PD, PH, T = G["PW"], G["PD"], G["PH"], G["T"]
hinge = bpy.data.objects["bisagra"]
cam = sc.camera; cam_d = cam.data
S = G["S"]

# rebotes de piso de la v3 corridos adentro (v2: asomaban por delante de la boca)
YA_ = -PD / 2
for o in bpy.data.objects:
    if o.type == "LIGHT" and o.data.type == "AREA" and o.users_collection[0].name == "luces_int":
        half = max(o.data.size, o.data.size_y) / 2
        if o.location.y - half < YA_ + 0.003:
            o.location.y = YA_ + 0.003 + half

# ---------------------------------------------------------------- luz de punto medio v2/v3
for o in coll("luces_int").objects:
    if o.type != "LIGHT":
        continue
    if o.data.type == "SPOT":
        o.data.spot_size = math.radians(A.spot); o.data.spot_blend = A.sblend
    elif o.data.type == "POINT" and o.name.endswith("_p"):
        o.data.energy *= A.pfrac
    elif o.data.type == "AREA" and o.name.startswith("reb_"):
        o.data.energy *= A.rebk
rto = bpy.data.objects.get("reb_tapa")
if rto:
    rto.data.energy *= A.rebtapa

bd = bpy.data.lights.new("boca_nave", "AREA"); bd.shape = "RECTANGLE"
bd.size = PW - 2 * T - 0.004; bd.size_y = PH - 2 * T - 0.004
bd.energy = A.boca; bd.color = light_col(A.tkboca)
bo = bpy.data.objects.new("boca_nave", bd)
bo.location = (0, -PD / 2 - 0.0002, PH / 2); bo.rotation_euler = (math.radians(-90), 0, 0)
coll("luces_boca").objects.link(bo)
for attr in ("visible_camera", "visible_glossy", "visible_transmission"):
    try: setattr(bo, attr, False)
    except Exception as e: print(attr, e)
rxb = bpy.data.collections.new("rx_boca")
rxb.children.link(coll("estudio")); rxb.children.link(coll("caja"))
try:
    bo.light_linking.receiver_collection = rxb
    for ch in rxb.collection_children: ch.light_linking.link_state = "INCLUDE"
except Exception as e:
    print("rx_boca:", e)

# ---------------------------------------------------------------- caja-libro v3
import caja03
CJ = caja03.aplicar(G, A, light_col)
cinta_k, linea_str = CJ["cinta_key"], CJ["linea_str"]
cuelga_k = CJ["cuelga_key"]

cu_d = bpy.data.lights.new("cuna_luz", "SPOT"); cu_d.energy = A.cuna; cu_d.color = light_col(A.tkcuna)
cu_d.spot_size = math.radians(120); cu_d.spot_blend = 0.2; cu_d.shadow_soft_size = 0.012
cu_o = bpy.data.objects.new("cuna_luz", cu_d); coll("luces_boca").objects.link(cu_o)
cu_o.location = (0.0, A.cunay, A.cunaz)
cu_o.rotation_euler = Vector((0.0, -0.46, -0.12)).normalized().to_track_quat("-Z", "Y").to_euler()
try: cu_o.visible_camera = False
except Exception: pass
rxc2 = bpy.data.collections.new("rx_cuna"); rxc2.children.link(coll("estudio"))   # v3: el papel negro de la puerta NO (la cuna lo encendia naranja)
try:
    cu_o.light_linking.receiver_collection = rxc2
    for ch in rxc2.collection_children: ch.light_linking.link_state = "INCLUDE"
    for co in rxc2.collection_objects: co.light_linking.link_state = "INCLUDE"
except Exception as e:
    print("rx_cuna:", e)
CUNA_W = cu_d.energy
BOCA_W = bd.energy

# ---------------------------------------------------------------- camara / foco
LOOK = Vector((0.0, 0.0, PH / 2))


def cam_pose(f):
    az, el, d, sx, sy = CV.cam(f)
    a_, e_ = math.radians(az), math.radians(el)
    loc = LOOK + Vector((math.sin(a_) * math.cos(e_), -math.cos(a_) * math.cos(e_), math.sin(e_))) * d
    return loc, sx, sy


# tarjeta de reflejo del foil (PACKAGING 15, ajuste B): un destello del MG cuando la puerta pasa por ~28 grados
f_fl = next(f for f in range(CV.N_FR) if CV.door(f / CV.FPS) >= 28.0)
th = math.radians(CV.door(f_fl / CV.FPS))
n_door = Vector((-math.sin(th), -math.cos(th), 0.0))
hloc = Vector(hinge.location)
P_mg = hloc + Vector((math.cos(th), -math.sin(th), 0.0)) * (PW / 2) + Vector((0, 0, CJ["zc"])) + n_door * 0.002
cl, _, _ = cam_pose(f_fl)
v = (cl - P_mg).normalized()
r = 2 * v.dot(n_door) * n_door - v
card_c = P_mg + r * 1.3
if card_c.z < 0.30:          # que no quede debajo del piso: sube y la tarjeta se hace alta
    card_c.z = 0.30
fd = bpy.data.lights.new("tarjeta_foil", "AREA"); fd.shape = "RECTANGLE"; fd.size = 0.6; fd.size_y = 0.9; fd.energy = A.foil
fd.color = light_col(5200)
fo_ = bpy.data.objects.new("tarjeta_foil", fd); coll("estudio_luces").objects.link(fo_)
fo_.location = card_c
fo_.rotation_euler = (P_mg - card_c).normalized().to_track_quat("-Z", "Y").to_euler()
for attr, val in (("visible_camera", False), ("visible_diffuse", False), ("visible_transmission", False), ("visible_shadow", False)):
    try: setattr(fo_, attr, val)
    except Exception as e: print("tarjeta", attr, e)
rxt = bpy.data.collections.new("rx_tarjeta"); rxt.objects.link(CJ["puerta"])
try:
    fo_.light_linking.receiver_collection = rxt
    for co in rxt.collection_objects: co.light_linking.link_state = "INCLUDE"
except Exception as e:
    print("rx_tarjeta:", e)
print("TARJETA_FOIL f%d puerta %.1f grados -> centro (%.2f, %.2f, %.2f)" % (f_fl, math.degrees(th), *card_c))

# estudio que baja al abrir
ST_L = [(o, o.data.energy) for o in bpy.data.objects if o.type == "LIGHT" and o.users_collection[0].name == "estudio_luces" and o.name != "tarjeta_foil"]
bgn = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
BG0 = bgn.inputs[1].default_value
PRAC_L = [(o, o.data.energy) for o in coll("luces_int").objects if o.type == "LIGHT"]
print("estudio:", [o.name for o, _ in ST_L], "mundo", BG0)

# ---------------------------------------------------------------- props reales (bloque 43): maquina de coser industrial
# v3.2: sin ruta absoluta. En la laptop: WEB MAYORISTA/Diseño/higgsfield/43-fabrica-3d-ia/props/render (solo con --props 1)
PROPS43 = os.environ.get("PROPS43_DIR", "")
if A.props and not PROPS43:
    raise SystemExit("--props 1 necesita la variable PROPS43_DIR con la carpeta de hunyuan_maquina_30k.glb")
if A.props:
    import_gltf = G["import_gltf"]
    OCULTAR = ("_tapa", "_pata", "_pata2", "_cajon", "_motor", "_pedal", "_base", "_col", "_brazo", "_cab", "_aguja", "_prensatela",
               "_volante", "_correa", "_varilla", "_guia")
    stations = sorted({o.name[:-len("_prenda")] for o in bpy.data.objects if o.name.startswith("costura_") and o.name.endswith("_prenda")})
    for nm in stations:
        st = bpy.data.objects[nm]
        for o in list(bpy.data.objects):
            if o.name.startswith(nm + "_") and (any(o.name == nm + suf or o.name.startswith(nm + suf + ".") for suf in OCULTAR) or o.name.startswith(nm + "_cono")):
                o.hide_render = True; o.hide_viewport = True
                for c in o.children_recursive:
                    c.hide_render = True; c.hide_viewport = True
        root, new, dim = import_gltf(os.path.join(PROPS43, "hunyuan_maquina_30k.glb"), target=1.2 * S)
        root.parent = st; root.matrix_parent_inverse.identity(); root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0)
        for o in new:   # repintado a la maqueta: el esmalte de las maquinas de build3, sin la textura de la IA
            if o.type == "MESH":
                o.data.materials.clear(); o.data.materials.append(G["M_white"])
    bpy.context.view_layer.update()
    dep = bpy.context.evaluated_depsgraph_get()
    for nm in stations:   # la prenda, la pila y la tijerita apoyan en la mesa real (altura medida con un rayo)
        st = bpy.data.objects[nm]
        top = st.matrix_world @ Vector((0.10 * S, -0.20 * S, 2.0 * S))
        hit, loc_, *_ = sc.ray_cast(dep, top, Vector((0, 0, -1)))
        if not hit:
            continue
        dz = loc_.z - (st.matrix_world.translation.z + 0.76 * S + 0.0175 * S)
        for o in bpy.data.objects:
            if o.name.startswith((nm + "_prenda", nm + "_pila", nm + "_tijerita")) and o.parent == st:
                o.location.z += dz
        print("PROPS43", nm, "mesa real %+.2f mm (modelo) sobre la de build3" % (dz * 1000))
    print("PROPS43: %d maquinas de coser" % len(stations))

# ---------------------------------------------------------------- trabajo en la nave (piezas rigidas)
bpy.context.view_layer.update()


def adopt(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


WORK = []   # (obj, rest matrix_basis, fn(t) -> Matrix delta en el espacio del padre del objeto)


def _rest(o):
    return o.matrix_basis.copy()


def lean_fig(name, hp, amp_deg, fn):
    """Inclina una figura (raiz en los pies, escala S) alrededor de un punto a hp m (reales) de altura."""
    o = bpy.data.objects.get(name)
    if o is None:
        print("falta figura", name); return
    rest = _rest(o)
    p = Vector((0, 0, hp))
    def m(t, rest=rest, p=p):
        a = -math.radians(amp_deg) * fn(t)
        return rest @ Matrix.Translation(p) @ Matrix.Rotation(a, 4, "X") @ Matrix.Translation(-p)
    WORK.append((o, m))


def slide(name, dvec, fn):
    o = bpy.data.objects.get(name)
    if o is None:
        print("falta", name); return
    rest = _rest(o); d = Vector(dvec)
    def m(t, rest=rest, d=d):
        return Matrix.Translation(d * fn(t)) @ rest
    WORK.append((o, m))


R_ = lambda x: x * S
# 1) cortadora en la mesa de corte: va y viene sobre el tendido en cada golpe; la operaria acompana
slide("corte_a_cortadora", (R_(A.corte_m), 0, 0), lambda t: CV.trabajo(t))   # v3.2: 0,72 m (antes 0,28 x kobj)
lean_fig("corte_a_op0", 1.0, 7.0, lambda t: CV.trabajo(t, 0.03))
lean_fig("corte_a_op1", 1.0, 4.0, lambda t: CV.trabajo(t, 0.10))
# 2) planchas: pasada sobre la prenda en cada golpe (una a contratiempo de la otra), el cuerpo acompana
for i, fase in ((0, 0.0), (1, 0.2)):
    slide("plancha%d" % i, (-R_(A.plancha_m), 0, 0), lambda t, fase=fase: CV.trabajo(t, fase))
    slide("plancha_manguera%d" % i, (-R_(A.plancha_m), 0, 0), lambda t, fase=fase: CV.trabajo(t, fase))
    lean_fig("op_plancha%d" % i, 1.0, 6.0, lambda t, fase=fase: CV.trabajo(t, fase + 0.02))
# 3) costura: la tela avanza un punto por golpe bajo el prensatela y la operaria se inclina con el pedal
n_cos = 0
TELA = []
for o in list(bpy.data.objects):
    if o.name.startswith("costura_") and o.name.endswith("_prenda"):
        root = o.parent
        fase = 0.03 * (n_cos % 3)
        rest = _rest(o)
        # v3.1 (CRITICO_v3 P2-4): la tela frena antes del borde de atras de la tapa (1,2 x 0,55 m, centrada en el puesto):
        # cuenta cuantos pasos enteros entran entre su borde de atras (bbox en coords del puesto) y el canto menos 1 cm.
        paso = R_(0.03 * A.ktela)
        ymax = max((rest @ Vector(c_)).y for c_ in o.bound_box)
        libre = R_(0.55 / 2 - 0.01) - ymax
        nmax = max(0, int(libre / paso))
        # v3.2: guia lateral (X del puesto) con el golpe; tope = canto de la tapa menos 1 cm, del lado que va (amp) y del
        # que vuelve en la anticipacion (0,2 x amp). Signo hacia el lado con mas lugar.
        xs_ = [(rest @ Vector(c_)).x for c_ in o.bound_box]
        lib_pos = R_(1.2 / 2 - 0.01) - max(xs_); lib_neg = min(xs_) + R_(1.2 / 2 - 0.01)
        sgn = 1.0 if lib_pos >= lib_neg else -1.0
        lib_go, lib_back = (lib_pos, lib_neg) if sgn > 0 else (lib_neg, lib_pos)
        ampx = max(0.0, min(R_(A.telax_m), lib_go, lib_back / 0.2))
        TELA.append((o.name, ymax / S, libre / S, nmax, sgn * ampx / S))
        def mpr(t, rest=rest, fase=fase, paso=paso, nmax=nmax, ax=sgn * ampx):   # transporte hacia atras + guia lateral
            return Matrix.Translation(Vector((0, paso, 0)) * min(float(nmax), CV.avance(t, fase))
                                      + Vector((ax, 0, 0)) * CV.trabajo(t, fase)) @ rest
        WORK.append((o, mpr))
        nm = o.name[:-len("_prenda")] + "_op"
        lean_fig(nm, 0.5, 8.0, lambda t, fase=fase: CV.trabajo(t, fase))
        n_cos += 1
# 4) el que carga: baja la caja al pallet y se endereza (la caja va en las manos)
cj = bpy.data.objects.get("caja_en_mano"); fc = bpy.data.objects.get("op_caja")
if cj and fc:
    adopt(cj, fc)
    lean_fig("op_caja", 0.05, 8.0, CV.carga)   # v3.1: pivote en los tobillos (antes 0,9 m: los pies patinaban 6,6 px) y 8 grados (antes 16)
    # v3.2: la caja CAE en cada golpe (misma curva carga, solo la bajada) hasta 0,64 m y nunca por debajo del piso + 1 cm
    bpy.context.view_layer.update()
    zbot = min((cj.matrix_world @ Vector(c_)).z for c_ in cj.bound_box)
    caida = max(0.0, min(R_(A.caja_m), zbot - fc.matrix_world.translation.z - R_(0.01)))
    slide("caja_en_mano", (0, 0, -caida), CV.carga)
    print("CAJA_CAE %.3f m reales (%.1f mm de escena)" % (caida / S, caida * 1000), flush=True)
# 5) control: sacude la camisa (acompana el golpe, chico)
cm_ = bpy.data.objects.get("camisa_en_mano"); fcn = bpy.data.objects.get("op_control")
if cm_ and fcn:
    adopt(cm_, fcn)
    lean_fig("op_control", 1.0, 4.0, lambda t: CV.trabajo(t, 0.15))
rp = bpy.data.objects.get("rollo_hombro_piv"); fr_ = bpy.data.objects.get("op_rollo")
if rp and fr_:
    adopt(rp, fr_)
    lean_fig("op_rollo", 1.0, 3.0, lambda t: CV.trabajo(t, 0.2))
for nm_, ym_, lb_, nx_, ax_ in TELA:
    print("TELA %s borde_atras %+.3f m libre %.3f m -> %d pasos; guia lateral %+.3f m" % (nm_, ym_, lb_, nx_, ax_))
print("TRABAJO: %d piezas animadas (costura %d)" % (len(WORK), n_cos))

# ---------------------------------------------------------------- animacion por cuadro
try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
except Exception as e:
    print("interp:", e)
sc.render.fps = CV.FPS
sc.frame_start, sc.frame_end = 0, CV.N_FR - 1
cam_d.dof.use_dof = True
cam_d.dof.aperture_fstop = A.fstop
P_NAVE = Vector((0.0, 0.0, PH / 2))


def pose(f, key=False):
    t = f / CV.FPS
    th_ = CV.door(t)
    hinge.rotation_euler = (0, 0, -math.radians(th_))
    loc, sx, sy = cam_pose(f)
    cam.location = loc
    cam.rotation_euler = (LOOK - loc).normalized().to_track_quat("-Z", "Y").to_euler()
    cam_d.shift_x, cam_d.shift_y = sx, sy
    # foco: cara de la puerta cerrada -> planta de costura
    fwd = (LOOK - loc).normalized()
    d_door = (Vector((0, -PD / 2 - 0.004, PH / 2)) - loc).dot(fwd)
    d_nave = (P_NAVE - loc).dot(fwd)
    k = CV.foco(t)
    cam_d.dof.focus_distance = d_door + (d_nave - d_door) * k
    L_ = CV.luz(t)
    bd.energy = BOCA_W * L_
    cu_d.energy = CUNA_W * L_
    # linea: sube con la luz y se apaga cuando la puerta abre (ahi la reemplaza la boca)
    p_ = min(1.0, max(0.0, (th_ - 3.0) / 5.0))
    linea_str.default_value = A.lin3 * L_ * (1.0 - p_ * p_ * (3 - 2 * p_))
    cinta_k.value = CV.cinta(t)
    cuelga_k.value = CV.cuelga(t)
    es = CV.estudio(t)
    for o, e0 in ST_L:
        o.data.energy = e0 * es
    bgn.inputs[1].default_value = BG0 * es
    pb = 1.0 + (A.pracboost - 1.0) * (1.0 - es) / 0.6
    for o, e0 in PRAC_L:
        o.data.energy = e0 * pb
    for o, m in WORK:
        o.matrix_basis = m(t)
    if key:
        hinge.keyframe_insert("rotation_euler", frame=f)
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
        cam_d.keyframe_insert("shift_x", frame=f); cam_d.keyframe_insert("shift_y", frame=f)
        cam_d.dof.keyframe_insert("focus_distance", frame=f)
        bd.keyframe_insert("energy", frame=f); cu_d.keyframe_insert("energy", frame=f)
        linea_str.keyframe_insert("default_value", frame=f)
        cinta_k.keyframe_insert("value", frame=f)
        cuelga_k.keyframe_insert("value", frame=f)
        bgn.inputs[1].keyframe_insert("default_value", frame=f)
        for o, _ in ST_L + PRAC_L:
            o.data.keyframe_insert("energy", frame=f)
        for o, _ in WORK:
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)


for f in range(0, CV.N_FR):
    pose(f, key=True)

# ---------------------------------------------------------------- render
sc.cycles.samples = A.samples
sc.cycles.adaptive_threshold = A.thr
sc.cycles.seed = A.seed
sc.cycles.use_animated_seed = False
sc.render.use_motion_blur = bool(A.mblur)
sc.render.motion_blur_shutter = 0.5
sc.render.use_persistent_data = True
try:
    sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    sc.cycles.denoising_prefilter = "ACCURATE"
except Exception as e:
    print("denoise:", e)
if A.look:
    try: sc.view_settings.look = A.look
    except TypeError as e: print("looks:", e)
if A.border:
    x0, x1, y0, y1 = [float(v) for v in A.border.split(",")]
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = x0, x1, y0, y1
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=A.blend)
from bpy_extras.object_utils import world_to_camera_view


def puntos(fr):
    """Pixeles (x, y desde arriba) de los puntos que mide medir03.py."""
    bpy.context.view_layer.update()
    rx = int(sc.render.resolution_x * sc.render.resolution_percentage / 100)
    ry = int(sc.render.resolution_y * sc.render.resolution_percentage / 100)
    Mh = hinge.matrix_world
    h = caja03.TC / 2
    YDI = -PD / 2 - caja03.YG
    pts = {"esq": Vector((-PW / 2, YDI - caja03.TC, PH * 0.40)), "esq_alta": Vector((-PW / 2, YDI - caja03.TC, PH * 0.75)),
           "tapa": Mh @ Vector((PW * 0.5, 0.0, PH)), "mg": Mh @ Vector((PW / 2, -h, CJ["zc"])),
           "mg_r": Mh @ Vector((PW / 2 + CJ["W_MG"] / 2, -h, CJ["zc"])),
           "forro": Mh @ Vector((PW / 2, h, PH / 2)), "nave": Vector((0, 0, PH / 2)), "nave_baja": Vector((0, 0, PH * 0.2)),
           "nave_alta": Vector((0, 0, PH * 0.8)), "base": Vector((0.0, -PD / 2, 0.0))}
    print("LUCES f%d estudio %s mundo %.3f" % (fr, " ".join("%s=%.1f" % (o.name, o.data.energy) for o, _ in ST_L), bgn.inputs[1].default_value), flush=True)
    for k_, w in pts.items():
        c = world_to_camera_view(sc, cam, w)
        print("PX f%d %s %.1f %.1f %.3f" % (fr, k_, c.x * rx, (1 - c.y) * ry, c.z), flush=True)


def _px(w):
    rx = int(sc.render.resolution_x * sc.render.resolution_percentage / 100)
    ry = int(sc.render.resolution_y * sc.render.resolution_percentage / 100)
    c = world_to_camera_view(sc, cam, w)
    return c.x * rx, (1 - c.y) * ry


if A.mode == "medir":   # --frames "107,108,109,129,135": pixeles de la cinta y de los objetos de trabajo, sin render
    NOMS = ["corte_a_cortadora", "plancha0", "plancha1", "caja_en_mano", "op_caja"] + sorted(
        o.name for o in bpy.data.objects if o.name.startswith("costura_") and o.name.endswith("_prenda"))
    for fr in [int(x) for x in A.frames.split(",")]:
        sc.frame_set(fr); pose(fr)
        dg = bpy.context.evaluated_depsgraph_get()
        if fr == int(A.frames.split(",")[0]):
            print("CINTAS", [(o.name, o.hide_render, o.data.shape_keys and [k.name for k in o.data.shape_keys.key_blocks]) for o in bpy.data.objects if o.name.startswith("cinta")], "cuelga", cuelga_k.value, flush=True)
        for vv in (0.0, 1.0):
            cuelga_k.value = vv; bpy.context.view_layer.update(); dg2 = bpy.context.evaluated_depsgraph_get()
            o2 = CJ["cinta"].evaluated_get(dg2); m2 = o2.to_mesh()
            print("TEST cuelga", vv, "use_relative", CJ["cinta"].data.shape_keys.use_relative, "mute", cuelga_k.mute, "rel", cuelga_k.relative_key.name,
                  "npt", len(m2.vertices), "xmax_local", max(v.co.x for v in m2.vertices), "zmin_local", min(v.co.z for v in m2.vertices), flush=True)
            M2 = o2.matrix_world
            pp = sorted(((_px(M2 @ v.co)[0], v.co.x) for v in m2.vertices))
            print("TEST px xmin %.1f (x_local %.4f)  xmax %.1f (x_local %.4f)  PW %.4f" % (pp[0][0], pp[0][1], pp[-1][0], pp[-1][1], PW), flush=True)
            o2.to_mesh_clear()
        cuelga_k.value = CV.cuelga(fr / CV.FPS); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        ob = CJ["cinta"].evaluated_get(dg)
        me = ob.to_mesh(); Mw = ob.matrix_world
        ps = [_px(Mw @ v.co) for v in me.vertices]; ob.to_mesh_clear()
        xs = [q[0] for q in ps]; ys = [q[1] for q in ps]
        rx = sc.render.resolution_x * sc.render.resolution_percentage / 100
        ry = sc.render.resolution_y * sc.render.resolution_percentage / 100
        print("CINTA f%d x %.1f..%.1f y %.1f..%.1f margen_min %.1f px" % (fr, min(xs), max(xs), min(ys), max(ys),
              min(min(xs), rx - max(xs), min(ys), ry - max(ys))), flush=True)
        for nm in NOMS:
            o = bpy.data.objects.get(nm)
            if o is None:
                continue
            e = o.evaluated_get(dg); Mw = e.matrix_world
            c = sum((Vector(b) for b in e.bound_box), Vector()) / 8
            x, y = _px(Mw @ c)
            print("OBJ f%d %s %.2f %.2f" % (fr, nm, x, y), flush=True)
            if nm.startswith("costura_"):
                pa = R_(0.03 * A.ktela)
                x2, y2 = _px(Mw @ (c + (e.matrix_world.inverted().to_3x3() @ (e.parent.matrix_world.to_3x3() @ Vector((0, pa, 0))))))
                print("PASO f%d %s %.2f px por paso" % (fr, nm, math.hypot(x2 - x, y2 - y)), flush=True)
elif A.mode == "still":
    for fr in [int(x) for x in str(A.frame).split(",")] if False else [A.frame]:
        sc.frame_set(fr); pose(fr)
        sc.render.filepath = A.out
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("RENDER_OK %s frame %d %.1f s" % (A.out, fr, time.time() - t1), flush=True)
elif A.mode == "stills":   # --frames "0,12,62,85,135" --out prefijo
    for fr in [int(x) for x in A.frames.split(",")]:
        sc.frame_set(fr); pose(fr); puntos(fr)
        p = "%s_f%03d.png" % (A.out, fr)
        if os.path.exists(p):
            continue
        sc.render.filepath = p
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("RENDER_OK %s frame %d %.1f s" % (p, fr, time.time() - t1), flush=True)
elif A.mode == "anim":
    os.makedirs(A.out, exist_ok=True)
    if A.lista:
        FR = [int(x) for x in A.lista.split(",") if x.strip()]
    elif A.frames == "auto":
        FR = [int(x) for x in open(os.path.join(HERE, "cuadros03.txt")).read().split(",")]
    else:
        FR = []
        for tr in A.frames.split(","):
            ab, st = tr.split(":"); a_, b_ = ab.split("-")
            FR += list(range(int(a_), int(b_) + 1, int(st)))
    print("CUADROS_A_RENDER", len(FR), flush=True)
    import datetime as _dt
    LIM = None
    if A.hasta:
        hh, mm = [int(x) for x in A.hasta.split(":")]
        now = _dt.datetime.now(); LIM = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if LIM <= now:
            LIM += _dt.timedelta(days=1)
        print("HASTA", LIM.isoformat(timespec="minutes"), flush=True)
    durs = []
    for f in FR:
        p = os.path.join(A.out, "f%04d.png" % f)
        if os.path.exists(p):
            continue
        if os.path.exists(os.path.join(A.out, "PAUSA")):      # render_noche.sh pausar: termina el cuadro en curso y sale
            print("PAUSA antes de f%d" % f, flush=True); break
        if LIM is not None:
            est = max(durs) if durs else 0.0
            if _dt.datetime.now() + _dt.timedelta(seconds=est) > LIM:
                print("HASTA_CORTE antes de f%d (estimado %.0f s)" % (f, est), flush=True); break
        sc.frame_set(f)
        tmp = p[:-4] + "_tmp.png"            # escritura atomica: un cuadro cortado a mitad nunca queda con el nombre final
        sc.render.filepath = tmp
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, p)
        durs.append(time.time() - t1)
        print("FRAME_OK %d %.1f s" % (f, time.time() - t1), flush=True)
    print("ANIM_OK")
