"""Inserisce il progetto IFC (Edificius o altro) nella scena del contesto (fase 3b della filiera).

  blender -b <modello>/uscita_blender/contesto.blend -P importa_progetto.py -- <cartella modello>
          [--render] [--viste SV-08,VISTA_angolo] [--samples 16]

Legge <modello>/lotto.json → "progetto_ifc" (valori di allineamento: allinea_ifc.py, se l'IFC non è georiferito):
  file              percorso dell'IFC (relativo alla cartella del modello o assoluto)
  rotazione_gradi   rotazione in pianta attorno all'origine IFC (antioraria)
  traslazione       [x, y] in metri, coordinate locali del contesto (x = Est, y = Nord)
  dz                quota comune (IFC → contesto); con "ville" vale solo dove non c'è un cancello di riferimento
  escludi_nomi      prefissi dei nomi IFC da non importare (strade e volumi di contesto disegnati nel progetto)
  marciapiede_nomi  elementi IFC che sono il marciapiede di progetto: planimetria IFC, quota = carreggiata accanto
                    + alzata_marciapiede_m (0,12)
  nascondi          prefissi degli oggetti del contesto sostituiti dal progetto (nascosti)
  margine_m         tolleranza attorno al perimetro per tenere un elemento (1,0)
  muraglione        spessore_m, passo_m, minimo_m, materiale: muri in c.a. sul perimetro e fra le ville
  ville             asse_gradi, tagli [s1, s2, ...], cancelli [nome IFC per villa]: il progetto si divide lungo linee
                    perpendicolari all'asse; ogni villa va alla quota che porta la soglia del suo cancello carraio
                    al marciapiede davanti
Regole: l'IFC è planimetricamente giusto. Il terreno di progetto resta dentro il perimetro del lotto (buchi sotto le
ville riempiti); strade, marciapiedi e terreno del contesto sotto il lotto e sotto il marciapiede di progetto si
tolgono; arredi e verde del contesto dentro il lotto si nascondono. Il perimetro si scrive anche in
<modello>/perimetro_progetto.json per il motore del contesto (lotto.perimetro_progetto).
Salva <uscita>/contesto_progetto.blend; con --render rende le camere in <uscita>/viste_progetto/.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector, kdtree, geometry as mgeo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, registro, z_piano, rendi_camere
import ifcopenshell, ifcopenshell.geom
from shapely import affinity
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

argv, opt = argomenti()
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
L = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8"))
P = L["progetto_ifc"]
CT = json.load(open(os.path.join(MOD, "contesto.json"), encoding="utf-8"))
log = registro(os.path.join(USCITA, "importa_progetto.log"))
scn = bpy.context.scene

FILE = P["file"] if os.path.isabs(P["file"]) else os.path.normpath(os.path.join(MOD, P["file"]))
f = ifcopenshell.open(FILE); log("IFC", FILE, f.schema)
ROT = P.get("rotazione_gradi", 0.0); a = math.radians(ROT); tx, ty = P.get("traslazione", [0, 0]); dz = P.get("dz", 0.0)
def matrice(dz_): return Matrix.Translation((tx, ty, dz_)) @ Matrix.Rotation(a, 4, "Z")
M = matrice(dz)
def a_ctx(g): return affinity.translate(affinity.rotate(g, ROT, origin=(0, 0)), tx, ty)
def xy_ctx(x, y): w_ = M @ Vector((x, y, 0)); return w_.x, w_.y
ESCL = tuple(P.get("escludi_nomi", [])); MARC = tuple(P.get("marciapiede_nomi", [])); NASC = tuple(P.get("nascondi", []))
def e_marciapiede(el): return bool(MARC) and bool(el.Name) and el.Name.startswith(MARC)

# ------------------------------------------------------------------ geometria IFC
st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
forme = []
for el in f.by_type("IfcProduct"):
    if not el.Representation or el.is_a("IfcSpace") or el.is_a("IfcOpeningElement"): continue
    if el.Name and el.Name.startswith(ESCL): continue
    try: g = ifcopenshell.geom.create_shape(st, el).geometry
    except Exception as e: log("salto", el.is_a(), el.Name, str(e)[:120]); continue
    if g.verts: forme.append((el, g))
def triangoli(g):
    v = g.verts; F = g.faces
    return ([Vector((v[i], v[i + 1], v[i + 2])) for i in range(0, len(v), 3)],
            [(F[k], F[k + 1], F[k + 2]) for k in range(0, len(F), 3)], list(g.material_ids))
def nz(V, t):
    n_ = (V[t[1]] - V[t[0]]).cross(V[t[2]] - V[t[0]]); return n_.normalized().z if n_.length > 1e-9 else 0.0
def centro(V, idx=None):
    pp = [V[i] for i in idx] if idx is not None else V
    return Point(sum(p.x for p in pp) / len(pp), sum(p.y for p in pp) / len(pp))

# perimetro del lotto di progetto: inviluppo di muri e solai, esclusi gli elementi isolati lontani (coord. IFC)
pts = [(g.verts[i], g.verts[i + 1]) for el, g in forme if el.is_a() in ("IfcWall", "IfcWallStandardCase", "IfcSlab")
       for i in range(0, len(g.verts), 3)]
cx = sorted(p[0] for p in pts)[len(pts) // 2]; cy = sorted(p[1] for p in pts)[len(pts) // 2]
LOTTO = MultiPoint([p for p in pts if abs(p[0] - cx) < 60 and abs(p[1] - cy) < 60]).convex_hull
PERIM = LOTTO.buffer(P.get("margine_m", 1.0))
log("lotto di progetto", round(LOTTO.area), "m²")
json.dump({"_nota": "perimetro del lotto dal progetto IFC, coordinate locali del contesto (x Est, y Nord)",
           "origine": CT["origine"], "anello": [[round(x, 3), round(y, 3)] for x, y in a_ctx(LOTTO).exterior.coords]},
          open(os.path.join(MOD, "perimetro_progetto.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ quote del rilievo (contesto.json, coord. contesto)
TRI, TRIZ, CARR = [], [], []
for s_ in CT["superfici"]:
    if s_["nome"].startswith(NASC): continue          # lo stato di fatto sostituito non conta
    carr = s_["nome"].startswith(P.get("carreggiata", "P01")); Vs = s_["vertici"]
    for t in s_["triangoli"]:
        q3 = [Vs[i] for i in t[:3]]; pl = Polygon([q[:2] for q in q3])
        TRI.append(pl); TRIZ.append(q3)
        if carr and pl.area > 1e-4: CARR.append(len(TRI) - 1)
ALB = STRtree(TRI); ALBC = STRtree([TRI[k] for k in CARR])
def z_reale(x, y):
    """quota del rilievo nel punto, None se lì non c'è superficie."""
    pt = Point(x, y)
    for k in ALB.query(pt):
        if TRI[k].contains(pt): return z_piano(TRIZ[k], x, y)
    return None
