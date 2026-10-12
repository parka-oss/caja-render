# Cuadro ancla "La caja trae la fábrica", VUELTA 3 — Blender 5.1 / Cycles CPU. (v3: menos sepia, figuras MPFB2 pintadas, tapa de arriba)
# Uso: blender -b --python build2.py -- --stage blockout|full --variant tapa|pared --elev 42 --res 0.5 --samples 64 --out path.png
# tapa = caja acostada, tapa a medio abrir; pared = la misma caja parada, tapa abierta como puerta, nave de 3 plantas.
import bpy, bmesh, math, sys, os, random, argparse
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--stage", default="blockout")
ap.add_argument("--variant", default="tapa")
ap.add_argument("--elev", type=float, default=22.0)
ap.add_argument("--azim", type=float, default=28.0)
ap.add_argument("--res", type=float, default=0.5)
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--out", default="")
ap.add_argument("--blend", default="")
ap.add_argument("--fill_ratio", type=float, default=3.0)
ap.add_argument("--prac", type=float, default=1.0)   # multiplicador de las prácticas
ap.add_argument("--key", type=float, default=1.0)    # multiplicador de la llave
ap.add_argument("--amb", type=float, default=1.0)    # derrame neutro dentro de la caja
ap.add_argument("--expo", type=float, default=0.0)
ap.add_argument("--dist", type=float, default=4.4)
ap.add_argument("--shift", type=float, default=0.08)
ap.add_argument("--bh", type=float, default=0.27)
ap.add_argument("--closeup", default="")   # "esquina" | "maqueta": cámara de verificación
ap.add_argument("--ids", action="store_true")       # render de máscaras para medir
ap.add_argument("--lid", type=float, default=55.0)   # apertura de la tapa (tapa)
ap.add_argument("--door", type=float, default=118.0) # apertura de la puerta (pared)
ap.add_argument("--telax", type=float, default=1.8)  # rapport de la tela x (trampa de escala declarada)
ap.add_argument("--spill", type=int, default=-1)     # prácticas iluminan todo (1) o solo caja+maqueta (0); -1 = auto
ap.add_argument("--reb", type=float, default=1.0)    # rebote hacia la tapa/puerta
ap.add_argument("--wash", type=float, default=1.0)   # baño cálido de la pared del fondo (pared)
ap.add_argument("--lens", type=float, default=85.0)
ap.add_argument("--lookx", type=float, default=0.0)
ap.add_argument("--looky", type=float, default=0.0)
ap.add_argument("--lookz", type=float, default=0.0)
ap.add_argument("--shiftx", type=float, default=0.0)
ap.add_argument("--tkamb", type=float, default=5200.0)  # v3: temperatura de los rebotes/baños (tarjetas de apoyo)
ap.add_argument("--kint", type=float, default=1.0)      # v3: llave neutra de estudio dentro de la nave
ap.add_argument("--desat", type=float, default=0.35)    # v3: saturación de todo lo que no es tela, piel ni pelo
ap.add_argument("--tkreb", type=float, default=4200.0)  # v3: rebote de piso (la luz de puesto devuelta por mesas y tela)
ap.add_argument("--toplid", type=float, default=0.0)    # v3: apertura de la tapa de arriba (grados; 0 = cerrada)
A = ap.parse_args(argv)
FULL = A.stage == "full"

HERE = os.path.dirname(os.path.abspath(__file__))
ACT = os.path.join(HERE, "..", "activos")
TELA = os.path.join(HERE, "..", "assets", "tela_2k_colorfoto.jpg")
rng = random.Random(1022)

S = 1.0 / 32.0          # escala de la maqueta (1:32, ver PROGRESO)
BW, BD, T = 0.56, 0.40, 0.007   # caja exterior (m) y espesor del cartón
BH = A.bh
FLOOR_D = 0.06          # piso de la maqueta bajo el borde
ZF = BH - FLOOR_D
IW, ID = BW - 2 * T, BD - 2 * T

# ---------------------------------------------------------------- escena
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
except TypeError as e:
    print(e)
sc.cycles.device = "CPU"
sc.cycles.samples = A.samples
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.01
sc.cycles.use_denoising = True
try:
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
sc.cycles.max_bounces = 8
sc.cycles.diffuse_bounces = 4
sc.cycles.glossy_bounces = 3
sc.cycles.transmission_bounces = 2
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.blur_glossy = 1.0
sc.render.resolution_x = int(1080 * A.res)
sc.render.resolution_y = int(1920 * A.res)
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "None"
except Exception:
    pass
sc.view_settings.exposure = A.expo
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "16"

world = bpy.data.worlds.new("W") if not sc.world else sc.world
sc.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.02, 0.02, 0.02, 1)
bg.inputs[1].default_value = 1.0

COL = {}
def coll(name):
    if name not in COL:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
        COL[name] = c
    return COL[name]

def link(o, cname):
    for c in o.users_collection:
        c.objects.unlink(o)
    coll(cname).objects.link(o)
    return o

# ---------------------------------------------------------------- color
def kelvin_rgb(Tk):
    t = float(Tk)
    if t <= 4000:
        x = -0.2661239e9 / t**3 - 0.2343589e6 / t**2 + 0.8776956e3 / t + 0.179910
    else:
        x = -3.0258469e9 / t**3 + 2.1070379e6 / t**2 + 0.2226347e3 / t + 0.240390
    if t <= 2222:
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    elif t <= 4000:
        y = -0.9549476 * x**3 - 1.37418593 * x**2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x**3 - 5.87338670 * x**2 + 3.75112997 * x - 0.37001483
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
    return (r, g, b)

WB = kelvin_rgb(5900)   # balance de blancos de cámara = la llave
def light_col(Tk):
    c = kelvin_rgb(Tk)
    c = [c[i] / WB[i] for i in range(3)]
    m = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    return tuple(v / m for v in c)

# ---------------------------------------------------------------- materiales
def nodes_of(mat):
    return mat.node_tree.nodes, mat.node_tree.links

