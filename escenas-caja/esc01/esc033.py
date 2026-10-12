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
ap.add_argument("--giro_corte", type=float, default=25.0)    # v3.3: giro del tronco de la operaria que lleva la cortadora (grados)
ap.add_argument("--giro_plancha", type=float, default=22.0)  # v3.3: giro del tronco de las planchadoras
ap.add_argument("--giro_costura", type=float, default=14.0)  # v3.3: giro del tronco de las costureras (la pieza va con las manos)
ap.add_argument("--flexion_caja", type=float, default=28.0)  # v3.3: flexion de cadera del que carga (baja la caja con el cuerpo)
ap.add_argument("--tela_marron", type=float, default=0.5)    # v3.3: mezcla de la foto MT-1022 con su fondo marron (0 = foto)
ap.add_argument("--muestras_nave", type=int, default=128)    # v3.3 (CRITICO_v32 P1-2): muestras desde f84 (la nave); antes, --samples
ap.add_argument("--desde_nave", type=int, default=84)
ap.add_argument("--obturador_puerta", type=float, default=1.0)   # v3.3 (P2-1): motion blur en f95-100 (la puerta de canto en f98)
ap.add_argument("--seed", type=int, default=1022)         # v3.2: semilla fija de Cycles (igual que v3.1)
ap.add_argument("--fin", type=int, default=212)             # v3.3 (PLAN 55 §1): ultimo cuadro animado; la nave sigue trabajando
ap.add_argument("--caja_z0", type=float, default=0.72)      # v3.3: zona de flexion del que carga (m reales; pivote = (z0+z1)/2 = 0,81: con 0,94 el fondo de la caja iba hacia atras y se hundia 2 cm mas en los muslos)
ap.add_argument("--caja_z1", type=float, default=0.90)
ap.add_argument("--caja_espalda", default="0.95,1.10")   # v3.3: rampa de pesos de la espalda del que carga ("" = igual que el frente)
ap.add_argument("--mascara", default="")                    # v3.3 (PLAN 55 §1): carpeta de la mascara del interior (AOV); "" = sin
A = ap.parse_args(argv)
# v3.3 [XG·792d] (PLAN 55 §1, fuente de 3-4 s para la IA): la nave sigue trabajando hasta A.fin con el MISMO ciclo
# (un golpe cada PERIODO_NAVE). Los golpes nuevos empiezan en 5,20 s; su anticipacion (t >= 5,10 s = f153, fases >= 0)
# no toca f0-149. La camara queda quieta despues de f149 (cam() satura en N_FR) y la puerta ya esta en reposo.
N_ANIM = max(CV.N_FR, A.fin + 1)
_nb = int(math.ceil((N_ANIM / CV.FPS + 0.5 - CV.T_BEAT2) / CV.PERIODO_NAVE))
_b0 = CV.BEATS
CV.BEATS = CV.T_PULSOS + (CV.T_BEAT2,) + tuple(round(CV.T_BEAT2 + CV.PERIODO_NAVE * k, 4) for k in range(1, max(8, _nb + 1)))
assert CV.BEATS[:len(_b0)] == _b0

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

# ---------------------------------------------------------------- trabajo en la nave v3.3 [XG·792d] (CRITICO_v32 P0-N1)
# Las figuras son mallas horneadas sin rig (figuras3.blend: sin armature ni grupos). Via (b) del critico: el CUERPO
# acompana con pivote en la cadera. Cada figura animada recibe un armature de 1 hueso ("tronco") que gira SOLO el tronco:
# piernas con peso 0 (pies quietos: cero patinado), rampa de peso suave en la cintura y brazos con peso 1 (rigidos con el
# pecho). El objeto de trabajo sigue la MISMA matriz D(t) del hueso: la mano no se separa del mango por construccion.
#   - giro (eje vertical por la cadera): plancha, cuchilla, costura, mesa de corte, control, rollo -> las manos no cambian
#     de altura: la plancha y la cuchilla siguen apoyadas.
#   - flexion (eje lateral por la cadera): el que carga baja la caja con el cuerpo.
bpy.context.view_layer.update()