def z_carreggiata(x, y):
    """quota della carreggiata più vicina, prolungandone il piano fino al punto."""
    return z_piano(TRIZ[CARR[ALBC.nearest(Point(x, y))]], x, y)

# ------------------------------------------------------------------ oggetti Blender
MATS, COLL = {}, {}
def materiale(m):
    nome = "IFC_" + (m.name or "senza_nome")
    if nome in MATS: return MATS[nome]
    bm_ = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); bm_.use_nodes = True
    b = next(n for n in bm_.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    d_ = getattr(m, "diffuse", None)      # ifcopenshell ≥ 0.8: tupla; versioni precedenti: oggetto colore con r()
    if d_ is not None and (not hasattr(m, "has_diffuse") or m.has_diffuse):
        rgb = (d_.r(), d_.g(), d_.b()) if hasattr(d_, "r") else tuple(d_)[:3]
        b.inputs["Base Color"].default_value = (*rgb, 1); bm_.diffuse_color = (*rgb, 1)
    tr = getattr(m, "transparency", 0.0) or 0.0
    if (hasattr(m, "has_transparency") and not m.has_transparency) or tr != tr: tr = 0.0
    b.inputs["Roughness"].default_value = 0.6
    if tr > 0.05:                         # vetri
        b.inputs["Roughness"].default_value = 0.03
        for k in ("Transmission Weight", "Transmission"):
            if k in b.inputs: b.inputs[k].default_value = min(1.0, tr + 0.2); break
        b.inputs["Alpha"].default_value = max(0.15, 1 - tr)
        try: bm_.surface_render_method = "BLENDED"
        except Exception: pass
    MATS[nome] = bm_; return bm_
def coll(nome):
    if nome not in COLL:
        radice = bpy.data.collections.get("PROGETTO") or bpy.data.collections.new("PROGETTO")
        if radice.name not in scn.collection.children: scn.collection.children.link(radice)
        c = bpy.data.collections.new("PRG_" + nome); radice.children.link(c); COLL[nome] = c
    return COLL[nome]
def oggetto(el, W, T, g, mid, nome=None, villa=None):
    nome = nome or el.Name or el.is_a()
    me = bpy.data.meshes.new(nome); me.from_pydata(W, [], T)
    for m in g.materials: me.materials.append(materiale(m))
    if mid and g.materials and len(mid) == len(me.polygons): me.polygons.foreach_set("material_index", [max(0, i) for i in mid])
    me.validate(); me.update()
    ob = bpy.data.objects.new(nome, me); ob["ifc_classe"] = el.is_a(); ob["ifc_guid"] = el.GlobalId
    coll(el.is_a().replace("Ifc", "")).objects.link(ob)
    if villa is not None:
        ob["villa"] = villa + 1
        if NV > 1: coll(f"Villa {villa + 1}").objects.link(ob)
    return ob

# ------------------------------------------------------------------ 1) marciapiede di progetto
# prima degli altri elementi: le quote dei cancelli si leggono sul marciapiede
MARC_POL, MARC_Z = [], []
n_marc = 0
for el, g in forme:
    if not e_marciapiede(el): continue
    V, T, mid = triangoli(g); top = {i for t in T if nz(V, t) > 0.5 for i in t}
    W = []
    for i, p in enumerate(V):
        w_ = M @ p
        W.append(Vector((w_.x, w_.y, z_carreggiata(w_.x, w_.y) + (P.get("alzata_marciapiede_m", 0.12) if i in top else -0.25))))
    for t in T:
        if nz(V, t) > 0.5: MARC_POL.append(Polygon([(W[i].x, W[i].y) for i in t])); MARC_Z.append([tuple(W[i]) for i in t])
    oggetto(el, W, T, g, mid); n_marc += 1
ALBM = STRtree(MARC_POL) if MARC_POL else None
def normale_esterna(q):
    """normale al perimetro del lotto nel punto q, verso l'esterno (coord. IFC)."""
    ext = LOTTO.exterior; pr = ext.project(q); qa = ext.interpolate(max(0, pr - 0.05)); qb = ext.interpolate(pr + 0.05)
    tx_, ty_ = qb.x - qa.x, qb.y - qa.y; l_ = math.hypot(tx_, ty_) or 1; nx, ny = ty_ / l_, -tx_ / l_
    return (-nx, -ny) if LOTTO.contains(Point(q.x + nx * 0.2, q.y + ny * 0.2)) else (nx, ny)
def z_esterno(q, nx, ny):
    """piano di calpestio appena fuori dal lotto davanti a q (coord. IFC): marciapiede di progetto se c'è, altrimenti
    il rilievo, cercando sempre più lontano (oltre il filo del progetto il contesto può non avere superfici)."""
    for passo in (0.4, 0.8, 1.5, 2.5, 4.0):
        x, y = xy_ctx(q.x + nx * passo, q.y + ny * passo); pt = Point(x, y)
        if ALBM is not None:
            for k in ALBM.query(pt):
                if MARC_POL[k].buffer(0.01).contains(pt): return z_piano(MARC_Z[k], x, y)
        z = z_reale(x, y)
        if z is not None: return z
    return None

# ------------------------------------------------------------------ 2) ville e loro quote
VL = P.get("ville")
if VL:
    AX = (math.cos(math.radians(VL["asse_gradi"])), math.sin(math.radians(VL["asse_gradi"]))); TAGLI = sorted(VL["tagli"])
    NV = len(TAGLI) + 1
    if len(VL["cancelli"]) != NV: sys.exit(f"ville: {NV} ville ma {len(VL['cancelli'])} cancelli in lotto.json")
    def villa_di(x, y): s_ = x * AX[0] + y * AX[1]; return sum(1 for c in TAGLI if s_ > c)
    DZV = []
    for k_v, nome_c in enumerate(VL["cancelli"]):
        trovato = next(((e, gg) for e, gg in forme if e.Name == nome_c), None)
        if not trovato: sys.exit(f"cancello {nome_c} non trovato nell'IFC")
        V, _, _ = triangoli(trovato[1]); zb = min(p.z for p in V); c_ = centro(V)
        if villa_di(c_.x, c_.y) != k_v: log(f"ATTENZIONE: il cancello {nome_c} cade nella villa {villa_di(c_.x, c_.y) + 1}, non nella {k_v + 1}")
        q = LOTTO.exterior.interpolate(LOTTO.exterior.project(c_)); zm = z_esterno(q, *normale_esterna(q))
        DZV.append(zm - zb if zm is not None else dz)
        log(f"villa {k_v + 1}: cancello {nome_c}, soglia IFC {zb:.2f}, marciapiede {zm if zm is None else round(zm, 2)} → dz {DZV[-1]:.2f}")
    scn["ville_dz"] = DZV
else:
    NV = 1; DZV = [dz]
    def villa_di(x, y): return 0
MV = [matrice(d_) for d_ in DZV]

# ------------------------------------------------------------------ 3) elementi del progetto e terreno per villa
SITO = [[] for _ in range(NV)]; SITO_MID = [[] for _ in range(NV)]; SITO_G = None
n_ok = n_fuori = 0
for el, g in forme:
    if e_marciapiede(el): continue
    V, T, mid = triangoli(g)
    if el.is_a("IfcSite"):        # solo la superficie superiore, dentro il lotto (la terra è contenuta dai muraglioni)
        SITO_G = (el, g)
        for k, t in enumerate(T):
            c_ = centro(V, t)
            if nz(V, t) > 0.3 and LOTTO.contains(c_):
                kv = villa_di(c_.x, c_.y); SITO[kv].append([V[i] for i in t]); SITO_MID[kv].append(mid[k] if mid else 0)
        continue
    c_ = centro(V)
    if not PERIM.contains(c_): n_fuori += 1; log("fuori dal lotto, non importato:", el.is_a(), el.Name); continue
    kv = villa_di(c_.x, c_.y); oggetto(el, [MV[kv] @ p for p in V], T, g, mid, villa=kv); n_ok += 1
for kv in range(NV):
    if not SITO[kv] or not SITO_G: continue
    W = [MV[kv] @ p for t in SITO[kv] for p in t]; T = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(SITO[kv]))]
    ob = oggetto(SITO_G[0], W, T, SITO_G[1], SITO_MID[kv], nome=f"Terreno di progetto – villa {kv + 1}", villa=kv)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002); bm.to_mesh(ob.data); bm.free()
