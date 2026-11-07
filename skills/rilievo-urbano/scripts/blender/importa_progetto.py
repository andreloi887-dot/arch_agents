"""Inserisce il progetto IFC (Edificius o altro) nella scena del contesto (fase 3b della filiera).

  blender -b <modello>/uscita_blender/contesto.blend -P importa_progetto.py -- <cartella modello> [--render] [--samples 16]

Legge <modello>/lotto.json → "progetto_ifc":
  file              percorso dell'IFC (relativo alla cartella del modello o assoluto)
  rotazione_gradi   rotazione in pianta attorno all'origine IFC (antioraria)
  traslazione       [x, y] in metri, coordinate locali del contesto (x = Est, y = Nord)
  dz                quota da sommare alle z IFC per portarle nel riferimento del contesto
  escludi_nomi      prefissi dei nomi IFC da non importare (strade e volumi di contesto disegnati nel progetto)
  nascondi          prefissi degli oggetti del contesto da nascondere (stato di fatto sostituito dal progetto)
  margine_m         tolleranza attorno al perimetro del progetto per tenere un elemento (default 1.0)
Se l'IFC non è georiferito, i valori si ricavano con allinea_ifc.py (adattamento del perimetro del progetto ai bordi
strada DBGT e ai confini catastali). La geometria si legge con ifcopenshell (incluso in Bonsai), un oggetto per
elemento IFC, collezioni per classe, colori dagli stili IFC. Salva <uscita>/contesto_progetto.blend; con --render
rende le camere del contesto in <uscita>/viste_progetto/.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
def opt(nome, default=None):
    return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else default
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
L = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8"))
P = L["progetto_ifc"]
LOG = open(os.path.join(USCITA, "importa_progetto.log"), "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.write(s + "\n"); LOG.flush()

import ifcopenshell, ifcopenshell.geom
from shapely.geometry import MultiPoint, Point, Polygon
FILE = P["file"] if os.path.isabs(P["file"]) else os.path.normpath(os.path.join(MOD, P["file"]))
f = ifcopenshell.open(FILE); log("IFC", FILE, f.schema)
a = math.radians(P.get("rotazione_gradi", 0.0)); tx, ty = P.get("traslazione", [0, 0]); dz = P.get("dz", 0.0)
M = Matrix.Translation((tx, ty, dz)) @ Matrix.Rotation(a, 4, "Z")
ESCL = tuple(P.get("escludi_nomi", []))
scn = bpy.context.scene

# ------------------------------------------------------------------ geometria
st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
forme = []
for el in f.by_type("IfcProduct"):
    if not el.Representation or el.is_a("IfcSpace") or el.is_a("IfcOpeningElement"): continue
    if el.Name and el.Name.startswith(ESCL): continue
    try: g = ifcopenshell.geom.create_shape(st, el).geometry
    except Exception as e: log("salto", el.is_a(), el.Name, e); continue
    if not g.verts: continue
    forme.append((el, g))
# perimetro del progetto: inviluppo di muri e solai (esclusi gli elementi isolati lontani)
pts = [(g.verts[i], g.verts[i + 1]) for el, g in forme if el.is_a() in ("IfcWall", "IfcSlab", "IfcWallStandardCase") for i in range(0, len(g.verts), 3)]
cx = sorted(p[0] for p in pts)[len(pts) // 2]; cy = sorted(p[1] for p in pts)[len(pts) // 2]
pts = [p for p in pts if abs(p[0] - cx) < 60 and abs(p[1] - cy) < 60]
PERIM = MultiPoint(pts).convex_hull.buffer(P.get("margine_m", 1.0))
log("perimetro progetto", round(PERIM.area), "m² (con margine)")

# ------------------------------------------------------------------ raccordo al terreno reale
# Il terreno di Edificius non segue l'andamento reale delle strade: gli edifici restano rigidi (quota dz), il terreno
# di progetto si deforma in una fascia lungo il perimetro fino alla quota rilevata appena fuori dal lotto
# (marciapiede, strada, terreno dei vicini) e i muri di confine hanno la base sulla quota reale.
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
RAC = P.get("raccordo", {"fascia_m": 5.0, "fuori_m": 1.0, "distanza_edifici_m": 1.5, "muri_entro_m": 1.5})
PERIM0 = MultiPoint(pts).convex_hull; BORDO = PERIM0.exterior; CEN = PERIM0.centroid
CT = json.load(open(os.path.join(MOD, "contesto.json"), encoding="utf-8"))
TRI, TRIZ = [], []
for s_ in CT["superfici"]:
    if s_["nome"].startswith(tuple(P.get("nascondi", []))): continue      # lo stato di fatto sostituito non conta
    Vs = s_["vertici"]
    for t in s_["triangoli"]:
        q3 = [Vs[i] for i in t[:3]]; TRI.append(Polygon([q[:2] for q in q3])); TRIZ.append(q3)
ALB = STRtree(TRI)
Minv = M.inverted()
def z_reale(x, y):
    """quota del rilievo in coordinate del contesto (interpolazione nel triangolo), None fuori."""
    pt = Point(x, y)
    for k in ALB.query(pt):
        if TRI[k].contains(pt):
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = (tuple(q[:3]) for q in TRIZ[k])
            d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
            if abs(d) < 1e-12: return z1
            l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / d; l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / d
            return l1 * z1 + l2 * z2 + (1 - l1 - l2) * z3
    return None
def z_fuori(px, py):
    """quota reale appena fuori dal perimetro, davanti al punto IFC (px, py); in coordinate del contesto."""
    q = BORDO.interpolate(BORDO.project(Point(px, py)))
    ux, uy = q.x - px, q.y - py; l = math.hypot(ux, uy)
    if l < 0.05: ux, uy = q.x - CEN.x, q.y - CEN.y; l = math.hypot(ux, uy)
    for passo in (RAC["fuori_m"], RAC["fuori_m"] * 2, 0.3):
        w_ = M @ Vector((q.x + ux / l * passo, q.y + uy / l * passo, 0))
        z = z_reale(w_.x, w_.y)
        if z is not None: return z
    return None
def liscio(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
# zone degli edifici (tetti e infissi): lì il terreno di progetto non si tocca
_ed = []
for el, g in forme:
    if el.is_a() in ("IfcRoof", "IfcWindow", "IfcDoor", "IfcColumn", "IfcStairFlight", "IfcStair"):
        q_ = [(g.verts[i], g.verts[i + 1]) for i in range(0, len(g.verts), 3)]
        if len(q_) >= 3: _ed.append(MultiPoint(q_).convex_hull)
EDIF = unary_union(_ed).buffer(0.5) if _ed else Polygon()
log("zone edifici", round(EDIF.area), "m²")

MATS = {}
def materiale(m):
    nome = "IFC_" + (m.name or "senza_nome")
    if nome in MATS: return MATS[nome]
    bm_ = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); bm_.use_nodes = True
    b = next(n for n in bm_.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    d_ = getattr(m, "diffuse", None)      # ifcopenshell ≥ 0.8: tupla o colore; versioni vecchie: has_diffuse + r()
    if d_ is not None and (not hasattr(m, "has_diffuse") or m.has_diffuse):
        r, g_, bl = (d_.r(), d_.g(), d_.b()) if hasattr(d_, "r") else tuple(d_)[:3]
        b.inputs["Base Color"].default_value = (r, g_, bl, 1); bm_.diffuse_color = (r, g_, bl, 1)
    tr = getattr(m, "transparency", 0.0) or 0.0
    if hasattr(m, "has_transparency") and not m.has_transparency: tr = 0.0
    if tr != tr: tr = 0.0   # NaN
    b.inputs["Roughness"].default_value = 0.6
    if tr > 0.05:   # vetri
        b.inputs["Roughness"].default_value = 0.03
        for k in ("Transmission Weight", "Transmission"):
            if k in b.inputs: b.inputs[k].default_value = min(1.0, tr + 0.2); break
        b.inputs["Alpha"].default_value = max(0.15, 1 - tr)
        try: bm_.surface_render_method = "BLENDED"
        except Exception: pass
    MATS[nome] = bm_; return bm_

COLL = {}
def coll(nome):
    if nome not in COLL:
        radice = bpy.data.collections.get("PROGETTO") or bpy.data.collections.new("PROGETTO")
        if radice.name not in scn.collection.children: scn.collection.children.link(radice)
        c = bpy.data.collections.new("PRG_" + nome); radice.children.link(c); COLL[nome] = c
    return COLL[nome]

n_ok = n_fuori = n_rac = n_muri = 0
for el, g in forme:
    v = g.verts; F = g.faces
    V = [Vector((v[i], v[i + 1], v[i + 2])) for i in range(0, len(v), 3)]
    T = [(F[k], F[k + 1], F[k + 2]) for k in range(0, len(F), 3)]
    mid = list(g.material_ids)
    if el.is_a("IfcSite"):   # terreno di progetto: solo dentro il perimetro, fuori resta il terreno del rilievo
        # i fianchi del solido restano: dove il terreno di progetto è più alto del marciapiede fanno da scarpata
        # nella fascia di raccordo il terreno arriva alla quota reale: lì i fianchi non servono e farebbero denti
        def tieni(t):
            c_ = Point(sum(V[i].x for i in t) / 3, sum(V[i].y for i in t) / 3)
            if not PERIM.contains(c_): return False
            if not RAC or BORDO.distance(c_) > RAC["fascia_m"]: return True
            n_ = (V[t[1]] - V[t[0]]).cross(V[t[2]] - V[t[0]])
            return n_.length > 1e-9 and n_.normalized().z > 0.3
        keep = [k for k, t in enumerate(T) if tieni(t)]
        T = [T[k] for k in keep]; mid = [mid[k] for k in keep] if mid else mid
    else:
        c_ = Point(sum(p.x for p in V) / len(V), sum(p.y for p in V) / len(V))
        if not PERIM.contains(c_): n_fuori += 1; log("fuori dal lotto, non importato:", el.is_a(), el.Name); continue
    if not T: continue
    W = [M @ p for p in V]
    if el.is_a("IfcSite") and RAC:       # terreno: fascia di raccordo lungo il perimetro, fuori dalle zone edifici
        usati = {i for t in T for i in t}
        for i in usati:
            p = V[i]; dp = BORDO.distance(Point(p.x, p.y)); w = liscio(1 - dp / RAC["fascia_m"])
            if w <= 0: continue
            w *= liscio(EDIF.distance(Point(p.x, p.y)) / RAC["distanza_edifici_m"])
            zf = z_fuori(p.x, p.y) if w > 0 else None
            if zf is not None: W[i].z = (1 - w) * W[i].z + w * zf; n_rac += 1
    elif el.is_a() in ("IfcWall", "IfcWallStandardCase", "IfcRailing") and RAC:   # muri di confine: base sul reale
        cw = Point(sum(p.x for p in V) / len(V), sum(p.y for p in V) / len(V))
        if BORDO.distance(cw) < RAC["muri_entro_m"]:
            zb = min(p.z for p in V)
            for i, p in enumerate(V):
                if p.z <= zb + 0.05:
                    zf = z_fuori(p.x, p.y)
                    if zf is not None: W[i].z = zf - 0.05
            n_muri += 1
    me = bpy.data.meshes.new(el.Name or el.is_a()); me.from_pydata(W, [], T)
    for m in g.materials: me.materials.append(materiale(m))
    if mid and g.materials:
        for k, poly in enumerate(me.polygons): poly.material_index = max(0, mid[k])
    me.validate(); me.update()
    for poly in me.polygons: poly.use_smooth = False
    ob = bpy.data.objects.new(el.Name or el.is_a(), me)
    ob["ifc_classe"] = el.is_a(); ob["ifc_guid"] = el.GlobalId
    coll(el.is_a().replace("Ifc", "")).objects.link(ob); n_ok += 1
log("elementi importati:", n_ok, "esclusi fuori lotto:", n_fuori, "| vertici di terreno raccordati:", n_rac, "muri di confine adattati:", n_muri)

# ------------------------------------------------------------------ stato di fatto sostituito
nasc = tuple(P.get("nascondi", []))
n_n = 0
for ob in scn.objects:
    if ob.name.startswith(nasc) and not any(ob.name in c.objects for c in COLL.values()):
        ob.hide_render = True; ob.hide_viewport = True; n_n += 1
log("oggetti del contesto nascosti:", n_n)
scn["progetto_ifc"] = json.dumps({k: P[k] for k in P if not k.startswith("_")}, ensure_ascii=False)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend"))

if "--render" in argv:
    # stesse impostazioni di resa di importa_contesto.py (non sono salvate nel .blend del contesto)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: scn.render.engine = eng; break
        except Exception: pass
    try: scn.eevee.taa_render_samples = int(opt("--samples", "16"))
    except Exception: pass
    try: scn.eevee.shadow_pool_size = "2048"     # contesto + progetto: più ombre
    except Exception: pass
    try: scn.view_settings.view_transform = "AgX"
    except Exception: pass
    for look in ("AgX - Punchy", "Punchy", "AgX - High Contrast"):
        try: scn.view_settings.look = look; break
        except Exception: pass
    scn.view_settings.exposure = -0.2
    out = os.path.join(USCITA, "viste_progetto"); os.makedirs(out, exist_ok=True)
    solo = opt("--viste")
    for co in [o for o in scn.objects if o.type == "CAMERA" and "res" in o]:
        if solo and not any(s in co.name for s in solo.split(",")): continue
        scn.camera = co; scn.render.resolution_x, scn.render.resolution_y = co["res"]
        scn.render.filepath = os.path.join(out, co.name + ".png")
        bpy.ops.render.render(write_still=True); log("render", co.name)
log("fine")