WORK = []    # (obj, fn(t) -> matrix_basis)
BONES = []   # (pose_bone, ML^-1, ML, D(t))
RIGS = {}    # nombre de figura -> dict(D=fn, P=pivote, body=obj, fig=root)
FOLLOW = {}  # objeto -> figura (para medir el contacto)


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def rig_tronco(name, kind, amp_deg, fn, z0, z1, arm_y=0.20, arm_z=0.80, py=0.0, espalda=None):
    """Armature de 1 hueso con pivote P = (0, py, (z0+z1)/2) en coords de la figura (metros, mira a +y)."""
    fo = bpy.data.objects.get(name); body = bpy.data.objects.get(name + "_cuerpo")
    if fo is None or body is None:
        print("falta figura", name); return None
    body.data = body.data.copy()          # la malla es compartida por pose: los pesos van en una copia propia
    vg = body.vertex_groups.new(name="tronco")
    # v3.3 [XG·792d]: la malla de figuras3.blend trae pesos viejos en el indice de grupo 0 (sin nombre, de su rig de origen).
    # El grupo nuevo toma ese indice y los heredaba: pies y tobillos giraban hasta 25 % con el tronco (pie levantado en f135).
    vg.remove([v.index for v in body.data.vertices])
    for v in body.data.vertices:
        x, y, z = v.co
        a0, a1 = z0, z1
        if espalda:   # v3.3: la cola y la parte de atras de los muslos no rotan con el pivote bajo (se iban hacia atras y arriba)
            ty = _smooth((0.05 - y) / 0.15); a0 = z0 + (espalda[0] - z0) * ty; a1 = z1 + (espalda[1] - z1) * ty
        w = max(_smooth((z - a0) / (a1 - a0)), _smooth((y - arm_y + 0.05) / 0.10) * _smooth((z - arm_z) / 0.08))
        if w > 1e-4:
            vg.add([v.index], w, "REPLACE")
    ad = bpy.data.armatures.new(name + "_rig"); ao = bpy.data.objects.new(name + "_rig", ad)
    coll("interior").objects.link(ao); ao.parent = fo; ao.matrix_parent_inverse.identity()
    P = Vector((0.0, py, (z0 + z1) / 2))
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ad.edit_bones.new("tronco"); eb.head = P; eb.tail = P + Vector((0, 0, 0.3)); eb.roll = 0.0
    bpy.ops.object.mode_set(mode="OBJECT")
    md = body.modifiers.new("tronco", "ARMATURE"); md.object = ao; md.use_vertex_groups = True
    pb = ao.pose.bones["tronco"]; pb.rotation_mode = "QUATERNION"
    ML = ad.bones["tronco"].matrix_local.copy()
    ax = "Z" if kind == "giro" else "X"
    sg = 1.0 if kind == "giro" else -1.0      # flexion: Rx negativo = el pecho va hacia adelante y abajo
    def D(t, P=P, ax=ax, a0=math.radians(amp_deg) * sg):
        return Matrix.Translation(P) @ Matrix.Rotation(a0 * fn(t), 4, ax) @ Matrix.Translation(-P)
    BONES.append((pb, ML.inverted(), ML, D))
    RIGS[name] = dict(D=D, P=P, body=body, fig=fo, kind=kind, amp=amp_deg)
    return D


def follow(oname, fig_name):
    """El objeto sigue la matriz del tronco de la figura (en mundo: F @ D(t) @ F^-1 @ M0)."""
    o = bpy.data.objects.get(oname); rg = RIGS.get(fig_name)
    if o is None or rg is None:
        print("falta", oname, fig_name); return
    bpy.context.view_layer.update()
    F = rg["fig"].matrix_world.copy(); Fi = F.inverted(); M0 = o.matrix_world.copy()
    PP = (o.parent.matrix_world @ o.matrix_parent_inverse) if o.parent else Matrix.Identity(4)
    PPi = PP.inverted(); D = rg["D"]
    def m(t):
        return PPi @ (F @ D(t) @ Fi @ M0)
    WORK.append((o, m))


R_ = lambda x: x * S

