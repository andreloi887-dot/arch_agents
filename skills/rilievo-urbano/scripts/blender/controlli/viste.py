"""viste di controllo Cycles: python viste.py <blend> <cartella> <campioni> nome:x,y,h,tx,ty,th[,focale] ..."""
import bpy, sys, os, time
from mathutils import Vector
blend, out, samples = sys.argv[1], sys.argv[2], int(sys.argv[3])
bpy.ops.wm.open_mainfile(filepath=blend); scn = bpy.context.scene
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = samples
scn.cycles.use_denoising = True; scn.cycles.max_bounces = 6; scn.cycles.diffuse_bounces = 4
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080; scn.render.resolution_percentage = 50
scn.render.image_settings.file_format = 'PNG'; scn.view_settings.exposure = float(os.environ.get('ESP', 0.6))
bg = next((n for n in scn.world.node_tree.nodes if n.type == 'BACKGROUND'), None)
if bg: bg.inputs['Strength'].default_value = 1.0
z0 = min((o.matrix_world @ v.co).z for o in scn.objects if o.get('villa') == 1 and str(o.get('vano', '')).startswith('Soggiorno') for v in o.data.vertices)
cd = bpy.data.cameras.new('vista'); co = bpy.data.objects.new('vista', cd); scn.collection.objects.link(co); scn.camera = co; cd.clip_start = 0.05
for a in sys.argv[4:]:
    nome, val = a.split(':'); n = [float(x) for x in val.split(',')]; cd.lens = n[6] if len(n) > 6 else 16
    p = Vector((n[0], n[1], z0 + n[2])); t = Vector((n[3], n[4], z0 + n[5])); co.location = p
    co.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
    t0 = time.time(); scn.render.filepath = os.path.join(out, nome + '.png'); bpy.ops.render.render(write_still=True); print('FATTO', nome, round(time.time() - t0), 's')
