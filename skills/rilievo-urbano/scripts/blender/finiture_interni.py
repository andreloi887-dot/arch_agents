"""Finiture degli interni del progetto (fase 3 della filiera): quello che l'IFC di Edificius non porta.

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P finiture_interni.py -- <cartella modello>
  python finiture_interni.py -- <cartella modello> --blend contesto_progetto.blend      (Blender come modulo)

Dopo importa_progetto.py e prima di percorsi_camera.py. Riscrive contesto_progetto.blend; si può rilanciare.
Valori in <modello>/lotto.json → progetto_ifc → "finiture" (tutti facoltativi; predefiniti in PRED):
  soffitto   le falde (elementi IFC il cui nome comincia con "nomi") viste da sotto diventano perlinato: doghe larghe
             doga_m, colore del legno. Orditura a vista, solo sopra i vani interni: travi lungo colmi, displuvi e
             compluvi (sezione_displuvio_m); travetti lungo la pendenza, sezione_m [base, altezza] e passo interasse_m
             identici ovunque: sulle travi d'incontro arrivano a coppie nello stesso punto, e la differenza di
             misura finisce in un campo di compensazione al centro; sopra gli infissi il travetto si ferma
             arretro_infisso_m prima, su una trave perpendicolare che scarica sui travetti ai lati
  pavimento  una superficie per vano interno, appoggiata al solaio: piastrelle formato_m con fuga_mm, colore, posate
             parallele ai muri con le fughe continue in tutta la villa; "per_vano"
             cambia i valori per le stanze il cui nome comincia con la chiave (es. "Bagno")
  battiscopa dello stesso materiale del pavimento, altezza_m, lungo tutti i muri tranne che davanti a porte e
             portefinestre; "escludi": vani senza battiscopa (bagni)
  porte      le porte interne dell'IFC (tra due vani interni) si nascondono e si rifanno: imbotte, coprifilo sottile
             (coprifilo_m), anta liscia aperta di apertura_gradi con il verso della planimetria (proprietà scritte da
             importa_progetto.py), maniglia; le scorrevoli spariscono nel muro. L'anta è un oggetto a parte con
             l'origine sulla cerniera: in Unreal si può animare
  controsoffitto  nei vani "vani" (disimpegno): lastra a altezza_m, faretti LED tondi a incasso (con luce vera),
             griglie di ripresa; nelle stanze servite, sopra la porta verso il disimpegno, una bocchetta di immissione
             ("bocchette_escludi": vani senza bocchetta)
Regole generali, nessuna eccezione per il singolo progetto: l'IFC Edificius ha un solo materiale per falda (sopra e
sotto) e nessuno strato di pavimento distinto dal solaio.
I materiali sono procedurali (nodi Blender): per Unreal vanno rifatti come materiali della libreria di studio.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import avvio, lin, svuota
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

argv, opt, MOD, USCITA, log, scn = avvio("finiture_interni.log")
L = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8"))

PRED = {"esterni": ["Cortile", "Balcone", "Veranda", "Terrazza", "Portico", "Giardino"],
        "soffitto": {"nomi": ["Falda"], "colore": "#EFE8D6", "doga_m": 0.12,
                     "travetti": {"sezione_m": [0.10, 0.16], "interasse_m": 0.70, "sezione_displuvio_m": [0.14, 0.22],
                                  "arretro_infisso_m": 0.25}},
        "pavimento": {"colore": "#BDB6A8", "formato_m": [0.60, 0.60], "fuga_mm": 2.0, "ruvidita": 0.45, "per_vano": {}},
        "battiscopa": {"altezza_m": 0.07, "spessore_m": 0.01, "escludi": ["Bagno"]},
        "porte": {"colore": "#F1EEE6", "maniglia": "#8E8C88", "coprifilo_m": 0.05, "imbotte_m": 0.025, "anta_m": 0.04, "apertura_gradi": 90.0},
        "controsoffitto": {"vani": ["Dis"], "altezza_m": 2.40, "colore": "#F4F2EC", "faretti_passo_m": 0.9, "faretto_diametro_m": 0.085,
                           "faretto_w": 12.0, "faretto_colore": [1.0, 0.88, 0.72], "griglia_m": [0.50, 0.20], "griglia_ogni_m2": 3.0,
                           "bocchetta_m": [0.50, 0.15], "bocchetta_sopra_m": 0.05, "bocchette_escludi": ["Bagno"]}}
def unisci(a, b):
    return {k: (unisci(a[k], b[k]) if isinstance(a[k], dict) and isinstance(b.get(k), dict) and k != "per_vano" else b.get(k, a[k])) for k in a}
F = unisci(PRED, {k: v for k, v in L.get("progetto_ifc", {}).get("finiture", {}).items() if not k.startswith("_")})


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
svuota(bpy, FIN.objects)      # rilancio: le finiture si rifanno

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
# posa parallela ai muri: direzione del lato lungo del vano più grande di ogni villa, la stessa per tutta la villa
# (le fughe continuano da una stanza all'altra attraverso le porte)
POSA = {}
for villa in {v["villa"] for v in interni}:
    grande = max((v for v in interni if v["villa"] == villa), key=lambda v: v["pol"].area)
    r = list(grande["pol"].minimum_rotated_rectangle.exterior.coords)
    lati = [(Vector(r[k + 1]) - Vector(r[k])) for k in range(2)]; lato = max(lati, key=lambda q: q.length).normalized()
    POSA[villa] = (lato, Vector((-lato.y, lato.x)), Vector(r[0]))
def tinta(nome, colore, ruvidita, metallo=0.0, emissione=0.0):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = lin(colore); b.inputs["Roughness"].default_value = ruvidita; b.inputs["Metallic"].default_value = metallo
    if emissione: b.inputs["Emission Color"].default_value = lin(colore); b.inputs["Emission Strength"].default_value = emissione
    return m
def poligoni(g): return [q for q in ([g] if g.geom_type == "Polygon" else getattr(g, "geoms", [])) if q.geom_type == "Polygon" and q.area > 1e-5]
def piano(bm, pol, z):
    """facce orizzontali del poligono (anche con fori) alla quota z, normale in alto."""
    edges = []
    for an in [pol.exterior] + list(pol.interiors):
        vs = [bm.verts.new((x, y, z)) for x, y in list(an.coords)[:-1]]
        edges += [bm.edges.new((vs[k], vs[(k + 1) % len(vs)])) for k in range(len(vs))]
    ff = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)["geom"]
    ff = [x for x in ff if isinstance(x, bmesh.types.BMFace)]
    for x in ff:
        x.normal_update()
        if x.normal.z < 0: x.normal_flip()
    return ff
def nuovo_oggetto(nome, me, villa, finitura):
    ob = bpy.data.objects.new(nome, me); ob["villa"] = villa; ob["finitura"] = finitura; FIN.objects.link(ob); return ob
class Volumi:
    """scatole in un riferimento locale: origine o (x, y, z), asse u in pianta, v = u ruotato di 90°."""
    def __init__(s, o, u): s.o = Vector(o); s.u = Vector(u).normalized(); s.v = Vector((-s.u.y, s.u.x)); s.V, s.F, s.M, s.m = [], [], [], []
    def scat(s, u0, u1, v0, v1, z0, z1, mat):
        if mat not in s.m: s.m.append(mat)
        n = len(s.V)
        for z in (z0, z1):
            for a, b in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)): s.V.append((s.o.x + s.u.x * a + s.v.x * b, s.o.y + s.u.y * a + s.v.y * b, s.o.z + z))
        s.F += [(n, n + 3, n + 2, n + 1), (n + 4, n + 5, n + 6, n + 7), (n, n + 1, n + 5, n + 4), (n + 1, n + 2, n + 6, n + 5), (n + 2, n + 3, n + 7, n + 6), (n + 3, n, n + 4, n + 7)]
        s.M += [s.m.index(mat)] * 6
    def asta(s, p0, p1, r0, r1, mat, seg=20):
        """cilindro (anche rastremato) tra due punti (x, y, z) del riferimento locale, in qualsiasi direzione: rosette, leve."""
        if mat not in s.m: s.m.append(mat)
        P0 = s.o + Vector((*(s.u * p0[0] + s.v * p0[1]), p0[2])); P1 = s.o + Vector((*(s.u * p1[0] + s.v * p1[1]), p1[2]))
        ax = (P1 - P0).normalized(); e1 = ax.cross(Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))).normalized(); e2 = ax.cross(e1)
        n = len(s.V)
        for q, r in ((P0, r0), (P1, r1)):
            for i in range(seg): t = 2 * math.pi * i / seg; s.V.append(tuple(q + (e1 * math.cos(t) + e2 * math.sin(t)) * r))
        for i in range(seg): s.F.append((n + i, n + (i + 1) % seg, n + seg + (i + 1) % seg, n + seg + i))
        s.F += [tuple(n + i for i in reversed(range(seg))), tuple(n + seg + i for i in range(seg))]; s.M += [s.m.index(mat)] * (seg + 2)
    def tubo(s, punti, raggi, mat, seg=32):
        """tubo continuo lungo una linea di punti (x, y, z locali) con il raggio che cambia punto per punto: leve delle maniglie
        (un pezzo solo che curva e si assottiglia, non cilindri accostati). Sezioni orientate con il trasporto parallelo."""
        if mat not in s.m: s.m.append(mat)
        P = [s.o + Vector((*(s.u * q[0] + s.v * q[1]), q[2])) for q in punti]; n = len(P)
        T = [((P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()) for i in range(n)]
        e1 = T[0].cross(Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))).normalized(); base = len(s.V)
        for i in range(n):
            if i: e1 = (e1 - T[i] * e1.dot(T[i])).normalized()
            e2 = T[i].cross(e1)
            for k in range(seg): t = 2 * math.pi * k / seg; s.V.append(tuple(P[i] + (e1 * math.cos(t) + e2 * math.sin(t)) * raggi[i]))
        for i in range(n - 1):
            for k in range(seg):
                a_, b_ = base + i * seg + k, base + i * seg + (k + 1) % seg; s.F.append((a_, b_, b_ + seg, a_ + seg)); s.M.append(s.m.index(mat))
        s.F += [tuple(base + k for k in reversed(range(seg))), tuple(base + (n - 1) * seg + k for k in range(seg))]; s.M += [s.m.index(mat)] * 2
    def cil(s, a, b, r, z0, z1, mat, seg=24):
        if mat not in s.m: s.m.append(mat)
        n = len(s.V); cx, cy = s.o.x + s.u.x * a + s.v.x * b, s.o.y + s.u.y * a + s.v.y * b
        for z in (z0, z1):
            for i in range(seg): s.V.append((cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), s.o.z + z))
        for i in range(seg): s.F.append((n + i, n + (i + 1) % seg, n + seg + (i + 1) % seg, n + seg + i))
        s.F += [tuple(n + i for i in reversed(range(seg))), tuple(n + seg + i for i in range(seg))]; s.M += [s.m.index(mat)] * (seg + 2)
    def fine(s, nome, villa, finitura, smusso=0.0, locale=None):
        """locale = (origine, angolo): i vertici passano nel riferimento dell'oggetto (anta con origine sulla cerniera)."""
        V = s.V
        if locale:
            Mi = (Matrix.Translation(locale[0]) @ Matrix.Rotation(locale[1], 4, "Z")).inverted(); V = [tuple(Mi @ Vector(q)) for q in V]
        me = bpy.data.meshes.new(nome); me.from_pydata(V, [], s.F)
        for m in s.m: me.materials.append(m)
        me.polygons.foreach_set("material_index", s.M); me.update(); ob = nuovo_oggetto(nome, me, villa, finitura)
        if smusso:
            bv = ob.modifiers.new("Smusso", "BEVEL"); bv.limit_method = "ANGLE"; bv.width = smusso; bv.segments = 2
        return ob