# 1) mesa de corte: la cortadora la lleva la operaria 0 con las dos manos en la manija (pose "inspect": manos a 1,30 m,
#    la altura de la manija). Antes estaba en pose "lean" (manos en la tela, a 0,4 m de la manija) y la cuchilla iba sola.
fo0 = bpy.data.objects.get("corte_a_op0"); sup = bpy.data.objects.get("op_supervisora")
cut = bpy.data.objects.get("corte_a_cortadora"); tend = bpy.data.objects.get("corte_a_tendido")
if fo0 and sup and cut and tend:
    b0 = bpy.data.objects["corte_a_op0_cuerpo"]
    b0.data = bpy.data.objects["op_supervisora_cuerpo"].data
    for k in list(fo0.keys()):
        if k.startswith(("mano", "hombro", "rollo", "altura")):
            del fo0[k]
    for k in sup.keys():
        if k.startswith(("mano", "hombro", "altura")):
            fo0[k] = sup[k]
    bpy.context.view_layer.update()
    mR, mL = Vector(fo0["mano_R"]), Vector(fo0["mano_L"])
    zbar = min(fo0["mano_R_zmin"], fo0["mano_L_zmin"]) - 0.012       # la manija (r 1,2 cm) queda tocando las palmas
    yaw_f = fo0.matrix_world.to_euler().z
    man = bpy.data.objects[cut.name + "_manija"]; base = bpy.data.objects[cut.name + "_base"]
    tb = [tend.matrix_world @ Vector(c_) for c_ in tend.bound_box]
    TX0, TX1 = min(p.x for p in tb), max(p.x for p in tb); TY0, TY1 = min(p.y for p in tb), max(p.y for p in tb)
    loc0 = fo0.location.copy(); fwd = fo0.matrix_world.to_3x3().normalized() @ Vector((0, 1, 0)); fwd.z = 0; fwd.normalize()
    best = None
    for k in range(0, 40):    # se acerca a la mesa de a 1 cm hasta que la base de la cortadora apoya entera en el tendido
        fo0.location = loc0 + fwd * (R_(0.01) * k)
        bpy.context.view_layer.update()
        hc = fo0.matrix_world @ Vector(((mR.x + mL.x) / 2, (mR.y + mL.y) / 2, zbar))
        cut.rotation_euler = (0, 0, yaw_f + math.pi)
        bpy.context.view_layer.update()
        Rc = cut.matrix_world.to_3x3().normalized()
        cut.location = Vector((hc.x, hc.y, cut.location.z)) - Rc @ Vector((0, R_(0.102), 0))
        bpy.context.view_layer.update()
        corners = [base.matrix_world @ Vector(c_) for c_ in base.bound_box]
        if all(TX0 + R_(0.02) < p.x < TX1 - R_(0.02) and TY0 + R_(0.02) < p.y < TY1 - R_(0.02) for p in corners):
            best = k; break
    man.location = (0.0, R_(0.102), hc.z - cut.location.z)
    man.scale = (1.0, 1.0, (abs(mR.x - mL.x) + 0.10) / 0.18)            # el eje del cilindro es su z local
    bpy.context.view_layer.update()
    print("CORTE op0 -> pose inspect, %s cm hacia la mesa; manija a %.3f m del piso, largo %.2f m" % (
        best, (hc.z - fo0.matrix_world.translation.z) / S, abs(mR.x - mL.x) + 0.10), flush=True)
rig_tronco("corte_a_op0", "giro", A.giro_corte, lambda t: CV.trabajo(t), 0.90, 1.12)
follow("corte_a_cortadora", "corte_a_op0"); FOLLOW["corte_a_cortadora_manija"] = "corte_a_op0"
rig_tronco("corte_a_op1", "giro", 6.0, lambda t: CV.trabajo(t, 0.10), 0.90, 1.12)     # alisa el tendido: manos en la tela
# 2) planchas: la plancha va en la mano izquierda; el tronco gira y la lleva por la tabla (una a contratiempo de la otra)
for i, fase in ((0, 0.0), (1, 0.2)):
    rig_tronco("op_plancha%d" % i, "giro", -A.giro_plancha, lambda t, fase=fase: CV.trabajo(t, fase), 0.90, 1.12)
    follow("plancha%d" % i, "op_plancha%d" % i); follow("plancha_manguera%d" % i, "op_plancha%d" % i)
    FOLLOW["plancha%d" % i] = "op_plancha%d" % i
