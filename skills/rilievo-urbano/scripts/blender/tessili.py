"""Tessili simulati per gli arredi (2026-11-16): piumone, plaid e guanciali fatti con la simulazione dei tessuti di Blender,
non con scatole. Usato da arredi_interni.py; funziona in modalità -b (fotogrammi avanzati a mano, modificatori applicati con
temp_override).

  telo(...)      un telo (griglia) che cade su degli ostacoli: piumone, lenzuolo, plaid
  cuscino(...)   un cuscino gonfiato con la pressione interna, senza gravità: guanciali, cuscini decorativi, cuscini del divano

Ogni funzione restituisce un oggetto mesh già applicato (forma fissa), con le UV in metri divise per il lato della texture.
"""
import bmesh, bpy, math
from mathutils import Matrix, Vector


def _applica(ob, nome_mod):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=nome_mod)


def _ostacolo(scn, scatole, nome="ostacolo tessili"):
    """mesh temporanea con la collisione: scatole = [(centro Vector, asse u Vector 2D, asse v Vector 2D, lu, lv, z0, z1), ...]"""
    bm = bmesh.new()
    for c, u, v, lu, lv, z0, z1 in scatole:
        c, u, v = Vector(c[:2]), Vector(u[:2]), Vector(v[:2])
        if u.cross(v) < 0: v = -v                 # terna destrorsa: facce verso l'esterno (con le facce rovesciate il materasso
                                                  # attirava il piumone, che si accartocciava; 2026-11-16)
        vs = []
        for z in (z0, z1):
            for a, b in ((-lu / 2, -lv / 2), (lu / 2, -lv / 2), (lu / 2, lv / 2), (-lu / 2, lv / 2)):
                q = c + u * a + v * b; vs.append(bm.verts.new((q.x, q.y, z)))
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)): bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    ob.modifiers.new("Collisione", "COLLISION"); ob.collision.thickness_outer = 0.012; ob.collision.cloth_friction = 10.0; ob.collision.damping = 0.5
    return ob


def _simula(scn, ob, fotogrammi):
    scn.frame_start, scn.frame_end = 1, fotogrammi
    cl = ob.modifiers["Tessuto"]; cl.point_cache.frame_start = 1; cl.point_cache.frame_end = fotogrammi
    for f in range(1, fotogrammi + 1): scn.frame_set(f)
    _applica(ob, "Tessuto"); scn.frame_set(1)


def _uv_metri(me, lato):
    """UV dalla posizione di riposo della griglia (in metri), divise per il lato della texture."""
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for pl in me.polygons:
        for li in pl.loop_indices: uvl.data[li].uv = uvl.data[li].uv * (1.0 / lato)


def superficie(scn, ob, alzo, nome="superficie tessili"):
    """ostacolo per un altro telo: la forma simulata di ob (senza spessore né lisciatura) alzata di alzo. ATTENZIONE: vicino a
    un'altra collisione (pochi cm) il telo resta stretto tra le due e le attraversa (plaid sul piumone, 2026-11-17): in quel caso
    meglio una scatola che inviluppi tutti e due."""
    me = ob.data.copy(); me.transform(Matrix.Translation((0, 0, alzo)))
    o2 = bpy.data.objects.new(nome, me); scn.collection.objects.link(o2)
    o2.modifiers.new("Collisione", "COLLISION"); o2.collision.thickness_outer = 0.006; o2.collision.cloth_friction = 10.0
    return o2


