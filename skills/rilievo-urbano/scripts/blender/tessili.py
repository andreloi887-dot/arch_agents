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


CACHE = None      # cartella della cache delle simulazioni (arredi_interni.py: uscita_blender/cache_tessili); None = sempre simulare


def _chiave(scn, ob, fotogrammi):
    """impronta di ciò che decide il risultato: forma di partenza, impostazioni del tessuto, ostacoli presenti in scena."""
    import hashlib
    h = hashlib.sha1()
    for v in ob.data.vertices: h.update(("%.5f %.5f %.5f;" % tuple(ob.matrix_world @ v.co)).encode())
    st = ob.modifiers["Tessuto"].settings
    for k in ("quality", "mass", "air_damping", "tension_stiffness", "compression_stiffness", "shear_stiffness", "bending_stiffness",
              "use_pressure", "uniform_pressure_force", "shrink_min", "pin_stiffness", "vertex_group_mass", "use_internal_springs"):
        h.update(f"{k}={getattr(st, k, None)};".encode())
    # ogni impostazione nuova deve entrare qui, altrimenti la cache restituisce un risultato vecchio (2026-11-17)
    cs = ob.modifiers["Tessuto"].collision_settings
    for k in ("distance_min", "collision_quality", "use_self_collision", "self_distance_min", "use_collision"):
        h.update(f"{k}={getattr(cs, k, None)};".encode())
    h.update(f"g={st.effector_weights.gravity};f={fotogrammi};".encode())
    for o in sorted((o for o in scn.objects if any(m.type == "COLLISION" for m in o.modifiers)), key=lambda o: o.name):
        for v in o.data.vertices: h.update(("%.4f %.4f %.4f;" % tuple(o.matrix_world @ v.co)).encode())
        c_ = o.collision; h.update(f"attrito={c_.cloth_friction};spessore={c_.thickness_outer};smorza={c_.damping};".encode())
    # vertici fermati (gruppo "fisso" delle camicie) e versione delle ricette: cambiano il risultato anche a forma uguale
    g_ = ob.vertex_groups.get(st.vertex_group_mass) if st.vertex_group_mass else None
    if g_:
        for v in ob.data.vertices:
            for gg in v.groups:
                if gg.group == g_.index: h.update(f"p{v.index}:{gg.weight:.3f};".encode())
    h.update(f"versione={VERSIONE};".encode())
    return h.hexdigest()[:20]


VERSIONE = 3      # cambia quando cambia il modo di simulare (forza una nuova simulazione di tutto)
LOG = print       # arredi_interni.py ci mette il suo log: i controlli automatici finiscono nel log della filiera


def _scatole_di(scn):
    """oggetti con la collisione presenti in scena (ostacoli)."""
    return [o for o in scn.objects if any(m.type == "COLLISION" for m in o.modifiers)]


ESEMPI = []


def _dentro_oggetti(scn, ob, margine=0.003):
    """quanti vertici del tessuto stanno DENTRO un ostacolo (lato interno della superficie più vicina, entro 15 cm)."""
    from mathutils.bvhtree import BVHTree
    import bmesh as bm_
    n = {}
    alberi = []
    for o in _scatole_di(scn):
        if o is ob: continue
        b = bm_.new(); b.from_mesh(o.data); b.transform(o.matrix_world)
        if all(len(e.link_faces) == 2 for e in b.edges):                                     # solo forme chiuse: normali verso fuori
            bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
            if b.calc_volume(signed=True) < 0: bmesh.ops.reverse_faces(b, faces=b.faces[:])
        b.normal_update(); alberi.append((o.name, BVHTree.FromBMesh(b))); b.free()
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        for nome_o, a in alberi:
            r = a.find_nearest(p, 0.15)
            if r[0] is not None and (p - r[0]).dot(r[1]) < -margine:
                n[nome_o] = n.get(nome_o, 0) + 1
                if n[nome_o] <= 3: ESEMPI.append(f"{tuple(round(x, 3) for x in p)} a {(p - r[0]).length * 100:.1f} cm dentro")
                break
    return n


def grinze(ob):
    """indice di accartocciamento: angolo medio (gradi) tra facce vicine. Un tessuto morbido e disteso sta sotto 8-10°; la
    lastra accartocciata del plaid del 2026-11-17 era sopra 20°."""
    import bmesh as bm_
    b = bm_.new(); b.from_mesh(ob.data); ang = [e.calc_face_angle(0.0) for e in b.edges if len(e.link_faces) == 2]; b.free()
    return math.degrees(sum(ang) / len(ang)) if ang else 0.0


def _controlli_prima(scn, ob):
    """controlli automatici prima di simulare (lezioni del 2026-11-17): massa totale realistica, normali verso fuori per gli
    involucri chiusi, nessun vertice dentro un ostacolo."""
    import bmesh as bm_
    st = ob.modifiers["Tessuto"].settings; nv = len(ob.data.vertices); kg = st.mass * nv
    # negli involucri gonfiati (pressione) il peso fa da contrappeso alla pressione: il piumone da 0,004 kg per vertice diventava un
    # pallone (2026-11-17). Il controllo della massa vale per i teli
    if st.effector_weights.gravity > 0 and not st.use_pressure and kg > 25: LOG(f"AVVISO tessili {ob.name}: massa {kg:.0f} kg ({st.mass} kg per vertice × {nv}): troppo pesante, si accartoccia")
    if st.use_pressure:
        b = bm_.new(); b.from_mesh(ob.data); vol = b.calc_volume(signed=True); b.free()
        if vol < 0: LOG(f"AVVISO tessili {ob.name}: normali verso dentro (volume {vol:.4f}): la pressione lo schiaccia invece di gonfiarlo")
    ESEMPI.clear(); n = _dentro_oggetti(scn, ob)
    if n: LOG(f"AVVISO tessili {ob.name}: {sum(n.values())} vertici nascono dentro un ostacolo ({', '.join(f'{k}: {v}' for k, v in n.items())}): esplode o lo attraversa; per esempio {'; '.join(ESEMPI)}")


