"""Caja-libro MG v3 (PACKAGING_v3.md, responde a F58 "bloque CG" y a CRITICO_v2 P0-2 / P1-2 / P1-3 / P1-7) sobre build3.

Reemplaza la cascara de build3 (paredes de 7 mm a filo) por una caja rigida de verdad, a 40 x 27 x 56 cm:
  - CASCO en L (lomo + tapa de atras) y PUERTA (tapa de adelante): carton gris 3 mm + papel 0,2 mm por cara = 3,4 mm.
    Radio de canto 1,5 mm GEOMETRICO (bevel 3 segmentos, profile 0,5, harden normals); 3 mm donde el papel da la vuelta
    al lomo (en el perfil). Surco de bisagra en la puerta: 6 mm de ancho a 8 mm del lomo, 1 mm de hondo.
  - BANDEJA metida 3 mm adentro de las tapas arriba, abajo y en el canto libre (flota 3 mm: linea oscura en la base).
    Boca con el papel exterior doblado 15 mm hacia adentro (los forros de la nave arrancan 15 mm atras).
  - Exterior soft-touch carbon #2b2a2a (rug 0,62 +-0,04 en manchas de 10 cm, sheen 0,25, diente 0,25 mm, filo bruñido,
    2 marcas de mano en el canto libre). Papel interior negro sin estucar #232222 rug 0,9 (reemplaza el #d1d2d4, luma 166).
  - MG: foil negro tono sobre tono (#1c1c1c rug 0,12 sobre 0,62), 46 % del ancho (circulo 185 mm), centro optico +2 %,
    bajorrelieve 0,8 mm con talud (bump de la mascara suavizada). MAGONTEX del lomo: foil peltre mate (metal 1, #8a8a8c,
    rug 0,30), 48 % del alto. Logos = mascaras de los PDF reales (logos/hacer_mascaras.py), nunca redibujados.
  - Cinta de grosgrain 16 mm en lazo, acanalada a lo ancho (0,8 mm), cae en S floja; forma "flex" para el temblor.
Uso: import caja03; CJ = caja03.aplicar(G, A, light_col)
"""
import math
import os

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "logos")


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


C_ST = tuple(c * 0.72 for c in srgb("2b2a2a"))   # #2b2a2a bajo esta llave leia gris medio (t1): 0,72x = el carbon de la v2
C_INT = srgb("232222")
C_FOIL = srgb("1c1c1c")
C_PELTRE = srgb("8a8a8c")
C_CINTA = srgb("2e2c2b")
TC = 0.0034      # tapa: carton 3 mm + papel 0,2 x 2
OV = 0.003       # las tapas sobresalen 3 mm de la bandeja
R_BEV = 0.0015
R_LOMO = 0.003
YG = 0.0005      # linea de cierre entre la puerta y la boca de la bandeja
MG_FRAC = 0.46   # circulo del MG / ancho de la puerta
MG_CIRC_ART = 355.0 / 463.0   # circulo / ancho del arte (medido en v2)
LOMO_FRAC = 0.48
LET_ART = 0.84   # letras / alto del arte del canto (v2)


def _N(m):
    return m.node_tree.nodes, m.node_tree.links


def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _set(b, name, v):
    try:
        b.inputs[name].default_value = v
    except KeyError as e:
        print("input", name, e)


def _math(N, L, op, a, b=None, clamp=False):
    n = N.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            L.new(v, n.inputs[i])
    return n.outputs[0]


def _img(N, fn):
    t = N.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(LOG, fn), check_existing=True)
    t.image.colorspace_settings.name = "Non-Color"
    t.interpolation = "Cubic"; t.extension = "CLIP"
    return t


def _uv(N, L, ax_u, sgn_u, c_u, w_u, ax_v, c_v, w_v):
    """(u, v) de la imagen desde coordenadas Object (metros del objeto): u = 0,5 + sgn (x - c) / w."""
    tc = N.new("ShaderNodeTexCoord")
    sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sp.inputs[0])
    u = _math(N, L, "ADD", _math(N, L, "MULTIPLY", _math(N, L, "SUBTRACT", sp.outputs[ax_u], c_u), sgn_u / w_u), 0.5)
    v = _math(N, L, "ADD", _math(N, L, "MULTIPLY", _math(N, L, "SUBTRACT", sp.outputs[ax_v], c_v), 1.0 / w_v), 0.5)
    cm = N.new("ShaderNodeCombineXYZ"); L.new(u, cm.inputs[0]); L.new(v, cm.inputs[1])
    return cm.outputs[0]