def telo(scn, nome, centro, u, v, lu, lv, z, ostacoli, materiale, lato_tex, spessore=0.02, peso=0.3, piega=0.5, fotogrammi=45, passo=0.025,
         grinze=0.0, seme=2):
    """telo rettangolare lu × lv (u, v assi in pianta) a quota z che cade sugli ostacoli; poi spessore e lisciatura."""
    import random
    rnd = random.Random(seme)
    nu, nv = max(2, round(lu / passo)), max(2, round(lv / passo)); centro, u, v = Vector(centro[:2]), Vector(u[:2]), Vector(v[:2])
    if u.cross(v) < 0: v = -v                     # normali del telo verso l'alto: lo spessore cresce sopra, non dentro il materasso
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); grid = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            a, b = -lu / 2 + lu * i / nu, -lv / 2 + lv * j / nv; q = centro + u * a + v * b
            grid[i, j] = bm.verts.new((q.x, q.y, z + (rnd.uniform(-grinze, grinze) if grinze else 0.0)))
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
    # UV in metri dalla griglia (prima della caduta)
    for f in bm.faces:
        for lp in f.loops:
            q = Vector(lp.vert.co.xy) - centro; lp[uvl].uv = (q.dot(u), q.dot(v))
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
    st.quality = 12; st.mass = peso; st.air_damping = 1.0
    st.tension_stiffness = st.compression_stiffness = 10.0; st.shear_stiffness = 3.0; st.bending_stiffness = piega
    cl.collision_settings.distance_min = 0.008; cl.collision_settings.collision_quality = 4; cl.collision_settings.use_self_collision = False
    obs = _ostacolo(scn, [o for o in ostacoli if not isinstance(o, bpy.types.Object)])   # scatole, più oggetti già pronti
    _simula(scn, ob, fotogrammi)
    bpy.data.objects.remove(obs, do_unlink=True)
    for pl in ob.data.polygons: pl.use_smooth = True
    _uv_metri(ob.data, lato_tex)
    so = ob.modifiers.new("Spessore", "SOLIDIFY"); so.thickness = spessore; so.offset = 1.0; so.use_even_offset = False   # l'offset uniforme sulle facce strette faceva punte
    sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 1; sd.render_levels = 2
    ob.data.materials.append(materiale)
    return ob


def trapunta(scn, nome, centro, u, v, lu, lv, z, ostacoli, materiale, lato_tex, spessore=0.035, pressione=1.5, passo=0.03,
             fotogrammi=110, peso=0.6, piega=0.05, grinze=0.004, seme=1, tensione=8.0):
    """piumone vero: involucro chiuso lu × lv alto spessore, gonfiato con la pressione, che cade sugli ostacoli con la
    gravità (2026-11-17, Andrea: "i tessuti sono durissimi"). Bordi tondi e gonfi, pieghe dove si curva sul materasso; una
    piccola irregolarità iniziale (grinze, in m) perché cadendo non resti perfettamente piatto."""
    import random
    rnd = random.Random(seme); centro, u, v = Vector(centro[:2]), Vector(u[:2]), Vector(v[:2])
    if u.cross(v) < 0: v = -v
    nu, nv = max(2, round(lu / passo)), max(2, round(lv / passo))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=nu, y_segments=nv, size=0.5)
    bmesh.ops.scale(bm, vec=(lu, lv, 1), verts=bm.verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:]); vs_ = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, spessore), verts=vs_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops: x_, y_, _ = lp.vert.co; lp[uvl].uv = (x_ / lato_tex, y_ / lato_tex)
    for vt in bm.verts: vt.co.z += rnd.uniform(-grinze, grinze)
    M = Matrix(((u.x, v.x, 0, centro.x), (u.y, v.y, 0, centro.y), (0, 0, 1, z), (0, 0, 0, 1)))
    bm.transform(M)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
    st.quality = 10; st.mass = peso; st.air_damping = 1.0
    st.tension_stiffness = st.compression_stiffness = tensione; st.shear_stiffness = 2.0; st.bending_stiffness = piega
    st.use_pressure = True; st.uniform_pressure_force = pressione
    cl.collision_settings.distance_min = 0.006; cl.collision_settings.collision_quality = 4; cl.collision_settings.use_self_collision = False
    obs = _ostacolo(scn, [o for o in ostacoli if not isinstance(o, bpy.types.Object)])
    _simula(scn, ob, fotogrammi)
    bpy.data.objects.remove(obs, do_unlink=True)
    for pl in ob.data.polygons: pl.use_smooth = True
    sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 1; sd.render_levels = 2
    ob.data.materials.append(materiale)
    return ob