def _simula(scn, ob, fotogrammi):
    """simulazione dei tessuti, con la cache: la simulazione non dà due volte esattamente lo stesso risultato (piumone e plaid
    cambiavano a ogni giro, 2026-11-17) e l'impronta della geometria non serviva più; con la cache, a parità di ingressi, il
    risultato è identico (e più veloce)."""
    import os
    import numpy as np
    f_c = None
    if CACHE:
        os.makedirs(CACHE, exist_ok=True); f_c = os.path.join(CACHE, _chiave(scn, ob, fotogrammi) + ".npy")
        if os.path.isfile(f_c):
            co = np.load(f_c)
            if len(co) == len(ob.data.vertices):
                ob.modifiers.remove(ob.modifiers["Tessuto"]); ob.data.vertices.foreach_set("co", co.ravel()); ob.data.update(); return
    _controlli_prima(scn, ob)
    scn.frame_start, scn.frame_end = 1, fotogrammi
    cl = ob.modifiers["Tessuto"]; cl.point_cache.frame_start = 1; cl.point_cache.frame_end = fotogrammi
    for f in range(1, fotogrammi + 1): scn.frame_set(f)
    _applica(ob, "Tessuto"); scn.frame_set(1)
    if f_c:
        co = np.empty(len(ob.data.vertices) * 3, np.float32); ob.data.vertices.foreach_get("co", co); np.save(f_c, co.reshape(-1, 3))


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