def mat_st(name, logo=None, manos=None):
    """Soft-touch carbon. logo = dict(uv=(...), mask, bump, color, rough, metal, depth). manos = [(x, z)] en coords Object."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = _N(m); b = _bsdf(m)
    _set(b, "Specular IOR Level", 0.35)
    _set(b, "Sheen Weight", 0.06); _set(b, "Sheen Roughness", 0.5); _set(b, "Sheen Tint", (1, 1, 1, 1))
    tc = N.new("ShaderNodeTexCoord")
    # tono parejo (+-1 %)
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 2
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nr = N.new("ShaderNodeMapRange"); L.new(nz.outputs[0], nr.inputs[0]); nr.inputs[3].default_value = 0.99; nr.inputs[4].default_value = 1.01
    col = N.new("ShaderNodeVectorMath"); col.operation = "SCALE"; col.inputs[0].default_value = C_ST
    L.new(nr.outputs[0], col.inputs["Scale"])
    # filo bruñido: mascara por Bevel del shader (1 mm) -> rug 0,5 y 1,2x mas claro (la fibra aplastada)
    bev = N.new("ShaderNodeBevel"); bev.inputs["Radius"].default_value = 0.001; bev.samples = 6
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    L.new(bev.outputs[0], dot.inputs[0]); L.new(geo.outputs["Normal"], dot.inputs[1])
    em = N.new("ShaderNodeMapRange"); L.new(dot.outputs["Value"], em.inputs[0])
    em.inputs[1].default_value = 0.9995; em.inputs[2].default_value = 0.97
    edge = em.outputs[0]
    cmx = N.new("ShaderNodeMix"); cmx.data_type = "RGBA"; L.new(edge, cmx.inputs[0])
    L.new(col.outputs[0], cmx.inputs[6]); cmx.inputs[7].default_value = (*(c * 1.8 for c in C_ST), 1)
    base_col = cmx.outputs[2]
    # rugosidad 0,62 +-0,04 en manchas de ~10 cm; filo 0,5
    rn = N.new("ShaderNodeTexNoise"); rn.inputs["Scale"].default_value = 10; rn.inputs["Detail"].default_value = 1
    L.new(tc.outputs["Object"], rn.inputs["Vector"])
    rr = N.new("ShaderNodeMapRange"); L.new(rn.outputs[0], rr.inputs[0])
    rr.inputs[1].default_value = 0.3; rr.inputs[2].default_value = 0.7; rr.inputs[3].default_value = 0.60; rr.inputs[4].default_value = 0.68
    rough = rr.outputs[0]
    if manos:   # marcas de mano: rug -0,08 en dos manchas de ~25 mm
        acc = None
        for (mx, mz) in manos:
            vm = N.new("ShaderNodeVectorMath"); vm.operation = "DISTANCE"
            L.new(tc.outputs["Object"], vm.inputs[0]); vm.inputs[1].default_value = (mx, 0.0, mz)
            # distancia en xz: el eje y (espesor) es chico, alcanza con la distancia 3D
            mk = N.new("ShaderNodeMapRange"); L.new(vm.outputs["Value"], mk.inputs[0])
            mk.inputs[1].default_value = 0.025; mk.inputs[2].default_value = 0.008
            acc = mk.outputs[0] if acc is None else _math(N, L, "MAXIMUM", acc, mk.outputs[0])
        rough = _math(N, L, "SUBTRACT", rough, _math(N, L, "MULTIPLY", acc, 0.08))
    rmx = N.new("ShaderNodeMix"); rmx.data_type = "FLOAT"; L.new(edge, rmx.inputs[0])
    L.new(rough, rmx.inputs[2]); rmx.inputs[3].default_value = 0.42
    rough = rmx.outputs[0]
    # diente del papel: bump de 0,25 mm
    fb = N.new("ShaderNodeTexNoise"); fb.inputs["Scale"].default_value = 4000; fb.inputs["Detail"].default_value = 4
    fb.inputs["Roughness"].default_value = 0.55
    L.new(tc.outputs["Object"], fb.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.06; bp.inputs["Distance"].default_value = 0.0002
    L.new(fb.outputs[0], bp.inputs["Height"])
    normal = bp.outputs[0]
    metal = None; sheen = None; spec = None
    if logo:
        vec = _uv(N, L, *logo["uv"])
        mk = _img(N, logo["mask"]); L.new(vec, mk.inputs[0])
        k = mk.outputs["Color"]
        c2 = N.new("ShaderNodeMix"); c2.data_type = "RGBA"; L.new(k, c2.inputs[0])
        L.new(base_col, c2.inputs[6]); c2.inputs[7].default_value = (*logo["color"], 1)
        base_col = c2.outputs[2]
        r2 = N.new("ShaderNodeMix"); r2.data_type = "FLOAT"; L.new(k, r2.inputs[0])
        L.new(rough, r2.inputs[2]); r2.inputs[3].default_value = logo["rough"]
        rough = r2.outputs[0]
        s2 = N.new("ShaderNodeMix"); s2.data_type = "FLOAT"; L.new(k, s2.inputs[0])
        s2.inputs[2].default_value = 0.06; s2.inputs[3].default_value = 0.0
        sheen = s2.outputs[0]
        sp2 = N.new("ShaderNodeMix"); sp2.data_type = "FLOAT"; L.new(k, sp2.inputs[0])
        sp2.inputs[2].default_value = 0.35; sp2.inputs[3].default_value = logo.get("spec", 0.5)
        spec = sp2.outputs[0]
        if logo.get("metal", 0) > 0:
            metal = _math(N, L, "MULTIPLY", k, logo["metal"])
        if logo.get("depth", 0) > 0:     # estampado: el logo queda hundido, con talud (mascara suavizada)
            bk = _img(N, logo["bump"]); L.new(vec, bk.inputs[0])
            inv = _math(N, L, "SUBTRACT", 1.0, bk.outputs["Color"])
            bp2 = N.new("ShaderNodeBump"); bp2.inputs["Strength"].default_value = 1.0
            bp2.inputs["Distance"].default_value = logo["depth"]
            L.new(inv, bp2.inputs["Height"]); L.new(normal, bp2.inputs["Normal"])
            normal = bp2.outputs[0]
    L.new(base_col, b.inputs["Base Color"])
    L.new(rough, b.inputs["Roughness"])
    L.new(normal, b.inputs["Normal"])
    if sheen is not None:
        L.new(sheen, b.inputs["Sheen Weight"])
    if spec is not None:
        L.new(spec, b.inputs["Specular IOR Level"])
    if metal is not None:
        L.new(metal, b.inputs["Metallic"])
    return m


def mat_interior():
    m = bpy.data.materials.new("papel_interior_232222"); m.use_nodes = True
    b = _bsdf(m); N, L = _N(m)
    _set(b, "Base Color", (*C_INT, 1)); _set(b, "Roughness", 0.9); _set(b, "Specular IOR Level", 0.3); _set(b, "Sheen Weight", 0.0)
    tc = N.new("ShaderNodeTexCoord")
    fb = N.new("ShaderNodeTexNoise"); fb.inputs["Scale"].default_value = 2600; fb.inputs["Detail"].default_value = 5
    L.new(tc.outputs["Object"], fb.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.2; bp.inputs["Distance"].default_value = 0.0001
    L.new(fb.outputs[0], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    return m


def mat_cinta():
    m = bpy.data.materials.new("grosgrain_2e2c2b"); m.use_nodes = True
    b = _bsdf(m); N, L = _N(m)
    _set(b, "Base Color", (*C_CINTA, 1)); _set(b, "Roughness", 0.45); _set(b, "Specular IOR Level", 0.4)
    _set(b, "Sheen Weight", 0.4); _set(b, "Sheen Roughness", 0.35)
    tc = N.new("ShaderNodeTexCoord")
    wv = N.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 1.0 / 0.0008    # acanalado a lo ancho, periodo 0,8 mm (coordenada u a lo largo)
    wv.inputs["Distortion"].default_value = 0.0
    L.new(tc.outputs["UV"], wv.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6; bp.inputs["Distance"].default_value = 0.00015
    L.new(wv.outputs["Color"], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    return m


def mat_linea(rgb):
    m = bpy.data.materials.new("linea_luz_v3"); m.use_nodes = True
    N, L = _N(m)
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    for n in list(N):
        if n.type == "BSDF_PRINCIPLED":
            N.remove(n)
    # intensidad que cae hacia las esquinas: sin(pi u^2,4)^0,7 (pico hacia el canto libre, donde la ranura abre mas)
    tc = N.new("ShaderNodeTexCoord")
    sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sp.inputs[0])
    k = _math(N, L, "POWER", _math(N, L, "SINE", _math(N, L, "MULTIPLY", _math(N, L, "POWER", sp.outputs[0], 2.4), math.pi)), 0.7)   # pico en u = 0,75
    em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = (*rgb, 1)
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L.new(k, mul.inputs[0]); mul.inputs[1].default_value = 1.0
    L.new(mul.outputs[0], em.inputs[1])
    L.new(em.outputs[0], out.inputs[0])
    return m, mul.inputs[1]


# ---------------------------------------------------------------- geometria
def _prism(name, prof, z0, z1, coll, parent=None, bevel=R_BEV, angle=50.0):
    """Extruye un perfil (x, y) CCW entre z0 y z1; bevel geometrico con harden normals."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in prof]
    hi = [bm.verts.new((x, y, z1)) for x, y in prof]
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    if parent:
        o.parent = parent
    if bevel:
        md = o.modifiers.new("bisel", "BEVEL"); md.width = bevel; md.segments = 3; md.profile = 0.5
        md.limit_method = "ANGLE"; md.angle_limit = math.radians(angle); md.harden_normals = True; md.use_clamp_overlap = True
    return o