def collisore(scn, ob, nome="appoggio tessili"):
    """copia di un tessile già simulato (forma fissa) come ostacolo per il tessile che ci cade sopra."""
    me = ob.data.copy(); o2 = bpy.data.objects.new(nome, me); scn.collection.objects.link(o2)
    o2.modifiers.new("Collisione", "COLLISION"); o2.collision.thickness_outer = 0.004; o2.collision.cloth_friction = 12.0
    return o2


def cuscino(scn, nome, centro, u, lu, lv, h, materiale, lato_tex, pressione=6.0, inclina=0.0, fotogrammi=40, tagli=14, scatolato=False,
            in_piedi=None, morbido=1.0):
    """cuscino lu × lv alto h a riposo, gonfiato senza gravità: forma vera di cuscino (pieno al centro, angoli a punta).
    centro = punto più basso al centro; u = asse in pianta lungo lu; inclina = rotazione attorno a u (radianti, schienale).
    scatolato=True: cuscino a scatola (divani): parte già alto h, poca pressione e tessuto più rigido: facce appena gonfie,
    bordi squadrati, invece della forma a guanciale.
    in_piedi=α (radianti): cuscino in piedi sul suo bordo (lv diventa l'altezza), con il bordo inferiore lungo u in centro,
    inclinato di α verso il lato +perp(u) (perp = u ruotato di 90° a sinistra), con lo spessore dalla parte opposta:
    schienali dei divani, cuscini appoggiati ai guanciali."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(lu, lv, h if scatolato else max(0.02, h * 0.35)), verts=bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=tagli, use_grid_fill=True)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        for lp in f.loops:
            x, y, z = lp.vert.co
            lp[uvl].uv = (x / lato_tex, y / lato_tex) if abs(n.z) > 0.5 else ((x + y) / lato_tex, z / lato_tex)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
    st.quality = 8; st.mass = 0.2; st.air_damping = 2.0; st.tension_stiffness = st.compression_stiffness = 20.0; st.bending_stiffness = 0.1
    st.effector_weights.gravity = 0.0; st.use_pressure = True; st.uniform_pressure_force = pressione
    if scatolato: st.tension_stiffness = st.compression_stiffness = 60.0; st.bending_stiffness = 2.0
    # morbido > 1: tessuto più cedevole (rigidezze divise), più grinze e cuciture che tirano, come un imbottito vero
    st.tension_stiffness /= morbido; st.compression_stiffness /= morbido; st.bending_stiffness /= morbido
    _simula(scn, ob, fotogrammi)
    # porta il cuscino al suo posto: asse x della mesh su u, appoggio in basso al centro
    # la simulazione con la pressione può far scivolare il cuscino (nel divano fino a 46 cm, 2026-11-17): si ricentra in pianta
    vs = [v.co for v in ob.data.vertices]; zmin = min(v.z for v in vs)
    cx_, cy_ = (min(v.x for v in vs) + max(v.x for v in vs)) / 2, (min(v.y for v in vs) + max(v.y for v in vs)) / 2
    ang = math.atan2(u.y, u.x)
    ob.data.transform(Matrix.Translation((-cx_, -cy_, -zmin)))
    if in_piedi is not None:
        # in piedi: (y, z) → (-z, y), poi base a z = 0, poi inclinato verso +y di in_piedi
        ob.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
        zb = min(v.co.z for v in ob.data.vertices); yb = max(v.co.y for v in ob.data.vertices)
        ob.data.transform(Matrix.Translation((0, -yb, -zb)))
        ob.data.transform(Matrix.Rotation(-in_piedi, 4, "X"))
    else:
        ob.data.transform(Matrix.Rotation(inclina, 4, "X"))
    ob.data.transform(Matrix.Rotation(ang, 4, "Z"))
    ob.data.transform(Matrix.Translation(Vector((centro[0], centro[1], centro[2] if len(centro) > 2 else 0.0))))
    for pl in ob.data.polygons: pl.use_smooth = True
    sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
    ob.data.materials.append(materiale)
    return ob