# porte e portefinestre: riferimento locale e vani ai due lati (proprietà scritte da importa_progetto.py)
def vano_in(villa, q): return next((v for v in vani if v["villa"] == villa and v["pol"].contains(Point(q.x, q.y))), None)
porte = []
for ob in scn.objects:
    if "porta_tipo" not in ob: continue
    o = Vector(ob["porta_origine"]); x = Vector(ob["porta_x"]); y = Vector(ob["porta_y"]); Wd = ob["porta_larghezza"]; y0, y1 = ob["porta_muro_y"]
    c = o.xy + x * Wd / 2; villa = int(ob.get("villa", 1))
    pt = {"ob": ob, "o": o, "x": x, "y": y, "W": Wd, "H": ob["porta_altezza"], "y0": y0, "y1": y1, "tipo": ob["porta_tipo"], "zero": bool(ob["porta_cerniera_a_zero"]),
          "villa": villa, "piu": vano_in(villa, c + y * (y1 + 0.25)), "meno": vano_in(villa, c + y * (y0 - 0.25))}
    pt["interna"] = bool(pt["piu"] and pt["meno"] and not pt["piu"]["esterno"] and not pt["meno"]["esterno"])
    def rett(mx, my, pt=pt): return Polygon([tuple(pt["o"].xy + pt["x"] * a + pt["y"] * b) for a, b in ((-mx, pt["y0"] - my), (pt["W"] + mx, pt["y0"] - my), (pt["W"] + mx, pt["y1"] + my), (-mx, pt["y1"] + my))])
    pt["rett"] = rett; porte.append(pt)
from shapely.geometry import MultiPoint
a_terra = []                                                  # impronte di porte e portefinestre che arrivano al pavimento
for ob in scn.objects:
    if ob.get("ifc_classe") not in ("IfcWindow", "IfcDoor") or ob.type != "MESH" or not ob.data.vertices or "porta_tipo" in ob: continue
    W = [ob.matrix_world @ v_.co for v_ in ob.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle
    if r_.geom_type == "Polygon" and r_.length < 14: a_terra.append((r_.buffer(0.12, join_style=2), min(w.z for w in W), int(ob.get("villa", 1))))

# un solo pavimento per villa, piano e materiale: continuo da una stanza all'altra, anche nelle soglie delle porte interne
gruppi = {}
for v in interni:
    P = dict(F["pavimento"]); chiave = next((k for k in P["per_vano"] if v["nome"].startswith(k)), None)
    if chiave: P.update(P["per_vano"][chiave])
    v["mat_pav"] = materiale("Pavimento " + (chiave or "interni"), P["colore"], P["ruvidita"], P["formato_m"], P["fuga_mm"] / 1000.0)
    gruppi.setdefault((v["villa"], round(v["z0"], 2), v["mat_pav"].name), []).append(v)
n_pav = 0
for (villa, z0, nome_m), gv in gruppi.items():
    pezzi = [v["pol"].buffer(0.06, join_style=2) for v in gv]         # sotto il filo dell'intonaco
    pezzi += [pt["rett"](0.0, 0.07) for pt in porte if pt["interna"] and pt["villa"] == villa and (pt["piu"] in gv or pt["meno"] in gv)]
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); eu, ev, o0 = POSA[villa]
    for pol in poligoni(unary_union(pezzi).buffer(0.002).simplify(0.003)):
        for f_ in piano(bm, pol, z0 + 0.004):
            for lp in f_.loops:                                   # UV in metri lungo i muri: il reticolo ha misure reali
                d = Vector(lp.vert.co.xy) - o0; lp[uvl].uv = (d.dot(eu), d.dot(ev))
    me = bpy.data.meshes.new(f"Pavimento villa {villa}"); bm.to_mesh(me); bm.free(); me.materials.append(bpy.data.materials[nome_m])
    nuovo_oggetto(f"Pavimento villa {villa} quota {z0:.2f}", me, villa, "pavimento"); n_pav += 1
log("pavimenti", n_pav, "continui tra le stanze | posa parallela ai muri")