def bsdf_of(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

def mat_basic(name, col, rough=0.6, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = bsdf_of(m)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    try:
        b.inputs["Specular IOR Level"].default_value = spec
    except KeyError:
        pass
    return m

def tex(nodes, path, noncolor=False):
    t = nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        t.image.colorspace_settings.name = "Non-Color"
    return t

def mat_pbr(name, folder, prefix, scale=1.0, tint=None, sat=1.0, val=1.0, rough_add=0.0,
            metal=False, bump=0.3, dust=0.0, coord="UV"):
    """Material PBR ambientCG / Poly Haven con mapeo en metros (coord Object) o UV."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = nodes_of(m)
    b = bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    L.new(tc.outputs["Object" if coord == "Object" else "UV"], mp.inputs[0])
    files = os.listdir(folder)
    def f(*keys):
        for k in keys:
            for fn in files:
                if k.lower() in fn.lower() and fn.lower().endswith((".jpg", ".png", ".jpeg")):
                    return os.path.join(folder, fn)
        return None
    cpath = f("_Color", "_diff", "baseColor")
    rpath = f("_Roughness", "_rough")
    npath = f("_NormalGL", "_nor_gl", "normal")
    mpath = f("_Metalness")
    tri = N.new("ShaderNodeTexImage") if False else None
    if cpath:
        tcn = tex(N, cpath)
        if coord == "Object":
            tcn.projection = "BOX"; tcn.projection_blend = 0.2
        L.new(mp.outputs[0], tcn.inputs[0])
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = sat
        hs.inputs["Value"].default_value = val
        L.new(tcn.outputs[0], hs.inputs["Color"])
        last = hs.outputs[0]
        if tint:
            mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
            mx.inputs[0].default_value = 1.0
            L.new(last, mx.inputs[6]); mx.inputs[7].default_value = (*tint, 1)
            last = mx.outputs[2]
        if dust > 0:
            last = add_dust(N, L, last, dust)
        L.new(last, b.inputs["Base Color"])
    if rpath:
        tr = tex(N, rpath, True)
        if coord == "Object":
            tr.projection = "BOX"; tr.projection_blend = 0.2
        L.new(mp.outputs[0], tr.inputs[0])
        ma = N.new("ShaderNodeMath"); ma.operation = "ADD"; ma.use_clamp = True
        L.new(tr.outputs[0], ma.inputs[0]); ma.inputs[1].default_value = rough_add
        L.new(ma.outputs[0], b.inputs["Roughness"])
    if npath:
        tn = tex(N, npath, True)
        if coord == "Object":
            tn.projection = "BOX"; tn.projection_blend = 0.2
        L.new(mp.outputs[0], tn.inputs[0])
        nm = N.new("ShaderNodeNormalMap"); nm.inputs[0].default_value = bump
        L.new(tn.outputs[0], nm.inputs[1]); L.new(nm.outputs[0], b.inputs["Normal"])
    if metal and mpath:
        tm = tex(N, mpath, True)
        if coord == "Object":
            tm.projection = "BOX"; tm.projection_blend = 0.2
        L.new(mp.outputs[0], tm.inputs[0]); L.new(tm.outputs[0], b.inputs["Metallic"])
    return m

def add_dust(N, L, col_socket, amount, scale=900.0, color=(0.42, 0.41, 0.39)):
    """Polvo en caras que miran arriba: ruido fino × normal.z."""
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sep.inputs[0])
    up = N.new("ShaderNodeMapRange"); L.new(sep.outputs[2], up.inputs[0])
    up.inputs[1].default_value = 0.55; up.inputs[2].default_value = 0.95
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale / 25
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    L.new(nz.outputs[0], mul.inputs[0]); L.new(nz2.outputs[0], mul.inputs[1])
    mr = N.new("ShaderNodeMapRange"); L.new(mul.outputs[0], mr.inputs[0])
    mr.inputs[1].default_value = 0.2; mr.inputs[2].default_value = 0.45
    mul2 = N.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"
    L.new(mr.outputs[0], mul2.inputs[0]); L.new(up.outputs[0], mul2.inputs[1])
    mul3 = N.new("ShaderNodeMath"); mul3.operation = "MULTIPLY"
    L.new(mul2.outputs[0], mul3.inputs[0]); mul3.inputs[1].default_value = amount
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
    L.new(mul3.outputs[0], mx.inputs[0]); L.new(col_socket, mx.inputs[6])
    mx.inputs[7].default_value = (*color, 1)
    return mx.outputs[2]

def edge_wear(N, L, col_socket, radius=0.0015, lift=(0.16, 0.155, 0.15), amount=0.8, noise_scale=300):
    """Canto gastado: donde el Bevel node se aparta de la normal geométrica."""
    bev = N.new("ShaderNodeBevel"); bev.inputs["Radius"].default_value = radius; bev.samples = 8
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    L.new(bev.outputs[0], dot.inputs[0]); L.new(geo.outputs["Normal"], dot.inputs[1])
    mr = N.new("ShaderNodeMapRange"); L.new(dot.outputs["Value"], mr.inputs[0])
    mr.inputs[1].default_value = 0.9995; mr.inputs[2].default_value = 0.97
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = noise_scale; nz.inputs["Detail"].default_value = 8
    nr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], nr.inputs[0])
    nr.inputs[1].default_value = 0.35; nr.inputs[2].default_value = 0.6
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    L.new(mr.outputs[0], mul.inputs[0]); L.new(nr.outputs[0], mul.inputs[1])
    mul2 = N.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"; mul2.use_clamp = True
    L.new(mul.outputs[0], mul2.inputs[0]); mul2.inputs[1].default_value = amount
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
    L.new(mul2.outputs[0], mx.inputs[0]); L.new(col_socket, mx.inputs[6]); mx.inputs[7].default_value = (*lift, 1)
    return mx.outputs[2], mul2.outputs[0]

# ---- cartón carbón (caja) ----
def mat_carbon(name, base=(0.045, 0.044, 0.043), inner=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = nodes_of(m); b = bsdf_of(m)
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = 0.72
    try: b.inputs["Specular IOR Level"].default_value = 0.35
    except KeyError: pass
    if not FULL:
        return m
    tc = N.new("ShaderNodeTexCoord")
    # fibra del liner (Cardboard002 desaturado, solo como modulación de tono y rugosidad)
    cb = os.path.join(ACT, "texturas", "Cardboard002")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.2, 2.2, 2.2)
    L.new(tc.outputs["Object"], mp.inputs[0])
    tcol = tex(N, os.path.join(cb, "Cardboard002_2K-JPG_Color.jpg")); tcol.projection = "BOX"; tcol.projection_blend = 0.3
    L.new(mp.outputs[0], tcol.inputs[0])
    bw = N.new("ShaderNodeRGBToBW"); L.new(tcol.outputs[0], bw.inputs[0])
    mr = N.new("ShaderNodeMapRange"); L.new(bw.outputs[0], mr.inputs[0])
    mr.inputs[1].default_value = 0.25; mr.inputs[2].default_value = 0.6
    mr.inputs[3].default_value = 0.85; mr.inputs[4].default_value = 1.15
    mulc = N.new("ShaderNodeVectorMath"); mulc.operation = "SCALE"
    mulc.inputs[0].default_value = base; L.new(mr.outputs[0], mulc.inputs["Scale"])
    # manchas de tono de impresión (tinta mate despareja)
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9; nz.inputs["Detail"].default_value = 4
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], nr.inputs[0])
    nr.inputs[3].default_value = 0.9; nr.inputs[4].default_value = 1.12
    mul2 = N.new("ShaderNodeVectorMath"); mul2.operation = "SCALE"
    L.new(mulc.outputs[0], mul2.inputs[0]); L.new(nr.outputs[0], mul2.inputs["Scale"])
    col = mul2.outputs[0]
    # rozaduras: parches de tinta gastada (bajo contraste), más en la mitad baja de la caja
    sp = N.new("ShaderNodeTexNoise"); sp.inputs["Scale"].default_value = 7; sp.inputs["Detail"].default_value = 8
    sp.inputs["Roughness"].default_value = 0.7
    L.new(tc.outputs["Object"], sp.inputs["Vector"])
    sr = N.new("ShaderNodeMapRange"); L.new(sp.outputs[0], sr.inputs[0])
    sr.inputs[1].default_value = 0.62; sr.inputs[2].default_value = 0.75
    sm = N.new("ShaderNodeMix"); sm.data_type = "RGBA"; L.new(sr.outputs[0], sm.inputs[0])
    L.new(col, sm.inputs[6]); sm.inputs[7].default_value = (base[0] * 1.22, base[1] * 1.21, base[2] * 1.2, 1)
    col = sm.outputs[2]
    col, wear = edge_wear(N, L, col, radius=0.004, lift=(0.14, 0.135, 0.128), amount=1.0)
    col = add_dust(N, L, col, 0.35, scale=1400, color=(0.30, 0.29, 0.28))
    L.new(col, b.inputs["Base Color"])
    # rugosidad: tinta mate con zonas lustradas por roce
    rn = N.new("ShaderNodeTexNoise"); rn.inputs["Scale"].default_value = 40
    rr = N.new("ShaderNodeMapRange"); L.new(rn.outputs[0], rr.inputs[0])
    rr.inputs[3].default_value = 0.62; rr.inputs[4].default_value = 0.8
    L.new(rr.outputs[0], b.inputs["Roughness"])
    # ondulado del corrugado (washboard) + fibra
    tn = tex(N, os.path.join(cb, "Cardboard002_2K-JPG_NormalGL.jpg"), True); tn.projection = "BOX"
    L.new(mp.outputs[0], tn.inputs[0])
    nm = N.new("ShaderNodeNormalMap"); nm.inputs[0].default_value = 0.25; L.new(tn.outputs[0], nm.inputs[1])
    wv = N.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 1.0 / 0.0085 / 1.0  # período ~8,5 mm (en metros de objeto)
    wv.inputs["Distortion"].default_value = 0.4
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.012; bp.inputs["Distance"].default_value = 0.0004
    L.new(wv.outputs["Color"], bp.inputs["Height"]); L.new(nm.outputs[0], bp.inputs["Normal"])
    L.new(bp.outputs[0], b.inputs["Normal"])
    return m

def mat_canto():
    """Canto del corrugado de doble onda: liner carbón afuera, onda y liners interiores gris kraft."""
    m = bpy.data.materials.new("canto"); m.use_nodes = True
    N, L = nodes_of(m); b = bsdf_of(m)
    paper = (0.20, 0.185, 0.165)
    b.inputs["Base Color"].default_value = (*paper, 1)
    b.inputs["Roughness"].default_value = 0.9
    if not FULL:
        return m
    # patrón por Generated: 'u' a lo largo del canto, 'v' a través del espesor. Se arma en attrs por objeto
    at_u = N.new("ShaderNodeAttribute"); at_u.attribute_name = "cu"; at_u.attribute_type = "GEOMETRY"
    at_v = N.new("ShaderNodeAttribute"); at_v.attribute_name = "cv"; at_v.attribute_type = "GEOMETRY"
    # dos ondas: v en [0,1] -> fila 1 en [0.12,0.48], fila 2 en [0.52,0.88]
    def wave_row(center, phase):
        mu = N.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; L.new(at_u.outputs["Fac"], mu.inputs[0])
        mu.inputs[1].default_value = 2 * math.pi / 0.0042   # paso de onda 4,2 mm
        ad = N.new("ShaderNodeMath"); ad.operation = "ADD"; L.new(mu.outputs[0], ad.inputs[0]); ad.inputs[1].default_value = phase
        sn = N.new("ShaderNodeMath"); sn.operation = "SINE"; L.new(ad.outputs[0], sn.inputs[0])
        wv = N.new("ShaderNodeMath"); wv.operation = "MULTIPLY_ADD"; L.new(sn.outputs[0], wv.inputs[0])
        wv.inputs[1].default_value = 0.15; wv.inputs[2].default_value = center
        df = N.new("ShaderNodeMath"); df.operation = "SUBTRACT"; L.new(at_v.outputs["Fac"], df.inputs[0]); L.new(wv.outputs[0], df.inputs[1])
        ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L.new(df.outputs[0], ab.inputs[0])
        st = N.new("ShaderNodeMath"); st.operation = "LESS_THAN"; L.new(ab.outputs[0], st.inputs[0]); st.inputs[1].default_value = 0.07
        # hueco: dentro de la fila y fuera de la onda
        d2 = N.new("ShaderNodeMath"); d2.operation = "SUBTRACT"; L.new(at_v.outputs["Fac"], d2.inputs[0]); d2.inputs[1].default_value = center
        a2 = N.new("ShaderNodeMath"); a2.operation = "ABSOLUTE"; L.new(d2.outputs[0], a2.inputs[0])
        inrow = N.new("ShaderNodeMath"); inrow.operation = "LESS_THAN"; L.new(a2.outputs[0], inrow.inputs[0]); inrow.inputs[1].default_value = 0.15
        return st.outputs[0], inrow.outputs[0]
    s1, r1 = wave_row(0.30, 0.0)
    s2, r2 = wave_row(0.70, 1.7)
    paperm = N.new("ShaderNodeMath"); paperm.operation = "MAXIMUM"; L.new(s1, paperm.inputs[0]); L.new(s2, paperm.inputs[1])
    rows = N.new("ShaderNodeMath"); rows.operation = "MAXIMUM"; L.new(r1, rows.inputs[0]); L.new(r2, rows.inputs[1])
    hole = N.new("ShaderNodeMath"); hole.operation = "SUBTRACT"; hole.use_clamp = True
    L.new(rows.outputs[0], hole.inputs[0]); L.new(paperm.outputs[0], hole.inputs[1])
    # liner exterior (v<0.08) es carbón impreso
    outer = N.new("ShaderNodeMath"); outer.operation = "LESS_THAN"; L.new(at_v.outputs["Fac"], outer.inputs[0]); outer.inputs[1].default_value = 0.07
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; L.new(hole.outputs[0], mx.inputs[0])
    mx.inputs[6].default_value = (*paper, 1); mx.inputs[7].default_value = (0.055, 0.05, 0.045, 1)
    mx2 = N.new("ShaderNodeMix"); mx2.data_type = "RGBA"; L.new(outer.outputs[0], mx2.inputs[0])
    L.new(mx.outputs[2], mx2.inputs[6]); mx2.inputs[7].default_value = (0.04, 0.039, 0.038, 1)
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2500
    nr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], nr.inputs[0]); nr.inputs[3].default_value = 0.8; nr.inputs[4].default_value = 1.15
    sc2 = N.new("ShaderNodeVectorMath"); sc2.operation = "SCALE"; L.new(mx2.outputs[2], sc2.inputs[0]); L.new(nr.outputs[0], sc2.inputs["Scale"])
    L.new(sc2.outputs[0], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.0006
    iv = N.new("ShaderNodeMath"); iv.operation = "SUBTRACT"; iv.inputs[0].default_value = 1.0; L.new(hole.outputs[0], iv.inputs[1])
    L.new(iv.outputs[0], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    return m

# ---------------------------------------------------------------- geometría utilitaria
def box_obj(name, size, loc, mat=None, bevel=0.0, rot=(0, 0, 0), cname="interior"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = loc; o.rotation_euler = rot
    coll(cname).objects.link(o)
    if mat: me.materials.append(mat)
    if bevel > 0:
        md = o.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = 2; md.limit_method = "ANGLE"
        md.harden_normals = False
    return o

def cyl_obj(name, r, h, loc, mat=None, rot=(0, 0, 0), verts=24, cname="interior", r2=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    coll(cname).objects.link(o)
    if mat: me.materials.append(mat)
    return o

def import_gltf(path, target=None, scale=None, cname="interior"):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(os.path.basename(path) + "_root", None)
    coll(cname).objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
        link(o, cname)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    dim = mx - mn
    k = scale if scale else (target / max(dim.x, dim.y) if target else 1.0)
    # centrar XY y apoyar en Z=0
    for o in new:
        if o.parent is root:
            o.location -= Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    root.scale = (k, k, k)
    # la tela es el único color: los activos importados se desaturan (neutros con temperatura, S ~8 %)
    seen = set()
    for o in new:
        if o.type != "MESH": continue
        for m in o.data.materials:
            if m is None or m.name in seen or not m.use_nodes: continue
            seen.add(m.name)
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if b is None: continue
            lk = [l for l in m.node_tree.links if l.to_socket == b.inputs["Base Color"]]
            hs = m.node_tree.nodes.new("ShaderNodeHueSaturation")
            hs.inputs["Saturation"].default_value = 0.12
            hs.inputs["Value"].default_value = 0.8
            if lk:
                src = lk[0].from_socket; m.node_tree.links.remove(lk[0])
                m.node_tree.links.new(src, hs.inputs["Color"])
            else:
                hs.inputs["Color"].default_value = b.inputs["Base Color"].default_value
            m.node_tree.links.new(hs.outputs[0], b.inputs["Base Color"])
    return root, new, dim * k

def place(root, loc, yaw=0.0):
    root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw))

# ================================================================ v2 — materiales de la escena (R3 / R13)
import zlib
VAR = A.variant
TAPA = VAR == "tapa"
TK = 3500
def R(v):  # metros reales -> maqueta
    return v * S
def srng(name):
    return random.Random(zlib.crc32(name.encode()))

def tone_socket(N, L, col, amp):
    oi = N.new("ShaderNodeObjectInfo")
    mr = N.new("ShaderNodeMapRange"); L.new(oi.outputs["Random"], mr.inputs[0])
    mr.inputs[3].default_value = 1 - amp / 2; mr.inputs[4].default_value = 1 + amp / 2
    vm = N.new("ShaderNodeVectorMath"); vm.operation = "SCALE"; L.new(col, vm.inputs[0]); L.new(mr.outputs[0], vm.inputs["Scale"])
    return vm.outputs[0]

def tone_var(m, amp=0.08, wear=False, wear_lift=None):
    """R13: +-amp/2 de valor por objeto (Object Info > Random). R3: canto gastado opcional."""
    if not FULL:
        return m
    N, L = nodes_of(m); b = bsdf_of(m)
    lk = [l for l in m.node_tree.links if l.to_socket == b.inputs["Base Color"]]
    if lk:
        src = lk[0].from_socket; m.node_tree.links.remove(lk[0])
    else:
        rgb = N.new("ShaderNodeRGB"); rgb.outputs[0].default_value = b.inputs["Base Color"].default_value
        src = rgb.outputs[0]
    col = tone_socket(N, L, src, amp)
    if wear:
        col, _ = edge_wear(N, L, col, radius=R(0.02), lift=wear_lift, amount=0.75, noise_scale=1500)
    L.new(col, b.inputs["Base Color"])
    return m

def mat_floor(name):
    if not FULL:
        return mat_basic(name, (0.22, 0.22, 0.215), 0.8)
    m = mat_pbr(name, os.path.join(ACT, "polyhaven", "texturas", "concrete_floor_worn_001"), "",
                scale=32 / 3.0, sat=0.08, val=0.8, bump=0.5, dust=0.25, coord="Object")
    N, L = nodes_of(m); b = bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord")
    src = next(l for l in m.node_tree.links if l.to_socket == b.inputs["Base Color"]).from_socket
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    outs = []
    for ch in (0, 1):
        md = N.new("ShaderNodeMath"); md.operation = "PINGPONG"; L.new(sep.outputs[ch], md.inputs[0]); md.inputs[1].default_value = R(6.0) / 2
        lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; L.new(md.outputs[0], lt.inputs[0]); lt.inputs[1].default_value = R(0.012)
        outs.append(lt.outputs[0])
    jm = N.new("ShaderNodeMath"); jm.operation = "MAXIMUM"; L.new(outs[0], jm.inputs[0]); L.new(outs[1], jm.inputs[1])
    # tono por paño (+-6 % L): coordenada redondeada al paño -> ruido blanco
    sn = N.new("ShaderNodeVectorMath"); sn.operation = "SNAP"; L.new(tc.outputs["Object"], sn.inputs[0])
    sn.inputs[1].default_value = (R(6.0), R(6.0), 1.0)
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"; L.new(sn.outputs[0], wn.inputs["Vector"])
    wr = N.new("ShaderNodeMapRange"); L.new(wn.outputs["Value"], wr.inputs[0]); wr.inputs[3].default_value = 0.94; wr.inputs[4].default_value = 1.06
    vm = N.new("ShaderNodeVectorMath"); vm.operation = "SCALE"; L.new(src, vm.inputs[0]); L.new(wr.outputs[0], vm.inputs["Scale"])
    # manchas de aceite y tránsito
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1 / R(2.2); nz.inputs["Detail"].default_value = 4
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], nr.inputs[0]); nr.inputs[1].default_value = 0.58; nr.inputs[2].default_value = 0.72
    ms = N.new("ShaderNodeMix"); ms.data_type = "RGBA"; ms.blend_type = "MULTIPLY"; L.new(nr.outputs[0], ms.inputs[0])
    L.new(vm.outputs[0], ms.inputs[6]); ms.inputs[7].default_value = (0.62, 0.61, 0.6, 1)
    mj = N.new("ShaderNodeMix"); mj.data_type = "RGBA"; L.new(jm.outputs[0], mj.inputs[0]); L.new(ms.outputs[2], mj.inputs[6])
    mj.inputs[7].default_value = (0.05, 0.05, 0.05, 1)
    L.new(mj.outputs[2], b.inputs["Base Color"])
    return m

M_floor = mat_floor("hormigon")
if FULL:
    M_steel = mat_pbr("metal_pintado", os.path.join(ACT, "texturas", "Metal028"), "", scale=43 / 1.5,
                      sat=0.3, val=1.0, bump=0.4, metal=True, coord="Object", dust=0.3)
    M_lam = mat_pbr("laminado", os.path.join(ACT, "texturas", "Plastic013B"), "", scale=32 / 1.0,
                    sat=0.1, val=0.42, bump=0.2, coord="Object", dust=0.2)
    M_plas = mat_pbr("plastico_gris", os.path.join(ACT, "texturas", "Plastic018B"), "", scale=43 / 0.8,
                     sat=0.2, val=0.8, bump=0.3, coord="Object")
else:
    M_steel = mat_basic("metal_pintado", (0.06, 0.065, 0.07), 0.45)
    M_lam = mat_basic("laminado", (0.2, 0.2, 0.195), 0.5)
    M_plas = mat_basic("plastico_gris", (0.18, 0.18, 0.18), 0.6)
tone_var(M_steel, 0.12, wear=True, wear_lift=(0.16, 0.16, 0.155))
tone_var(M_lam, 0.10, wear=True, wear_lift=(0.30, 0.295, 0.285))
tone_var(M_plas, 0.14)
M_dark = tone_var(mat_basic("negro_maquina", (0.025, 0.026, 0.028), 0.4, spec=0.5), 0.2, wear=True, wear_lift=(0.09, 0.09, 0.09))
M_white = tone_var(mat_basic("esmalte_maquina", (0.34, 0.345, 0.33), 0.42), 0.08, wear=True, wear_lift=(0.12, 0.12, 0.12))
M_chrome = mat_basic("cromo", (0.55, 0.55, 0.55), 0.25, metal=1.0)
M_paper = tone_var(mat_basic("papel_molde", (0.50, 0.48, 0.44), 0.85), 0.12)
M_card = tone_var(mat_basic("carton_gris", (0.16, 0.15, 0.14), 0.85), 0.2)
M_kraft = tone_var(mat_basic("carton_cajas", (0.22, 0.20, 0.18), 0.85), 0.2)
M_hilos = [tone_var(mat_basic("hilo_%d" % i, c, 0.45), 0.05) for i, c in
           enumerate([(0.62, 0.61, 0.58), (0.03, 0.03, 0.032), (0.30, 0.29, 0.28), (0.45, 0.43, 0.40)])]

def mat_tizada():
    m = mat_basic("papel_tizada", (0.60, 0.60, 0.58), 0.85)
    if not FULL:
        return m
    N, L = nodes_of(m); b = bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord")
    vo = N.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"; vo.inputs["Scale"].default_value = 1 / R(0.8)
    vo.inputs["Randomness"].default_value = 0.6
    L.new(tc.outputs["Object"], vo.inputs["Vector"])
    lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; L.new(vo.outputs["Distance"], lt.inputs[0]); lt.inputs[1].default_value = 0.008
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; L.new(lt.outputs[0], mx.inputs[0])
    mx.inputs[6].default_value = (0.60, 0.60, 0.58, 1); mx.inputs[7].default_value = (0.30, 0.30, 0.31, 1)
    L.new(mx.outputs[2], b.inputs["Base Color"])
    return m
M_tizada = mat_tizada()

def mat_tela(name="tela", rot90=False, uv=False):
    """MT-1022, foto real. Rapport x A.telax (trampa de escala declarada: a 1:32 real la raya mide 5 px)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = nodes_of(m); b = bsdf_of(m)
    b.inputs["Roughness"].default_value = 0.85
    try:
        b.inputs["Sheen Weight"].default_value = 0.1
    except KeyError:
        pass
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    kx = A.telax
    if uv:   # la malla trae UV en rapports (rollos)
        L.new(tc.outputs["UV"], mp.inputs[0])
        t = tex(N, TELA)
    else:
        mp.inputs["Scale"].default_value = (1 / (0.272 * S * kx), 1 / (0.268 * S * kx), 1 / (0.272 * S * kx))
        if rot90: mp.inputs["Rotation"].default_value = (0, 0, math.pi / 2)
        L.new(tc.outputs["Object"], mp.inputs[0])
        t = tex(N, TELA); t.projection = "BOX"; t.projection_blend = 0.2
    L.new(mp.outputs[0], t.inputs[0])
    col = t.outputs[0]
    if FULL:
        col = tone_socket(N, L, col, 0.10)
        bw = N.new("ShaderNodeRGBToBW"); L.new(t.outputs[0], bw.inputs[0])
        bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25; L.new(bw.outputs[0], bp.inputs["Height"])
        L.new(bp.outputs[0], b.inputs["Normal"])
    L.new(col, b.inputs["Base Color"])
    return m
M_tela = mat_tela()
M_tela_r = mat_tela("tela_r", True)
M_tela_uv = mat_tela("tela_uv", uv=True)

def mat_roll_end():
    """Canto del rollo: espiral de capas de la tela (anillos)."""
    m = mat_basic("tela_canto_rollo", (0.20, 0.16, 0.16), 0.9)
    if not FULL:
        return m
    N, L = nodes_of(m); b = bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord")
    wv = N.new("ShaderNodeTexWave"); wv.wave_type = "RINGS"; wv.rings_direction = "Z"
    wv.inputs["Scale"].default_value = 1 / R(0.9); wv.inputs["Distortion"].default_value = 1.5
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; L.new(wv.outputs["Fac"], mx.inputs[0])
    mx.inputs[6].default_value = (0.17, 0.13, 0.13, 1); mx.inputs[7].default_value = (0.36, 0.32, 0.29, 1)
    L.new(mx.outputs[2], b.inputs["Base Color"])
    return m
M_roll_end = mat_roll_end()

def mat_cloth(name, col, rough=0.85):
    """Ropa de las figuras: neutro con temperatura, sheen, manchas de uso y arrugas en bump.
    Coordenadas Object = metros reales de la figura (el objeto va escalado x S)."""
    m = mat_basic(name, col, rough)
    b = bsdf_of(m)
    try:
        b.inputs["Sheen Weight"].default_value = 0.06   # v3: con 0,35 (tinte blanco) la ropa oscura se leía crema bajo las prácticas
    except KeyError:
        pass
    if not FULL:
        return m
    N, L = nodes_of(m)
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 14.0; nz.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], nr.inputs[0]); nr.inputs[3].default_value = 0.85; nr.inputs[4].default_value = 1.12
    vm = N.new("ShaderNodeVectorMath"); vm.operation = "SCALE"; vm.inputs[0].default_value = col
    L.new(nr.outputs[0], vm.inputs["Scale"])
    L.new(tone_socket(N, L, vm.outputs[0], 0.12), b.inputs["Base Color"])
    wv = N.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 30.0; wv.inputs["Distortion"].default_value = 9.0; wv.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    ad = N.new("ShaderNodeMath"); ad.operation = "ADD"; L.new(wv.outputs["Fac"], ad.inputs[0]); L.new(nz.outputs[0], ad.inputs[1])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.45; L.new(ad.outputs[0], bp.inputs["Height"])
    L.new(bp.outputs[0], b.inputs["Normal"])
    return m