def telo_appoggiato(scn, nome, centro, u, v, lu, lv, sotto, materiale, lato_tex, spessore=0.015, peso=0.02, piega=1.0, fotogrammi=50,
                    passo=0.02, alzo=0.012, pieghe=0.008, seme=3, ostacoli=(), attrito=4.0):
    """telo PREFIGURATO (2026-11-17, Andrea: "il plaid è pietoso"): invece di lasciarlo cadere dall'alto (lastra accartocciata
    dove atterra), il telo nasce già steso sulla superficie dell'oggetto 'sotto' (il piumone simulato), alzo sopra, e la parte
    che sporge oltre il bordo pende in verticale lungo il fianco, con la stessa lunghezza di stoffa. La simulazione deve solo
    assestarlo: pieghe lunghe e morbide (pieghe = ampiezza in m di due onde lungo il telo), bordi che ricadono puliti.
    Regola generale: un tessuto parte sempre vicino alla sua forma finale."""
    import random
    from mathutils.bvhtree import BVHTree
    rnd = random.Random(seme); centro, u, v = Vector(centro[:2]), Vector(u[:2]).normalized(), Vector(v[:2]).normalized()
    if u.cross(v) < 0: v = -v
    # la stessa superficie dell'ostacolo (collisore = mesh di base, senza la lisciatura): appoggiato sulla superficie lisciata,
    # il plaid nasceva dentro la gabbia che sporge sui bordi (145 vertici dentro, poi esplodeva: grinze 30°, 2026-11-17)
    b_ = bmesh.new(); b_.from_mesh(sotto.data); b_.transform(sotto.matrix_world); albero = BVHTree.FromBMesh(b_); b_.free()
    z_su = max((sotto.matrix_world @ q.co).z for q in sotto.data.vertices) + 0.5
    nu, nv = max(2, round(lu / passo)), max(2, round(lv / passo))
    onde = [(rnd.uniform(0.6, 1.0) * pieghe, rnd.uniform(9, 16), rnd.uniform(0, 6.3)) for _ in range(2)]
    def tocca(a, b):
        q = centro + u * a + v * b; r = albero.ray_cast(Vector((q.x, q.y, z_su)), Vector((0, 0, -1)), 3.0)
        if r[0] is None: return None
        n_ = r[1] if r[1].z >= 0 else -r[1]                    # le normali del piumone possono guardare dentro: si prende quella in su
        return (r[0], n_)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); grid = {}
    for i in range(nu + 1):
        a = -lu / 2 + lu * i / nu
        onda = sum(am * math.sin(k * a + f) for am, k, f in onde)
        for lato in (1, -1):                     # dal centro verso i due bordi: l'ultimo punto appoggiato fa da spigolo
            ultimo = None; b_ult = 0.0
            for j in range(nv // 2, nv + 1) if lato == 1 else range(nv // 2, -1, -1):
                b = -lv / 2 + lv * j / nv; h = tocca(a, b)
                # solo dove la superficie guarda in su (sul fianco del piumone il punto alzato in verticale finiva dentro)
                if h is not None and h[1].z > 0.5 and (ultimo is None or abs(h[0].z - ultimo.z) < 0.05):
                    p = h[0] + h[1] * alzo + Vector((0, 0, onda * max(0.0, 1 - abs(b) / (lv / 2)))); ultimo, b_ult = p, b
                elif ultimo is not None:
                    # lembo che pende: alla sua quota si cerca il fianco del piumone con un raggio orizzontale da fuori, e lo si
                    # segue a 'alzo' dalla superficie; sotto il piumone pende dritto (prima nasceva dentro il fianco gonfio)
                    giu = abs(b - b_ult); zq = ultimo.z - giu; fuori = Vector((v.x, v.y, 0)) * lato
                    q0 = Vector((ultimo.x, ultimo.y, zq)) + fuori * 0.6
                    r = albero.ray_cast(q0, -fuori, 0.6)
                    if r[0] is not None: p = r[0] + fuori * (alzo + 0.004)
                    else: q = ultimo + fuori * min(0.05, giu); p = Vector((q.x, q.y, zq))
                else:
                    q = centro + u * a + v * b; p = Vector((q.x, q.y, z_su - 0.5 + alzo))   # sopra il punto più alto del piumone
                if (i, j) not in grid: grid[i, j] = bm.verts.new(p)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
    # UV in metri dalla griglia di partenza (lunghezze vere della stoffa)
    inv = {vv: k for k, vv in grid.items()}
    for f in bm.faces:
        for lp in f.loops:
            i, j = inv[lp.vert]; lp[uvl].uv = ((lu * i / nu) / lato_tex, (lv * j / nv) / lato_tex)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    if sum(p.normal.z for p in me.polygons) < 0: me.flip_normals()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
    st.quality = 10; st.mass = peso; st.air_damping = 1.0
    st.tension_stiffness = st.compression_stiffness = 10.0; st.shear_stiffness = 3.0; st.bending_stiffness = piega
    cl.collision_settings.distance_min = 0.006; cl.collision_settings.collision_quality = 4
    # ostacolo = la superficie su cui il telo è stato appoggiato (il telo di partenza abbassato di 'alzo' lungo le normali): il
    # piumone simulato ha strati che si incrociano e non ha un "fuori" pulito, il telo ci finiva dentro (2026-11-17)
    mc = me.copy(); mc.update()
    for vt in mc.vertices: vt.co = vt.co - vt.normal * (alzo + 0.002)
    col = bpy.data.objects.new(nome + " appoggio", mc); scn.collection.objects.link(col)
    col.modifiers.new("Collisione", "COLLISION"); col.collision.thickness_outer = 0.004; col.collision.cloth_friction = attrito
    obs = _ostacolo(scn, [o for o in ostacoli if not isinstance(o, bpy.types.Object)], nome + " ostacolo") if ostacoli else None
    _simula(scn, ob, fotogrammi)
    for o_ in (col, obs):
        if o_: bpy.data.objects.remove(o_, do_unlink=True)
    LOG(f"tessili {nome}: grinze {grinze(ob):.1f}°")
    for pl in ob.data.polygons: pl.use_smooth = True
    so = ob.modifiers.new("Spessore", "SOLIDIFY"); so.thickness = spessore; so.offset = 1.0; so.use_even_offset = False
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
    """copia di un tessile già simulato (forma fissa) come ostacolo per il tessile che ci cade sopra. Normali ricalcolate verso
    fuori: la collisione spinge il tessuto dal lato della normale, e il piumone simulato aveva facce rovesciate qua e là (il
    plaid ci finiva dentro e si accartocciava, 2026-11-17)."""
    me = ob.data.copy()
    b = bmesh.new(); b.from_mesh(me); bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
    if b.calc_volume(signed=True) < 0: bmesh.ops.reverse_faces(b, faces=b.faces[:])
    b.to_mesh(me); b.free()
    o2 = bpy.data.objects.new(nome, me); scn.collection.objects.link(o2)
    o2.modifiers.new("Collisione", "COLLISION"); o2.collision.thickness_outer = 0.004; o2.collision.cloth_friction = 12.0
    return o2


def _guanciale(lu, lv, n_u, n_v):
    """forma di partenza a "bordo a coltello": due griglie lu × lv unite sul perimetro (federa cucita sul bordo), la
    inferiore 4 mm più in basso all'interno. Gonfiata con la pressione dà il guanciale vero: pieno al centro, angoli a punta,
    cucitura sottile, senza la fascia laterale squadrata della scatola (2026-11-17)."""
    bm = bmesh.new(); top = {}; bot = {}
    for i in range(n_u + 1):
        for j in range(n_v + 1):
            x, y = -lu / 2 + lu * i / n_u, -lv / 2 + lv * j / n_v
            top[i, j] = bm.verts.new((x, y, 0.002))
            bordo = i in (0, n_u) or j in (0, n_v)
            bot[i, j] = top[i, j] if bordo else bm.verts.new((x, y, -0.002))
    for i in range(n_u):
        for j in range(n_v):
            bm.faces.new((top[i, j], top[i + 1, j], top[i + 1, j + 1], top[i, j + 1]))
            bm.faces.new((bot[i, j], bot[i, j + 1], bot[i + 1, j + 1], bot[i + 1, j]))
    return bm


def _dentro(q, sc, m=0.006):
    c, u, v, lu, lv, z0, z1 = sc; c, u, v = Vector(c[:2]), Vector(u[:2]).normalized(), Vector(v[:2]).normalized()
    d = Vector(q[:2]) - c
    return abs(d.dot(u)) < lu / 2 + m and abs(d.dot(v)) < lv / 2 + m and z0 - m < q[2] < z1 + m


def _fuori(ob, scatole, via, passo=0.004, max_passi=80, scn=None):
    """sposta l'oggetto finché nessun vertice sta dentro le scatole (con 6 mm di margine): verso l'alto se tocca il piano di
    sopra di una scatola, altrimenti lungo 'via'. Un tessuto che nasce dentro un ostacolo esplode o lo attraversa (guanciali
    nella testata, 2026-11-17)."""
    from mathutils import Matrix as M_
    from mathutils.bvhtree import BVHTree
    alberi = []
    for o in (_scatole_di(scn) if scn else []):
        if o is ob: continue
        b = bmesh.new(); b.from_mesh(o.data); b.transform(o.matrix_world)
        if all(len(e.link_faces) == 2 for e in b.edges):
            bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
            if b.calc_volume(signed=True) < 0: bmesh.ops.reverse_faces(b, faces=b.faces[:])
            b.normal_update(); alberi.append(BVHTree.FromBMesh(b))
        b.free()
    for _ in range(max_passi):
        su = lato = 0
        for vt in ob.data.vertices:
            for sc in scatole:
                if _dentro(vt.co, sc):
                    if vt.co.z > sc[6] - 0.03: su += 1
                    else: lato += 1
                    break
        if alberi:                                   # ostacoli fatti di oggetti (altri cuscini, 2026-11-17: i decorativi del divano
            for v in ob.data.vertices:               # nascevano fino a 254 vertici dentro gli schienali)
                for a in alberi:
                    r = a.find_nearest(v.co, 0.15)
                    if r[0] is not None and (v.co - r[0]).dot(r[1]) < -0.003:
                        if r[1].z > 0.7: su += 1                      # sotto un piano che guarda in su (seduta): si alza
                        else: lato += 1
                        break
        if not su and not lato: return
        d = Vector((0, 0, passo)) if su > lato or via is None else Vector((via[0], via[1], 0)).normalized() * passo
        ob.data.transform(M_.Translation(d))


def cuscino(scn, nome, centro, u, lu, lv, h, materiale, lato_tex, pressione=6.0, inclina=0.0, fotogrammi=40, tagli=14, scatolato=False,
            in_piedi=None, morbido=1.0, seme=None, varia=0.0, maglia=None, coltello=False, assesta=0, ostacoli=(), gonfio_assesta=0.6,
            attrito=8.0, rughe=1.0, massa_assesta=0.002, via=None):
    """cuscino lu × lv alto h a riposo, gonfiato senza gravità: forma vera di cuscino (pieno al centro, angoli a punta).
    centro = punto più basso al centro; u = asse in pianta lungo lu; inclina = rotazione attorno a u (radianti, schienale).
    scatolato=True: cuscino a scatola (divani): parte già alto h, poca pressione e tessuto più rigido: facce appena gonfie,
    bordi squadrati, invece della forma a guanciale.
    in_piedi=α (radianti): cuscino in piedi sul suo bordo (lv diventa l'altezza), con il bordo inferiore lungo u in centro,
    inclinato di α verso il lato +perp(u) (perp = u ruotato di 90° a sinistra), con lo spessore dalla parte opposta:
    schienali dei divani, cuscini appoggiati ai guanciali.

    Morbidezza (Andrea, 2026-11-17: "troppo rigidi e tutti uguali"):
      coltello=True   forma di partenza a bordo cucito (_guanciale) invece della scatola: guanciali e cuscini decorativi.
      maglia=m        lato delle maglie in m (la rigidezza del tessuto dipende dalla maglia: prima 4,5 cm, ora ~2 cm).
      rughe           compressione del tessuto più debole della trazione (rughe>1): la federa fa le grinze dove si stringe.
      seme, varia     ogni cuscino un po' diverso: misure ±4 %, pressione ±15 %, rotazione ±5°, una ammaccatura e un leggero
                      disordine della forma di partenza (varia = 0 tutti uguali, 1 normale). Cambia anche la chiave della cache.
      assesta=n       seconda fase: il cuscino già gonfio, messo al suo posto, cade con la gravità per n fotogrammi su
                      ostacoli (scatole come in telo(), oppure oggetti con la collisione: tessili.collisore di altri cuscini) e
                      si schiaccia dove appoggia; gonfio_assesta = parte della pressione che resta in questa fase.
                      massa_assesta = massa per VERTICE in kg (con 0,35 un guanciale di 1700 vertici pesava 600 kg e
                      crollava, 2026-11-17); via = direzione in pianta per uscire dagli ostacoli se ci nasce dentro."""
    import random
    rnd = random.Random(seme if seme is not None else 0); vv = varia if seme is not None else 0.0
    def r1(): return rnd.uniform(-1.0, 1.0)
    lu, lv = lu * (1 + 0.04 * vv * r1()), lv * (1 + 0.04 * vv * r1()); pressione *= 1 + 0.15 * vv * r1()
    gira = math.radians(5.0) * vv * r1(); piega_in = math.radians(4.0) * vv * r1()
    if maglia: tagli = max(tagli, round(max(lu, lv) / maglia))
    if coltello and not scatolato:
        passo_ = maglia or max(lu, lv) / (tagli + 1)
        bm = _guanciale(lu, lv, max(4, round(lu / passo_)), max(4, round(lv / passo_)))
    else:
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(lu, lv, h if scatolato else max(0.02, h * 0.35)), verts=bm.verts)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=tagli, use_grid_fill=True)
    if vv:
        for vt in bm.verts: vt.co += Vector((r1(), r1(), r1())) * 0.003 * vv
        # una ammaccatura: una zona spinta dentro di qualche mm (dove qualcuno si è appoggiato)
        cx, cy = r1() * lu * 0.3, r1() * lv * 0.3; rr = 0.25 * min(lu, lv)
        for vt in bm.verts:
            d = math.hypot(vt.co.x - cx, vt.co.y - cy)
            if d < rr and vt.co.z > 0: vt.co.z -= 0.004 * vv * (1 - d / rr)
    uvl = bm.loops.layers.uv.new("UVMap")
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        for lp in f.loops:
            x, y, z = lp.vert.co
            lp[uvl].uv = (x / lato_tex, y / lato_tex) if abs(n.z) > 0.5 else ((x + y) / lato_tex, z / lato_tex)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    def tessuto(gravita, pr):
        cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
        st.quality = 8; st.mass = 0.2; st.air_damping = 2.0; st.tension_stiffness = st.compression_stiffness = 20.0; st.bending_stiffness = 0.1
        st.effector_weights.gravity = gravita; st.use_pressure = True; st.uniform_pressure_force = pr
        if scatolato: st.tension_stiffness = st.compression_stiffness = 60.0; st.bending_stiffness = 2.0
        # morbido > 1: tessuto più cedevole (rigidezze divise), più grinze e cuciture che tirano, come un imbottito vero
        st.tension_stiffness /= morbido; st.compression_stiffness /= morbido * rughe; st.bending_stiffness /= morbido
        cl.collision_settings.distance_min = 0.004; cl.collision_settings.collision_quality = 3
        return cl
    tessuto(0.0, pressione)
    _simula(scn, ob, fotogrammi)
    # porta il cuscino al suo posto: asse x della mesh su u, appoggio in basso al centro
    # la simulazione con la pressione può far scivolare il cuscino (nel divano fino a 46 cm, 2026-11-17): si ricentra in pianta
    vs = [v.co for v in ob.data.vertices]; zmin = min(v.z for v in vs)
    cx_, cy_ = (min(v.x for v in vs) + max(v.x for v in vs)) / 2, (min(v.y for v in vs) + max(v.y for v in vs)) / 2
    ang = math.atan2(u.y, u.x) + gira
    ob.data.transform(Matrix.Translation((-cx_, -cy_, -zmin)))
    if in_piedi is not None:
        # in piedi: (y, z) → (-z, y), poi base a z = 0, poi inclinato verso +y di in_piedi
        ob.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
        zb = min(v.co.z for v in ob.data.vertices); yb = max(v.co.y for v in ob.data.vertices)
        ob.data.transform(Matrix.Translation((0, -yb, -zb)))
        ob.data.transform(Matrix.Rotation(-(in_piedi + piega_in), 4, "X"))
    else:
        ob.data.transform(Matrix.Rotation(inclina, 4, "X"))
    ob.data.transform(Matrix.Rotation(ang, 4, "Z"))
    ob.data.transform(Matrix.Translation(Vector((centro[0], centro[1], (centro[2] if len(centro) > 2 else 0.0) + (0.008 if assesta else 0.0)))))
    if assesta:
        # seconda fase: gravità e appoggi veri. Il cuscino si schiaccia dove tocca e si adagia sulla testata o su ciò che ha dietro
        scat = [o for o in ostacoli if not isinstance(o, bpy.types.Object)]
        _fuori(ob, scat, via, scn=scn)
        cl = tessuto(1.0, pressione * gonfio_assesta); cl.settings.mass = massa_assesta
        obs = _ostacolo(scn, scat, nome + " ostacolo") if scat else None
        if obs: obs.collision.cloth_friction = attrito; obs.collision.thickness_outer = 0.015
        cl.collision_settings.collision_quality = 6
        _simula(scn, ob, assesta)
        if obs: bpy.data.objects.remove(obs, do_unlink=True)
    for pl in ob.data.polygons: pl.use_smooth = True
    sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
    ob.data.materials.append(materiale)
    return ob


