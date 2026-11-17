"""Viste di controllo Cycles da un punto verso un bersaglio (h = altezza sul pavimento del soggiorno della villa).

  blender -b -P viste.py -- <file.blend> <cartella> <campioni> nome:x,y,h,tx,ty,th[,focale] ...   (PC: GPU se c'è)
  python viste.py <file.blend> <cartella> <campioni> nome:...                                   (Blender come modulo)
Variabili: ESP esposizione (0,6), VILLA (1), FILIERA_CPU=1 per forzare la CPU.
"""
import bpy, sys, os, time
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comune import cycles

arg = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
blend, out, samples = arg[0], arg[1], int(arg[2])
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend)); scn = bpy.context.scene
cycles(bpy, scn, samples)
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080; scn.render.resolution_percentage = int(os.environ.get('VISTE_SCALA', 50))   # filiera.py --scala
scn.render.image_settings.file_format = 'PNG'; scn.view_settings.exposure = float(os.environ.get('ESP', 0.6))
bg = next((n for n in scn.world.node_tree.nodes if n.type == 'BACKGROUND'), None)
if bg: bg.inputs['Strength'].default_value = 1.0
villa = int(os.environ.get('VILLA', 1))
z0 = min((o.matrix_world @ v.co).z for o in scn.objects if o.get('villa') == villa and str(o.get('vano', '')).startswith('Soggiorno') for v in o.data.vertices)
cd = bpy.data.cameras.new('vista'); co = bpy.data.objects.new('vista', cd); scn.collection.objects.link(co); scn.camera = co; cd.clip_start = 0.05
os.makedirs(out, exist_ok=True)
for a in arg[3:]:
    nome, val = a.split(':'); n = [float(x) for x in val.split(',')]; cd.lens = n[6] if len(n) > 6 else 16
    p = Vector((n[0], n[1], z0 + n[2])); t = Vector((n[3], n[4], z0 + n[5])); co.location = p
    co.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
    t0 = time.time(); scn.render.filepath = os.path.join(os.path.abspath(out), nome + '.png'); bpy.ops.render.render(write_still=True)
    print('FATTO', nome, round(time.time() - t0, 1), 's')