log("elementi importati:", n_ok, "+ marciapiedi", n_marc, "| esclusi fuori lotto:", n_fuori, "| ville:", NV)

# ------------------------------------------------------------------ 4) vuoti del terreno sotto le ville
SITO_TOP = [t for L_ in SITO for t in L_]
kd = kdtree.KDTree(max(1, 3 * len(SITO_TOP))); _zs = []
for t in SITO_TOP:
    for p in t: kd.insert(Vector((p.x, p.y, 0)), len(_zs)); _zs.append(p.z)
kd.balance()
def z_prog(x, y):
    """quota IFC del terreno di progetto nel punto più vicino (coord. IFC, senza dz)."""
    return _zs[kd.find(Vector((x, y, 0)))[1]]
def z_prog_ctx(x, y): return z_prog(x, y) + DZV[villa_di(x, y)]
coperto = unary_union([pl.buffer(0.02) for pl in (Polygon([(p.x, p.y) for p in t]) for t in SITO_TOP) if pl.area > 1e-6])
buchi = LOTTO.difference(coperto); VB, FB = [], []
for gb in getattr(buchi, "geoms", [buchi]):
    if gb.is_empty or gb.geom_type != "Polygon" or gb.area < 0.3: continue
    gb = gb.simplify(0.05); kv = villa_di(gb.centroid.x, gb.centroid.y)
    loops = [[Vector((x, y, z_prog(x, y))) for x, y in list(r.coords)[:-1]] for r in [gb.exterior, *gb.interiors]]
    base = len(VB); FB += [tuple(base + i for i in tri) for tri in mgeo.tessellate_polygon(loops)]
    VB += [MV[kv] @ p for r in loops for p in r]