# ---------------------------------------------------------------- CAJA
box_parts = []
if FULL:
    M_box = mat_carbon("carbon_ext")
    M_box_in = mat_carbon("carbon_int", base=(0.10, 0.098, 0.095))
    M_canto = mat_canto()
else:
    M_box = mat_basic("carbon_ext", (0.045, 0.044, 0.043), 0.72, spec=0.35)
    M_box_in = mat_basic("carbon_int", (0.10, 0.098, 0.095), 0.75, spec=0.35)
    M_canto = mat_basic("canto", (0.20, 0.185, 0.165), 0.9)

def board(name, size, loc, canto_axis, rot=(0, 0, 0), inner_face=None, parent=None, cantos=((2, 1),)):
    """Plancha de cartón: caras grandes carbón, caras de corte (canto) con material de canto.
    canto_axis: eje del espesor (0/1/2). Atributos cu/cv para el patrón del corrugado."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges], cuts=6, use_grid_fill=True)
    cu = bm.faces.layers.float.new("dummy") if False else None
    bm.to_mesh(me); bm.free()
    me.materials.append(M_box); me.materials.append(M_canto); me.materials.append(M_box_in)
    ax = canto_axis
    for p in me.polygons:
        n = p.normal
        if abs(n[ax]) > 0.9:
            p.material_index = 0
            if inner_face is not None and (n[ax] > 0) == (inner_face > 0):
                p.material_index = 2
        else:
            # solo los cortes reales muestran el corrugado; los pliegues (esquinas, bisagra) son carbón
            is_cut = any(abs(n[a_]) > 0.9 and (n[a_] > 0) == (sg > 0) for a_, sg in cantos)
            p.material_index = 1 if is_cut else 0
    # atributos de punto: cu = coordenada a lo largo (m), cv = 0..1 a través del espesor (0 = cara exterior)
    a_u = me.attributes.new("cu", "FLOAT", "POINT"); a_v = me.attributes.new("cv", "FLOAT", "POINT")
    for i, v in enumerate(me.vertices):
        c = v.co
        others = [k for k in range(3) if k != ax]
        # a lo largo: la coordenada que varía en esa cara lateral; se usa la suma (sirve para ambas)
        a_u.data[i].value = c[others[0]] + c[others[1]] + 0.0
        t = (c[ax] / size[ax]) + 0.5
        if inner_face is not None and inner_face < 0:
            t = 1 - t
        a_v.data[i].value = t
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    coll("caja").objects.link(o)
    if parent: o.parent = parent
    md = o.modifiers.new("bev", "BEVEL"); md.width = 0.0012; md.segments = 2; md.limit_method = "ANGLE"
    if FULL:
        tx = bpy.data.textures.new(name + "_bulge", "CLOUDS"); tx.noise_scale = 0.25
        dm = o.modifiers.new("bulge", "DISPLACE"); dm.texture = tx; dm.strength = 0.0012; dm.mid_level = 0.5
        dm.texture_coords = "GLOBAL"
    box_parts.append(o)
    return o


# ---------------------------------------------------------------- CAJA: geometría por variante
if TAPA:
    board("pared_frente", (BW, T, BH - T), (0, -BD / 2 + T / 2, T + (BH - T) / 2), 1, inner_face=+1)
    board("pared_fondo", (BW, T, BH - T), (0, BD / 2 - T / 2, T + (BH - T) / 2), 1, inner_face=-1)
    board("pared_izq", (T, BD - 2 * T, BH - T), (-BW / 2 + T / 2, 0, T + (BH - T) / 2), 0, inner_face=+1)
    board("pared_der", (T, BD - 2 * T, BH - T), (BW / 2 - T / 2, 0, T + (BH - T) / 2), 0, inner_face=-1)
    board("fondo", (BW, BD, T), (0, 0, T / 2), 2, inner_face=+1)
    LID_ANG = math.radians(A.lid)
    hinge = bpy.data.objects.new("bisagra", None); coll("caja").objects.link(hinge)
    hinge.location = (0, BD / 2, BH)
    LW, LD = BW + 0.004, BD + 0.004
    lid = board("tapa", (LW, LD, T), (0, -LD / 2, T / 2), 2, inner_face=-1, parent=hinge, cantos=((0, 1), (0, -1)))
    FLAP = 0.036
    flap_piv = bpy.data.objects.new("solapa_piv", None); coll("caja").objects.link(flap_piv)
    flap_piv.parent = hinge; flap_piv.location = (0, -LD, 0.0)
    flap_piv.rotation_euler = (math.radians(-10), 0, 0)
    board("solapa", (LW - 0.012, T * 0.8, FLAP), (0, T * 0.4 + 0.001, -FLAP / 2 + T * 0.2), 1, inner_face=+1, parent=flap_piv, cantos=((0, 1), (0, -1), (2, -1)))
    hinge.rotation_euler = (-LID_ANG, 0, 0)
    _e = 0.0003
    for nm_, sz_, lc_ in (("forro_fondo", (IW, 0.0004, BH - T), (0, BD / 2 - T - _e, T + (BH - T) / 2)),
                          ("forro_frente", (IW, 0.0004, BH - T), (0, -BD / 2 + T + _e, T + (BH - T) / 2)),
                          ("forro_izq", (0.0004, ID, BH - T), (-BW / 2 + T + _e, 0, T + (BH - T) / 2)),
                          ("forro_der", (0.0004, ID, BH - T), (BW / 2 - T - _e, 0, T + (BH - T) / 2))):
        box_obj(nm_, sz_, lc_, M_box_in, cname="interior")
    cyl_obj("pliegue", T * 0.55, BW - 0.004, (0, BD / 2 - T / 2, BH + 0.0005), M_box, rot=(0, math.radians(90), 0), cname="caja")
    if FULL:
        sd = lid.modifiers.new("comba", "SIMPLE_DEFORM"); sd.deform_method = "BEND"; sd.angle = math.radians(1.6)
        sd.deform_axis = "X"
    XA, XB, YA, YB = -IW / 2, IW / 2, -ID / 2, ID / 2
else:
    # la misma caja MUESTRA parada sobre una punta: el fondo queda atrás, la tapa abre como una puerta (bisagra a la derecha)
    PW, PD, PH = BD, BH, BW          # 0,40 de ancho, 0,27 de profundidad, 0,56 de alto
    BW, BD, BH = PW, PD, PH
    HW = PH - T    # las paredes llegan hasta abajo de la tapa de arriba
    board("pared_fondo", (PW, T, HW), (0, PD / 2 - T / 2, HW / 2), 1, inner_face=-1, cantos=())
    board("pared_izq", (T, PD - T, HW), (-PW / 2 + T / 2, -T / 2, HW / 2), 0, inner_face=+1, cantos=((1, -1), (2, 1)))
    board("pared_der", (T, PD - T, HW), (PW / 2 - T / 2, -T / 2, HW / 2), 0, inner_face=-1, cantos=((1, -1), (2, 1)))
    board("pared_piso", (PW - 2 * T, PD - T, T), (0, -T / 2, T / 2), 2, inner_face=+1, cantos=((1, -1),))
    # tapa de arriba = la tapa de la caja MG: plancha con bisagra (pliegue) en la pared del fondo, cantos de corte a los costados,
    # pliegue adelante y solapa de cierre que entra detrás del frente. Cerrada en este cuadro; --toplid la abre (bisagra atrás).
    tpiv = bpy.data.objects.new("bisagra_arriba", None); coll("caja").objects.link(tpiv)
    tpiv.location = (0, PD / 2, HW + 0.0006)   # la tapa apoya: línea de sombra de 0,6 mm sobre las paredes
    TLD = PD + T + 0.001
    board("techo_tapa", (PW + 0.003, TLD, T), (0, -TLD / 2, T / 2), 2, inner_face=-1, parent=tpiv, cantos=((0, 1), (0, -1)))
    cyl_obj("techo_pliegue_fondo", T * 0.55, PW - 0.002, (0, -T * 0.45, T * 0.45), M_box, rot=(0, math.radians(90), 0), cname="caja").parent = tpiv
    cyl_obj("techo_pliegue_frente", T * 0.55, PW + 0.001, (0, -TLD + T * 0.45, T * 0.45), M_box, rot=(0, math.radians(90), 0), cname="caja").parent = tpiv
    fpiv = bpy.data.objects.new("techo_solapa_piv", None); coll("caja").objects.link(fpiv)
    fpiv.parent = tpiv; fpiv.location = (0, -PD + 0.0012, 0.0)
    TFL = 0.02
    board("techo_solapa", (PW - 2 * T - 0.004, T * 0.8, TFL), (0, T * 0.4, -TFL / 2), 1, inner_face=+1, parent=fpiv,   # cara exterior (carbón) hacia la boca
          cantos=((0, 1), (0, -1), (2, -1)))
    tpiv.rotation_euler = (-math.radians(A.toplid), 0, 0)
    if FULL:
        tl_ = bpy.data.objects["techo_tapa"]
        sd = tl_.modifiers.new("comba", "SIMPLE_DEFORM"); sd.deform_method = "BEND"; sd.angle = math.radians(0.8); sd.deform_axis = "X"
    hinge = bpy.data.objects.new("bisagra", None); coll("caja").objects.link(hinge)
    hinge.location = (-PW / 2 - 0.0015, -PD / 2 - T / 2 - 0.0005, 0.0)
    LW, LH = PW + 0.004, PH + 0.004
    lid = board("tapa", (LW, T, LH), (LW / 2, 0, LH / 2 - 0.002), 1, inner_face=+1, parent=hinge, cantos=((2, 1), (2, -1)))
    FLAP = 0.036
    flap_piv = bpy.data.objects.new("solapa_piv", None); coll("caja").objects.link(flap_piv)
    flap_piv.parent = hinge; flap_piv.location = (LW, 0.0, 0.0)
    flap_piv.rotation_euler = (0, 0, math.radians(10))
    board("solapa", (T * 0.8, FLAP, LH - 0.012), (-T * 0.4, FLAP / 2 + T * 0.3, LH / 2), 0, inner_face=+1, parent=flap_piv,
          cantos=((1, 1), (2, 1), (2, -1)))
    hinge.rotation_euler = (0, 0, -math.radians(A.door))
    cyl_obj("pliegue", T * 0.55, PH - 0.002, (-PW / 2 + T * 0.2, -PD / 2 - T * 0.3, PH / 2), M_box, cname="caja")
    if FULL:
        sd = lid.modifiers.new("comba", "SIMPLE_DEFORM"); sd.deform_method = "BEND"; sd.angle = math.radians(1.2)
        sd.deform_axis = "Z"
    _e = 0.0003
    for nm_, sz_, lc_ in (("forro_fondo", (PW - 2 * T, 0.0004, PH - 2 * T), (0, PD / 2 - T - _e, PH / 2)),
                          ("forro_izq", (0.0004, PD - T, PH - 2 * T), (-PW / 2 + T + _e, -T / 2, PH / 2)),
                          ("forro_der", (0.0004, PD - T, PH - 2 * T), (PW / 2 - T - _e, -T / 2, PH / 2)),
                          ("forro_techo", (PW - 2 * T, PD - T, 0.0004), (0, -T / 2, PH - T - _e))):
        box_obj(nm_, sz_, lc_, M_box_in, cname="interior")
    # v3: el forro del techo es la cara interior de la tapa de arriba: se abre con ella (si no, la boca de arriba queda tapada)
    fo_t = bpy.data.objects["forro_techo"]; fo_t.parent = tpiv
    fo_t.location = (0, -T / 2 - PD / 2, -_e - 0.0006); fo_t.rotation_euler = (0, 0, 0)
    XA, XB, YA, YB = -PW / 2 + T, PW / 2 - T, -PD / 2, PD / 2 - T

# ================================================================ MAQUETA 1:32 — piezas
PP = 0.06 * A.prac

SKINS = [mat_basic("piel_%d" % i, c, 0.5) for i, c in enumerate([(0.40, 0.31, 0.27), (0.29, 0.215, 0.18), (0.17, 0.125, 0.105), (0.35, 0.265, 0.225)])]
for m_ in SKINS:   # piel de figura pintada: color de piel pero apagado, para que la tela siga siendo lo más saturado
    b_ = bsdf_of(m_); c_ = b_.inputs["Base Color"].default_value; g_ = 0.2126 * c_[0] + 0.7152 * c_[1] + 0.0722 * c_[2]
    b_.inputs["Base Color"].default_value = tuple(g_ + (c_[k] - g_) * 0.6 for k in range(3)) + (1,)
HAIRS = [mat_basic("pelo_%d" % i, c, 0.45) for i, c in enumerate([(0.03, 0.028, 0.027), (0.09, 0.075, 0.065), (0.25, 0.245, 0.24), (0.15, 0.115, 0.09)])]
SHIRTS = [mat_cloth("remera_%d" % i, c) for i, c in enumerate(
    [(0.20, 0.20, 0.197), (0.085, 0.087, 0.09), (0.27, 0.27, 0.265), (0.05, 0.052, 0.055), (0.14, 0.14, 0.139), (0.22, 0.22, 0.216),
     (0.06, 0.066, 0.08), (0.12, 0.126, 0.132)])]   # ropa de trabajo: grises y carbones (más oscuros: bajo 3500 K los claros se leían beige)
PANTS = [mat_cloth("pantalon_%d" % i, c, 0.8) for i, c in enumerate([(0.045, 0.05, 0.06), (0.12, 0.12, 0.12), (0.07, 0.068, 0.066), (0.03, 0.03, 0.032)])]
M_shoe = mat_basic("zapato", (0.02, 0.02, 0.02), 0.45)
M_apron = mat_cloth("delantal", (0.36, 0.36, 0.355))
APRONS = [M_apron, mat_cloth("delantal_1", (0.10, 0.10, 0.102))]

def seg(bm, a, b, r1, r2, mat_i, segs=10):
    a, b = Vector(a), Vector(b)
    d = b - a; L_ = d.length
    if L_ < 1e-6: return
    geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=L_)
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    M = Matrix.Translation((a + b) / 2) @ rot
    bmesh.ops.transform(bm, matrix=M, verts=geom["verts"])
    for f in {f for v in geom["verts"] for f in v.link_faces}:
        f.material_index = mat_i; f.smooth = True

def ball(bm, c, r, mat_i, sx=1, sy=1, sz=1):
    geom = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=9, radius=r)
    M = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.transform(bm, matrix=M, verts=geom["verts"])
    for f in {f for v in geom["verts"] for f in v.link_faces}:
        f.material_index = mat_i; f.smooth = True

def skin_obj(name, pts, edges, radii, mat, parent, disp=0.0, disp_scale=0.06):
    """Prenda continua: Skin modifier sobre un esqueleto de puntos + subdivisión + arrugas (displace)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], edges, [])
    o = bpy.data.objects.new(name, me); coll("interior").objects.link(o); o.parent = parent
    sk = o.modifiers.new("skin", "SKIN"); sk.use_smooth_shade = True; sk.branch_smoothing = 0.6
    d = me.skin_vertices[0].data
    for i, r in enumerate(radii):
        d[i].radius = r if isinstance(r, tuple) else (r, r)
        d[i].use_root = (i == 0)
    sb = o.modifiers.new("sub", "SUBSURF"); sb.levels = 1; sb.render_levels = 2
    if disp > 0 and FULL:
        tx = bpy.data.textures.new(name + "_arrugas", "CLOUDS"); tx.noise_scale = disp_scale; tx.noise_depth = 2
        dm = o.modifiers.new("arrugas", "DISPLACE"); dm.texture = tx; dm.strength = disp; dm.mid_level = 0.5
        dm.texture_coords = "LOCAL"
    me.materials.append(mat)
    return o