# 3) costura: la operaria guia la pieza con las manos (giro del tronco) y la pieza va con las manos. Tela MT-1022 con el
#    fondo marron mezclado (A.tela_marron): la foto promedia beige (raya casi blanca) y sobre la tapa blanca no se veia.
M_cos = None
try:
    M_cos = bpy.data.materials["tela"].copy(); M_cos.name = "tela_costura"
    N_ = M_cos.node_tree.nodes; L_ = M_cos.node_tree.links
    bs = next(n for n in N_ if n.type == "BSDF_PRINCIPLED")
    lk = [l for l in L_ if l.to_socket == bs.inputs["Base Color"]][0]
    mx = N_.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MIX"
    mx.inputs[0].default_value = A.tela_marron
    src = lk.from_socket; L_.remove(lk)
    L_.new(src, mx.inputs[6]); mx.inputs[7].default_value = (0.038, 0.025, 0.020, 1.0)   # fondo MT-1022, sRGB 55/44/39 en lineal
    L_.new(mx.outputs[2], bs.inputs["Base Color"])
except Exception as e:
    print("tela_costura:", e)
n_cos = 0
TELA = []
for o in list(bpy.data.objects):
    if o.name.startswith("costura_") and o.name.endswith("_prenda"):
        st = o.parent; nm = o.name[:-len("_prenda")] + "_op"
        fase = 0.03 * (n_cos % 3)
        if M_cos is not None:
            o.data = o.data.copy(); o.data.materials.clear(); o.data.materials.append(M_cos)
        if bpy.data.objects.get(nm) is None:
            n_cos += 1; continue
        fo_ = bpy.data.objects[nm]; Mst = st.matrix_world.inverted(); Ff = fo_.matrix_world.copy(); Ffi = Ff.inverted()
        pts0 = [o.matrix_world @ Vector(c_) for c_ in o.bound_box]
        def fuera(sg, pts0=pts0, Mst=Mst, Ff=Ff, Ffi=Ffi):
            """Cuanto sale la pieza de la tapa (1,2 x 0,55 m) en el golpe (+1) y en la anticipacion (-0,2), en m de escena."""
            P_ = Vector((0, 0.0, 0.70)); worst = -1.0
            for k_ in (1.0, -0.2):
                Dm = Matrix.Translation(P_) @ Matrix.Rotation(math.radians(A.giro_costura) * sg * k_, 4, "Z") @ Matrix.Translation(-P_)
                for p in pts0:
                    q = Mst @ (Ff @ Dm @ Ffi @ p)
                    worst = max(worst, abs(q.x) - R_(0.6), abs(q.y) - R_(0.275))
            return worst
        sg = 1.0 if fuera(1.0) <= fuera(-1.0) else -1.0
        rig_tronco(nm, "giro", sg * A.giro_costura, lambda t, fase=fase: CV.trabajo(t, fase), 0.60, 0.80, arm_z=0.66)
        follow(o.name, nm); FOLLOW[o.name] = nm
        TELA.append((o.name, sg, fuera(sg) / S))
        n_cos += 1
# 4) el que carga: flexiona en la cadera y baja la caja con el cuerpo (la caja va en las manos)
rig_tronco("op_caja", "flexion", A.flexion_caja, CV.carga, A.caja_z0, A.caja_z1, arm_z=0.72,
           espalda=[float(v) for v in A.caja_espalda.split(",")] if A.caja_espalda else None)
follow("caja_en_mano", "op_caja"); FOLLOW["caja_en_mano"] = "op_caja"
# 5) control: acomoda la camisa sobre el escritorio (giro chico; la camisa va en las manos)
rig_tronco("op_control", "giro", 3.0, lambda t: CV.trabajo(t, 0.15), 0.90, 1.12)
follow("camisa_en_mano", "op_control"); FOLLOW["camisa_en_mano"] = "op_control"
# 6) rollo al hombro: giro chico, el rollo (pivote + malla + tubo) va en el hombro
rig_tronco("op_rollo", "giro", 3.0, lambda t: CV.trabajo(t, 0.2), 0.90, 1.12)
follow("rollo_hombro_piv", "op_rollo")
for nm_, sg_, fu_ in TELA:
    print("TELA %s giro %+.0f grados, sale de la tapa %+.3f m reales (negativo = adentro)" % (nm_, sg_ * A.giro_costura, fu_))
print("TRABAJO: %d objetos + %d troncos (costura %d)" % (len(WORK), len(BONES), n_cos))

# ---------------------------------------------------------------- animacion por cuadro
try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
except Exception as e:
    print("interp:", e)