# battiscopa: fascia del materiale del pavimento lungo i muri, interrotta davanti a porte e portefinestre
BS = F["battiscopa"]; n_bs = 0
for v in interni:
    if v["nome"].startswith(tuple(BS["escludi"])): continue
    vuoti = [pt["rett"](F["porte"]["coprifilo_m"], 0.35) for pt in porte if pt["villa"] == v["villa"]] + [r_ for r_, zb, vl in a_terra if vl == v["villa"] and zb < v["z0"] + 0.15]
    fascia = v["pol"].buffer(-0.01, join_style=2).difference(v["pol"].buffer(-0.01 - BS["spessore_m"], join_style=2)).difference(unary_union(vuoti))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); eu, ev, o0 = POSA[v["villa"]]
    for pol in poligoni(fascia):
        ff = piano(bm, Polygon(pol.exterior), v["z0"] + 0.004)
        su = bmesh.ops.extrude_face_region(bm, geom=ff)["geom"]
        bmesh.ops.translate(bm, verts=[x for x in su if isinstance(x, bmesh.types.BMVert)], vec=(0, 0, BS["altezza_m"]))
        bmesh.ops.delete(bm, geom=ff, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f_ in bm.faces:
        for lp in f_.loops:
            d = Vector(lp.vert.co.xy) - o0; lp[uvl].uv = (d.dot(eu) + d.dot(ev), 0.3 + lp.vert.co.z - v["z0"])
    if bm.faces:
        me = bpy.data.meshes.new(f"Battiscopa {v['nome']}"); bm.to_mesh(me); me.materials.append(v["mat_pav"])
        nuovo_oggetto(f"Battiscopa {v['nome']} v{v['villa']}", me, v["villa"], "battiscopa"); n_bs += 1
    bm.free()
log("battiscopa", n_bs, f"vani | {BS['altezza_m'] * 100:.0f} cm, materiale del pavimento | esclusi {BS['escludi']}")

# ------------------------------------------------------------------------------------------------ rivestimento dei bagni
# Andrea, 2026-11-17 sera (riferimento bagno.jpg): lastre di pietra beige opaca a grana fine con fughe sottili fino a 1,50 m da
# terra, nella doccia fino a 2,10 m; sopra intonaco. Lastre 75 × 75 cm (ipotesi letta sulla foto: lastre quasi quadrate;
# due file arrivano giuste a 1,50 m), spessore 8 mm, fuga 2 mm color sabbia. La doccia è il blocco IFC alto almeno 1,8 m del
# bagno. Il rivestimento si ferma alle porte (con il coprifilo), alle portefinestre e alle finestre (anche quella dentro la
# doccia del secondo bagno) e sotto il soffitto. Solo nelle ville arredate (le altre restano com'erano).
import random as _rnd
import materiali_arredo as MA
_A = json.load(open(os.path.join(MOD, "arredi.json"), encoding="utf-8")) if os.path.isfile(os.path.join(MOD, "arredi.json")) else {"arredi": []}
MA.configura(_A.get("stile", {}))
RV = {"vani": ["Bagno"], "altezza_m": 1.50, "doccia_m": 2.10, "modulo_m": [0.75, 0.75], "fuga_m": 0.002, "spessore_m": 0.008, **F.get("rivestimento", {})}
VILLE_RV = {int(x.get("villa", 1)) for x in _A["arredi"]}
from mathutils.bvhtree import BVHTree
_V, _F = [], []
for ob in scn.objects:
    if ob.type != "MESH" or "vano" in ob or not (ob.name.startswith(tuple(F["soffitto"]["nomi"])) or ob.get("ifc_classe") in ("IfcRoof", "IfcSlab")): continue
    n0 = len(_V); _V += [ob.matrix_world @ q.co for q in ob.data.vertices]; _F += [[n0 + i for i in pl.vertices] for pl in ob.data.polygons]
_TETTO = BVHTree.FromPolygons(_V, _F) if _F else None
def _soffitto(x, y, z_da):
    h = _TETTO.ray_cast(Vector((x, y, z_da)), Vector((0, 0, 1)), 12.0) if _TETTO else (None,)
    return h[0].z if h[0] is not None else z_da + 3.0
def _togli(r, buchi):
    """rettangoli (s0, s1, z0, z1) di r che restano togliendo i rettangoli buchi."""
    pezzi = [r]
    for b in buchi:
        nuovi = []
        for s0, s1, z0, z1 in pezzi:
            if b[0] >= s1 or b[1] <= s0 or b[2] >= z1 or b[3] <= z0: nuovi.append((s0, s1, z0, z1)); continue
            if b[0] > s0: nuovi.append((s0, b[0], z0, z1))
            if b[1] < s1: nuovi.append((b[1], s1, z0, z1))
            ms0, ms1 = max(s0, b[0]), min(s1, b[1])
            if b[2] > z0: nuovi.append((ms0, ms1, z0, b[2]))
            if b[3] < z1: nuovi.append((ms0, ms1, b[3], z1))
        pezzi = [p_ for p_ in nuovi if p_[1] - p_[0] > 0.005 and p_[3] - p_[2] > 0.005]
    return pezzi
# aperture: (impronta in pianta, quota bassa, quota alta, villa, asse lungo in pianta). Le porte interne rifatte si tagliano sul
# filo esterno del coprifilo (+2 mm): Andrea, 2026-11-17: "fai toccare il rivestimento al coprifilo della porta"
_CF_ESTERNO = F["porte"]["coprifilo_m"] - F["porte"]["imbotte_m"] + 0.01 + 0.002
aperture = []
for pt in porte:
    if pt["interna"]:
        aperture.append((pt["rett"](_CF_ESTERNO, 0.35), pt["o"].z, pt["o"].z + pt["H"] + _CF_ESTERNO, pt["villa"], Vector(pt["x"][:2]).normalized()))
rifatte = {pt["ob"].name for pt in porte if pt["interna"]}
for ob in scn.objects:
    if ob.get("ifc_classe") not in ("IfcWindow", "IfcDoor") or ob.type != "MESH" or not ob.data.vertices or ob.name in rifatte: continue
    W = [ob.matrix_world @ v_.co for v_ in ob.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle
    if r_.geom_type != "Polygon" or r_.length >= 14: continue
    cc = list(r_.exterior.coords); l1, l2 = Vector(cc[1]) - Vector(cc[0]), Vector(cc[2]) - Vector(cc[1])
    aperture.append((r_.buffer(0.01, join_style=2), min(w.z for w in W) - 0.01, max(w.z for w in W) + 0.01, int(ob.get("villa", 1)), (l1 if l1.length >= l2.length else l2).normalized()))
m_riv = MA.mat("pietra_bagno"); m_fuga = tinta("Fuga rivestimento", MA.ST["fuga_bagno"], 0.9)
n_riv = n_lastre = 0
for v in interni:
    if not v["nome"].startswith(tuple(RV["vani"])) or v["villa"] not in VILLE_RV: continue
    rnd = _rnd.Random(len(v["nome"]) * 7 + round(v["pol"].area * 100))
    docce = []
    for ob in scn.objects:
        if ob.get("ifc_classe") != "IfcBuildingElementProxy" or ob.type != "MESH" or not ob.data.vertices or ob.hide_render: continue
        W = [ob.matrix_world @ q.co for q in ob.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle
        if v["pol"].contains(r_.centroid) and max(w.z for w in W) - min(w.z for w in W) >= 1.8 and r_.area >= 0.6: docce.append(r_.buffer(0.06, join_style=2))
    muro = v["pol"].buffer(-0.01, join_style=2); anello = list(muro.exterior.coords)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); bf = bmesh.new()
    mu, mv = RV["modulo_m"]; fg = RV["fuga_m"]; sp = RV["spessore_m"]
    def scatola(bm_, a, d, n, s0, s1, z0, z1, t0, t1, uv0=None):
        vs = []
        for z in (z0, z1):
            for s, t in ((s0, t0), (s1, t0), (s1, t1), (s0, t1)): q = a + d * s + n * t; vs.append(bm_.verts.new((q.x, q.y, z)))
        ff = [bm_.faces.new([vs[i] for i in f]) for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
        if uv0 is not None:
            for f_ in ff:
                for lp in f_.loops:
                    q = Vector(lp.vert.co); s_ = (q.xy - a).dot(d); lp[uvl].uv = ((s_ - s0 + uv0[0]) / 3.0, (q.z - z0 + uv0[1]) / 3.0)
    for k in range(len(anello) - 1):
        a, b = Vector(anello[k]), Vector(anello[k + 1]); L = (b - a).length
        if L < 0.05: continue
        d = (b - a).normalized(); n = Vector((-d.y, d.x))
        if not muro.contains(Point(*((a + b) / 2 + n * 0.1))): n = -n
        riga = LineString([tuple(a), tuple(b)])
        alti = []                                                # tratti in doccia (s0, s1)
        for dc in docce:
            x_ = riga.intersection(dc)
            for g in ([x_] if x_.geom_type == "LineString" else getattr(x_, "geoms", [])):
                if g.geom_type == "LineString" and g.length > 0.02:
                    ss = sorted((Vector(c_) - a).dot(d) for c_ in g.coords); alti.append((ss[0], ss[-1]))
        buchi = []
        for imp, zlo, zhi, vl, asse in aperture:
            # taglia solo le aperture di QUESTO muro: parallele al muro e che lo attraversano per almeno 10 cm (prima tagliava
            # anche le porte vicine e quelle dei muri perpendicolari vicino all'angolo: nel bagno B mancava il muro della porta)
            if vl != v["villa"] or abs(asse.dot(d)) < 0.9 or imp.intersection(riga).length < 0.10: continue
            ss = [(Vector(c_) - a).dot(d) for c_ in imp.exterior.coords]
            buchi.append((max(0.0, min(ss)), min(L, max(ss)), zlo - v["z0"], zhi - v["z0"]))
        # tagli verticali: moduli dal capo del muro, più i bordi della doccia (la lastra cambia altezza lì)
        tagli = sorted(set([min(L, mu * i) for i in range(int(L / mu) + 2)] + [x for t_ in alti for x in t_ if 0 < x < L]))
        for i in range(len(tagli) - 1):
            s0, s1 = tagli[i], tagli[i + 1]
            if s1 - s0 < 0.005: continue
            sm = (s0 + s1) / 2; doccia = any(t_[0] - 0.01 <= sm <= t_[1] + 0.01 for t_ in alti)
            q = a + d * sm + n * 0.05; tetto = _soffitto(q.x, q.y, v["z0"] + 1.0) - v["z0"] - 0.005
            H = min(RV["doccia_m"] if doccia else RV["altezza_m"], tetto)
            righe = [(mv * j, min(H, mv * (j + 1))) for j in range(int(H / mv) + 1) if mv * j < H - 0.005]
            for z0r, z1r in righe:
                for s0_, s1_, z0_, z1_ in _togli((s0, s1, z0r, z1r), buchi):
                    uv0 = (rnd.uniform(0, 2.0), rnd.uniform(0, 2.0))
                    # ogni lastra rientra di mezza fuga, tranne a terra, in cima e ai capi del muro
                    scatola(bm, a, d, n, s0_ + (fg / 2 if s0_ > 1e-6 else 0.0), s1_ - (fg / 2 if s1_ < L - 1e-6 else 0.0),
                            v["z0"] + z0_ + (fg / 2 if z0_ > 1e-6 else 0.0), v["z0"] + z1_ - (fg / 2 if z1_ < H - 1e-6 else 0.0), 0.002, sp, uv0)
                    scatola(bf, a, d, n, s0_, s1_, v["z0"] + z0_, v["z0"] + z1_, 0.0, 0.004)          # fuga dietro le lastre
                    n_lastre += 1
    for b_, mt_, nm_ in ((bm, m_riv, "lastre"), (bf, m_fuga, "fughe")):
        bmesh.ops.recalc_face_normals(b_, faces=b_.faces[:])
        if b_.faces:
            me = bpy.data.meshes.new(f"Rivestimento {nm_} {v['nome']}"); b_.to_mesh(me); me.materials.append(mt_)
            if not me.uv_layers: me.uv_layers.new(name="UVMap")
            nuovo_oggetto(f"Rivestimento {nm_} {v['nome']} v{v['villa']}", me, v["villa"], "rivestimento")
        b_.free()
    n_riv += 1
    log(f"rivestimento {v['nome']} v{v['villa']}: docce {len(docce)}, fino a {RV['altezza_m']:.2f} m (doccia {RV['doccia_m']:.2f} m)")
log("rivestimento bagni", n_riv, "vani |", n_lastre, f"lastre {RV['modulo_m'][0] * 100:.0f}×{RV['modulo_m'][1] * 100:.0f} cm")

# doccia (Andrea, 2026-11-17 sera): vetro temperato chiaro e montanti in acciaio lucido. La doccia dell'IFC è un blocco solo:
# si divide in parti connesse; le lastre (sottili, alte) diventano vetro chiaro, il piatto resta com'è, il resto (montanti,
# profili, rubinetteria) acciaio lucido. In Unreal il vetro (opacità < 1) diventa M_Vetro da solo (prepara_render.py)
m_vd = bpy.data.materials.get("Vetro doccia") or bpy.data.materials.new("Vetro doccia"); m_vd.use_nodes = True
_b = next(n for n in m_vd.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
_b.inputs["Base Color"].default_value = (0.93, 0.95, 0.95, 1); _b.inputs["Roughness"].default_value = 0.0; _b.inputs["Alpha"].default_value = 0.12
if "Transmission Weight" in _b.inputs: _b.inputs["Transmission Weight"].default_value = 1.0
try: m_vd.surface_render_method = "BLENDED"
except Exception: m_vd.blend_method = "BLEND"
m_acc = tinta("Acciaio lucido", "#D9D9D7", 0.06, metallo=1.0); n_doc = 0
for ob in scn.objects:
    if ob.get("ifc_classe") != "IfcBuildingElementProxy" or ob.type != "MESH" or not ob.data.vertices or ob.hide_render or int(ob.get("villa", 1)) not in VILLE_RV: continue
    W = [ob.matrix_world @ q.co for q in ob.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle
    if not (max(w.z for w in W) - min(w.z for w in W) >= 1.8 and r_.area >= 0.6 and any(v["pol"].contains(r_.centroid) and v["nome"].startswith(tuple(RV["vani"])) for v in interni)): continue
    me = ob.data
    for m_ in (m_vd, m_acc):
        if m_.name not in [x.name for x in me.materials if x]: me.materials.append(m_)
    i_vd = [x.name if x else "" for x in me.materials].index(m_vd.name); i_acc = [x.name if x else "" for x in me.materials].index(m_acc.name)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); visti = set(); n_v = n_a = 0
    for f0 in bm.faces:
        if f0.index in visti: continue
        comp = []; pila = [f0]
        while pila:
            x = pila.pop()
            if x.index in visti: continue
            visti.add(x.index); comp.append(x)
            for e in x.edges:
                for y in e.link_faces:
                    if y.index not in visti: pila.append(y)
        P = [ob.matrix_world @ q.co for f_ in comp for q in f_.verts]; zs_ = max(q.z for q in P) - min(q.z for q in P)
        rr = MultiPoint([q.xy[:] for q in P]).minimum_rotated_rectangle
        lati = sorted(Vector(rr.exterior.coords[k + 1]).__sub__(Vector(rr.exterior.coords[k])).length for k in range(2)) if rr.geom_type == "Polygon" else [0.0, 0.0]
        if zs_ < 0.06 and lati[1] > 0.5: continue                                       # piatto doccia
        # lastra = scatola semplice (12-13 facce), sottile e alta; i telai dei montanti sono sottili ma fatti di più facce (28)
        lastra = lati[0] < 0.02 and zs_ > 1.0 and len(comp) <= 16
        for f_ in comp: f_.material_index = i_vd if lastra else i_acc
        if lastra: n_v += 1
        else: n_a += 1
    bm.to_mesh(me); bm.free(); n_doc += 1
    # via gli slot dei materiali IFC rimasti senza facce: l'USD li esporterebbe e il controllo in Unreal (materiali usati)
    # non tornerebbe più (101 attesi, 100 trovati, 2026-11-17)
    idx = [0] * len(me.polygons); me.polygons.foreach_get("material_index", idx); usati = sorted(set(idx))
    if len(usati) < len(me.materials):
        tenuti = [me.materials[i] for i in usati]; mappa_ = {o_: n_ for n_, o_ in enumerate(usati)}
        me.materials.clear()
        for m_ in tenuti: me.materials.append(m_)
        me.polygons.foreach_set("material_index", [mappa_[i] for i in idx]); me.update()
    log(f"doccia {ob.name}: {n_v} lastre di vetro chiaro, {n_a} parti in acciaio lucido")
log("docce rifinite", n_doc)

# porte interne: l'oggetto dell'IFC si nasconde (resta per i percorsi di camera), al suo posto imbotte, coprifili e anta aperta
PP = F["porte"]; m_porta = tinta("Porta laccata", PP["colore"], 0.35)
# maniglia in acciaio satinato e bocchetta della chiave con il foro scuro (Andrea, 2026-11-17: "maniglie più vere, ogni porta
# con la sua toppa per la chiave")
m_man = tinta("Maniglia", "#B9B7B2", 0.22, metallo=1.0); m_foro = tinta("Foro chiave", "#0C0C0C", 0.6)
TI, CF, TA = PP["imbotte_m"], PP["coprifilo_m"], PP["anta_m"]; n_bat = n_sco = 0
for pt in porte:
    if not pt["interna"]: continue
    ob = pt["ob"]; ob.hide_render = True; ob.hide_viewport = True; ob["sostituita"] = True
    Wd, H, y0, y1 = pt["W"], pt["H"], pt["y0"], pt["y1"]; scorre = "SLIDING" in pt["tipo"]
    t = Volumi(pt["o"], pt["x"])
    for xa, xb in ((0, TI), (Wd - TI, Wd)): t.scat(xa, xb, y0, y1, 0, H, m_porta)
    t.scat(0, Wd, y0, y1, H - TI, H, m_porta)
    for ya, yb in ((y1, y1 + 0.01), (y0 - 0.01, y0)):                 # coprifili sulle due facce del muro
        t.scat(TI - 0.01 - CF, TI - 0.01, ya, yb, 0, H + CF - TI + 0.01, m_porta); t.scat(Wd - TI + 0.01, Wd - TI + 0.01 + CF, ya, yb, 0, H + CF - TI + 0.01, m_porta)
        t.scat(TI - 0.01, Wd - TI + 0.01, ya, yb, H - TI + 0.01, H + CF - TI + 0.01, m_porta)
    t.fine(f"Telaio {ob.name}", pt["villa"], "porta", smusso=0.0015)
    ang_x = math.atan2(pt["x"].y, pt["x"].x)
    if scorre:
        # a scomparsa: le ante (una o due) stanno dentro il muro, ne sporgono 6 cm
        ym = (y0 + y1) / 2; n_ante = 2 if "DOUBLE" in pt["tipo"] else 1; la = Wd / n_ante
        for k in range(n_ante):
            a = Volumi(pt["o"], pt["x"]); xa, xb = ((-la + 0.06 + TI, 0.06 + TI) if k == 0 else (Wd - TI - 0.06, Wd - TI - 0.06 + la))
            a.scat(xa, xb, ym - TA / 2, ym + TA / 2, 0.006, H - TI - 0.003, m_porta)
            oa = a.fine(f"Anta scorrevole {ob.name} {k + 1}", pt["villa"], "anta", smusso=0.0015, locale=(Vector((*(pt["o"].xy + pt["x"] * xa), pt["o"].z)), ang_x))
            oa.matrix_world = Matrix.Translation(Vector((*(pt["o"].xy + pt["x"] * xa), pt["o"].z))) @ Matrix.Rotation(ang_x, 4, "Z"); oa["corsa_m"] = (la - 0.06) * (1 if k == 0 else -1)
        n_sco += 1; continue
    # battente: apre verso +y; cerniera a x = 0 oppure a x = larghezza (vedi importa_progetto.py → dati_porta)
    zero = pt["zero"]; sg = 1 if zero else -1; xh = TI + 0.003 if zero else Wd - TI - 0.003; La = Wd - 2 * TI - 0.006
    a = Volumi(pt["o"], pt["x"]); xa, xb = sorted((xh, xh + sg * La))
    a.scat(xa, xb, y1 - TA, y1, 0.006, H - TI - 0.003, m_porta)
    # maniglia e bocchetta in un oggetto a parte, liscio e con più segmenti (Andrea, 2026-11-17: "maniglie non ben definite":
    # dentro l'anta prendevano lo smusso e le facce piatte, i cilindri piccoli sembravano sfaccettati)
    h = Volumi(pt["o"], pt["x"])
    xm = xh + sg * (La - 0.065)                                        # maniglia e bocchetta sulle due facce
    zm = 1.0; zk = zm - 0.075                                          # leva a 1 m, bocchetta 7,5 cm sotto
    for yf, dy in ((y1, 1), (y1 - TA, -1)):
        h.asta((xm, yf, zm), (xm, yf + dy * 0.009, zm), 0.026, 0.025, m_man, seg=48)                    # rosetta tonda
        # leva in un pezzo: collo che esce dalla rosetta, curva morbida (raggio 2 cm), leva che si assottiglia, punta arrotondata
        pts, rr = [], []
        for k in range(5): pts.append((xm, yf + dy * (0.008 + 0.006 * k), zm)); rr.append(0.0098)
        for k in range(1, 9):
            th = math.pi / 2 * k / 8
            pts.append((xm - sg * 0.02 * (1 - math.cos(th)), yf + dy * (0.032 + 0.02 * math.sin(th)), zm)); rr.append(0.0098 - 0.0006 * k / 8)
        for k in range(1, 9):
            pts.append((xm - sg * (0.02 + 0.10 * k / 8), yf + dy * (0.052 + 0.004 * k / 8), zm - 0.005 * k / 8)); rr.append(0.0092 - 0.0014 * k / 8)
        for k in range(1, 5):
            th = math.pi / 2 * k / 4; pts.append((xm - sg * (0.12 + 0.0078 * math.sin(th)), yf + dy * 0.056, zm - 0.005)); rr.append(max(0.0012, 0.0078 * math.cos(th)))
        h.tubo(pts, rr, m_man, seg=32)
        h.asta((xm, yf, zk), (xm, yf + dy * 0.007, zk), 0.020, 0.019, m_man, seg=48)                    # bocchetta
        h.asta((xm, yf + dy * 0.0065, zk + 0.003), (xm, yf + dy * 0.0078, zk + 0.003), 0.0042, 0.0042, m_foro, seg=16)   # foro
        h.scat(xm - 0.0016, xm + 0.0016, *sorted((yf + dy * 0.0065, yf + dy * 0.0078)), zk - 0.007, zk + 0.002, m_foro)
    cern = Vector((*(pt["o"].xy + pt["x"] * xh + pt["y"] * y1), pt["o"].z)); ap = math.radians(PP["apertura_gradi"]) * sg
    oa = a.fine(f"Anta {ob.name}", pt["villa"], "anta", smusso=0.0015, locale=(cern, ang_x))
    oa.matrix_world = Matrix.Translation(cern) @ Matrix.Rotation(ang_x + ap, 4, "Z"); oa["apertura_gradi"] = math.degrees(ap)
    oh = h.fine(f"Maniglia {ob.name}", pt["villa"], "maniglia", smusso=0.0, locale=(cern, ang_x))
    oh.matrix_world = oa.matrix_world.copy()
    for pl in oh.data.polygons: pl.use_smooth = True
    try: oh.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    # spazio spazzato dall'anta: arredi_interni.py controlla che nessun mobile ci cada dentro
    arco = [cern.xy + (Matrix.Rotation(ang_x + ap * k / 8, 2) @ Vector((sg * La, 0))) for k in range(9)]
    oa["battuta"] = [c_ for q in [cern.xy] + arco for c_ in q]; n_bat += 1
log("porte interne rifatte:", n_bat, "a battente (verso dalla planimetria),", n_sco, "scorrevoli a scomparsa | coprifilo", f"{CF * 100:.0f} cm")

# controsoffitto del disimpegno, faretti, griglie di ripresa; bocchette di immissione nelle stanze, sopra le porte
CS = F["controsoffitto"]; m_cg = tinta("Cartongesso", CS["colore"], 0.9); m_led = tinta("Faretto LED", "#FFF1DC", 0.4, emissione=6.0)
m_gr = tinta("Griglia aria", "#F2F0EA", 0.4); m_buio = tinta("Griglia fondo", "#1A1A1A", 0.9); n_cs = n_far = n_gri = n_boc = 0
for v in interni:
    if not v["nome"].startswith(tuple(CS["vani"])): continue
    zc = v["z0"] + 0.004 + CS["altezza_m"]; bm = bmesh.new()
    ff = piano(bm, v["pol"].buffer(0.05, join_style=2).simplify(0.003), zc)
    su = bmesh.ops.extrude_face_region(bm, geom=ff)["geom"]; bmesh.ops.translate(bm, verts=[x for x in su if isinstance(x, bmesh.types.BMVert)], vec=(0, 0, 0.05))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"Controsoffitto {v['nome']}"); bm.to_mesh(me); bm.free(); me.materials.append(m_cg)
    oc = nuovo_oggetto(f"Controsoffitto {v['nome']} v{v['villa']}", me, v["villa"], "controsoffitto")
    oc["controsoffitto_anello"] = [c_ for q in v["pol"].exterior.coords[:-1] for c_ in q]; n_cs += 1
    # faretti lungo l'asse del vano, a passo costante; griglie di ripresa nei campi tra i faretti (o accanto, se è uno solo)
    r = list(v["pol"].minimum_rotated_rectangle.exterior.coords); l1, l2 = Vector(r[1]) - Vector(r[0]), Vector(r[2]) - Vector(r[1])
    asse, larg = (l1, l2) if l1.length >= l2.length else (l2, l1); cen = (Vector(r[0]) + Vector(r[2])) / 2; u = asse.normalized()
    n = max(1, round(asse.length / CS["faretti_passo_m"])); file_ = [0.0] if larg.length < 1.8 else [-larg.length / 4, larg.length / 4]
    dentro_cs = v["pol"].buffer(-0.2)
    def punti(ss): return [q for q in (cen + u * s_ + Vector((-u.y, u.x)) * w for s_ in ss for w in file_) if dentro_cs.contains(Point(q))]
    far = punti([(k + 0.5) * asse.length / n - asse.length / 2 for k in range(n)]) or [Vector(v["pol"].representative_point().coords[0])]
    g_ = Volumi((0, 0, zc), (1, 0)); rf = CS["faretto_diametro_m"] / 2
    for q in far:
        g_.cil(q.x, q.y, rf, -0.004, 0.0, m_gr); g_.cil(q.x, q.y, rf * 0.72, -0.0045, -0.004, m_led)
        ld = bpy.data.lights.new("Faretto LED", "SPOT"); ld.energy = CS["faretto_w"]; ld.color = CS["faretto_colore"]; ld.spot_size = math.radians(110); ld.spot_blend = 0.6; ld.shadow_soft_size = rf
        lo = bpy.data.objects.new(f"Faretto {v['nome']} v{v['villa']}", ld); lo.location = (q.x, q.y, zc - 0.01); FIN.objects.link(lo); lo["villa"] = v["villa"]; n_far += 1
    n_g = max(1, math.ceil(v["pol"].area / CS["griglia_ogni_m2"])) if CS["griglia_ogni_m2"] else 0; gl, gw = CS["griglia_m"]
    ss = [((k + 1) * asse.length / n - asse.length / 2) for k in range(n - 1)] or [asse.length / 4, -asse.length / 4]
    for q in punti(ss)[:n_g]:
        gg = Volumi((q.x, q.y, zc), (-u.y, u.x) if larg.length > gl + 0.3 else u)        # di traverso al corridoio, se ci sta
        gg.scat(-gl / 2, gl / 2, -gw / 2, gw / 2, -0.006, 0.0, m_gr); gg.scat(-gl / 2 + 0.02, gl / 2 - 0.02, -gw / 2 + 0.02, gw / 2 - 0.02, -0.0065, -0.006, m_buio)
        k_ = int((gw - 0.04) / 0.02)
        for i in range(k_): gg.scat(-gl / 2 + 0.02, gl / 2 - 0.02, -gw / 2 + 0.02 + i * 0.02 + 0.004, -gw / 2 + 0.02 + i * 0.02 + 0.014, -0.008, -0.0065, m_gr)
        gg.fine(f"Griglia di ripresa {v['nome']} v{v['villa']}", v["villa"], "griglia"); n_gri += 1
    g_.fine(f"Faretti {v['nome']} v{v['villa']}", v["villa"], "faretti")
    # bocchette: sul muro della stanza servita, sopra la porta che dà su questo vano, appena sopra la quota del controsoffitto
    bl, bh = CS["bocchetta_m"]; zb = CS["altezza_m"] + CS["bocchetta_sopra_m"]
    for pt in porte:
        if not pt["interna"] or v not in (pt["piu"], pt["meno"]): continue
        stanza = pt["meno"] if pt["piu"] is v else pt["piu"]
        if stanza["nome"].startswith(tuple(CS["bocchette_escludi"])) or stanza["nome"].startswith(tuple(CS["vani"])): continue
        yf, sgy = (pt["y1"], 1) if stanza is pt["piu"] else (pt["y0"], -1); xc = pt["W"] / 2
        b = Volumi(pt["o"], pt["x"]); ya, yb = sorted((yf, yf + sgy * 0.012)); yc, yd = sorted((yf + sgy * 0.012, yf + sgy * 0.018))
        b.scat(xc - bl / 2, xc + bl / 2, ya, yb, zb, zb + bh, m_gr); b.scat(xc - bl / 2 + 0.02, xc + bl / 2 - 0.02, yc, yc + 0.001, zb + 0.02, zb + bh - 0.02, m_buio)
        for i in range(int((bh - 0.04) / 0.022)): b.scat(xc - bl / 2 + 0.02, xc + bl / 2 - 0.02, yc, yd, zb + 0.024 + i * 0.022, zb + 0.036 + i * 0.022, m_gr)
        b.fine(f"Bocchetta {stanza['nome']} v{pt['villa']}", pt["villa"], "bocchetta"); n_boc += 1
log("controsoffitti", n_cs, f"a {CS['altezza_m']:.2f} m | faretti LED", n_far, "| griglie di ripresa", n_gri, "| bocchette di immissione", n_boc)

# ------------------------------------------------------------------------------------------------ soffitti: perlinato
S = F["soffitto"]; T = S["travetti"]; INT = T["interasse_m"]
# doghe continue, senza giunzioni trasversali in vista (Andrea, 2026-11-16: i tagli stanno sopra le travi)
m_perl = materiale("Perlinato soffitto", S["colore"], 0.55, [1000.0, S["doga_m"]], 0.004, scuro=0.7)
m_trave = bpy.data.materials.get("Legno travetti") or bpy.data.materials.new("Legno travetti")
m_trave.use_nodes = True
bt = next(n for n in m_trave.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bt.inputs["Base Color"].default_value = lin(S["colore"]); bt.inputs["Roughness"].default_value = 0.5
# legno pitturato (Andrea, 2026-11-17): sotto la pittura grossa una venatura appena visibile e un nodino ogni tanto, nelle
# perline e nelle travi. Immagini ripetibili di legno_dipinto.py (fattore × tinta, più il rilievo); Unreal usa le stesse
# (prepara_render.py: M_Perlinato e M_Travetti). Ogni fila di doghe è spostata lungo la fibra di una quantità a caso (hash
# della fila, la stessa formula di Unreal), così i nodi non si ripetono allineati.
import legno_dipinto
LIBMAT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "libreria_materiali"))
F_LD, N_LD, (LU_LD, LV_LD) = legno_dipinto.genera(os.path.join(LIBMAT, "legno_dipinto"), S["doga_m"])
def _legno_pitturato(m, colore_sock, uv_sock, sposta_file):
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    def mn(op, a, b_=None, v=None):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op; nt.links.new(a, n.inputs[0])
        if b_ is not None: nt.links.new(b_, n.inputs[1])
        elif v is not None: n.inputs[1].default_value = v
        return n.outputs[0]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv_sock, sep.inputs[0]); u_, v_ = sep.outputs[0], sep.outputs[1]
    if sposta_file:
        fila = mn("FLOOR", mn("DIVIDE", v_, v=S["doga_m"]))
        hs = mn("FRACT", mn("MULTIPLY", mn("SINE", mn("MULTIPLY", fila, v=78.233)), v=43758.5453))
        u_ = mn("ADD", u_, mn("MULTIPLY", hs, v=LU_LD))
    cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(mn("DIVIDE", u_, v=LU_LD), cmb.inputs[0]); nt.links.new(mn("DIVIDE", v_, v=LV_LD), cmb.inputs[1])
    tf = nt.nodes.new("ShaderNodeTexImage"); tf.image = bpy.data.images.load(F_LD, check_existing=True); tf.image.colorspace_settings.name = "Non-Color"
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(N_LD, check_existing=True); tn.image.colorspace_settings.name = "Non-Color"
    for t_ in (tf, tn): nt.links.new(cmb.outputs[0], t_.inputs["Vector"])
    x2 = nt.nodes.new("ShaderNodeVectorMath"); x2.operation = "MULTIPLY_ADD"; nt.links.new(tf.outputs["Color"], x2.inputs[0])   # f = 0,875 + t / 4
    x2.inputs[1].default_value = (0.25, 0.25, 0.25); x2.inputs[2].default_value = (0.875, 0.875, 0.875)
    mu = nt.nodes.new("ShaderNodeVectorMath"); mu.operation = "MULTIPLY"; nt.links.new(colore_sock, mu.inputs[0]); nt.links.new(x2.outputs[0], mu.inputs[1])
    nt.links.new(mu.outputs[0], b.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
br_ = next(n for n in m_perl.node_tree.nodes if n.type == "TEX_BRICK"); uv_ = next(n for n in m_perl.node_tree.nodes if n.type == "TEX_COORD")
_legno_pitturato(m_perl, br_.outputs["Color"], uv_.outputs["UV"], True)
m_trave.node_tree.nodes.clear()
_bo = m_trave.node_tree.nodes.new("ShaderNodeOutputMaterial"); _bt = m_trave.node_tree.nodes.new("ShaderNodeBsdfPrincipled"); m_trave.node_tree.links.new(_bt.outputs[0], _bo.inputs[0])
_bt.inputs["Roughness"].default_value = 0.5
_rgb = m_trave.node_tree.nodes.new("ShaderNodeRGB"); _rgb.outputs[0].default_value = lin(S["colore"])
_tc = m_trave.node_tree.nodes.new("ShaderNodeTexCoord")
_legno_pitturato(m_trave, _rgb.outputs[0], _tc.outputs["UV"], False)
falde = []
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
    g = Vector((n.x, n.y)); g = g.normalized() if g.length > 0.02 else Vector((1, 0)); t = Vector((-g.y, g.x))
    # UV dell'intradosso in metri: u lungo le doghe (perpendicolari ai travetti), v lungo la pendenza
    uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    passo_v = 1.0 / max(0.2, abs(n.z))                        # la doga si misura sulla falda, non in pianta
    for pl in sotto:
        pl.material_index = idx
        for li in pl.loop_indices:
            w = mw @ me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (w.x * t.x + w.y * t.y, (w.x * g.x + w.y * g.y) * passo_v)
    imp = unary_union([Polygon([(mw @ me.vertices[i].co).xy[:] for i in pl.vertices]) for pl in sotto]).buffer(0.01)
    falde.append({"nome": ob.name, "villa": villa, "n": n, "c": c, "g": g, "t": t, "imp": imp, "travetti": []})
def zf(f, x, y): return f["c"].z - (f["n"].x * (x - f["c"].x) + f["n"].y * (y - f["c"].y)) / f["n"].z

# ------------------------------------------------------------------------------------------------ orditura del tetto
# Regole (Andrea, 2026-11-15):
#  1. dove due falde si incontrano (colmo, displuvio, compluvio) c'è una trave lungo la linea d'incontro;
#  2. i travetti delle due falde arrivano su quella trave negli stessi punti e alla stessa quota (incastro a coda di
#     rondine);
#  2b. passo e sezione dei travetti identici ovunque; dove le misure non tornano resta un solo campo di compensazione,
#     al centro (scelta 2 di Andrea, 2026-11-15: incontro esatto, passo quasi identico);
#  3. un travetto non appoggia mai sopra un infisso: si ferma prima (arretro_infisso_m) su una trave perpendicolare
#     della stessa sezione, che porta il carico ai travetti subito a destra e a sinistra dell'infisso.
B_, H_ = T["sezione_m"]; BD, HD = T["sezione_displuvio_m"]; ARR = T["arretro_infisso_m"]
travi = {}                                                    # villa → (vertici, facce)
def trave(villa, a, b, larg, alt, zfun):
    """parallelepipedo in pianta da a a b, faccia superiore alla quota zfun(x, y) (+5 mm dentro il perlinato)."""
    V, Fc = travi.setdefault(villa, ([], [])); d = Vector(b) - Vector(a)
    if d.length < 0.05: return
    pr = Vector((-d.y, d.x)).normalized() * larg / 2; k = len(V)
    for q in (Vector(a), Vector(b)):
        for sg in (-1, 1):
            px, py = q.x + pr.x * sg, q.y + pr.y * sg; zt = zfun(px, py) + 0.005
            V.extend([(px, py, zt), (px, py, zt - alt)])
    Fc.extend([(k, k + 1, k + 3, k + 2), (k + 4, k + 6, k + 7, k + 5), (k, k + 4, k + 5, k + 1), (k + 2, k + 3, k + 7, k + 6),
               (k + 1, k + 5, k + 7, k + 3), (k, k + 2, k + 6, k + 4)])
def linee(gm): return [q for q in ([gm] if gm.geom_type == "LineString" else getattr(gm, "geoms", [])) if q.geom_type == "LineString" and not q.is_empty]

n_giunti = n_trav = n_camb = n_doppi = 0; avvisi = []
def campo(lung, capo_a, capo_b):
    """posizioni su [0, lung] a passo INT dai due capi verso il centro (capo_x: c'è un travetto anche sul capo);
    l'unico campo diverso, quello di compensazione, resta al centro ed è largo tra 0,5 e 1,5 passi."""
    xa = 0.0 if capo_a else INT; xb = lung - (0.0 if capo_b else INT)
    if xb - xa < 0.4 * INT: return [(xa + xb) / 2] if lung > 0.8 * INT else []
    pos = [xa, xb]
    while xb - xa > 1.5 * INT:
        if xb - xa > 2.5 * INT: xa += INT; xb -= INT; pos += [xa, xb]
        else: xa += INT; pos.append(xa)
    return sorted(pos)
VILLE = {}
for villa in sorted({f["villa"] for f in falde}):
    FV = [f for f in falde if f["villa"] == villa]; VILLE[villa] = {"FV": FV}
    # involucro interno della villa: i vani uniti oltre i tramezzi, così i travetti passano sopra i muri interni
    dentro = unary_union([v["pol"].buffer(0.40) for v in interni if v["villa"] == villa]).buffer(-0.28)
    for f in FV: f["zona"] = f["imp"].intersection(dentro); f["giunti"] = []
    # 1: linee d'incontro = tratti in cui i contorni di due falde di giacitura diversa si toccano
    giunti = []
    for i_, fa in enumerate(FV):
        for fb in FV[i_ + 1:]:
            striscia = fa["imp"].buffer(0.08).intersection(fb["imp"].buffer(0.08))
            if striscia.is_empty or striscia.area < 0.03: continue
            if fa["n"].dot(fb["n"]) > 0.995: continue          # stessa giacitura (falda divisa in due pezzi): nessuna trave
            # asse lungo della striscia comune ai due contorni. Edificius taglia le falde lungo linee che non sempre sono
            # l'intersezione esatta dei due piani: si accetta fino a 30 cm di differenza di quota tra i due intradossi
            r = list(striscia.minimum_rotated_rectangle.exterior.coords)
            m1 = (Vector(r[0]) + Vector(r[1])) / 2; m2 = (Vector(r[2]) + Vector(r[3])) / 2
            if (Vector(r[1]) - Vector(r[0])).length > (Vector(r[2]) - Vector(r[1])).length:
                m1 = (Vector(r[1]) + Vector(r[2])) / 2; m2 = (Vector(r[3]) + Vector(r[0])) / 2
            if (m2 - m1).length < 0.35: continue
            if max(abs(zf(fa, q.x, q.y) - zf(fb, q.x, q.y)) for q in (m1, m2)) > 0.30: continue
            for pz in linee(LineString([tuple(m1), tuple(m2)]).intersection(dentro)):
                if pz.length < 0.3: continue
                a, b = Vector(pz.coords[0]), Vector(pz.coords[-1])
                if zf(fa, b.x, b.y) > zf(fa, a.x, a.y) + 0.01: a, b = b, a                    # a = capo alto
                giunti.append({"a": a, "b": b, "fa": fa, "fb": fb, "ln": pz, "colmo": fa["g"].dot(fb["g"]) < -0.9})
                fa["giunti"].append(pz); fb["giunti"].append(pz); n_giunti += 1
                def zl(x, y, a=a, b=b, fa=fa, fb=fb):                 # quota sull'asse della trave: il più basso dei due intradossi
                    q = a + (b - a) * max(0.0, min(1.0, (Vector((x, y)) - a).dot(b - a) / (b - a).length_squared))
                    return min(zf(fa, q.x, q.y), zf(fb, q.x, q.y))
                trave(villa, a, b, BD, HD, zl)
    def travetto(f, p):
        """travetto della falda f dal punto p della trave d'incontro, lungo la pendenza, fino al bordo opposto."""
        global n_doppi
        if f["zona"].is_empty: return
        g = f["g"]; ln = LineString([(p.x - g.x * 60, p.y - g.y * 60), (p.x + g.x * 60, p.y + g.y * 60)])
        for pz in linee(ln.intersection(f["zona"])):
            if pz.distance(Point(p.x, p.y)) > 0.25: continue
            a, b = Vector(pz.coords[0]), Vector(pz.coords[-1])
            b = b if (b - p).length >= (a - p).length else a; a = p.copy()
            if (b - a).length < 0.3: continue
            s_ = a.dot(f["t"]); va, vb = sorted((a.dot(g), b.dot(g)))
            if any(abs(e["s"] - s_) < 0.5 * INT and min(vb, max(e["a"].dot(g), e["b"].dot(g))) - max(va, min(e["a"].dot(g), e["b"].dot(g))) > 0.3 for e in f["travetti"]):
                n_doppi += 1; continue
            f["travetti"].append({"a": a, "b": b, "s": s_, "fermo": None})
    # 2: i travetti partono a coppie dagli stessi punti della trave d'incontro. Displuvi e compluvi: dal capo alto, un punto
    # ogni passo misurato sulla falda; colmi: dai due capi verso il centro, con il campo di compensazione al centro
    def nodo(g_, q): return any(o is not g_ and o["ln"].distance(Point(q.x, q.y)) < 0.3 for o in giunti)
    def arrivi(f, g_):
        """ascisse lungo la trave g_ dei travetti della falda f che già vi arrivano."""
        d = (g_["b"] - g_["a"]).normalized()
        return sorted((e[c] - g_["a"]).dot(d) for e in f["travetti"] for c in "ab" if g_["ln"].distance(Point(e[c].x, e[c].y)) < 0.2)
    # prima i colmi (campata tra due nodi: dai capi verso il centro), poi displuvi e compluvi dall'alto verso il basso:
    # ognuno riprende la griglia dei travetti che gli arrivano già addosso, così il passo resta lo stesso da una campata all'altra
    ordine = sorted(giunti, key=lambda x: (not x["colmo"], -max(zf(x["fa"], x["a"].x, x["a"].y), zf(x["fa"], x["b"].x, x["b"].y))))
    for g_ in ordine:
        a, b, fa, fb = g_["a"], g_["b"], g_["fa"], g_["fb"]; d = (b - a).normalized(); lung = (b - a).length
        if g_["colmo"]:
            for u in campo(lung, nodo(g_, a), nodo(g_, b)):
                p = a + d * u; travetto(fa, p); travetto(fb, p)
            continue
        sa, sb = max(abs(d.dot(fa["t"])), 0.3), max(abs(d.dot(fb["t"])), 0.3); ea, eb = arrivi(fa, g_), arrivi(fb, g_)
        def griglia(du, base):
            k0 = math.ceil((0.12 - base) / du); return [base + k * du for k in range(k0, int((lung - 0.1 - base) / du) + 1)]
        if abs(sa - sb) <= 0.08:                               # linea a 45°: stessi punti per le due falde, passo INT su entrambe
            du = INT / ((sa + sb) / 2); base = (ea or eb or [0.0])[0]
            for u in griglia(du, base):
                p = a + d * u
                for f, e_ in ((fa, ea), (fb, eb)):
                    if not any(abs(u - x) < 0.12 for x in e_): travetto(f, p)
        else:
            # linea non a 45° (falde tagliate male nel modello): passo uguale e incontro esatto non stanno insieme; vince il passo
            avvisi.append(f"villa {villa}: {fa['nome']} e {fb['nome']} si incontrano su una linea non a 45°: passo rispettato, incontro dei travetti solo approssimato")
            for f, sn, e_ in ((fa, sa, ea), (fb, sb, eb)):
                for u in griglia(INT / sn, (e_ or [0.0])[0]):
                    if not any(abs(u - x) < 0.12 for x in e_): travetto(f, a + d * u)
    # campi senza trave d'incontro (falde a una pendenza, tratti tra due zone): stesso passo, compensazione al centro
    for f in FV:
        if f["zona"].is_empty: continue
        g, t = f["g"], f["t"]
        cz = [q for gp in ([f["zona"]] if f["zona"].geom_type == "Polygon" else f["zona"].geoms) for q in gp.exterior.coords]
        ss = [q[0] * t.x + q[1] * t.y for q in cz]; s_min, s_max = min(ss), max(ss)
        fissi = sorted({round(e["s"], 3) for e in f["travetti"]}); bordi = [s_min] + fissi + [s_max]
        for k in range(len(bordi) - 1):
            lo, hi = bordi[k], bordi[k + 1]
            if hi - lo <= 1.5 * INT and not (k == 0 or k == len(bordi) - 2): continue
            for u in campo(hi - lo, k > 0, k < len(bordi) - 2):
                if u < 0.05 or u > hi - lo - 0.05: continue
                s = lo + u
                ln = LineString([(t.x * s - g.x * 60, t.y * s - g.y * 60), (t.x * s + g.x * 60, t.y * s + g.y * 60)])
                for pz in linee(ln.intersection(f["zona"])):
                    if pz.length < 0.3: continue
                    a, b = Vector(pz.coords[0]), Vector(pz.coords[-1]); va, vb = sorted((a.dot(g), b.dot(g)))
                    if any(abs(e["s"] - s) < 0.4 * INT and min(vb, max(e["a"].dot(g), e["b"].dot(g))) - max(va, min(e["a"].dot(g), e["b"].dot(g))) > 0.3 for e in f["travetti"]): continue
                    f["travetti"].append({"a": a, "b": b, "s": s, "fermo": None})
        for e in f["travetti"]:
            for capo in "ab": e["giunto_" + capo] = any(j.distance(Point(e[capo].x, e[capo].y)) < 0.25 for j in f["giunti"])
def portante_nuovo(f, s_c, v_st, infissi):
    """travetto intero della falda f all'ascissa s_c che copre la quota v_st lungo la pendenza, solo se la posizione è
    pulita: dentro la falda con tutto lo spessore, lontano dagli altri travetti, capi non sopra un infisso.
    Restituisce (travetto, None) oppure (None, motivo)."""
    g, t = f["g"], f["t"]
    ln = LineString([(t.x * s_c - g.x * 60, t.y * s_c - g.y * 60), (t.x * s_c + g.x * 60, t.y * s_c + g.y * 60)])
    for pz in linee(ln.intersection(f["zona"])):
        a, b = Vector(pz.coords[0]), Vector(pz.coords[-1]); va, vb = sorted((a.dot(g), b.dot(g)))
        if not va - 0.1 <= v_st <= vb + 0.1: continue
        if pz.length < 0.6: return None, f"lì la falda è lunga solo {pz.length:.2f} m"
        if not f["zona"].buffer(0.01).contains(pz.buffer(B_ / 2, cap_style=2)): return None, "uscirebbe dal bordo della falda"
        if any(abs(e["s"] - s_c) < 0.4 * INT and min(vb, max(e["a"].dot(g), e["b"].dot(g))) - max(va, min(e["a"].dot(g), e["b"].dot(g))) > 0.3 for e in f["travetti"]):
            return None, "si sovrapporrebbe a un altro travetto"
        e = {"a": a, "b": b, "s": s_c, "fermo": None}
        for capo, altro in (("a", "b"), ("b", "a")):
            q = e[capo]; e["giunto_" + capo] = any(j.distance(Point(q.x, q.y)) < 0.25 for j in f["giunti"])
            if e["giunto_" + capo]: continue
            fuori = (q - e[altro]).normalized(); zq = zf(f, q.x, q.y); sonda = LineString([tuple(q - fuori * 0.05), tuple(q + fuori * 0.7)])
            if any(x["pol"].intersects(sonda) and zq - 1.8 <= x["z1"] <= zq + 0.3 for x in infissi): return None, "finirebbe anch'esso sopra un infisso"
        return e, None
    return None, "a un passo di distanza la falda è già finita"
n_port = 0
for villa, DV in VILLE.items():
    FV = DV["FV"]
    # 3: infissi sotto l'appoggio → travetto arretrato e trave perpendicolare
    infissi = []
    for ob in scn.objects:
        if ob.get("ifc_classe") not in ("IfcWindow", "IfcDoor") or ob.type != "MESH" or int(ob.get("villa", 1)) != villa or not ob.data.vertices: continue
        W = [ob.matrix_world @ v_.co for v_ in ob.data.vertices]
        infissi.append({"nome": ob.name, "pol": MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle.buffer(0.03), "z1": max(w.z for w in W)})
    for f in FV:
        fermati = {}
        for e in f["travetti"]:
            for capo, altro in (("b", "a"), ("a", "b")):
                if e["giunto_" + capo]: continue                              # capo sulla trave d'incontro
                q = e[capo]; fuori = (q - e[altro]).normalized(); zq = zf(f, q.x, q.y)
                sonda = LineString([tuple(q - fuori * 0.05), tuple(q + fuori * 0.7)])
                inf = next((x for x in infissi if x["pol"].intersects(sonda) and zq - 1.8 <= x["z1"] <= zq + 0.3), None)
                if inf is None or (q - e[altro]).length < ARR + 0.4: continue
                e[capo] = q - fuori * ARR; e["fermo"] = inf["nome"]; fermati.setdefault(inf["nome"], []).append((e, capo))
        for nome_i, gruppo in fermati.items():
            g, t = f["g"], f["t"]; v_st = sum(e[capo].dot(g) for e, capo in gruppo) / len(gruppo)
            s_g = [e["s"] for e, _ in gruppo]
            portanti = [e for e in f["travetti"] if not e["fermo"] and min(e["a"].dot(g), e["b"].dot(g)) - 0.1 <= v_st <= max(e["a"].dot(g), e["b"].dot(g)) + 0.1]
            sx = max((e["s"] for e in portanti if e["s"] < min(s_g) - 0.05), default=None)
            dx = min((e["s"] for e in portanti if e["s"] > max(s_g) + 0.05), default=None)
            # infisso al bordo della falda: da un lato non c'è un travetto intero su cui scaricare la trave perpendicolare.
            # Se c'è una posizione pulita a un passo dall'ultimo travetto fermato, lo si aggiunge (Andrea, 2026-11-15)
            for lato, s_c in (("sinistra", min(s_g) - INT), ("destra", max(s_g) + INT)):
                if (sx if lato == "sinistra" else dx) is not None: continue
                nuovo, motivo = portante_nuovo(f, s_c, v_st, infissi)
                if nuovo is None:
                    avvisi.append(f"{f['nome']}: sopra {nome_i} manca il travetto portante a {lato}: non aggiunto ({motivo})"); continue
                f["travetti"].append(nuovo); n_port += 1
                log(f"{f['nome']}: sopra {nome_i} aggiunto il travetto portante a {lato}, lungo {(nuovo['b'] - nuovo['a']).length:.2f} m")
                if lato == "sinistra": sx = s_c
                else: dx = s_c
            sx = sx if sx is not None else min(s_g); dx = dx if dx is not None else max(s_g)
            if dx - sx < 0.1: continue
            trave(villa, t * sx + g * v_st, t * dx + g * v_st, B_, H_, lambda x, y, f=f: zf(f, x, y)); n_camb += 1
        for e in f["travetti"]:
            trave(villa, e["a"], e["b"], B_, H_, lambda x, y, f=f: zf(f, x, y)); n_trav += 1
for villa, (V, Fc) in travi.items():
    mt = bpy.data.meshes.new(f"Orditura tetto villa {villa}"); mt.from_pydata(V, [], Fc); mt.materials.append(m_trave)
    bm = bmesh.new(); bm.from_mesh(mt); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(mt); bm.free()
    # UV in metri con la U lungo la trave (fibra del legno pitturato): su ogni faccia, U lungo il suo lato più lungo
    uvl = mt.uv_layers.new(name="UVMap")
    for pl in mt.polygons:
        q = [Vector(mt.vertices[i].co) for i in pl.vertices]; lati = [(q[(k + 1) % len(q)] - q[k]) for k in range(len(q))]
        e = max(lati, key=lambda x: x.length).normalized(); w = pl.normal.cross(e).normalized()
        for li in pl.loop_indices:
            c_ = mt.vertices[mt.loops[li].vertex_index].co; uvl.data[li].uv = (c_.dot(e), c_.dot(w))
    ot = bpy.data.objects.new(f"Orditura tetto villa {villa}", mt); ot["villa"] = villa; ot["finitura"] = "orditura"; FIN.objects.link(ot)
log("falde con perlinato", len(falde), "| travi d'incontro (colmi, displuvi, compluvi)", n_giunti, f"{BD * 100:.0f}×{HD * 100:.0f} cm",
    "| travetti", n_trav, f"{B_ * 100:.0f}×{H_ * 100:.0f} cm a {INT * 100:.1f} cm", "| travi perpendicolari sopra gli infissi", n_camb, "| travetti portanti aggiunti", n_port, "| travetti doppi scartati", n_doppi)
for a_ in avvisi: log("AVVISO", a_)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend")); log("fine")