# ---- v3: figuras de maqueta pintada (registro Preiser): cuerpos MPFB2 (CC0) posados con su rig -> figuras3.py -> figuras3.blend
FIGD = {}
with bpy.data.libraries.load(os.path.join(HERE, "figuras3.blend"), link=False) as (src_, dst_):
    dst_.objects = [n for n in src_.objects if n.startswith("fig_")]
for o_ in dst_.objects:
    if o_ is None: continue
    o_.data.use_fake_user = True
    FIGD[o_.name] = (o_.data, {k: (list(v) if hasattr(v, "__len__") else v) for k, v in o_.items()})
    bpy.data.objects.remove(o_)
POSEMAP = {"lean": ["fig_M1_lean", "fig_F1_lean"], "smooth": ["fig_M2_smooth"], "iron": ["fig_F1_iron", "fig_M1_iron"],
           "pack": ["fig_F2_pack"], "seat": ["fig_F1_seat", "fig_F2_seat", "fig_M1_seat"], "box": ["fig_M2_box"],
           "roll": ["fig_M1_roll"], "inspect": ["fig_F2_inspect"]}
ALIAS = {"carry": "box", "push": "box", "look": "smooth", "stand": "inspect"}

def figure(name, pose, loc, yaw, shirt=0, pants=0, apron=False, h=1.72, pick=None):
    """Figura pintada en metros reales dentro de un empty escalado x S (y = adelante). Devuelve (root, manos en coords de la figura).
    Malla compartida por pose; los materiales van por objeto (piel, pelo, camisa, pantalón, zapato, delantal, antebrazo)."""
    rs = srng(name)
    pose = ALIAS.get(pose, pose)
    opts = POSEMAP[pose]
    key = opts[(pick if pick is not None else rs.randrange(len(opts))) % len(opts)]
    me_, props = FIGD[key]
    root = bpy.data.objects.new(name, None); coll("interior").objects.link(root)
    root.scale = (S, S, S); root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw))
    ob = bpy.data.objects.new(name + "_cuerpo", me_); coll("interior").objects.link(ob); ob.parent = root
    skin = SKINS[rs.randrange(len(SKINS))]
    sh = SHIRTS[shirt % len(SHIRTS)]
    mats = [skin, HAIRS[rs.randrange(len(HAIRS))], sh, PANTS[pants % len(PANTS)], M_shoe, APRONS[rs.randrange(len(APRONS))],
            skin if rs.random() < 0.3 else sh]
    for i, sl in enumerate(ob.material_slots):
        sl.link = "OBJECT"; sl.material = mats[i]
    for k, v in props.items():
        root[k] = v
    return root, [Vector(props["mano_R"]), Vector(props["mano_L"])]

def prism(name, pts, thick, loc, rot=(0, 0, 0), mat=None, k=S, cname="interior"):
    """Pieza plana (molde, pieza cortada, camisa colgada) desde un contorno en metros reales."""
    bm = bmesh.new()
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    vs = [bm.verts.new(((x - cx) * k, (y - cy) * k, 0)) for x, y in pts]
    f = bm.faces.new(vs); bm.normal_update()
    if f.normal.z < 0: f.normal_flip()
    ret = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, thick), verts=nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    coll(cname).objects.link(o)
    if mat: me.materials.append(mat)
    return o

SHAPES = {
    "delantero": [(0, 0), (0.30, 0), (0.31, 0.50), (0.27, 0.55), (0.23, 0.58), (0.22, 0.66), (0.13, 0.70), (0.07, 0.65), (0.04, 0.61), (0, 0.61)],
    "espalda": [(0, 0), (0.58, 0), (0.59, 0.50), (0.52, 0.58), (0.50, 0.68), (0.36, 0.72), (0.22, 0.72), (0.08, 0.68), (0.06, 0.58), (-0.01, 0.50)],
    "manga": [(0.05, 0), (0.29, 0), (0.34, 0.44), (0.28, 0.52), (0.17, 0.57), (0.06, 0.52), (0.0, 0.44)],
    "cuello": [(0, 0), (0.44, 0), (0.44, 0.05), (0.40, 0.09), (0.04, 0.09), (0, 0.05)],
    "colgada": [(-0.2, 0), (0.2, 0), (0.21, 0.52), (0.25, 0.16), (0.31, 0.18), (0.27, 0.64), (0.18, 0.73), (0.06, 0.77), (0, 0.75),
                (-0.06, 0.77), (-0.18, 0.73), (-0.27, 0.64), (-0.31, 0.18), (-0.25, 0.16), (-0.21, 0.52)],
}

def bundle(nm, shape, c, rotz, layers=1, mat=None, thick=0.012):
    """Paquete de piezas cortadas: capas apenas desalineadas (R13)."""
    rs = srng(nm)
    for i in range(layers):
        prism(nm, SHAPES[shape], R(thick), c + Vector((R(rs.uniform(-0.015, 0.015)), R(rs.uniform(-0.015, 0.015)), i * R(thick))),
              rot=(0, 0, rotz + math.radians(rs.uniform(-1.5, 1.5))), mat=mat or M_tela)