if FB and SITO_G:
    oggetto(SITO_G[0], VB, FB, SITO_G[1], [0] * len(FB), nome="Terreno di progetto – riempimento sotto le ville")
log("vuoti riempiti:", round(buchi.area, 1), "m²")

# ------------------------------------------------------------------ 5) muraglioni in c.a.
MU = {"spessore_m": 0.3, "passo_m": 0.5, "minimo_m": 0.1, "materiale": "#9C9A93", **P.get("muraglione", {})}
mc = bpy.data.materials.get("CLS_muraglione") or bpy.data.materials.new("CLS_muraglione"); mc.use_nodes = True
_b = next(n for n in mc.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
_rgb = tuple((int(MU["materiale"].lstrip("#")[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4))
_b.inputs["Base Color"].default_value = (*_rgb, 1); _b.inputs["Roughness"].default_value = 0.85; mc.diffuse_color = (*_rgb, 1)
VM, FM = [], []
def tratto(sezioni):
    """sezioni consecutive (faccia esterna xy, faccia interna xy, z basso, z alto) → solido; None interrompe."""
    prev = None
    for s_ in sezioni:
        if s_ is None: prev = None; continue
        e_, i_, z0, z1 = s_; b = len(VM)
        VM.extend([Vector((*e_, z0)), Vector((*e_, z1)), Vector((*i_, z1)), Vector((*i_, z0))])
        if prev is not None:
            p_ = prev; FM.extend([(p_, b, b + 1, p_ + 1), (p_ + 1, b + 1, b + 2, p_ + 2), (p_ + 2, b + 2, b + 3, p_ + 3), (p_ + 3, b + 3, b, p_)])
        prev = b
# sul perimetro: dal piano esterno (marciapiede o rilievo) al terreno della villa
sez = []; n_mu = 0; n_salti = 0; per = LOTTO.exterior; k = 0.0
while k <= per.length + 1e-6:
    q = per.interpolate(min(k, per.length)); nx, ny = normale_esterna(q)
    zin = z_prog_ctx(q.x - nx * 0.4, q.y - ny * 0.4); zout = z_esterno(q, nx, ny)
    if zout is not None and zin - zout > MU["minimo_m"]:
        sez.append((xy_ctx(q.x, q.y), xy_ctx(q.x - nx * MU["spessore_m"], q.y - ny * MU["spessore_m"]), zout - 0.3, zin)); n_mu += 1
    else: sez.append(None); n_salti += zout is None
    k += MU["passo_m"]
tratto(sez)
# fra due ville a quote diverse: lungo la linea di divisione, dalla parte della villa più alta
n_div = 0
if VL:
    nax = (-AX[1], AX[0])
    for c in TAGLI:
        lin = LineString([(AX[0] * c - nax[0] * 200, AX[1] * c - nax[1] * 200), (AX[0] * c + nax[0] * 200, AX[1] * c + nax[1] * 200)]).intersection(LOTTO)
        for seg in getattr(lin, "geoms", [lin]):
            if seg.is_empty or seg.length < 0.5: continue
            sez = []; d_ = 0.0
            while d_ <= seg.length:
                q = seg.interpolate(d_); d_ += MU["passo_m"]
                zg = z_prog_ctx(q.x - AX[0] * 0.4, q.y - AX[1] * 0.4); zs_ = z_prog_ctx(q.x + AX[0] * 0.4, q.y + AX[1] * 0.4)
                if abs(zs_ - zg) <= MU["minimo_m"]: sez.append(None); continue
                sg = MU["spessore_m"] * (1 if zs_ > zg else -1)
                sez.append((xy_ctx(q.x, q.y), xy_ctx(q.x + AX[0] * sg, q.y + AX[1] * sg), min(zg, zs_) - 0.3, max(zg, zs_))); n_div += 1
            tratto(sez)
if FM:
    me = bpy.data.meshes.new("Muraglione di contenimento in c.a."); me.from_pydata(VM, [], FM); me.materials.append(mc)
    me.validate(); me.update(); coll("Muraglioni").objects.link(bpy.data.objects.new(me.name, me))
log(f"muraglioni: {n_mu} sezioni sul perimetro, {n_div} fra le ville (passo {MU['passo_m']} m); perimetro senza quota esterna: {n_salti}")

# ------------------------------------------------------------------ 6) il progetto comanda sul contesto
PRG = {o.name for c in COLL.values() for o in c.objects}
# facce di strade, marciapiedi e terreno sotto il lotto e sotto il marciapiede di progetto (solo dove il progetto copre)
TAGLIO = unary_union([a_ctx(LOTTO).buffer(-0.05)] + MARC_POL).buffer(-0.08)
n_t = 0
for ob in list(scn.objects):
    if ob.type != "MESH" or ob.name in PRG or not ob.name.startswith(tuple(P.get("taglia_superfici", ["P01", "P02", "Terreno"]))): continue
    bm = bmesh.new(); bm.from_mesh(ob.data); mw = ob.matrix_world
    via = [fc for fc in bm.faces if TAGLIO.contains(Point(*(mw @ fc.calc_center_median()).xy))]
    if via: bmesh.ops.delete(bm, geom=via, context="FACES"); bm.to_mesh(ob.data); n_t += len(via)
    bm.free()
# stato di fatto sostituito (prefissi "nascondi") e arredi, recinzioni, verde del contesto dentro il lotto: nascosti
LC = a_ctx(LOTTO).buffer(-0.3); n_h = 0
for ob in scn.objects:
    if ob.name in PRG or ob.type not in ("MESH", "EMPTY") or ob.hide_render: continue
    if not ob.name.startswith(NASC):
        if any(c.name in ("Terreno", "Strade") for c in ob.users_collection): continue
        if ob.type == "MESH" and ob.data.vertices:
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]; cpt = Point(sum(p.x for p in bb) / 8, sum(p.y for p in bb) / 8)
        else: cpt = Point(*ob.matrix_world.translation.xy)
        if not LC.contains(cpt): continue
    ob.hide_render = True; ob.hide_viewport = True; n_h += 1
log("contesto: facce tolte sotto il progetto", n_t, "| oggetti nascosti", n_h)
scn["progetto_ifc"] = json.dumps({k: P[k] for k in P if not k.startswith("_")}, ensure_ascii=False)

try: scn.eevee.shadow_pool_size = "2048"     # contesto + progetto: più ombre (il resto della resa viene dal contesto)
except Exception: pass
if opt("--samples"):
    try: scn.eevee.taa_render_samples = int(opt("--samples"))
    except Exception: pass
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend"))
if "--render" in argv: rendi_camere(bpy, scn, os.path.join(USCITA, "viste_progetto"), opt("--viste"), log)
log("fine")
