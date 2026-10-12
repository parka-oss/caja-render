"""Chequeo de paquete [XG·792d]: corre DESPUES de esc032.py en el mismo Blender y falla si falta un archivo.
  blender -b --factory-startup --python escenas-caja/esc01/esc032.py --python tools/chequeo.py -- --mode medir --frames 135
Lista cada imagen, biblioteca y archivo externo que la escena usa (ARCHIVO <ruta>) y sale con codigo 3 si alguno no existe.
Blender NO falla solo con una textura faltante (la pinta de rosa): por eso este chequeo."""
import os, sys
import bpy

faltan, usados = [], set()
for im in bpy.data.images:
    if im.source in ("FILE", "SEQUENCE", "MOVIE") and not im.packed_file and im.filepath:
        p = os.path.normpath(bpy.path.abspath(im.filepath))
        usados.add(p)
        if not os.path.exists(p):
            faltan.append(p)
for lib in bpy.data.libraries:
    p = os.path.normpath(bpy.path.abspath(lib.filepath)); usados.add(p)
    if not os.path.exists(p):
        faltan.append(p)
for p in sorted(usados):
    print("ARCHIVO", p, flush=True)
print("CHEQUEO %d archivos, %d faltan" % (len(usados), len(faltan)), flush=True)
for p in faltan:
    print("FALTA", p, flush=True)
if faltan:
    sys.exit(3)