def roll(name, c, axis="x", length=1.5, r=0.14):
    """Rollo de tela con UV propia: la raya (paralela a la urdimbre) da la vuelta al rollo; cantos con la espiral."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rr, hh = R(r), R(length)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=28, radius1=rr, radius2=rr, depth=hh)
    uv = bm.loops.layers.uv.new("UVMap")
    kx = A.telax
    for f in bm.faces:
        if abs(f.normal.z) > 0.9:
            f.material_index = 1; f.smooth = False; continue
        f.smooth = True
        cen = f.calc_center_median(); ac = math.atan2(cen.y, cen.x)
        for lp in f.loops:
            a = math.atan2(lp.vert.co.y, lp.vert.co.x)
            if a - ac > math.pi: a -= 2 * math.pi
            if a - ac < -math.pi: a += 2 * math.pi
            lp[uv].uv = (lp.vert.co.z / (0.272 * S * kx), a * rr / (0.268 * S * kx))
    bm.to_mesh(me); bm.free()
    me.materials.append(M_tela_uv); me.materials.append(M_roll_end)
    o = bpy.data.objects.new(name, me); coll("interior").objects.link(o); o.location = c
    rs = srng(name + str(c.x) + str(c.y))
    spin = rs.uniform(0, math.pi * 2)
    o.rotation_mode = "ZYX"      # primero el giro sobre su propio eje, después se acuesta
    if axis == "x":
        o.rotation_euler = (math.radians(rs.uniform(-1.2, 1.2)), math.radians(90), spin)
    elif axis == "y":
        o.rotation_euler = (math.radians(-90), math.radians(rs.uniform(-1.2, 1.2)), spin)
    else:
        o.rotation_euler = (math.radians(rs.uniform(-1.5, 1.5)), math.radians(rs.uniform(-1.5, 1.5)), spin)
    tb = cyl_obj(name + "_tubo", rr * 0.28, hh + R(0.03), c, M_kraft, verts=12)
    tb.rotation_mode = "ZYX"; tb.rotation_euler = o.rotation_euler
    return o

def roll_pyramid(nm, c, rows=(3, 2, 1), length=1.5, r=0.14):
    """Pila de rollos acostados (eje x), escalonada de adelante hacia atrás."""
    rs = srng(nm)
    d = R(2 * r)
    for lev, n in enumerate(rows):
        for i in range(n):
            y = c.y + (i + lev * 0.5) * d
            z = c.z + R(r) + lev * d * 0.87
            roll("%s_%d_%d" % (nm, lev, i), Vector((c.x + R(rs.uniform(-0.06, 0.06)), y, z)), "x", length, r)

def bolt_stack(nm, c, n=7, size=(1.45, 0.55, 0.085), yaw=0.0):
    """Pila de piezas de tela dobladas (R13: capas desalineadas)."""
    rs = srng(nm)
    for i in range(n):
        box_obj(nm, (R(size[0]), R(size[1]), R(size[2])),
                c + Vector((R(rs.uniform(-0.035, 0.035)), R(rs.uniform(-0.03, 0.03)), R(size[2] * (i + 0.5)))),
                M_tela_r, bevel=R(0.03), rot=(0, 0, yaw + math.radians(rs.uniform(-1.5, 1.5))))

def pallet(nm, c, yaw=0.0, w=1.2, d=1.0):
    root = bpy.data.objects.new(nm, None); coll("interior").objects.link(root)
    root.location = c; root.rotation_euler = (0, 0, yaw)
    for i in range(5):
        o = box_obj(nm + "_tabla", (R(w), R(0.14), R(0.022)), (0, R(-d / 2 + 0.07 + i * (d - 0.14) / 4), R(0.133)), M_kraft); o.parent = root
    for j in (-1, 0, 1):
        o = box_obj(nm + "_taco", (R(w), R(0.1), R(0.1)), (0, R(j * (d / 2 - 0.05)), R(0.061)), M_kraft); o.parent = root
    return R(0.144)

def cone_thread(nm, c, mat):
    return cyl_obj(nm, R(0.034), R(0.11), c + Vector((0, 0, R(0.055))), mat, verts=14, r2=R(0.014))

def scissors(nm, c, yaw):
    root = bpy.data.objects.new(nm, None); coll("interior").objects.link(root)
    root.location = c; root.rotation_euler = (0, 0, yaw)
    for s in (-1, 1):
        o = box_obj(nm + "_hoja", (R(0.16), R(0.014), R(0.004)), (R(0.07), 0, R(0.003 + 0.002 * (s + 1))), M_chrome,
                    rot=(0, 0, math.radians(5 * s))); o.parent = root
        o = cyl_obj(nm + "_ojo", R(0.03), R(0.008), (R(-0.04), R(0.022 * s), R(0.004)), M_dark, verts=12); o.parent = root

def cutter(nm, c, yaw, rail_z=None):
    """Cortadora vertical de cuchilla recta sobre el tendido."""
    root = bpy.data.objects.new(nm, None); coll("interior").objects.link(root)
    root.location = c; root.rotation_euler = (0, 0, yaw)
    parts = [box_obj(nm + "_base", (R(0.26), R(0.17), R(0.02)), (0, 0, R(0.01)), M_chrome, bevel=R(0.005)),
             box_obj(nm + "_col", (R(0.035), R(0.03), R(0.30)), (0, R(0.04), R(0.17)), M_steel),
             box_obj(nm + "_cuchilla", (R(0.006), R(0.035), R(0.22)), (0, R(0.005), R(0.13)), M_chrome),
             box_obj(nm + "_motor", (R(0.13), R(0.12), R(0.13)), (0, R(0.03), R(0.37)), M_dark, bevel=R(0.015)),
             cyl_obj(nm + "_manija", R(0.012), R(0.18), (0, R(0.12), R(0.40)), M_dark, rot=(0, math.radians(90), 0), verts=8)]
    for p_ in parts: p_.parent = root
    if rail_z is not None:
        o = cyl_obj(nm + "_cable", R(0.01), rail_z - c.z - R(0.43), (0, R(0.03), R(0.43) + (rail_z - c.z - R(0.43)) / 2), M_dark, verts=6)
        o.parent = root

def practical(name, pos, Tk, power, cone_r=R(0.22), cone_h=R(0.2), spot=math.radians(95), stem_to=None, pfrac=0.08):
    """Lámpara de puesto: cono de chapa pintada + lámpara emisiva + spot (+ puntual chica dentro del cono)."""
    c = cyl_obj(name + "_cono", cone_r * 0.25, cone_h, (pos[0], pos[1], pos[2] + cone_h / 2), M_steel, verts=20)
    me = c.data; bm = bmesh.new(); bm.from_mesh(me)
    for v_ in bm.verts:
        if v_.co.z < 0: v_.co.x *= 4.0; v_.co.y *= 4.0
    bottom = [f for f in bm.faces if f.normal.z < -0.9]
    bmesh.ops.delete(bm, geom=bottom, context="FACES_ONLY")
    bm.to_mesh(me); bm.free()
    sol = c.modifiers.new("sol", "SOLIDIFY"); sol.thickness = R(0.01)
    bulb_mat = bpy.data.materials.new(name + "_bulbo"); bulb_mat.use_nodes = True
    N, L = nodes_of(bulb_mat)
    em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = (*light_col(Tk), 1); em.inputs[1].default_value = 6.0
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL"); L.new(em.outputs[0], out.inputs[0])
    cyl_obj(name + "_bulbo", R(0.05), R(0.04), (pos[0], pos[1], pos[2] + R(0.03)), bulb_mat, verts=12)
    ld = bpy.data.lights.new(name, "SPOT"); ld.energy = power; ld.spot_size = spot; ld.spot_blend = 0.6
    ld.shadow_soft_size = R(0.08); ld.color = light_col(Tk)
    lo = bpy.data.objects.new(name, ld); lo.location = (pos[0], pos[1], pos[2] + R(0.02))
    coll("luces_int").objects.link(lo)
    pd = bpy.data.lights.new(name + "_p", "POINT"); pd.energy = power * pfrac; pd.shadow_soft_size = R(0.04); pd.color = light_col(Tk)
    po = bpy.data.objects.new(name + "_p", pd); po.location = (pos[0], pos[1], pos[2] + R(0.05))
    coll("luces_int").objects.link(po)
    if stem_to is not None:
        a = Vector(stem_to); bb = Vector((pos[0], pos[1], pos[2] + cone_h))
        d = bb - a
        s = cyl_obj(name + "_barra", R(0.02), d.length, (a + bb) / 2, M_steel, verts=8)
        s.rotation_euler = d.normalized().to_track_quat("Z", "Y").to_euler()
    return lo

def cutting_table(nm, c, length=6.5, lamps=3, ops=((-1.8, "lean", 0, 0), (0.3, "lean", 3, 1), (2.3, "look", 2, 0)), ceiling=None):
    """Mesa de corte: tendido (urdimbre a lo largo), tizada a medio tender, cortadora, tijeras, pesas, paquetes cortados."""
    rs = srng(nm)
    ct_len, ct_w, ct_h = R(length), R(1.8), R(0.88)
    box_obj(nm + "_tapa", (ct_len, ct_w, R(0.05)), c + Vector((0, 0, ct_h - R(0.025))), M_lam, bevel=R(0.01))
    nlegs = max(3, int(length / 2) + 1)
    for ix in range(nlegs):
        for iy in (-1, 1):
            box_obj(nm + "_pata", (R(0.06), R(0.06), ct_h - R(0.05)),
                    c + Vector((-ct_len / 2 + R(0.2) + ix * (ct_len - R(0.4)) / (nlegs - 1), iy * (ct_w / 2 - R(0.1)), (ct_h - R(0.05)) / 2)), M_steel)
    box_obj(nm + "_trav", (ct_len - R(0.3), R(0.05), R(0.05)), c + Vector((0, 0, R(0.2))), M_steel)
    # estante bajo la mesa con rollos de reserva
    box_obj(nm + "_estante", (ct_len - R(0.3), ct_w - R(0.3), R(0.02)), c + Vector((0, 0, R(0.22))), M_lam)
    for i in range(int(length / 1.7)):
        roll(nm + "_reserva%d" % i, c + Vector((-ct_len / 2 + R(0.95) + i * R(1.65), rs.uniform(-1, 1) * R(0.25), R(0.23) + R(0.14))), "x")
    tl = ct_len * 0.8
    tx0 = -ct_len / 2 + R(0.25)
    box_obj(nm + "_tendido", (tl, R(1.52), R(0.03)), c + Vector((tx0 + tl / 2, 0, ct_h + R(0.015))), M_tela_r, bevel=R(0.006))
    # tizada (papel con el marcado) sobre la mitad del tendido, con el sobrante enrollado
    tz = tl * 0.3
    box_obj(nm + "_tizada", (tz, R(1.5), R(0.003)), c + Vector((tx0 + tl - tz / 2, 0, ct_h + R(0.032))), M_tizada)
    cyl_obj(nm + "_tizada_rollo", R(0.05), R(1.5), c + Vector((tx0 + tl - tz, 0, ct_h + R(0.08))), M_tizada, rot=(math.radians(90), 0, 0), verts=16)
    # portarrollo con el rollo que alimenta el tendido
    roll(nm + "_rollo", c + Vector((ct_len / 2 - R(0.35), 0, ct_h + R(0.45))), "y", 1.55, 0.16)
    for iy in (-1, 1):
        box_obj(nm + "_portarrollo", (R(0.05), R(0.05), R(0.5)), c + Vector((ct_len / 2 - R(0.35), iy * R(0.86), ct_h + R(0.25))), M_steel)
    # herramientas y trabajo encima
    cutter(nm + "_cortadora", c + Vector((tx0 + tl * 0.28, R(0.25), ct_h + R(0.03))), math.radians(rs.uniform(-30, 30)),
           rail_z=(ceiling if ceiling else c.z + R(2.1)))
    scissors(nm + "_tijera", c + Vector((tx0 + tl * 0.55, -R(0.45), ct_h + R(0.036))), rs.uniform(0, 6.28))
    for i in range(4):
        box_obj(nm + "_pesa", (R(0.16), R(0.08), R(0.05)), c + Vector((tx0 + R(0.3) + i * tl * 0.12, R(0.62) * (1 if i % 2 else -1), ct_h + R(0.055))),
                M_dark, bevel=R(0.008), rot=(0, 0, rs.uniform(-0.4, 0.4)))
    # paquetes de piezas cortadas, apilados en el extremo libre de la mesa
    xs = -ct_len / 2 + R(0.15)
    for i, shp in enumerate(("delantero", "espalda", "manga", "manga", "cuello")):
        bundle(nm + "_paq%d" % i, shp, c + Vector((tx0 + tl * (0.08 + 0.1 * i), R(rs.uniform(-0.3, 0.3)), ct_h + R(0.03))),
               math.radians(rs.uniform(-20, 20)) + (math.pi / 2 if shp == "cuello" else 0), layers=rs.randint(2, 4))
    # moldes de cartulina encima de la tizada
    for i in range(2):
        prism(nm + "_molde", SHAPES[rs.choice(("delantero", "manga"))], R(0.004),
              c + Vector((tx0 + tl * (0.62 + 0.15 * i), R(rs.uniform(-0.3, 0.3)), ct_h + R(0.036))),
              rot=(0, 0, rs.uniform(0, 6.28)), mat=M_paper)
    for sx in (-1, 1):
        box_obj(nm + "_poste", (R(0.06), R(0.06), R(2.1)), c + Vector((sx * (ct_len / 2 - R(0.3)), ct_w / 2 + R(0.2), R(1.05))), M_steel)
    box_obj(nm + "_riel", (ct_len - R(0.5), R(0.06), R(0.06)), c + Vector((0, ct_w / 2 + R(0.2), R(2.1))), M_steel)
    for i in range(lamps):
        xo = -ct_len / 2 + ct_len * (i + 0.5) / lamps
        practical(nm + "_luz%d" % i, (c.x + xo, c.y + R(0.15), c.z + R(1.8)), TK, PP * 0.72,
                  stem_to=(c.x + xo, c.y + ct_w / 2 + R(0.2), c.z + R(2.07)))
    for j, (xo, pose, sh, pa) in enumerate(ops):
        figure(nm + "_op%d" % j, pose, c + Vector((R(xo), ct_w / 2 + R(0.30), 0)), 180 + rs.uniform(-6, 6), shirt=sh, pants=pa)

def sewing_station(nm, p, yaw_deg, lamp=True, op=True, shirt=0, pants=0):
    """Puesto de costura recta industrial: mesa, máquina con brazo y volante, portaconos, pedal, trabajo encima."""
    rs = srng(nm)
    root = bpy.data.objects.new(nm, None); coll("interior").objects.link(root)
    root.location = p; root.rotation_euler = (0, 0, math.radians(yaw_deg + rs.uniform(-1.5, 1.5)))
    def add(o):
        o.parent = root; return o
    th = R(0.76)
    add(box_obj(nm + "_tapa", (R(1.2), R(0.55), R(0.035)), (0, 0, th), M_lam, bevel=R(0.006)))
    for sx in (-1, 1):
        add(box_obj(nm + "_pata", (R(0.04), R(0.5), R(0.04)), (sx * R(0.52), 0, R(0.03)), M_steel))
        add(box_obj(nm + "_pata2", (R(0.04), R(0.04), th), (sx * R(0.52), 0, th / 2), M_steel))
    add(box_obj(nm + "_cajon", (R(0.32), R(0.4), R(0.12)), (-R(0.35), 0, th - R(0.08)), M_lam, bevel=R(0.006)))
    add(box_obj(nm + "_motor", (R(0.25), R(0.18), R(0.16)), (R(0.22), R(0.05), th - R(0.14)), M_dark, bevel=R(0.01)))
    add(box_obj(nm + "_pedal", (R(0.28), R(0.18), R(0.03)), (R(0.05), -R(0.1), R(0.04)), M_dark, rot=(math.radians(-12), 0, 0)))
    # máquina
    add(box_obj(nm + "_base", (R(0.48), R(0.18), R(0.05)), (0, R(0.02), th + R(0.04)), M_white, bevel=R(0.012)))
    add(box_obj(nm + "_col", (R(0.10), R(0.14), R(0.28)), (R(0.19), R(0.02), th + R(0.2)), M_white, bevel=R(0.02)))
    add(box_obj(nm + "_brazo", (R(0.40), R(0.10), R(0.085)), (R(0.0), R(0.02), th + R(0.32)), M_white, bevel=R(0.025)))
    add(box_obj(nm + "_cab", (R(0.10), R(0.12), R(0.18)), (-R(0.2), R(0.02), th + R(0.27)), M_white, bevel=R(0.02)))
    add(cyl_obj(nm + "_aguja", R(0.008), R(0.1), (-R(0.23), -R(0.02), th + R(0.14)), M_chrome, verts=6))
    add(box_obj(nm + "_prensatela", (R(0.04), R(0.03), R(0.01)), (-R(0.23), -R(0.02), th + R(0.075)), M_chrome))
    add(cyl_obj(nm + "_volante", R(0.065), R(0.035), (R(0.26), R(0.02), th + R(0.29)), M_dark, rot=(0, math.radians(90), 0), verts=20))
    add(box_obj(nm + "_correa", (R(0.02), R(0.02), R(0.36)), (R(0.26), R(0.04), th + R(0.1)), M_dark))
    # portaconos
    add(cyl_obj(nm + "_varilla", R(0.008), R(0.62), (R(0.46), R(0.2), th + R(0.31)), M_chrome, verts=6))
    add(box_obj(nm + "_guia", (R(0.22), R(0.012), R(0.012)), (R(0.43), R(0.2), th + R(0.62)), M_chrome))
    hm = M_hilos[rs.randrange(len(M_hilos))]
    for k_ in range(2):
        add(cone_thread(nm + "_cono%d" % k_, Vector((R(0.36) + k_ * R(0.1), R(0.2), th + R(0.018))), hm))
    # trabajo: prenda bajo el prensatela, paquete de piezas a la izquierda, tijerita, canasto con piezas
    add(prism(nm + "_prenda", SHAPES["delantero"], R(0.006), (-R(0.3), -R(0.1), th + R(0.02)), rot=(0, 0, math.radians(rs.uniform(70, 110))), mat=M_tela))
    for i in range(rs.randint(2, 4)):
        add(prism(nm + "_pila", SHAPES[rs.choice(("manga", "cuello", "delantero"))], R(0.008), (-R(0.45) + R(rs.uniform(-0.02, 0.02)), R(0.12), th + R(0.02) + i * R(0.008)),
                  rot=(0, 0, math.radians(rs.uniform(-10, 10))), mat=M_tela))
    scissors(nm + "_tijerita", Vector((R(0.1), -R(0.18), th + R(0.02))), rs.uniform(0, 6.28))
    bpy.data.objects[nm + "_tijerita"].parent = root
    add(box_obj(nm + "_canasto", (R(0.42), R(0.36), R(0.32)), (R(0.86), -R(0.1), R(0.16)), M_plas, bevel=R(0.01)))
    for i in range(2):
        add(prism(nm + "_canasto_t", SHAPES["espalda"], R(0.02), (R(0.86), -R(0.1), R(0.3) + i * R(0.02)),
                  rot=(0, 0, rs.uniform(0, 6.28)), mat=M_tela, k=S * 0.6))
    add(cyl_obj(nm + "_banco", R(0.18), R(0.04), (-R(0.05), -R(0.62), R(0.44)), M_dark, verts=16))
    add(cyl_obj(nm + "_bancop", R(0.025), R(0.42), (-R(0.05), -R(0.62), R(0.21)), M_steel, verts=8))
    if op:
        fo, _ = figure(nm + "_op", "seat", Vector((0, 0, 0)), 0, shirt=shirt, pants=pants)
        fo.parent = root; fo.location = (-R(0.05), -R(0.62), 0); fo.rotation_euler = (0, 0, math.radians(rs.uniform(-8, 8)))
    if lamp:
        bpy.context.view_layer.update()
        wpos = root.matrix_world @ Vector((-R(0.15), -R(0.08), th + R(0.62)))
        wst = root.matrix_world @ Vector((R(0.45), R(0.24), th + R(0.02)))
        practical(nm + "_luz", tuple(wpos), TK, PP * 0.8, cone_r=R(0.15), cone_h=R(0.15), stem_to=tuple(wst))
    return root

def rack(nm, c, yaw, n=14, length=1.6):
    """Perchero con camisas colgadas (contorno con mangas, en perchas)."""
    rs = srng(nm)
    root = bpy.data.objects.new(nm, None); coll("interior").objects.link(root)
    root.location = c; root.rotation_euler = (0, 0, math.radians(yaw))
    def add(o):
        o.parent = root; return o
    for sx in (-1, 1):
        add(box_obj(nm + "_poste", (R(0.035), R(0.035), R(1.75)), (sx * R(length / 2), 0, R(0.875)), M_steel))
        add(box_obj(nm + "_pie", (R(0.04), R(0.5), R(0.03)), (sx * R(length / 2), 0, R(0.03)), M_steel))
    add(cyl_obj(nm + "_barra", R(0.015), R(length), (0, 0, R(1.72)), M_steel, rot=(0, math.radians(90), 0), verts=8))
    for i in range(n):
        x = -R(length / 2) + R(0.08) + i * R((length - 0.16) / (n - 1)) + R(rs.uniform(-0.02, 0.02))
        o = prism(nm + "_camisa", SHAPES["colgada"], R(0.025), (x, 0, R(1.62) - R(0.4)),
                  rot=(math.radians(90), math.radians(rs.uniform(-2, 2)), math.radians(90 + rs.uniform(-7, 7))), mat=M_tela)
        add(o)
        add(cyl_obj(nm + "_percha", R(0.006), R(0.06), (x, 0, R(1.68)), M_chrome, verts=6))

def moldes_rail(nm, c, length=2.4, n=7):
    """Moldes de cartulina colgados de un riel en la pared (típico de la sala de corte)."""
    rs = srng(nm)
    cyl_obj(nm + "_riel", R(0.02), R(length), c, M_steel, rot=(0, math.radians(90), 0), verts=8)
    for i in range(n):
        x = c.x - R(length / 2) + R(0.15) + i * R((length - 0.3) / (n - 1))
        prism(nm + "_molde", SHAPES[rs.choice(("delantero", "espalda", "manga", "manga"))], R(0.003),
              Vector((x, c.y - R(0.02) - i * R(0.004), c.z - R(0.42))),
              rot=(math.radians(90), math.radians(rs.uniform(-4, 4)), 0), mat=M_paper)

def mg_box(nm, c, yaw=0.0):
    box_obj(nm, (R(0.56), R(0.40), R(0.33)), c + Vector((0, 0, R(0.165))), M_box, bevel=R(0.01), rot=(0, 0, yaw))

def box_pallet(nm, c, levels=3, yaw=0.0):
    rs = srng(nm)
    h0 = pallet(nm + "_pallet", c, yaw)
    for lev in range(levels):
        for ix in range(2):
            for iy in range(2):
                mg_box(nm + "_caja", c + Vector(((ix - 0.5) * R(0.58) + R(rs.uniform(-0.01, 0.01)), (iy - 0.5) * R(0.43), h0 + lev * R(0.335))),
                       yaw + math.radians(rs.uniform(-2, 2)))

def floor_litter(nm, x0, x1, y0, y1, z, n=20):
    rs = srng(nm)
    for i in range(n):
        box_obj(nm, (R(rs.uniform(0.08, 0.3)), R(rs.uniform(0.05, 0.2)), R(0.004)), (rs.uniform(x0, x1), rs.uniform(y0, y1), z + R(0.003)),
                M_tela_r, rot=(0, 0, rs.uniform(0, math.pi)))
    for i in range(n // 3):   # hilos sueltos
        a = rs.uniform(0, math.pi)
        cyl_obj(nm + "_hilo", R(0.004), R(rs.uniform(0.3, 0.7)), (rs.uniform(x0, x1), rs.uniform(y0, y1), z + R(0.004)),
                M_hilos[i % 2], rot=(math.radians(90), 0, a), verts=4)

# ================================================================ MAQUETA — distribución por variante
CU = {}   # blancos de las cámaras de verificación
def area_int(nm, loc, size, energy, rot=(0, 0, 0), sy=None, cname="luces_int", Tk=None):
    d = bpy.data.lights.new(nm, "AREA"); d.shape = "RECTANGLE"; d.size = size; d.size_y = sy or size
    d.energy = energy; d.color = light_col(Tk or TK)
    o = bpy.data.objects.new(nm, d); o.location = loc; o.rotation_euler = rot; coll(cname).objects.link(o)
    return o

if TAPA:
    ZF = BH - FLOOR_D
    box_obj("piso_nave", (IW - 0.001, ID - 0.001, 0.004), (0, 0, ZF - 0.002), M_floor)
    Y0 = -0.07
    # --- primer plano (lo primero que ve la cámara alta pasando el frente): la tela en volumen
    roll_pyramid("pila_rollos_a", Vector((-0.125, -0.124, ZF)), rows=(3, 2, 1))
    roll_pyramid("pila_rollos_b", Vector((-0.073, -0.124, ZF)), rows=(3, 2))
    h0 = pallet("pallet_tela0", Vector((0.075, -0.114, ZF)), math.radians(1.5))
    roll_pyramid("pila_rollos_c", Vector((0.075, -0.114 - R(0.4), ZF + h0)), rows=(3, 2, 1))
    figure("op_rollo", "carry", Vector((0.0, -0.106, ZF)), 250, shirt=4, pants=0)
    bpy.context.view_layer.update()
    fo = bpy.data.objects["op_rollo"]
    roll("rollo_en_mano_a", Vector(fo.matrix_world @ Vector((0.0, 0.35, 1.05))), "x", 1.5, 0.12)
    CU["tela"] = Vector((-0.1, -0.11, ZF + 0.012)); CU["figura"] = fo.location + Vector((0, 0, R(1.0)))
    practical("luz_rollos", (-0.098, -0.105, ZF + R(1.9)), TK, PP * 0.9, stem_to=(-0.098, -ID / 2 + 0.001, ZF + R(2.0)))
    practical("luz_piezas", (0.1, -0.105, ZF + R(1.9)), TK, PP * 0.9, stem_to=(0.1, -ID / 2 + 0.001, ZF + R(2.0)))
    floor_litter("retazo_pp", -0.1, 0.1, -0.125, -0.075, ZF, 22)
    # --- corte
    cutting_table("corte_a", Vector((-0.11, Y0 + 0.035, ZF)), 6.5, 3,
                  ops=((-1.8, "lean", 0, 0), (0.3, "lean", 3, 1), (2.3, "look", 2, 0)))
    root, _, _ = import_gltf(os.path.join(ACT, "polyhaven", "modelos", "industrial_storage_cart", "industrial_storage_cart_2k.gltf"), scale=S)
    CR = Vector((-0.005, Y0 + 0.13, ZF)); place(root, CR, 84)
    for i in range(5):
        roll("rollo_carro%d" % i, CR + Vector((R(-0.55) + i * R(0.27), 0, R(1.05))), "y", 1.5, 0.13)
    figure("op_carro", "push", CR + Vector((R(0.25), R(1.45), 0)), 180 + 84 - 90 + 12, shirt=0, pants=1)
    for i in range(7):
        roll("rollo_parado%d" % i, Vector((-IW / 2 + R(0.25), Y0 + 0.12 + i * R(0.29), ZF + R(0.8))), "z", 1.6, 0.13)
    moldes_rail("moldes", Vector((-0.12, Y0 + 0.07, ZF + R(2.3))), 2.6, 7)
    # --- costura: 2 filas x 4 puestos, operarios de frente a cámara
    k_op = 0
    for row in range(2):
        for col in range(4):
            p = Vector((0.06 + col * R(1.5), Y0 + 0.03 + row * R(1.75), ZF))
            has_op = srng("st%d%d" % (row, col)).random() < 0.85
            sewing_station("costura_%d_%d" % (row, col), p, 180, lamp=True, op=has_op, shirt=k_op, pants=k_op)
            k_op += 1
    figure("op_supervisora", "look", Vector((0.06 + 3 * R(1.5) + R(1.0), Y0 + 0.03 + R(1.75) * 0.5, ZF)), 250, shirt=2, pants=0, apron=True)
    for i, (x, y) in enumerate(((0.10, 0.105), (0.19, 0.105))):
        practical("luz_perchero%d" % i, (x, y, ZF + R(2.0)), TK, PP * 0.9, stem_to=(x, y + R(0.8), ZF + R(2.1)))
        box_obj("poste_perchero%d" % i, (R(0.05), R(0.05), R(2.1)), (x, y + R(0.8), ZF + R(1.05)), M_steel)
    for i, (x, y, yw) in enumerate(((0.10, 0.13, 0), (0.19, 0.13, 0), (0.245, 0.06, 90))):
        rack("perchero%d" % i, Vector((x, y, ZF)), yw)
    figure("op_perchero", "look", Vector((0.145, 0.11, ZF)), 160, shirt=3, pants=1)
    # --- control y empaque (atrás-izquierda)
    root, _, _ = import_gltf(os.path.join(ACT, "polyhaven", "modelos", "metal_office_desk", "metal_office_desk_2k.gltf"), scale=S)
    EP = Vector((-0.15, 0.125, ZF)); place(root, EP, 0)
    desk_h = R(0.788)
    for i in range(5):
        rs_ = srng("dob%d" % i)
        for jn in range(3 + i % 3):
            box_obj("camisa_doblada", (R(0.30), R(0.38), R(0.035)),
                    EP + Vector((-R(0.8) + i * R(0.34) + R(rs_.uniform(-0.01, 0.01)), -R(0.05), desk_h + R(0.02) + jn * R(0.037))), M_tela,
                    bevel=R(0.008), rot=(0, 0, math.radians(rs_.uniform(-3, 3))))
    mg_box("caja_mg_abierta", EP + Vector((R(0.65), -R(0.02), desk_h)))
    figure("op_empaque", "lean", EP + Vector((-R(0.2), R(0.72), 0)), 180, shirt=4, pants=0)
    practical("luz_empaque0", (EP.x - R(0.4), EP.y - R(0.05), ZF + R(1.75)), TK, PP * 0.9, stem_to=(EP.x - R(0.4), EP.y + R(0.6), ZF + R(1.95)))
    practical("luz_empaque1", (EP.x + R(0.5), EP.y - R(0.05), ZF + R(1.75)), TK, PP * 0.9, stem_to=(EP.x + R(0.5), EP.y + R(0.6), ZF + R(1.95)))
    box_obj("poste_empaque", (R(1.2), R(0.06), R(0.06)), EP + Vector((R(0.05), R(0.6), R(1.95))), M_steel)
    for sx in (-R(0.55), R(0.65)):
        box_obj("poste_empaque_v", (R(0.06), R(0.06), R(1.95)), EP + Vector((sx, R(0.6), R(0.975))), M_steel)
    for pi_, (px, py) in enumerate(((-0.235, 0.16), (-0.05, 0.16))):
        box_pallet("pallet_mg%d" % pi_, Vector((px, py, ZF)), 3 + pi_ % 2)
    fo, hh = figure("op_control", "carry", Vector((-0.075, 0.105, ZF)), 200, shirt=1, pants=1)
    hm = fo.matrix_basis @ ((hh[0] + hh[1]) / 2)
    box_obj("caja_en_mano", (R(0.56), R(0.40), R(0.33)), hm + Vector((0, 0, R(0.12))), M_box, bevel=R(0.008), rot=(0, 0, math.radians(200)))
    # --- fondo: estanterías contra la pared de atrás
    for xx in (0.02, 0.07, 0.12, 0.17, 0.22):
        r2, _, _ = import_gltf(os.path.join(ACT, "polyhaven", "modelos", "steel_frame_shelves_01", "steel_frame_shelves_01_2k.gltf"), target=R(1.1))
        place(r2, Vector((xx, ID / 2 - R(0.3), ZF)), 0)
        rs_ = srng("est%.2f" % xx)
        for lev in range(4):
            for k_ in range(3):
                if rs_.random() < 0.8:
                    box_obj("caja_estante", (R(0.3), R(0.35), R(0.28)), (xx - R(0.35) + k_ * R(0.35), ID / 2 - R(0.3), ZF + R(0.12) + lev * R(0.5) + R(0.14)),
                            M_kraft if rs_.random() < 0.5 else M_box, bevel=R(0.01), rot=(0, 0, math.radians(rs_.uniform(-5, 5))))
    for xx in (-0.14, 0.14):
        box_obj("columna", (R(0.3), R(0.3), FLOOR_D - 0.001), (xx, ID / 2 - R(1.0), ZF + (FLOOR_D - 0.001) / 2), M_steel)
    for i, (x_, y_) in enumerate(((-0.02, -0.06), (-0.03, -0.035), (0.03, 0.075), (-0.2, 0.06))):
        box_obj("canasto_suelo", (R(0.6), R(0.4), R(0.35)), (x_, y_, ZF + R(0.175)), M_plas, bevel=R(0.01), rot=(0, 0, srng("cs%d" % i).uniform(-0.3, 0.3)))
        bundle("canasto_suelo_t%d" % i, "espalda", Vector((x_, y_, ZF + R(0.3))), srng("cs%d" % i).uniform(0, 6), layers=3)
    floor_litter("retazo", -0.22, 0.0, -0.075, 0.0, ZF, 26)
    # rebote cálido por zona (luz de puesto devuelta por mesas, tela y piso)
    for nm_, (x_, y_) in (("reb_corte", (-0.11, -0.03)), ("reb_costura", (0.12, 0.0)), ("reb_empaque", (-0.14, 0.12)),
                          ("reb_perchero", (0.15, 0.11)), ("reb_pp_izq", (-0.098, -0.11)), ("reb_pp_der", (0.1, -0.11))):
        area_int(nm_, (x_, y_, ZF + 0.075), 0.12, 0.05 * A.prac)
    # la luz que sale: rebote de la nave encendida hacia la cara interior de la tapa (solo la caja lo recibe)
    rto = area_int("reb_tapa", (0, 0.02, ZF + 0.012), 0.34, 0.4 * A.prac * A.reb, rot=(math.radians(180 - 25), 0, 0), sy=0.2, cname="luces_tapa")
    ad = bpy.data.lights.new("derrame", "AREA"); ad.shape = "RECTANGLE"; ad.size = BW * 0.9; ad.size_y = BD * 0.6
    ad.energy = 0.16 * A.amb; ad.color = (1, 1, 1)
    ao = bpy.data.objects.new("derrame", ad); ao.location = (0, -0.05, BH + 0.25); ao.rotation_euler = (math.radians(-10), 0, 0)
    coll("luces_amb").objects.link(ao)
else:
    # ------------------------------------------------ B: nave de tres plantas en corte (la caja parada)
    SLAB = R(0.35); HFL = R(5.6); RUN = R(5.2)
    LV0 = T + 0.004
    LV1 = LV0 + HFL
    LV2 = LV1 + HFL
    TOP = PH - T
    box_obj("piso_nave0", (XB - XA - 0.0005, YB - YA - 0.0005, 0.004), (0, (YA + YB) / 2, T + 0.002), M_floor)
    YF = YA + R(0.15)     # frente de las losas (un poco adentro del canto de la caja)
    YH = YB - R(1.25)     # borde del hueco de escalera
    s1x0, s1x1 = XA + R(0.5), XA + R(0.5) + RUN          # escalera PB -> 1 (sube hacia +x)
    s2x0, s2x1 = XB - R(0.5), XB - R(0.5) - RUN          # escalera 1 -> 2 (sube hacia -x)
    for i, (lv, hx0, hx1) in enumerate(((LV1, XA, s1x1 + R(0.2)), (LV2, s2x1 - R(0.2), XB)), start=1):
        box_obj("losa%d" % i, (XB - XA - 0.0005, YH - YF, SLAB), (0, (YF + YH) / 2, lv - SLAB / 2), M_floor)
        bx0, bx1 = (hx1, XB) if i == 1 else (XA, hx0)
        box_obj("losa%d_fondo" % i, (bx1 - bx0 - 0.0005, YB - YH, SLAB), ((bx0 + bx1) / 2, (YH + YB) / 2, lv - SLAB / 2), M_floor)
        box_obj("viga%d" % i, (XB - XA - 0.0005, R(0.22), R(0.45)), (0, YF + R(0.2), lv - SLAB - R(0.225)), M_steel)
    def stair(nm, x0, x1, z0, z1, yc, width=1.0):
        run, rise = x1 - x0, z1 - z0
        Ls = math.hypot(run, rise); ang = math.atan2(rise, run)
        for s in (-1, 1):
            box_obj(nm + "_zanca", (Ls, R(0.04), R(0.25)), ((x0 + x1) / 2, yc + s * R(width / 2), (z0 + z1) / 2), M_steel, rot=(0, -ang, 0))
            box_obj(nm + "_pasamanos", (Ls, R(0.035), R(0.035)), ((x0 + x1) / 2, yc + s * R(width / 2), (z0 + z1) / 2 + R(0.95)), M_steel, rot=(0, -ang, 0))
            for t in (0.03, 0.5, 0.97):
                box_obj(nm + "_parante", (R(0.035), R(0.035), R(0.95)), (x0 + run * t, yc + s * R(width / 2), z0 + rise * t + R(0.475)), M_steel)
        n = 18
        for i in range(n):
            t = (i + 0.5) / n
            box_obj(nm + "_peldano", (abs(run) / n * 1.15, R(width), R(0.03)), (x0 + run * t, yc, z0 + rise * t), M_steel)
    YS = YB - R(0.7)
    # bandejas de cables y un conducto bajo cada losa (llenan la altura, dicen "nave")
    for i, zc in enumerate((LV1 - SLAB, LV2 - SLAB, TOP)):
        box_obj("bandeja%d" % i, (XB - XA - 0.002, R(0.3), R(0.08)), (0, YA + R(2.6), zc - R(0.35)), M_steel)
        cyl_obj("conducto%d" % i, R(0.22), XB - XA - 0.002, (0, YA + R(5.2), zc - R(0.4)), M_steel, rot=(0, math.radians(90), 0), verts=20)
        for x_ in (-0.12, 0.0, 0.12):
            box_obj("bandeja%d_colg" % i, (R(0.02), R(0.02), R(0.3)), (x_, YA + R(2.6), zc - R(0.15)), M_steel)
    stair("escalera1", s1x0, s1x1, LV0, LV1, YS)
    stair("escalera2", s2x0, s2x1, LV1, LV2, YS)
    # ---------- planta baja: depósito de tela y corte
    roll_pyramid("pila_rollos_a", Vector((-0.162, YA + R(0.45), LV0)), rows=(3, 2, 1))
    roll_pyramid("pila_rollos_b", Vector((-0.110, YA + R(0.45), LV0)), rows=(3, 2))
    h0 = pallet("pallet_tela0", Vector((0.155, YA + R(0.9), LV0)), math.radians(1.5))
    roll_pyramid("pila_rollos_c", Vector((0.155, YA + R(0.9) - R(0.4), LV0 + h0)), rows=(3, 2, 1))
    h0 = pallet("pallet_tela1", Vector((0.155, YA + R(2.05), LV0)), math.radians(-2))
    bolt_stack("pieza_tela_1", Vector((0.155, YA + R(2.05), LV0 + h0)), n=6)
    for i in range(5):
        roll("rollo_parado%d" % i, Vector((XA + R(0.2) + R(srng("rp%d" % i).uniform(0, 0.12)), YA + R(2.2) + i * R(0.45), LV0 + R(0.8))), "z", 1.6, 0.13)
    cutting_table("corte_a", Vector((0.035, YA + R(3.3), LV0)), 6.0, 3,
                  ops=((-1.6, "lean", 0, 0), (0.6, "lean", 3, 1), (2.2, "look", 2, 0)), ceiling=LV1 - SLAB)
    moldes_rail("moldes", Vector((0.07, YB - R(0.06), LV0 + R(2.5))), 3.0, 8)
    root, _, _ = import_gltf(os.path.join(ACT, "polyhaven", "modelos", "industrial_storage_cart", "industrial_storage_cart_2k.gltf"), scale=S)
    CR = Vector((0.13, YB - R(2.1), LV0)); place(root, CR, 90)
    for i in range(5):
        roll("rollo_carro%d" % i, CR + Vector((R(-0.55) + i * R(0.27), 0, R(1.05))), "y", 1.5, 0.13)
    fo, _ = figure("op_rollo", "roll", Vector((-0.062, YA + R(0.9), LV0)), 112, shirt=4, pants=0)
    bpy.context.view_layer.update()
    piv = bpy.data.objects.new("rollo_hombro_piv", None); coll("interior").objects.link(piv)
    piv.location = fo.matrix_world @ Vector(fo["rollo_c"]); piv.rotation_euler = (0, 0, math.radians(112))
    ro = roll("rollo_en_mano", Vector((0, 0, 0)), "y", 1.5, 0.12)
    ro.parent = piv; bpy.data.objects["rollo_en_mano_tubo"].parent = piv
    for i, (x, y) in enumerate(((-0.14, YA + R(0.8)), (0.155, YA + R(1.3)))):
        practical("luz_pb%d" % i, (x, y, LV0 + R(2.4)), TK, PP * 0.9, stem_to=(x, y, LV1 - SLAB))
    floor_litter("retazo_pb", -0.09, 0.12, YA + R(0.4), YA + R(2.2), LV0, 24)
    # ---------- planta 1: costura
    k_op = 0
    for row in range(2):
        for col in range(5):
            p = Vector((-0.14 + col * R(1.55), YA + R(2.2) + row * R(1.8), LV1))
            has_op = srng("st%d%d" % (row, col)).random() < 0.9
            sewing_station("costura_%d_%d" % (row, col), p, 180, lamp=True, op=has_op, shirt=k_op, pants=k_op)
            k_op += 1
    rack("perchero_paquetes", Vector((0.168, YA + R(2.4), LV1)), 90, n=10, length=1.8)
    fo, hh = figure("op_supervisora", "inspect", Vector((0.115, YA + R(1.3), LV1)), 230, shirt=2, pants=0, apron=True)
    hm = (hh[0] + hh[1]) / 2
    cy_ = sum(p_[1] for p_ in SHAPES["colgada"]) / len(SHAPES["colgada"])
    bpy.context.view_layer.update()
    prism("prenda_control", SHAPES["colgada"], R(0.012), fo.matrix_world @ Vector((0, hm.y + 0.03, hm.z - 0.02 - (0.73 - cy_))),
          rot=(math.radians(90), 0, math.radians(230)), mat=M_tela)
    for i in range(2):
        box_obj("canasto_p1", (R(0.6), R(0.4), R(0.35)), (0.13 + i * R(0.7), YA + R(3.7), LV1 + R(0.175)), M_plas, bevel=R(0.01))
        bundle("canasto_p1_t%d" % i, "espalda", Vector((0.13 + i * R(0.7), YA + R(3.7), LV1 + R(0.3))), 0.3 * i, layers=3)
    practical("luz_p1_perchero", (0.15, YA + R(1.9), LV1 + R(2.3)), TK, PP * 0.8, stem_to=(0.15, YA + R(1.9), LV2 - SLAB))
    floor_litter("retazo_p1", -0.17, 0.08, YA + R(0.5), YA + R(4.5), LV1, 20)
    # ---------- planta 2: plancha, control y empaque
    for i, x in enumerate((-0.16, -0.105)):
        c_ = Vector((x, YA + R(1.9), LV2))
        box_obj("plancha_mesa%d" % i, (R(1.3), R(0.45), R(0.04)), c_ + Vector((0, 0, R(0.9))), M_white, bevel=R(0.02))
        box_obj("plancha_pata%d" % i, (R(0.05), R(0.35), R(0.88)), c_ + Vector((0, 0, R(0.44))), M_steel)
        prism("plancha_prenda%d" % i, SHAPES["espalda"], R(0.008), c_ + Vector((R(-0.15), 0, R(0.925))), rot=(0, 0, math.radians(90)), mat=M_tela)
        box_obj("plancha%d" % i, (R(0.25), R(0.12), R(0.1)), c_ + Vector((R(0.3), R(0.02), R(0.98))), M_dark, bevel=R(0.02))
        cyl_obj("plancha_manguera%d" % i, R(0.012), TOP - (LV2 + R(1.05)), c_ + Vector((R(0.3), R(0.02), (TOP - LV2 - R(1.05)) / 2 + R(1.05))), M_dark, verts=6)
        figure("op_plancha%d" % i, "iron", c_ + Vector((0, R(0.55), 0)), 180, shirt=5 - i, pants=i, pick=i)
        practical("luz_plancha%d" % i, (x, YA + R(1.8), LV2 + R(2.3)), TK, PP * 0.8, stem_to=(x, YA + R(1.8), TOP))
    root, _, _ = import_gltf(os.path.join(ACT, "polyhaven", "modelos", "metal_office_desk", "metal_office_desk_2k.gltf"), scale=S)
    EP = Vector((0.0, YA + R(2.0), LV2)); place(root, EP, 0)
    desk_h = R(0.788)
    for i in range(4):
        rs_ = srng("dob%d" % i)
        for jn in range(3 + i % 3):
            box_obj("camisa_doblada", (R(0.30), R(0.38), R(0.035)),
                    EP + Vector((-R(0.75) + i * R(0.34) + R(rs_.uniform(-0.01, 0.01)), -R(0.08), desk_h + R(0.02) + jn * R(0.037))), M_tela,
                    bevel=R(0.008), rot=(0, 0, math.radians(rs_.uniform(-3, 3))))
    mg_box("caja_mg_abierta", EP + Vector((R(0.6), -R(0.02), desk_h)))
    fo, hh = figure("op_control", "pack", EP + Vector((-R(0.2), R(0.72), 0)), 180, shirt=1, pants=1)
    hm = (hh[0] + hh[1]) / 2; zt = min(fo["mano_R_zmin"], fo["mano_L_zmin"])
    bpy.context.view_layer.update()
    box_obj("camisa_en_mano", (R(0.34), R(0.26), R(zt - 0.788)), fo.matrix_world @ Vector((hm.x, hm.y + 0.02, (zt + 0.788) / 2)), M_tela,
            bevel=R(0.006), rot=(0, 0, math.radians(180 + 4)))
    for i in range(2):
        practical("luz_control%d" % i, (EP.x + (i - 0.5) * R(1.0), EP.y - R(0.1), LV2 + R(2.3)), TK, PP * 0.85, stem_to=(EP.x + (i - 0.5) * R(1.0), EP.y - R(0.1), TOP))
    box_pallet("pallet_mg0", Vector((0.15, YA + R(1.4), LV2)), 3)
    box_pallet("pallet_mg1", Vector((0.15, YA + R(2.8), LV2)), 4)
    fo, hh = figure("op_caja", "box", Vector((0.085, YA + R(1.2), LV2)), 160, shirt=3, pants=2)
    hm = (hh[0] + hh[1]) / 2; xin = min(fo["mano_R_xin"], fo["mano_L_xin"])
    bpy.context.view_layer.update()
    # la caja MG (0,40 de través entre las palmas, 0,56 hacia adelante): las manos la toman de los costados, abajo
    box_obj("caja_en_mano", (R(2 * xin), R(0.56), R(0.33)), fo.matrix_world @ Vector((0, 0.42, hm.z + 0.08)), M_box, bevel=R(0.008),
            rot=(0, 0, math.radians(160)))
    practical("luz_pallets", (0.15, YA + R(2.0), LV2 + R(2.6)), TK, PP * 0.8, stem_to=(0.15, YA + R(2.0), TOP))
    rack("perchero_final0", Vector((-0.13, YA + R(4.2), LV2)), 0, n=14, length=1.8)
    rack("perchero_final1", Vector((-0.06, YA + R(4.6), LV2)), 0, n=14, length=1.8)
    practical("luz_percheros", (-0.1, YA + R(3.9), LV2 + R(2.6)), TK, PP * 0.8, stem_to=(-0.1, YA + R(3.9), TOP))
    # rack de pallets contra el fondo (llena la altura de la planta 2)
    for j, x in enumerate((-0.17, -0.128, -0.086, -0.044, -0.002)):
        box_obj("rack_parante", (R(0.09), R(0.09), R(4.6)), (x, YB - R(1.1), LV2 + R(2.3)), M_steel)
        box_obj("rack_parante", (R(0.09), R(0.09), R(4.6)), (x, YB - R(0.1), LV2 + R(2.3)), M_steel)
    for lev in range(3):
        zb = LV2 + R(0.15 + lev * 1.55)
        for sgn in (1.1, 0.1):
            box_obj("rack_larguero", (R(5.5), R(0.06), R(0.12)), (-0.086, YB - R(sgn), zb), M_steel)
        for q in range(4):
            if srng("rk%d%d" % (lev, q)).random() < 0.85:
                box_pallet("rack_pl%d%d" % (lev, q), Vector((-0.149 + q * 0.042, YB - R(0.6), zb + R(0.06))), 2 + (lev + q) % 2)
    floor_litter("retazo_p2", -0.18, 0.1, YA + R(0.5), YA + R(3.0), LV2, 12)
    CU["tela"] = Vector((-0.136, YA + R(0.8), LV0 + 0.012)); CU["figura"] = Vector((-0.043, YA + R(2.4), LV1 + R(1.0)))
    # rebote cálido por zona y por planta
    for nm_, (x_, y_, z_) in (("reb_pb_izq", (-0.14, YA + 0.03, LV0)), ("reb_pb_der", (0.14, YA + 0.04, LV0)), ("reb_corte", (0.03, YA + 0.1, LV0)),
                              ("reb_p1_a", (-0.09, YA + 0.07, LV1)), ("reb_p1_b", (0.07, YA + 0.07, LV1)),
                              ("reb_p2_a", (-0.13, YA + 0.06, LV2)), ("reb_p2_b", (0.08, YA + 0.06, LV2))):
        area_int(nm_, (x_, y_, z_ + 0.06), 0.1, 0.04 * A.prac, Tk=A.tkreb)
    for i, (lv, h_) in enumerate(((LV0, LV1 - SLAB - LV0), (LV1, LV2 - SLAB - LV1), (LV2, TOP - LV2))):
        for x_ in (-0.1, 0.1):
            area_int("baño_fondo%d" % i, (x_, YB - R(1.6), lv + h_ * 0.8), 0.08, 0.06 * A.prac * A.wash, rot=(math.radians(60), 0, 0), Tk=A.tkamb)
    # la luz que sale: la boca encendida de la nave devuelta hacia la cara interior de la puerta (solo la caja)
    phi = math.radians(A.door)
    dcx = -PW / 2 - 0.0015 + (LW / 2) * math.cos(phi); dcy = -PD / 2 - T / 2 - (LW / 2) * math.sin(phi)
    lx_, ly_ = -PW / 2 + 0.06, YA - 0.004
    rz_ = math.atan2(-(dcx - lx_), dcy - ly_)
    rto = area_int("reb_tapa", (lx_, ly_, PH / 2), 0.1, 0.35 * A.prac * A.reb,
                   rot=(math.radians(90), 0, rz_), sy=PH * 0.8, cname="luces_tapa", Tk=A.tkamb)
    ad = bpy.data.lights.new("derrame", "AREA"); ad.shape = "RECTANGLE"; ad.size = PW * 0.9; ad.size_y = PH * 0.9
    ad.energy = 0.10 * A.amb; ad.color = (1, 1, 1)
    ao = bpy.data.objects.new("derrame", ad); ao.location = (0, YA - 0.35, PH / 2 + 0.08)
    ao.rotation_euler = (math.radians(90 - 8), 0, 0)
    coll("luces_amb").objects.link(ao)
    # v3: llave neutra de estudio que entra por la boca (arriba a la izquierda): da los grises; las prácticas quedan como pozos cálidos
    kd = bpy.data.lights.new("llave_int", "AREA"); kd.shape = "RECTANGLE"; kd.size = 0.3; kd.size_y = 0.45
    kd.energy = 0.8 * A.kint; kd.color = light_col(5600)
    ko = bpy.data.objects.new("llave_int", kd); ko.location = (-0.32, YA - 0.55, PH * 0.95)
    ko.rotation_euler = (Vector((0.03, 0.02, PH * 0.45)) - ko.location).normalized().to_track_quat("-Z", "Y").to_euler()
    coll("luces_amb").objects.link(ko)

# ---------------------------------------------------------------- ESTUDIO (igual que la vuelta 1)
cyc = bpy.data.meshes.new("ciclo"); bm = bmesh.new()
W_ = 14.0; prof = []
for i in range(0, 41):
    t = i / 40
    if t < 0.6:
        prof.append((-3.0 + t / 0.6 * 6.5, 0.0))
    else:
        a = (t - 0.6) / 0.4 * (math.pi / 2)
        prof.append((3.5 + 1.2 * math.sin(a), 1.2 - 1.2 * math.cos(a)))
prof.append((4.7, 7.0))
vs = []
for (y, z) in prof:
    vs.append((bm.verts.new((-W_ / 2, y, z)), bm.verts.new((W_ / 2, y, z))))
for i in range(len(vs) - 1):
    bm.faces.new((vs[i][0], vs[i][1], vs[i + 1][1], vs[i + 1][0]))
bm.to_mesh(cyc); bm.free()
for p in cyc.polygons: p.use_smooth = True
cyco = bpy.data.objects.new("ciclo", cyc); coll("estudio").objects.link(cyco)
M_cyc = mat_basic("ciclo", (0.62, 0.605, 0.585), 0.9, spec=0.2)
cyc.materials.append(M_cyc)
if FULL:
    N, L = nodes_of(M_cyc); b = bsdf_of(M_cyc)
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 3
    mr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], mr.inputs[0]); mr.inputs[3].default_value = 0.97; mr.inputs[4].default_value = 1.03
    vm = N.new("ShaderNodeVectorMath"); vm.operation = "SCALE"; vm.inputs[0].default_value = (0.62, 0.605, 0.585)
    L.new(mr.outputs[0], vm.inputs["Scale"]); L.new(vm.outputs[0], b.inputs["Base Color"])

def area(name, size, loc, target, energy, Tk=5600, sy=None, cname="estudio_luces"):
    d = bpy.data.lights.new(name, "AREA"); d.shape = "RECTANGLE"; d.size = size; d.size_y = sy or size
    d.energy = energy; d.color = light_col(Tk)
    o = bpy.data.objects.new(name, d); o.location = loc
    dirv = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
    coll(cname).objects.link(o)
    return o

TGT = Vector((0, 0, 0.3))
key = area("llave", 1.2, (-1.7, -1.5, 2.3), TGT, 90 * A.key, 5600)
fill = area("relleno", 1.6, (2.4, -1.9, 1.1), TGT, 90 * A.key / A.fill_ratio * 1.35, 5600)
rim = area("rim", 0.3, (1.3, 1.9, 1.5), TGT, 16 * A.key, 7200, sy=1.6)
bgl = area("fondo_luz", 2.0, (0.0, 1.5, 3.2), (0, 4.0, 1.0), 480 * A.key, 5600)

# light linking: llave, relleno y fondo no entran a la maqueta (bandera del fotógrafo)
rx = bpy.data.collections.new("rx_sin_interior")
rx.children.link(coll("interior"))
rxf = bpy.data.collections.new("rx_relleno")
rxf.children.link(coll("interior"))
for o in bpy.data.objects:
    if o.name.startswith(("tapa", "solapa")):
        rxf.objects.link(o)
try:
    fill.light_linking.receiver_collection = rxf
    for ch in rxf.collection_children: ch.light_linking.link_state = "EXCLUDE"
    for co in rxf.collection_objects: co.light_linking.link_state = "EXCLUDE"
except Exception as e:
    print("rx_relleno:", e)
# la llave tampoco toca la cara interior de la tapa/puerta: ahí manda la luz de la nave
for o in bpy.data.objects:
    if o.name.startswith(("tapa", "solapa")):
        rx.objects.link(o)
for co in rx.collection_objects:
    try: co.light_linking.link_state = "EXCLUDE"
    except Exception as e: print("rx tapa:", e)
for lo in (key, bgl):
    try:
        lo.light_linking.receiver_collection = rx
        lo.light_linking.blocker_collection = None
    except Exception as e:
        print("light linking no disponible:", e)
try:
    for ch in rx.collection_children:
        ch.light_linking.link_state = "EXCLUDE"
except Exception as e:
    print("link_state:", e)
# derrame (y, si no hay 'spill', las prácticas) solo iluminan la maqueta y la caja
SPILL = (not TAPA) if A.spill < 0 else bool(A.spill)
rx2 = bpy.data.collections.new("rx_solo_caja")
rx2.children.link(coll("interior")); rx2.children.link(coll("caja"))
lights_rx2 = list(coll("luces_amb").objects) + ([] if SPILL else list(coll("luces_int").objects))
for lo in lights_rx2:
    try:
        lo.light_linking.receiver_collection = rx2
    except Exception as e:
        print(e)
try:
    for ch in rx2.collection_children:
        ch.light_linking.link_state = "INCLUDE"
except Exception as e:
    print("link_state2:", e)
rx3 = bpy.data.collections.new("rx_solo_tapa"); rx3.children.link(coll("caja"))
try:
    rto.light_linking.receiver_collection = rx3
    for ch in rx3.collection_children: ch.light_linking.link_state = "INCLUDE"
except Exception as e:
    print("rx_tapa:", e)

# ---------------------------------------------------------------- v3: menos sepia — materiales hacia grises neutros
def desat_all(f):
    skip = ("tela", "piel", "pelo", "id", "z_")
    n_ = 0
    for m in bpy.data.materials:
        if not m.use_nodes or m.name.startswith(skip) or "_bulbo" in m.name:
            continue
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b is None: continue
        N, L = nodes_of(m); inp = b.inputs["Base Color"]
        lk = [l for l in m.node_tree.links if l.to_socket == inp]
        hs = N.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = f
        if lk:
            src = lk[0].from_socket; m.node_tree.links.remove(lk[0]); L.new(src, hs.inputs["Color"])
        else:
            hs.inputs["Color"].default_value = inp.default_value
        L.new(hs.outputs["Color"], inp); n_ += 1
    print("desat_all", f, n_, "materiales")
if A.desat < 0.999:
    desat_all(A.desat)

# ---------------------------------------------------------------- CÁMARA 85 mm
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = A.lens; cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 36.0
cam_d.clip_start = 0.05; cam_d.clip_end = 60
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
el, az = math.radians(A.elev), math.radians(A.azim)
look = Vector((A.lookx, A.looky, (ZF if TAPA else PH / 2) + A.lookz))
cam.location = look + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * A.dist
cam.rotation_euler = (look - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
cam_d.shift_y = A.shift; cam_d.shift_x = A.shiftx
tgt = look
if A.closeup:
    tgt = {"esquina": Vector((BW / 2, -BD / 2, BH - 0.02)), "tela": CU["tela"], "figura": CU["figura"]}[A.closeup]
    dcu = 0.35 if A.closeup in ("tela", "figura") else 0.9
    cam.location = tgt + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dcu
    cam.rotation_euler = (tgt - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    cam_d.shift_y = 0.0; cam_d.shift_x = 0.0
cam_d.dof.use_dof = True; cam_d.dof.focus_distance = (cam.location - tgt).length
cam_d.dof.aperture_fstop = 32.0 if A.closeup else 16.0

# ---------------------------------------------------------------- máscaras para medir (rojo caja, verde maqueta, amarillo tela, azul fondo)
if A.ids:
    sc.cycles.samples = 4; sc.cycles.use_denoising = False
    sc.view_settings.view_transform = "Standard"
    cam_d.dof.use_dof = False
    def flat(c):
        m = bpy.data.materials.new("id"); m.use_nodes = True
        N, L = nodes_of(m); out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
        e = N.new("ShaderNodeEmission"); e.inputs[0].default_value = (*c, 1); L.new(e.outputs[0], out.inputs[0])
        return m
    ID_BOX, ID_IN, ID_TELA, ID_BG, ID_TAPA = flat((1, 0, 0)), flat((0, 1, 0)), flat((1, 1, 0)), flat((0, 0, 1)), flat((1, 0, 1))
    ID_FIG = flat((0, 1, 1))
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.name.startswith("fig_"):
            for sl in o.material_slots:
                sl.link = "OBJECT"; sl.material = ID_FIG
    for o in bpy.data.objects:
        if o.type != "MESH" or o.data.name.startswith("fig_"): continue
        cn = o.users_collection[0].name
        is_tela = any(m_ is not None and m_.name.startswith("tela") for m_ in o.data.materials[:1])
        m = (ID_TAPA if o.name.startswith(("tapa", "solapa")) else ID_BOX) if cn == "caja" else (ID_TELA if is_tela else ID_IN) if cn == "interior" else ID_BG
        o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons: p.material_index = 0
    for o in bpy.data.objects:
        if o.type == "LIGHT": o.hide_render = True
    sc.render.image_settings.color_depth = "8"

if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=A.blend)
if A.out:
    sc.render.filepath = A.out
    bpy.ops.render.render(write_still=True)
    print("RENDER_OK", A.out)