def _busta(larga, alta, passo, forma=None, spessore=None):
    """involucro chiuso a bordo cucito in coordinate locali (x di traverso, y verso il basso negativo, z spessore): due
    griglie larga × alta unite sul perimetro; forma(x, y) → (x, y) deforma la sagoma (spalle inclinate, scollo, maniche
    rastremate). Restituisce bm e l'elenco dei vertici del bordo alto."""
    n_u, n_v = max(4, round(larga / passo)), max(4, round(alta / passo))
    bm = bmesh.new(); top = {}; bot = {}; alto = []
    for i in range(n_u + 1):
        for j in range(n_v + 1):
            x, y = -larga / 2 + larga * i / n_u, -alta * j / n_v
            if forma: x, y = forma(x, y)
            bordo = i in (0, n_u) or j in (0, n_v)
            mz = 0.002 if (bordo or spessore is None) else max(0.002, spessore(x, y))       # mezzo spessore vero (busto a tubo)
            top[i, j] = bm.verts.new((x, y, 0.0 if bordo else mz))
            bot[i, j] = top[i, j] if bordo else bm.verts.new((x, y, -mz))
            if j == 0: alto.append(top[i, j])
    for i in range(n_u):
        for j in range(n_v):
            bm.faces.new((top[i, j], top[i, j + 1], top[i + 1, j + 1], top[i + 1, j]))
            bm.faces.new((bot[i, j], bot[i + 1, j], bot[i + 1, j + 1], bot[i, j + 1]))
    return bm, alto


