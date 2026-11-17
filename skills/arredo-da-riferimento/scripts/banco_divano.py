"""Banco di prova da studio (skill arredo-da-riferimento): costruisce solo il pezzo con tessili.py in una scena vuota e lo
rende in 1-2 minuti. Uso: blender -b --python banco_divano.py -- [parametro=valore ...] out=<png>
Valori buoni del 2026-11-17 come predefiniti nel codice o in SKILL.md."""
import bpy, sys, time, math
sys.path.insert(0, r"C:\Users\andre\Desktop\via della menta con claude\arch_agents\skills\rilievo-urbano\scripts\blender")
from mathutils import Vector
import tessili
scn = bpy.context.scene
for o in list(scn.objects): bpy.data.objects.remove(o, do_unlink=True)
P = dict(a.split("=") for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a); f = lambda k, d: float(P.get(k, d))
def mat(nome, col, r=0.95):
    m = bpy.data.materials.new(nome); m.use_nodes = True; b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = r; b.inputs["Sheen Weight"].default_value = 0.8; return m
def scatola(x0, x1, y0, y1, z0, z1, m, bv=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)); o = bpy.context.object
    o.scale = (x1 - x0, y1 - y0, z1 - z0); o.data.materials.append(m); b = o.modifiers.new("b", "BEVEL"); b.width = bv; b.segments = 4
    for pl in o.data.polygons: pl.use_smooth = True
    return o
bou = mat("boucle", (0.78, 0.75, 0.70)); ombra = mat("ombra", (0.03, 0.03, 0.03))
# divano 2,3 × 0,95: y = profondità (dietro a +y), x = lunghezza
scatola(-1.10, 1.10, -0.42, 0.44, 0, 0.05, ombra, 0.005)
scatola(-1.15, 1.15, -0.475, 0.475, 0.05, 0.30, bou); scatola(-1.15, 1.15, 0.26, 0.475, 0.30, 0.60, bou)
scatola(0.93, 1.15, -0.475, 0.475, 0.30, 0.56, bou)
t0 = time.time(); u = Vector((1, 0))
for k, (x0, x1) in enumerate(((-1.15, -0.005), (0.005, 0.93))):
    tessili.cuscino(scn, f"seduta {k}", ((x0 + x1) / 2, -0.105, f("zs", 0.285)), u, x1 - x0 - 0.01, 0.72, 0.13, bou, 0.33, pressione=f("ps", 0.5),
                    scatolato=True, morbido=f("ms", 1.0))
wb = (0.93 + 1.15) / 3
for i in range(3):
    # perp(u) = +y = verso lo schienale: u = (1, 0)
    tessili.cuscino(scn, f"schienale {i}", (-1.15 + (i + 0.5) * wb, 0.265, 0.40), u, wb - 0.03, f("hb", 0.40), f("tb", 0.22), bou, 0.33, pressione=f("pb", 3.0),
                    in_piedi=math.radians(f("ab", 16)), morbido=f("mb", 1.0))
print("CUSCINI", round(time.time() - t0, 1))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.location = (1.6, -2.6, 1.1); d = Vector((0, 0.1, 0.35)) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); cam.data.lens = 35
ar = bpy.data.objects.new("area", bpy.data.lights.new("area", "AREA")); ar.data.energy = 500; ar.data.size = 3; ar.location = (-1.5, -2.5, 2.5); ar.rotation_euler = (0.8, 0, -0.6); scn.collection.objects.link(ar)
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True; next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.5
scatola(-4, 4, -4, 4, -0.01, 0, mat("pav", (0.6, 0.56, 0.5)), 0.001)
scn.render.engine = "CYCLES"; scn.cycles.samples = 64; scn.cycles.device = "GPU"
try:
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "OPTIX"; pr.get_devices(); [setattr(d_, "use", True) for d_ in pr.devices]
except Exception as e: print(e)
scn.render.resolution_x, scn.render.resolution_y = 1280, 800
scn.render.filepath = P.get("out"); bpy.ops.render.render(write_still=True); print("FATTO")
