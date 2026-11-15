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
Regole generali, nessuna eccezione per il singolo progetto: l'IFC Edificius ha un solo materiale per falda (sopra e
sotto) e nessuno strato di pavimento distinto dal solaio.
I materiali sono procedurali (nodi Blender): per Unreal vanno rifatti come materiali della libreria di studio.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, registro
from shapely.geometry import LineString, Point, Polygon
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
                     "travetti": {"sezione_m": [0.10, 0.16], "interasse_m": 0.70, "sezione_displuvio_m": [0.14, 0.22],
                                  "arretro_infisso_m": 0.25}},
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
# posa parallela ai muri: direzione del lato lungo del vano più grande di ogni villa, la stessa per tutta la villa
# (le fughe continuano da una stanza all'altra attraverso le porte)
POSA = {}
for villa in {v["villa"] for v in interni}:
    grande = max((v for v in interni if v["villa"] == villa), key=lambda v: v["pol"].area)
    r = list(grande["pol"].minimum_rotated_rectangle.exterior.coords)
    lati = [(Vector(r[k + 1]) - Vector(r[k])) for k in range(2)]; lato = max(lati, key=lambda q: q.length).normalized()
    POSA[villa] = (lato, Vector((-lato.y, lato.x)), Vector(r[0]))
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
    uvl = bm.loops.layers.uv.new("UVMap"); eu, ev, o0 = POSA[v["villa"]]
    for lp in f_.loops:                                       # UV in metri lungo i muri: il reticolo ha misure reali
        d = Vector(lp.vert.co.xy) - o0; lp[uvl].uv = (d.dot(eu), d.dot(ev))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"Pavimento {v['nome']}"); bm.to_mesh(me); bm.free(); me.materials.append(m)
    ob = bpy.data.objects.new(f"Pavimento {v['nome']} v{v['villa']}", me); ob["villa"] = v["villa"]; ob["finitura"] = "pavimento"
    FIN.objects.link(ob); n_pav += 1
log("pavimenti", n_pav, "| posa parallela ai muri")

# ------------------------------------------------------------------------------------------------ soffitti: perlinato
S = F["soffitto"]; T = S["travetti"]; INT = T["interasse_m"]
m_perl = materiale("Perlinato soffitto", S["colore"], 0.55, [4.0, S["doga_m"]], 0.004, scuro=0.7, sfalsato=0.5)
m_trave = bpy.data.materials.get("Legno travetti") or bpy.data.materials.new("Legno travetti")
m_trave.use_nodes = True
bt = next(n for n in m_trave.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bt.inputs["Base Color"].default_value = lin(S["colore"]); bt.inputs["Roughness"].default_value = 0.5
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
for villa, DV in VILLE.items():
    FV = DV["FV"]
    # 3: infissi sotto l'appoggio → travetto arretrato e trave perpendicolare
    infissi = []
    for ob in scn.objects:
        if ob.get("ifc_classe") not in ("IfcWindow", "IfcDoor") or ob.type != "MESH" or int(ob.get("villa", 1)) != villa or not ob.data.vertices: continue
        W = [ob.matrix_world @ v_.co for v_ in ob.data.vertices]
        from shapely.geometry import MultiPoint
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
            if sx is None or dx is None:
                avvisi.append(f"{f['nome']}: sopra {nome_i} manca il travetto portante a {'sinistra' if sx is None else 'destra'} (infisso al bordo della falda)")
            sx = sx if sx is not None else min(s_g); dx = dx if dx is not None else max(s_g)
            if dx - sx < 0.1: continue
            trave(villa, t * sx + g * v_st, t * dx + g * v_st, B_, H_, lambda x, y, f=f: zf(f, x, y)); n_camb += 1
        for e in f["travetti"]:
            trave(villa, e["a"], e["b"], B_, H_, lambda x, y, f=f: zf(f, x, y)); n_trav += 1
for villa, (V, Fc) in travi.items():
    mt = bpy.data.meshes.new(f"Orditura tetto villa {villa}"); mt.from_pydata(V, [], Fc); mt.materials.append(m_trave)
    bm = bmesh.new(); bm.from_mesh(mt); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(mt); bm.free()
    ot = bpy.data.objects.new(f"Orditura tetto villa {villa}", mt); ot["villa"] = villa; ot["finitura"] = "orditura"; FIN.objects.link(ot)
log("falde con perlinato", len(falde), "| travi d'incontro (colmi, displuvi, compluvi)", n_giunti, f"{BD * 100:.0f}×{HD * 100:.0f} cm",
    "| travetti", n_trav, f"{B_ * 100:.0f}×{H_ * 100:.0f} cm a {INT * 100:.1f} cm", "| travi perpendicolari sopra gli infissi", n_camb, "| travetti doppi scartati", n_doppi)
for a_ in avvisi: log("AVVISO", a_)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend")); log("fine")