def camicia(scn, nome, gancio, d, materiale, lato_tex, larga=0.48, lunga=0.72, manica=0.56, spalla=0.22, seme=1, passo=0.016,
            pressione=0.35, fotogrammi=70, ostacoli=(), piega=0.7, fermo=0.15, ruota=0.0, massa=0.005, pressione_manica=0.3):
    """camicia appesa a una gruccia (Andrea, 2026-11-17: "una camicia morbida dentro l'armadio, appesa"). Busto e maniche
    sono involucri di stoffa chiusi (spessore vero, niente facce a una sola faccia in Unreal), fermati solo sulle spalle della
    gruccia e lasciati cadere con la gravità: pieghe dalle spalle, maniche che pendono sui fianchi; più un colletto.
    gancio = punto della gruccia al centro delle spalle (3D); d = direzione in pianta della larghezza (spalla-spalla); la
    camicia guarda lungo l'asta (perp(d)). spalla = metà larghezza della gruccia. seme: ogni camicia un po' diversa.
    Restituisce [busto, manica, manica, colletto]."""
    import random
    # terna destrorsa (d, su, t = d × su): con t = perp(d) la terna era sinistrorsa, le facce rovesciate e la pressione
    # schiacciava le camicie invece di gonfiarle (accartocciate nell'armadio, 2026-11-17; stessa lezione dei teli)
    rnd = random.Random(seme); g = Vector(gancio); d = Vector((d[0], d[1], 0)).normalized(); su = Vector((0, 0, 1)); t = d.cross(su)
    pend = 0.22                                         # pendenza delle spalle della gruccia
    # grucce girate (ruota, gradi): il numero a caso si estrae sempre, così la forma delle camicie non cambia con ruota = 0.
    # Nota (2026-11-17): per un errore di modifica la rotazione non è mai stata applicata; le camicie verificate sono senza
    # rotazione, quindi il predefinito è 0. Con ruota ≠ 0 le grucce si girano tutte nello stesso verso (da provare)
    gira = math.radians(ruota + rnd.uniform(-4, 4))
    if ruota: d, t = (d * math.cos(gira) + t * math.sin(gira)), (t * math.cos(gira) - d * math.sin(gira))
    M = Matrix(((d.x, su.x, t.x, g.x), (d.y, su.y, t.y, g.y), (d.z, su.z, t.z, g.z), (0, 0, 0, 1)))
    # pieghe morbide e irregolari nella forma di riposo (il tessuto ricorda la forma da cui parte: partendo piatto restava un
    # pannello rigido, 2026-11-17): tre onde di 10-18 cm, un po' oblique, più ampie verso l'orlo
    onde = [(rnd.uniform(0.008, 0.016) * piega, rnd.uniform(35, 62), rnd.uniform(0, 6.3), rnd.uniform(-2.5, 2.5)) for _ in range(3)]
    def ondula(x, y): return sum(a * math.sin(k * x + f + s_ * y) for a, k, f, s_ in onde)
    fatti = []
    def tessuto(ob, pin, pr, fot, obst):
        vg = ob.vertex_groups.new(name="fisso"); vg.add(pin, 1.0, "REPLACE")
        cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
        st.quality = 10; st.mass = massa; st.air_damping = 1.5; st.tension_stiffness = st.compression_stiffness = 8.0
        st.shear_stiffness = 2.0; st.bending_stiffness = 0.02; st.use_pressure = True; st.uniform_pressure_force = pr
        st.vertex_group_mass = "fisso"; st.pin_stiffness = 1.0
        cl.collision_settings.distance_min = 0.003; cl.collision_settings.collision_quality = 3
        o_ = _ostacolo(scn, [o for o in obst if not isinstance(o, bpy.types.Object)], nome + " ostacolo") if any(not isinstance(o, bpy.types.Object) for o in obst) else None
        _simula(scn, ob, fot)
        if o_: bpy.data.objects.remove(o_, do_unlink=True)
        if ob.vertex_groups.get("fisso"): ob.vertex_groups.remove(ob.vertex_groups["fisso"])
    def fai(nome_p, bm, alto, filtro):
        for vt in bm.verts:
            x, y, z = vt.co; vt.co.z += ondula(x, y) * min(1.0, max(0.0, (-y - 0.06) / 0.35)) + rnd.uniform(-0.002, 0.002)
        uvl = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for lp in f.loops: lp[uvl].uv = (lp.vert.co.x / lato_tex, lp.vert.co.y / lato_tex)
        bm.verts.index_update(); idx = [v.index for v in alto if filtro(v)]      # in coordinate locali, prima di girarla
        bm.transform(M)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])                       # involucro chiuso: normali verso fuori
        me = bpy.data.meshes.new(nome_p); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(nome_p, me); scn.collection.objects.link(ob); return ob, idx
    # busto: spalle inclinate come la gruccia, scollo, fondo appena svasato e arrotondato
    def sagoma(x, y):
        y2 = y - pend * max(0.0, abs(x) - 0.06) * (1 - min(1.0, -y / 0.12)) if y > -0.12 else y
        if abs(x) < 0.07 and y > -0.02: y2 -= 0.035 * (1 - abs(x) / 0.07)                         # scollo
        x2 = x * (1 + 0.04 * min(1.0, max(0.0, (-y - 0.35) / 0.35)))                                  # svasato in fondo
        if y < -lunga + 0.08: y2 += 0.05 * (abs(x) / (larga / 2)) ** 2 * ((-y - lunga + 0.08) / 0.08)   # orlo arrotondato
        return x2, y2
    # busto a tubo (foto di camicie appese, 2026-11-17): davanti e dietro staccati di 6 cm alle spalle (la gruccia ci sta
    # dentro) e di 2,5 cm all'orlo, sezione tonda: spalle piene invece della busta piatta
    def mezzo(x, y): return (0.03 - 0.0175 * min(1.0, -y / lunga)) * math.sqrt(max(0.0, 1 - (2 * x / larga) ** 2))
    bm, alto = _busta(larga, lunga, passo, sagoma, mezzo)
    busto, pin = fai(f"{nome} busto (tessili)", bm, alto, lambda v: abs(v.co.x) <= fermo)          # le spalle oltre la gruccia cadono
    busto.data.materials.append(materiale)
    tessuto(busto, pin, pressione, fotogrammi, ostacoli)
    fatti.append(busto)
    # maniche: attaccate dove la spalla del busto è scesa davvero, un po' davanti e un po' dietro al busto; rastremate al
    # polsino, con pieghe più piccole. Niente urto con il busto (le stropicciava): restano appena staccate
    Mi = M.inverted(); loc = [Mi @ v.co for v in busto.data.vertices]
    for k, sx in enumerate((-1, 1)):
        bordo = [q for q in loc if sx * q.x > larga / 2 - 0.05]
        y_sp = max(q.y for q in bordo) if bordo else -pend * (larga / 2 - 0.06)
        # maniche a tubo (foto: pendono lungo il fianco, in parte dietro il busto; piatte sembravano risvolti), 14 → 10 cm
        x0 = sx * (larga / 2 - 0.045); y0 = y_sp - 0.01; z0 = -0.018
        def sm(x, y, x0=x0, y0=y0, sx=sx):
            r = 1 - 0.30 * min(1.0, -y / manica)                                                       # da 14 a 10 cm
            return x0 + x * r - sx * 0.015 * (-y / manica), y0 + y                                      # verso il busto in basso
        onde_b = onde[:]; onde[:] = [(a * 0.9, k_ * 1.2, f + 1.3 * (k + 1), s_ * 2) for a, k_, f, s_ in onde_b]
        bm, alto = _busta(0.14, manica, passo, sm, lambda x, y: 0.012 * math.sqrt(max(0.0, 1 - (2 * (x - x0) / 0.14) ** 2)))
        for vt in bm.verts: vt.co.z += z0
        # ferma solo il centro del giro manica: il resto pende e si piega con il suo peso
        ob, pin = fai(f"{nome} manica {k + 1} (tessili)", bm, alto, lambda v, x0=x0: abs(v.co.x - x0) < 0.035)
        onde[:] = onde_b
        ob.data.materials.append(materiale)
        tessuto(ob, pin, pressione_manica, fotogrammi, list(ostacoli))     # tubo pieno: con la pressione del busto si afflosciava
        fatti.append(ob)
    # colletto vero (foto, 2026-11-17): collo in piedi alto 3 cm attorno al gancio, poi la vela ripiegata che scende di 4 cm
    # all'esterno, con le due punte che cadono sul davanti; più i bottoni sull'abbottonatura del busto
    bm = bmesh.new(); n = 32; anelli = []
    def anello(rx, rz, y0, giu=0.0):
        r = []
        for i in range(n):
            th = 2 * math.pi * i / n; fr = math.sin(th)                                  # fr = 1 davanti (+z)
            punta = giu * max(0.0, math.exp(-((th - math.pi / 2 - 0.42) / 0.22) ** 2) + math.exp(-((th - math.pi / 2 + 0.42) / 0.22) ** 2))
            r.append(bm.verts.new((rx * math.cos(th), y0 - 0.012 * max(0.0, fr) - punta, rz * fr + 0.004)))
        return r
    anelli = [anello(0.060, 0.046, -0.040), anello(0.058, 0.044, -0.008),               # collo in piedi
              anello(0.064, 0.050, -0.004), anello(0.074, 0.060, -0.030, 0.035)]        # vela ripiegata con le punte
    for a_, b_ in ((0, 1), (1, 2), (2, 3)):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((anelli[a_][i], anelli[a_][j], anelli[b_][j], anelli[b_][i]))
    # bottoni: dischetti sul davanti del busto, ogni 9 cm
    Mi_ = M.inverted(); loc_b = [(Mi_ @ v_.co) for v_ in busto.data.vertices]
    fronte = sorted((q for q in loc_b if abs(q.x) < 0.012 and q.z > 0), key=lambda q: -q.y)
    yb = -0.075
    while yb > -lunga + 0.06 and fronte:
        q = min(fronte, key=lambda q: abs(q.y - yb)); c_ = Vector((0.0, q.y, q.z + 0.0025))
        vs_ = [bm.verts.new(c_ + Vector((0.0055 * math.cos(2 * math.pi * k / 10), 0.0055 * math.sin(2 * math.pi * k / 10), 0))) for k in range(10)]
        bm.faces.new(vs_); yb -= 0.09
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops: lp[uvl].uv = (lp.vert.co.x / lato_tex, lp.vert.co.y / lato_tex)
    bm.transform(M); me = bpy.data.meshes.new(f"{nome} colletto"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f"{nome} colletto (tessili)", me); scn.collection.objects.link(ob); ob.data.materials.append(materiale)
    so = ob.modifiers.new("Spessore", "SOLIDIFY"); so.thickness = 0.0025
    fatti.append(ob)
    for ob in fatti:
        for pl in ob.data.polygons: pl.use_smooth = True
        sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
    return fatti