sc.render.fps = CV.FPS
sc.frame_start, sc.frame_end = 0, N_ANIM - 1
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
    for pb, MLi, ML, D in BONES:
        lo_, q_, _ = (MLi @ D(t) @ ML).decompose()
        pb.location = lo_; pb.rotation_quaternion = q_
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
        for pb, _, _, _ in BONES:
            pb.keyframe_insert("location", frame=f); pb.keyframe_insert("rotation_quaternion", frame=f)


for f in range(0, N_ANIM):
    pose(f, key=True)

# ---------------------------------------------------------------- render
sc.cycles.samples = A.samples
sc.cycles.adaptive_threshold = A.thr
sc.cycles.seed = A.seed
sc.cycles.use_animated_seed = False
sc.render.use_motion_blur = bool(A.mblur)
sc.render.motion_blur_shutter = 0.5


def calidad(f):
    """v3.3: 128 muestras en la nave (f84-149) y obturador largo en f95-100 (la puerta pasa de canto en f98)."""
    sc.cycles.samples = A.muestras_nave if f >= A.desde_nave else A.samples
    sc.render.motion_blur_shutter = A.obturador_puerta if 95 <= f <= 100 else 0.5
    print("CALIDAD f%d muestras %d obturador %.2f" % (f, sc.cycles.samples, sc.render.motion_blur_shutter), flush=True)
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

# ---------------------------------------------------------------- mascara del interior (PLAN 55 §1) [XG·792d] v3.3
# Pasada AOV "interior" en el MISMO render (0 muestras extra): 1 = lo que se ve de la nave por la abertura (coleccion
# "interior" + cara interna de las paredes, material carbon_int); 0 = caja por fuera, cantos, puerta entera (todo lo que
# cuelga de "bisagra", incluido su forro), estudio y fondo. Es la primera superficie que ve la camara, con el mismo motion
# blur y la misma profundidad de campo que la imagen: la puerta tapa la mascara cuadro a cuadro. La imagen no cambia
# (probado: diferencia maxima 0 con y sin el compositor). Sale en A.mascara/fNNNN.png, PNG gris 8 bits, sin transformada de vista.
FO_MASK = None
if A.mascara:
    os.makedirs(A.mascara, exist_ok=True)
    _door = set(); _st = [hinge]
    while _st:
        _o = _st.pop(); _door.add(_o.name); _st += list(_o.children)
    _int = set(o.name for o in coll("interior").all_objects)
    for _o in bpy.data.objects:
        _o.pass_index = 2 if _o.name in _door else (1 if _o.name in _int else 0)
    for _m in bpy.data.materials:
        if not _m.node_tree or any(n.type == "OUTPUT_AOV" for n in _m.node_tree.nodes):
            continue
        _nt = _m.node_tree
        _oi = _nt.nodes.new("ShaderNodeObjectInfo"); _mt = _nt.nodes.new("ShaderNodeMath")
        if _m.name.startswith("carbon_int"):     # cara interna de las paredes: blanca salvo en la puerta (indice 2)
            _mt.operation = "LESS_THAN"; _mt.inputs[1].default_value = 1.5
        else:                                      # resto: blanca solo si el objeto es de la nave (indice 1)
            _mt.operation = "COMPARE"; _mt.inputs[1].default_value = 1.0; _mt.inputs[2].default_value = 0.5
        _ao = _nt.nodes.new("ShaderNodeOutputAOV"); _ao.aov_name = "interior"
        _nt.links.new(_oi.outputs["Object Index"], _mt.inputs[0]); _nt.links.new(_mt.outputs[0], _ao.inputs["Value"])
        # segunda AOV "tela" (PLAN 55 §7, criterio 5: mascara de material): 1 = tela de costura (MT-1022), 0,5 = otras telas
        _at = _nt.nodes.new("ShaderNodeOutputAOV"); _at.aov_name = "tela"
        _at.inputs["Value"].default_value = 1.0 if _m.name.startswith("tela_costura") else (0.5 if _m.name.startswith("tela") else 0.0)
    for _nm in ("interior", "tela"):
        _a = bpy.context.view_layer.aovs.add(); _a.name = _nm; _a.type = "VALUE"
    _ng = bpy.data.node_groups.new("comp_mascara", "CompositorNodeTree"); sc.compositing_node_group = _ng
    _rl = _ng.nodes.new("CompositorNodeRLayers")
    _ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    _go = _ng.nodes.new("NodeGroupOutput"); _ng.links.new(_rl.outputs["Image"], _go.inputs[0])
    FO_MASK = _ng.nodes.new("CompositorNodeOutputFile"); FO_MASK.directory = A.mascara; FO_MASK.file_name = "tmp_"
    FO_MASK.format.media_type = "IMAGE"; FO_MASK.format.file_format = "PNG"
    FO_MASK.format.color_mode = "BW"; FO_MASK.format.color_depth = "8"; FO_MASK.save_as_render = False
    for _nm in ("interior", "tela"):
        FO_MASK.file_output_items.new("FLOAT", _nm)
        _ng.links.new(_rl.outputs[_nm], FO_MASK.inputs[_nm])
    print("MASCARA AOV en %d materiales; puerta %d objetos, nave %d -> %s" % (
        sum(1 for m in bpy.data.materials if m.node_tree and any(n.type == "OUTPUT_AOV" for n in m.node_tree.nodes)),
        len(_door), len(_int), A.mascara), flush=True)