def _arc(cx, cy, r, a0, a1, n=5):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _ring_tray(name, x0, x1, z0, z1, xi0, xi1, zi0, zi1, y0, y1, coll):
    """Bandeja: anillo rectangular (afuera x0..x1, z0..z1; adentro xi0..xi1, zi0..zi1) extruido en y (y0 boca .. y1 fondo)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    O = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    I = [(xi0, zi0), (xi1, zi0), (xi1, zi1), (xi0, zi1)]
    def vv(p, y):
        return bm.verts.new((p[0], y, p[1]))
    Of, If = [vv(p, y0) for p in O], [vv(p, y0) for p in I]
    Ob, Ib = [vv(p, y1) for p in O], [vv(p, y1) for p in I]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((Of[i], Of[j], If[j], If[i]))     # canto de la boca
        bm.faces.new((Ob[j], Ob[i], Ib[i], Ib[j]))     # atras (tapado)
        bm.faces.new((Of[j], Of[i], Ob[i], Ob[j]))     # exterior
        bm.faces.new((If[i], If[j], Ib[j], Ib[i]))     # interior
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    md = o.modifiers.new("bisel", "BEVEL"); md.width = R_BEV; md.segments = 3; md.profile = 0.5
    md.limit_method = "ANGLE"; md.angle_limit = math.radians(50); md.harden_normals = True; md.use_clamp_overlap = True
    return o


def _rx_exclude(rx_name, obj):
    rx = bpy.data.collections.get(rx_name)
    if rx is None:
        return
    rx.objects.link(obj)
    for co in rx.collection_objects:
        try:
            co.light_linking.link_state = "EXCLUDE"
        except Exception as e:
            print("rx", rx_name, e)


def aplicar(G, A, light_col):
    PW, PD, PH, T = G["PW"], G["PD"], G["PH"], G["T"]
    coll = G["coll"]; C = coll("caja")
    hinge = bpy.data.objects["bisagra"]
    # ---- fuera la cascara de build3
    for nm in ("pared_izq", "pared_der", "pared_piso", "pared_fondo", "techo_tapa", "techo_pliegue_fondo", "techo_pliegue_frente",
               "techo_solapa", "tapa", "solapa", "pliegue"):
        o = bpy.data.objects.get(nm)
        if o:
            o.hide_render = True; o.hide_viewport = True
    YDI = -PD / 2 - YG            # cara interior de la puerta cerrada
    XL, XR = -PW / 2, PW / 2
    # ---- casco en L: lomo (x = XL .. XL+TC) + tapa de atras (y = PD/2-TC .. PD/2); el papel da la vuelta con radio 3 mm
    prof = [(XL, YDI + R_BEV * 0)]
    prof += _arc(XL + R_LOMO, PD / 2 - R_LOMO, R_LOMO, math.pi, math.pi / 2)
    prof += [(XR, PD / 2), (XR, PD / 2 - TC), (XL + TC, PD / 2 - TC), (XL + TC, YDI)]
    casco = _prism("casco_lomo_atras", prof, 0.0, PH, C)
    # ---- puerta (tapa de adelante) en coordenadas de la bisagra: x 0..PW, y -TC/2..TC/2 (afuera = -y), z 0..PH
    hinge.location = (XL, YDI - TC / 2, 0.0)
    h = TC / 2
    g0, g1, gd = 0.008, 0.014, 0.001
    pd = [(0.0, h)]
    pd += _arc(R_LOMO, -h + R_LOMO, R_LOMO, math.pi, 1.5 * math.pi)
    pd += [(g0, -h), (g0 + 0.0012, -h + gd), (g1 - 0.0012, -h + gd), (g1, -h), (PW, -h), (PW, h)]
    puerta = _prism("puerta", pd, 0.0, PH, C, parent=hinge)
    # ---- bandeja: 3 mm adentro de las tapas arriba, abajo y en el canto libre; paredes hasta la cara interior de build3
    tray = _ring_tray("bandeja", XL + TC, XR - OV, OV, PH - OV, XL + T, XR - T, T, PH - T, -PD / 2, PD / 2 - TC, C)
    # ---- los forros de la nave arrancan 15 mm atras de la boca: se ve el papel exterior doblado hacia adentro
    FOLD = 0.015
    for nm in ("forro_izq", "forro_der", "forro_techo"):
        o = bpy.data.objects.get(nm)
        if not o:
            continue
        dy = o.dimensions.y
        if dy > 0.05:
            s = (dy - FOLD) / dy
            o.scale.y *= s
            o.location.y += FOLD / 2 * (1 if o.parent is None else 1)
    # ---- materiales
    M_st = mat_st("soft_touch_2b2a2a")
    W_MG = PW * MG_FRAC                      # circulo 185 mm
    ART = W_MG / MG_CIRC_ART                 # ancho del arte cuadrado
    zc = PH / 2 + 0.02 * PH                  # centro optico 2 % mas arriba
    M_door = mat_st("puerta_MG_foil", logo=dict(uv=(0, 1.0, PW / 2, ART, 2, zc, ART), mask="magontex_monograma_MG_tapa_mask.png",
                                                  bump="magontex_monograma_MG_tapa_bump.png", color=C_FOIL, rough=0.12, spec=0.5, depth=0.0008),
                    manos=[(PW - 0.03, PH * 0.55 + 0.035), (PW - 0.022, PH * 0.55 - 0.03)])
    let_h = PH * LOMO_FRAC; art_h = let_h / LET_ART; art_w = art_h * 110.0 / 163.0
    yc = (YDI - TC + PD / 2) / 2
    M_lomo = mat_st("lomo_MAGONTEX_peltre", logo=dict(uv=(1, -1.0, yc, art_w, 2, PH / 2, art_h), mask="magontex_logotipo_vertical_canto_mask.png",
                                                       bump="magontex_logotipo_vertical_canto_bump.png", color=C_PELTRE, rough=0.30, metal=1.0,
                                                       spec=0.5, depth=0.0))
    M_int = mat_interior()
    casco.data.materials.append(M_st); casco.data.materials.append(M_lomo)
    for p in casco.data.polygons:
        p.material_index = 1 if (p.normal.x < -0.99 and p.center.y < PD / 2 - R_LOMO - 1e-4) else 0
    puerta.data.materials.append(M_st); puerta.data.materials.append(M_door)
    for p in puerta.data.polygons:
        p.material_index = 1 if (p.normal.y < -0.99 and p.center.x > g1) else 0
    tray.data.materials.append(M_st)
    print("CAJA v3: MG circulo %.0f mm (%.0f %%), arte %.0f mm, centro z %.0f mm; lomo letras %.0f mm (%.0f %%), arte %.0fx%.0f mm" % (
        W_MG * 1000, MG_FRAC * 100, ART * 1000, zc * 1000, let_h * 1000, LOMO_FRAC * 100, art_w * 1000, art_h * 1000))
    # ---- papel interior de la puerta: marco soft-touch de 12 mm alrededor
    fme = bpy.data.meshes.new("puerta_papel_int")
    bm = bmesh.new()
    M12 = 0.012
    vs = [bm.verts.new(v) for v in ((M12, h + 0.00008, M12), (PW - M12, h + 0.00008, M12), (PW - M12, h + 0.00008, PH - M12), (M12, h + 0.00008, PH - M12))]
    bm.faces.new(vs); bm.to_mesh(fme); bm.free()
    if fme.polygons[0].normal.y < 0:
        fme.flip_normals()
    fme.materials.append(M_int)
    fo = bpy.data.objects.new("puerta_papel_int", fme); C.objects.link(fo); fo.parent = hinge
    for rxn in ("rx_sin_interior", "rx_relleno"):
        _rx_exclude(rxn, fo)
    # los forros de la nave (paredes interiores) quedan como estan: son las paredes de la maqueta aprobada
    # ---- cinta de grosgrain en lazo: 16 mm, sale del canto libre a 55 % del alto, 40 mm afuera, cae en S floja
    CW, CT, OUT = 0.016, 0.00035, 0.040
    zc_c = PH * 0.55
    NS = 40
    cme = bpy.data.meshes.new("cinta"); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV")
    # linea media del lazo (coordenadas de la bisagra): sale en +x por la ranura (y ~ +h + 0,25 mm), 5 mm recta y cae
    def mid(s):          # s 0..1 a lo largo de lo que asoma
        x = PW - 0.012 + (OUT + 0.012) * s
        e = max(0.0, (x - (PW + 0.005)) / (OUT - 0.005))
        dz = -0.010 * e * e * (3 - 2 * e)            # caida de la punta (S floja): 10 mm
        dy = -0.004 * e * e                           # se vence hacia la camara por su peso
        return Vector((x, h + 0.00025 + dy, zc_c + dz))
    rows = []; META = []
    for layer, off in ((0, -0.0004), (1, 0.0004)):   # las dos capas del lazo
        row = []
        for i in range(NS + 1):
            s = i / NS
            p = mid(s)
            twist = 0.35 * max(0.0, (p.x - PW) / OUT)   # gira ~20 grados al caer
            wdir = Vector((0.0, math.sin(twist), math.cos(twist)))
            ndir = Vector((0.0, math.cos(twist), -math.sin(twist)))
            a = p + ndir * off - wdir * CW / 2
            b = p + ndir * off + wdir * CW / 2
            row.append((bm.verts.new(a), bm.verts.new(b), s))
            META.append((s, off, -1.0)); META.append((s, off, 1.0))
        rows.append(row)
    L_len = OUT + 0.012
    for row in rows:
        for i in range(NS):
            (a0, b0, s0), (a1, b1, s1) = row[i], row[i + 1]
            f = bm.faces.new((a0, a1, b1, b0))
            for lp, (u, v) in zip(f.loops, ((s0 * L_len, 0), (s1 * L_len, 0), (s1 * L_len, CW), (s0 * L_len, CW))):
                lp[uvl].uv = (u, v)
    # la punta del lazo: une las dos capas
    (a0, b0, _), (a1, b1, _) = rows[0][-1], rows[1][-1]
    f = bm.faces.new((a0, b0, b1, a1))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(cme); bm.free()
    for p in cme.polygons:
        p.use_smooth = True
    cme.materials.append(mat_cinta())
    co = bpy.data.objects.new("cinta", cme); C.objects.link(co); co.parent = hinge
    sol = co.modifiers.new("espesor", "SOLIDIFY"); sol.thickness = CT; sol.offset = 0.0
    co.shape_key_add(name="Basis")
    sk = co.shape_key_add(name="flex"); sk.slider_min = -1.0; sk.slider_max = 1.0
    for i, v in enumerate(cme.vertices):
        e = max(0.0, (v.co.x - PW) / OUT)
        sk.data[i].co = (v.co.x - 0.001 * e ** 3, v.co.y - 0.006 * e * e, v.co.z - 0.004 * e * e)
    # v3.1 (CRITICO_v3 P2-3): forma "cuelga": cuando el iman cede, la cinta se tuerce 90 grados en los primeros 8 mm (el ancho
    # pasa de vertical a horizontal, que es como se puede doblar) y cae por su peso hasta ~78 grados. La punta queda ~11 mm
    # afuera del canto (antes 40 mm): no sale del cuadro con la puerta a 100 grados. Largo de arco conservado.
    sk2 = co.shape_key_add(name="cuelga", from_mix=False); sk2.slider_min = 0.0; sk2.slider_max = 1.0
    L_len = OUT + 0.012; U0 = 0.015; LB = 0.006; LT = 0.006; PHI = math.radians(88.0)
    def _sm(p):
        p = max(0.0, min(1.0, p)); return p * p * (3 - 2 * p)
    NI = 400
    tabla = [(0.0, 0.0, 0.0)]   # (a, dx, dz) integrado a lo largo del arco
    ax_, az_ = 0.0, 0.0
    amax = L_len - U0
    for k in range(1, NI + 1):
        a = amax * k / NI; da = amax / NI
        ph = PHI * _sm((a - da / 2) / LB)
        ax_ += math.cos(ph) * da; az_ += math.sin(ph) * da
        tabla.append((a, ax_, az_))
    for i, (s_, off, sg) in enumerate(META):
        u = L_len * s_
        if u <= U0:
            continue
        a = u - U0
        j = min(NI, int(round(a / amax * NI)))
        _, dx, dz = tabla[j]
        ph = PHI * _sm(a / LB); ps = (math.pi / 2) * _sm(a / LT)
        Cc = Vector((PW + 0.003 + dx, h + 0.00025 - 0.002 * (a / amax) ** 2, zc_c - dz))
        Tt = Vector((math.cos(ph), 0.0, -math.sin(ph)))
        Zp = Vector((math.sin(ph), 0.0, math.cos(ph)))
        Wt = (Zp * math.cos(ps) + Vector((0.0, 1.0, 0.0)) * math.sin(ps)).normalized()
        Nt = Wt.cross(Tt).normalized()
        sk2.data[i].co = Cc + Nt * off + Wt * sg * CW / 2
    print("CUELGA_KEY", len(META), len(cme.vertices), max((sk2.data[i].co - cme.vertices[i].co).length for i in range(len(META))), flush=True)
    # ---- linea de luz (tarjeta declarada): tira vertical en el plano de la ranura, a la altura del canto de la puerta.
    # Desde 12 grados se ve solo lo que la ranura deja ver por encima del canto: alto visible = ranura x tan(12) -> el ancho
    # acompana la apertura real y es 0 contra el iman. Intensidad que cae hacia las esquinas. Color de la boca, techo <= 235.
    lm, lstr = mat_linea(light_col(3000.0))
    lme_ = bpy.data.meshes.new("linea_luz_v3"); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV")
    yl = -PD / 2 - 0.0002
    x0, x1, z0, z1 = XL + TC + 0.004, XR - 0.001, PH - 0.006, PH - 0.0002
    vs = [bm.verts.new(v) for v in ((x0, yl, z0), (x1, yl, z0), (x1, yl, z1), (x0, yl, z1))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uvl].uv = uv
    bm.to_mesh(lme_); bm.free()
    lme_.materials.append(lm)
    lo = bpy.data.objects.new("linea_luz_v3", lme_); coll("luces_boca").objects.link(lo)
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission"):
        try:
            setattr(lo, attr, False)
        except Exception as e:
            print(attr, e)
    return dict(cinta=co, cinta_key=sk, cuelga_key=sk2, linea_str=lstr, forro=fo, puerta=puerta, casco=casco, bandeja=tray, W_MG=W_MG, zc=zc)