def asciugamano(scn, nome, barra, u, n, larga, giu_davanti, giu_dietro, materiale, lato_tex, r_barra=0.01, passo=0.015, seme=4,
                fotogrammi=45, muro=0.05, massa=0.004, onde=0.03):
    """asciugamano appeso a una barra (Andrea, 2026-11-17: "dettagli che rendano la casa vissuta"). Nasce già nella forma
    finale (regola 2 della skill): un telo avvolto sulla barra, con un lembo giù davanti e uno dietro; fermo in cima, la gravità
    e qualche onda di partenza gli danno le pieghe morbide. barra = centro della barra (3D); u = asse della barra in pianta;
    n = dal muro verso la stanza; muro = distanza della barra dal muro (il lembo dietro non lo attraversa)."""
    import random
    rnd = random.Random(seme); c = Vector(barra); u = Vector((u[0], u[1], 0)).normalized(); n = Vector((n[0], n[1], 0)).normalized()
    if u.cross(n).z < 0: u = -u                                          # terna destrorsa (u, n, su)
    R = r_barra + 0.004; arco = math.pi * R; Ltot = giu_davanti + arco + giu_dietro
    nu, nv = max(2, round(larga / passo)), max(4, round(Ltot / passo))
    # pieghe verticali morbide (onde lungo la larghezza, 8-14 cm) e un lembo un po' storto: piatto sembrava una lastra (2026-11-17)
    ond = [(rnd.uniform(0.6, 1.0) * onde, rnd.uniform(45, 80), rnd.uniform(0, 6.3)) for _ in range(3)]
    def punto(x, s):
        if s < giu_davanti: dn, dz = R, -(giu_davanti - s)                                        # lembo davanti
        elif s < giu_davanti + arco: th = (s - giu_davanti) / R; dn, dz = R * math.cos(th), R * math.sin(th)   # sopra la barra
        else: dn, dz = -R, -(s - giu_davanti - arco)                                             # lembo dietro
        giu_ = max(0.0, -dz) / max(giu_davanti, giu_dietro)
        dn += sum(a * math.sin(k * x + f) for a, k, f in ond) * giu_ * (1 if dn > 0 else -0.4)
        return c + u * x + n * dn + Vector((0, 0, dz))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); g = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            x, s = -larga / 2 + larga * i / nu, Ltot * j / nv; g[i, j] = bm.verts.new(punto(x, s))
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((g[i, j], g[i + 1, j], g[i + 1, j + 1], g[i, j + 1]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = ((larga * ii / nu) / lato_tex, (Ltot * jj / nv) / lato_tex)
    bm.verts.index_update()
    fermi = [g[i, j].index for i in range(nu + 1) for j in range(nv + 1) if giu_davanti + arco * 0.25 <= Ltot * j / nv <= giu_davanti + arco * 0.75]
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); scn.collection.objects.link(ob)
    vg = ob.vertex_groups.new(name="fisso"); vg.add(fermi, 1.0, "REPLACE")
    cl = ob.modifiers.new("Tessuto", "CLOTH"); st = cl.settings
    st.quality = 10; st.mass = massa; st.air_damping = 1.5; st.tension_stiffness = st.compression_stiffness = 12.0
    st.shear_stiffness = 4.0; st.bending_stiffness = 0.15; st.vertex_group_mass = "fisso"; st.pin_stiffness = 1.0
    cl.collision_settings.distance_min = 0.004; cl.collision_settings.collision_quality = 3
    lato_m = (c - n * (muro + 0.1)); obs = _ostacolo(scn, [(lato_m, u.xy, n.xy, larga + 0.6, 0.2, c.z - 2.0, c.z + 0.2)], nome + " muro")
    _simula(scn, ob, fotogrammi); bpy.data.objects.remove(obs, do_unlink=True)
    if ob.vertex_groups.get("fisso"): ob.vertex_groups.remove(ob.vertex_groups["fisso"])
    LOG(f"tessili {nome}: grinze {grinze(ob):.1f}°")
    for pl in ob.data.polygons: pl.use_smooth = True
    so = ob.modifiers.new("Spessore", "SOLIDIFY"); so.thickness = 0.005; so.offset = 0.0
    sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
    ob.data.materials.append(materiale)
    return ob