def mascara_antes(f):
    if FO_MASK is not None:
        FO_MASK.file_name = "f%04d_tmp_" % f


def mascara_despues(f):
    if FO_MASK is not None:
        for _nm, dst in (("interior", "f%04d.png" % f), ("tela", "tela_f%04d.png" % f)):
            src = os.path.join(A.mascara, "f%04d_tmp_%s.png" % (f, _nm))
            if os.path.exists(src):
                os.replace(src, os.path.join(A.mascara, dst))
            else:
                print("MASCARA_FALTA %s f%d (%s)" % (_nm, f, os.listdir(A.mascara)[:5]), flush=True)


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
elif A.mode == "contacto":   # v3.3 [XG·792d]: --frames "129,132,135": mano-objeto (px y mm), recorridos, pies y cruces, sin render
    from mathutils.bvhtree import BVHTree
    FRS = [int(x) for x in A.frames.split(",")]
    PARES = [("corte_a_op0", "corte_a_cortadora_manija", "RL"), ("op_plancha0", "plancha0", "L"), ("op_plancha1", "plancha1", "L"),
             ("op_caja", "caja_en_mano", "RL"), ("op_control", "camisa_en_mano", "RL")]
    PARES += [(fig, ob, "RL") for ob, fig in FOLLOW.items() if ob.startswith("costura_")]
    MANOS = {}
    for fig, ob, lados in PARES:
        fo = bpy.data.objects[fig]; me = RIGS[fig]["body"].data
        MANOS[fig] = {s: [v.index for v in me.vertices if (v.co - Vector(fo["mano_" + s])).length < 0.07] for s in lados}
        MANOS[fig]["pie"] = [v.index for v in me.vertices if v.co.z < 0.10]

    def bvh_w(o, dg):
        e = o.evaluated_get(dg); m = e.to_mesh(); M = e.matrix_world
        t = BVHTree.FromPolygons([M @ v.co for v in m.vertices], [tuple(p.vertices) for p in m.polygons]); e.to_mesh_clear(); return t

    def bbox_w(o):
        b = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return Vector((min(p.x for p in b), min(p.y for p in b), min(p.z for p in b))), Vector((max(p.x for p in b), max(p.y for p in b), max(p.z for p in b)))

    REG = {}
    for fr in FRS:
        sc.frame_set(fr); pose(fr); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        for fig, ob, lados in PARES:
            body = RIGS[fig]["body"]; e = body.evaluated_get(dg); m = e.to_mesh(); Mb = e.matrix_world
            co = [Mb @ v.co for v in m.vertices]; e.to_mesh_clear()
            o = bpy.data.objects[ob]; eo = o.evaluated_get(dg); Mo = eo.matrix_world; Moi = Mo.inverted()
            res = []
            for s in lados:
                best = None
                for i in MANOS[fig][s]:
                    ok, p, n, _ = eo.closest_point_on_mesh(Moi @ co[i])
                    if not ok: continue
                    pw = Mo @ p; nw = (Mo.to_3x3() @ n).normalized(); d = (co[i] - pw).length
                    sgn = 1.0 if (co[i] - pw).dot(nw) >= 0 else -1.0
                    if best is None or d < best[0]:
                        best = (d, sgn, co[i], pw)
                a_, b_ = _px(best[2]), _px(best[3])
                hc = sum((co[i] for i in MANOS[fig][s]), Vector()) / len(MANOS[fig][s])
                res.append((s, best[0] * best[1] / S * 1000, math.hypot(a_[0] - b_[0], a_[1] - b_[1]), _px(hc)))
            lo, hi = bbox_w(eo)
            pie = sum((co[i] for i in MANOS[fig]["pie"]), Vector()) / max(1, len(MANOS[fig]["pie"]))
            REG[(fr, ob)] = dict(obj=_px((lo + hi) / 2), manos=res, pie=_px(pie))
            print("POS f%d %s %.2f %.2f pie %.2f %.2f" % (fr, ob, REG[(fr, ob)]["obj"][0], REG[(fr, ob)]["obj"][1], REG[(fr, ob)]["pie"][0], REG[(fr, ob)]["pie"][1]), flush=True)
            for s, mm, pxd, hcp in res:
                print("CONTACTO f%d %-26s mano %s  dist %+7.1f mm reales  %.2f px" % (fr, ob, s, mm, pxd), flush=True)
            # cruces: el objeto contra la figura (sin las manos) y contra mallas quietas cercanas
            tb = bvh_w(o, dg)
            idx_m = set(i for s in lados for i in MANOS[fig][s])
            tri = [tuple(p.vertices) for p in body.data.polygons if not (set(p.vertices) & idx_m)]
            tbody = BVHTree.FromPolygons(co, tri)
            nb = len(tb.overlap(tbody))
            lo2, hi2 = lo - Vector((R_(0.01),) * 3), hi + Vector((R_(0.01),) * 3)
            veci = []
            for q in bpy.data.objects:
                if q.type != "MESH" or q == o or q.hide_render or q.parent == o or q == body or not q.visible_get():
                    continue
                ql, qh = bbox_w(q)
                if ql.x > hi2.x or qh.x < lo2.x or ql.y > hi2.y or qh.y < lo2.y or ql.z > hi2.z or qh.z < lo2.z:
                    continue
                n_ = len(tb.overlap(bvh_w(q, dg)))
                if n_:
                    veci.append("%s:%d" % (q.name, n_))
            print("CRUCE f%d %-26s con_cuerpo %d  con %s" % (fr, ob, nb, ", ".join(veci) or "-"), flush=True)
    for fig, ob, lados in PARES:
        for a_, b_ in ((FRS[0], FRS[-1]), (FRS[1], FRS[-1])) if len(FRS) > 2 else ((FRS[0], FRS[-1]),):
            A_, B_ = REG[(a_, ob)], REG[(b_, ob)]
            dob = math.hypot(B_["obj"][0] - A_["obj"][0], B_["obj"][1] - A_["obj"][1])
            dpi = math.hypot(B_["pie"][0] - A_["pie"][0], B_["pie"][1] - A_["pie"][1])
            print("RECORRIDO f%d->f%d %-26s objeto %.1f px  (dx %+.1f dy %+.1f)  pies %.2f px" % (
                a_, b_, ob, dob, B_["obj"][0] - A_["obj"][0], B_["obj"][1] - A_["obj"][1], dpi), flush=True)
elif A.mode == "still":
    for fr in [int(x) for x in str(A.frame).split(",")] if False else [A.frame]:
        sc.frame_set(fr); pose(fr); calidad(fr); mascara_antes(fr)
        sc.render.filepath = A.out
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        mascara_despues(fr)
        print("RENDER_OK %s frame %d %.1f s" % (A.out, fr, time.time() - t1), flush=True)
elif A.mode == "stills":   # --frames "0,12,62,85,135" --out prefijo
    for fr in [int(x) for x in A.frames.split(",")]:
        sc.frame_set(fr); pose(fr); puntos(fr); calidad(fr)
        p = "%s_f%03d.png" % (A.out, fr)
        if os.path.exists(p):
            continue
        sc.render.filepath = p; mascara_antes(fr)
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        mascara_despues(fr)
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
        sc.frame_set(f); calidad(f); mascara_antes(f)
        tmp = p[:-4] + "_tmp.png"            # escritura atomica: un cuadro cortado a mitad nunca queda con el nombre final
        sc.render.filepath = tmp
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, p)
        mascara_despues(f)
        durs.append(time.time() - t1)
        print("FRAME_OK %d %.1f s" % (f, time.time() - t1), flush=True)
    print("ANIM_OK")
