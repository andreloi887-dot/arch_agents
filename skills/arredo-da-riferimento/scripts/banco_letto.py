"""Banco di prova da studio (skill arredo-da-riferimento): costruisce solo il pezzo con tessili.py in una scena vuota e lo
rende in 1-2 minuti. Uso: blender -b --python banco_letto.py -- [parametro=valore ...] out=<png>
Valori buoni del 2026-11-17 come predefiniti nel codice o in SKILL.md."""
import bpy, sys, time
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rilievo-urbano", "scripts", "blender"))
from mathutils import Vector
import tessili
scn = bpy.context.scene
for o in list(scn.objects): bpy.data.objects.remove(o, do_unlink=True)
def mat(nome, col, r=0.9):
    m = bpy.data.materials.new(nome); m.use_nodes = True; b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = r
    if nome in ("lenzuolo", "plaid", "cuscino"): b.inputs["Sheen Weight"].default_value = 0.6
    return m
def scatola(nome, x0, x1, y0, y1, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)); o = bpy.context.object
    o.scale = (x1 - x0, y1 - y0, z1 - z0); o.data.materials.append(m)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = 0.01; bv.segments = 3; return o
P = dict(a.split("=") for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a)
f = lambda k, d: float(P.get(k, d))
bianco = mat("lenzuolo", (0.80, 0.78, 0.75)); plaid = mat("plaid", (0.30, 0.27, 0.24)); legno = mat("rovere", (0.52, 0.42, 0.31), 0.6)
L, W = 2.1, 1.8; u, v = Vector((1, 0)), Vector((0, 1))
scatola("base", -0.95, 0.80, -0.70, 0.70, 0, 0.12, mat("ombra", (0.05, 0.05, 0.05)))
scatola("piattaforma", -1.0, 1.05, -0.9, 0.9, 0.12, 0.24, legno); scatola("materasso", -0.97, 0.89, -0.76, 0.76, 0.25, 0.45, bianco)
scatola("testata", -1.10, -1.05, -1.45, 1.45, 0.0, 1.0, legno)
t0 = time.time()
mater = (Vector((-0.04, 0)), u, v, 1.86, 1.52, 0.25, 0.45); piatta = (Vector((0.025, 0)), u, v, 2.05, 1.8, 0.12, 0.24); pav = (Vector((0, 0)), u, v, 5, 5, -0.05, 0)
a0, a1 = -0.97 + 0.42, 1.02
pium = tessili.trapunta(scn, "piumone", ((a0 + a1) / 2, 0), u, v, a1 - a0, W - 0.04, 0.50, [mater, piatta, pav], bianco, 0.27,
                        spessore=f("sp", 0.035), pressione=f("pr", 1.5), passo=f("passo", 0.03), piega=f("piega", 0.05), grinze=f("gr", 0.004), fotogrammi=int(f("fot", 110)), tensione=f("te", 8.0))
print("PIUMONE", round(time.time() - t0, 1))
grigio = mat("cuscino", (0.50, 0.48, 0.45))
for k, sb in enumerate((-0.37, 0.37)):
    # guanciali in piedi appoggiati alla testata, cuscini grigi davanti (riferimento)
    tessili.cuscino(scn, f"guanciale {k}", (-0.90, sb, 0.45), Vector((0, 1)), 0.66, 0.50, 0.17, bianco, 0.27, in_piedi=f("ig", 0.55))
    tessili.cuscino(scn, f"cuscino {k}", (-0.66, sb, 0.47), Vector((0, 1)), 0.50, 0.40, 0.13, grigio, 0.27, in_piedi=f("ic", 0.40))
col = tessili.collisore(scn, pium)
if f("risvolto", 0):
    tessili.trapunta(scn, "risvolto", (a0 + 0.20, 0), u, v, 0.34, W - 0.02, 0.62, [pav], bianco, 0.27, spessore=0.05, pressione=2.0, piega=0.05, fotogrammi=70)
b0, b1 = 1.02 - 0.62, 1.02 - 0.08
tessili.telo(scn, "plaid", ((b0 + b1) / 2, 0), u, v, b1 - b0, f("lp", 2.3), 0.80, [pav], plaid, 0.27, spessore=f("spp", 0.015), peso=f("pp", 0.8), piega=f("pg", 0.3),
             fotogrammi=120, passo=0.025, grinze=0.003)
bpy.data.objects.remove(col, do_unlink=True)
print("TUTTO", round(time.time() - t0, 1))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.location = (3.4, 1.2, 1.25); d = Vector((-0.2, 0, 0.4)) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); cam.data.lens = 32
ar = bpy.data.objects.new("area", bpy.data.lights.new("area", "AREA")); ar.data.energy = 600; ar.data.size = 3; ar.location = (2.0, -2.2, 2.8); ar.rotation_euler = (0.8, 0, -0.75); scn.collection.objects.link(ar)
ar2 = bpy.data.objects.new("area2", bpy.data.lights.new("area2", "AREA")); ar2.data.energy = 200; ar2.data.size = 4; ar2.location = (3, 2.5, 2.0); ar2.rotation_euler = (0.9, 0, 2.3); scn.collection.objects.link(ar2)
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True; next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.4
scatola("pavimento", -4, 4, -4, 4, -0.01, 0, mat("pav", (0.55, 0.5, 0.45)))
scn.render.engine = "CYCLES"; scn.cycles.samples = 64; scn.cycles.device = "GPU"
try:
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "OPTIX"; pr.get_devices(); [setattr(d_, "use", True) for d_ in pr.devices]
except Exception as e: print(e)
scn.render.resolution_x, scn.render.resolution_y = 1280, 860
scn.render.filepath = P.get("out"); bpy.ops.render.render(write_still=True); print("FATTO")
