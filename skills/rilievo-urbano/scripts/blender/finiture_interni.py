"""Finiture degli interni del progetto (fase 3 della filiera): quello che l'IFC di Edificius non porta.

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P finiture_interni.py -- <cartella modello>
  python finiture_interni.py -- <cartella modello> --blend contesto_progetto.blend      (Blender come modulo)

Dopo importa_progetto.py e prima di percorsi_camera.py. Riscrive contesto_progetto.blend; si può rilanciare.
Valori in <modello>/lotto.json → progetto_ifc → "finiture" (tutti facoltativi; predefiniti in PRED):
  soffitto   le falde (elementi IFC il cui nome comincia con "nomi") viste da sotto diventano perlinato: doghe larghe
             doga_m, colore del legno; sotto ogni falda travetti a vista lungo la pendenza (sezione_m [base, altezza],
             interasse_m), solo sopra i vani interni
  pavimento  una superficie per vano interno, appoggiata al solaio: piastrelle formato_m con fuga_mm, colore; "per_vano"
             cambia i valori per le stanze il cui nome comincia con la chiave (es. "Bagno")
Regole generali, nessuna eccezione per il singolo progetto: l'IFC Edificius ha un solo materiale per falda (sopra e
sotto) e nessuno strato di pavimento distinto dal solaio.
I materiali sono procedurali (nodi Blender): per Unreal vanno rifatti come materiali della libreria di studio.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, registro
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

argv, opt = argomenti()
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
if opt("--blend"): bpy.ops.wm.open_mainfile(filepath=os.path.join(USCITA, opt("--blend")))
L = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8"))
log = registro(os.path.join(USCITA, "finiture_interni.log"))
scn = bpy.context.scene

PRED = {"esterni": ["Cortile", "Balcone", "Veranda", "Terrazza", "Portico", "Giardino"],
        "soffitto": {"nomi": ["Falda"], "colore": "#EFE8D6", "doga_m": 0.12,
                     "travetti": {"sezione_m": [0.10, 0.16], "interasse_m": 0.70}},
        "pavimento": {"colore": "#BDB6A8", "formato_m": [0.60, 0.60], "fuga_mm": 2.0, "ruvidita": 0.45, "per_vano": {}}}
def unisci(a, b):
    return {k: (unisci(a[k], b[k]) if isinstance(a[k], dict) and isinstance(b.get(k), dict) and k != "per_vano" else b.get(k, a[k])) for k in a}
F = unisci(PRED, {k: v for k, v in L.get("progetto_ifc", {}).get("finiture", {}).items() if not k.startswith("_")})

def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]

def materiale(nome, colore, ruvidita, modulo, fuga_m, scuro=0.55, sfalsato=0.0):
    """Principled con un reticolo procedurale (piastrelle o doghe) sulle coordinate UV in metri."""
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0]); b.inputs["Roughness"].default_value = ruvidita
    uv = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
    c = lin(colore); br.inputs["Color1"].default_value = c; br.inputs["Color2"].default_value = [x * 0.96 for x in c[:3]] + [1]
    br.inputs["Mortar"].default_value = [x * scuro for x in c[:3]] + [1]
    br.offset = sfalsato; br.squash = 1.0; br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = modulo[0]; br.inputs["Row Height"].default_value = modulo[1]
    br.inputs["Mortar Size"].default_value = fuga_m; br.inputs["Mortar Smooth"].default_value = 0.0
    nt.links.new(uv.outputs["UV"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    return m

def coll(nome):
    radice = bpy.data.collections.get("PROGETTO") or scn.collection
    c = bpy.data.collections.get(nome)
    if not c: c = bpy.data.collections.new(nome); radice.children.link(c)
    return c
FIN = coll("PRG_Finiture")
for o in list(FIN.objects): bpy.data.objects.remove(o, do_unlink=True)      # rilancio: le finiture si rifanno

# ------------------------------------------------------------------------------------------------ vani
vani = []
for ob in scn.objects:
    if "vano" not in ob or ob.type != "MESH": continue
    W = [ob.matrix_world @ v.co for v in ob.data.vertices]; z0 = min(w.z for w in W)
    base = [Polygon([W[i].xy[:] for i in pl.vertices]) for pl in ob.data.polygons if all(W[i].z < z0 + 0.05 for i in pl.vertices)]
    pol = unary_union([q for q in base if q.is_valid and q.area > 1e-6]).buffer(0.01)
    if pol.is_empty: continue
    if pol.geom_type != "Polygon": pol = max(pol.geoms, key=lambda q: q.area)
    vani.append({"nome": ob["vano"], "pol": pol, "z0": z0, "villa": int(ob.get("villa", 1)),
                 "esterno": ob["vano"].startswith(tuple(F["esterni"]))})
interni = [v for v in vani if not v["esterno"]]
log("vani interni", len(interni), "su", len(vani))

# ------------------------------------------------------------------------------------------------ pavimenti
n_pav = 0
for v in interni:
    P = dict(F["pavimento"]); chiave = next((k for k in P["per_vano"] if v["nome"].startswith(k)), None)
    if chiave: P.update(P["per_vano"][chiave])
    nome_m = "Pavimento " + (chiave or "interni")
    m = materiale(nome_m, P["colore"], P["ruvidita"], P["formato_m"], P["fuga_mm"] / 1000.0)
    pol = v["pol"].buffer(0.06, join_style=2)                 # sotto il filo dell'intonaco e nelle soglie delle porte
    anello = list(pol.exterior.coords)[:-1]
    bm = bmesh.new(); vs = [bm.verts.new((x, y, v["z0"] + 0.004)) for x, y in anello]
    f_ = bm.faces.new(vs)
    if f_.normal.z < 0: f_.normal_flip()
    uvl = bm.loops.layers.uv.new("UVMap")
    for lp in f_.loops: lp[uvl].uv = (lp.vert.co.x, lp.vert.co.y)       # UV in metri: il reticolo ha misure reali
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"Pavimento {v['nome']}"); bm.to_mesh(me); bm.free(); me.materials.append(m)
    ob = bpy.data.objects.new(f"Pavimento {v['nome']} v{v['villa']}", me); ob["villa"] = v["villa"]; ob["finitura"] = "pavimento"
    FIN.objects.link(ob); n_pav += 1
log("pavimenti", n_pav)

# ------------------------------------------------------------------------------------------------ soffitti e travetti
S = F["soffitto"]; T = S["travetti"]
m_perl = materiale("Perlinato soffitto", S["colore"], 0.55, [4.0, S["doga_m"]], 0.004, scuro=0.7, sfalsato=0.5)
m_trave = bpy.data.materials.get("Legno travetti") or bpy.data.materials.new("Legno travetti")
m_trave.use_nodes = True
bt = next(n for n in m_trave.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bt.inputs["Base Color"].default_value = lin(S["colore"]); bt.inputs["Roughness"].default_value = 0.5
n_falde = n_trav = 0
for ob in list(scn.objects):
    if ob.type != "MESH" or "vano" in ob or not ob.name.startswith(tuple(S["nomi"])) or ob.get("finitura"): continue
    villa = int(ob.get("villa", 1)); me = ob.data; mw = ob.matrix_world
    sotto = [pl for pl in me.polygons if (mw.to_3x3() @ pl.normal).z < -0.3]
    if not sotto: continue
    if m_perl.name not in [m.name for m in me.materials if m]: me.materials.append(m_perl)
    idx = [m.name if m else "" for m in me.materials].index(m_perl.name)
    # piano dell'intradosso: normale media pesata sull'area, punto = baricentro delle facce di sotto
    n = Vector((0, 0, 0)); c = Vector((0, 0, 0)); a_tot = 0.0
    for pl in sotto:
        n += (mw.to_3x3() @ pl.normal) * pl.area; c += (mw @ pl.center) * pl.area; a_tot += pl.area
    n.normalize(); c /= a_tot
    if abs(n.z) < 0.2: continue
    g = Vector((n.x, n.y)); piana = g.length < 0.02
    g = g.normalized() if not piana else Vector((1, 0)); t = Vector((-g.y, g.x))
    def z_piano(x, y): return c.z - (n.x * (x - c.x) + n.y * (y - c.y)) / n.z
    # UV dell'intradosso in metri: u lungo le doghe (perpendicolari ai travetti, cioè lungo t), v lungo la pendenza
    uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    passo_v = 1.0 / max(0.2, abs(n.z))                        # la doga si misura sulla falda, non in pianta
    for pl in sotto:
        pl.material_index = idx
        for li in pl.loop_indices:
            w = mw @ me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (w.x * t.x + w.y * t.y, (w.x * g.x + w.y * g.y) * passo_v)
    n_falde += 1
    # travetti: linee lungo la pendenza a interasse costante, ritagliate all'impronta della falda sopra i vani interni
    imp = unary_union([Polygon([(mw @ me.vertices[i].co).xy[:] for i in pl.vertices]) for pl in sotto]).buffer(0.01)
    dentro = unary_union([v["pol"].buffer(0.12) for v in interni if v["villa"] == villa])
    zona = imp.intersection(dentro)
    if zona.is_empty: continue
    xs = [p[0] * t.x + p[1] * t.y for p in imp.exterior.coords] if imp.geom_type == "Polygon" else [q[0] * t.x + q[1] * t.y for gp in imp.geoms for q in gp.exterior.coords]
    ys = [p[0] * g.x + p[1] * g.y for gp in ([imp] if imp.geom_type == "Polygon" else imp.geoms) for p in gp.exterior.coords]
    b_, h_ = T["sezione_m"]; s0 = math.ceil(min(xs) / T["interasse_m"]) * T["interasse_m"]   # griglia assoluta: le falde vicine si allineano
    V, Fc = [], []
    s = s0
    while s <= max(xs):
        ln = LineString([(t.x * s + g.x * (min(ys) - 1), t.y * s + g.y * (min(ys) - 1)), (t.x * s + g.x * (max(ys) + 1), t.y * s + g.y * (max(ys) + 1))])
        pezzi = ln.intersection(zona); s += T["interasse_m"]
        for pz in ([pezzi] if pezzi.geom_type == "LineString" else getattr(pezzi, "geoms", [])):
            if pz.geom_type != "LineString" or pz.length < 0.3: continue
            (x0, y0), (x1, y1) = pz.coords[0], pz.coords[-1]; k = len(V)
            for (x, y) in ((x0, y0), (x1, y1)):
                for sg in (-0.5, 0.5):
                    px, py = x + t.x * b_ * sg, y + t.y * b_ * sg; zt = z_piano(px, py) + 0.005
                    V += [(px, py, zt), (px, py, zt - h_)]
            Fc += [(k, k + 1, k + 3, k + 2), (k + 4, k + 6, k + 7, k + 5), (k, k + 4, k + 5, k + 1), (k + 2, k + 3, k + 7, k + 6),
                   (k + 1, k + 5, k + 7, k + 3), (k, k + 2, k + 6, k + 4)]
            n_trav += 1
    if V:
        mt = bpy.data.meshes.new("Travetti " + ob.name); mt.from_pydata(V, [], Fc); mt.materials.append(m_trave)
        bm = bmesh.new(); bm.from_mesh(mt); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(mt); bm.free()
        ot = bpy.data.objects.new("Travetti " + ob.name, mt); ot["villa"] = villa; ot["finitura"] = "travetti"; FIN.objects.link(ot)
log("falde con perlinato", n_falde, "| travetti", n_trav, f"(sezione {T['sezione_m'][0] * 100:.0f}×{T['sezione_m'][1] * 100:.0f} cm, interasse {T['interasse_m'] * 100:.0f} cm)")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend")); log("fine")
