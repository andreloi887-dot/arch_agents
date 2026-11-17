"""Arredi degli interni dagli ingombri indicati in planimetria (fase 3 della filiera).

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P arredi_interni.py -- <cartella modello>
  python arredi_interni.py -- <cartella modello> --blend contesto_progetto.blend        (Blender come modulo)

Dopo finiture_interni.py e prima di percorsi_camera.py. Riscrive contesto_progetto.blend; si può rilanciare.
Legge <modello>/arredi.json:
  stile    colori (hex) di legno, laccato, tessuto, tessuto_accento, piano_cucina, metallo, nero, tappeto
  arredi   elenco di pezzi: villa, vano, tipo, anello [[x, y], ...] in coordinate locali del contesto (l'ingombro in pianta)
Tipi: armadio, letto, comodino, madia_tv, scrivania (con sedia), parete_tv, lavabo (mobile del bagno al posto del blocco IFC
indicato in "sostituisce", che resta nel file nascosto), cucina (ingombro in linea, a L o a C, diviso
in moduli da 60 cm: frigo e colonna forno-microonde in fondo a una schiera, lavello e lavastoviglie sulla schiera più
libera, piano cottura con cappa su un'altra, basi, piano, paraschizzi, pensili dove non c'è una finestra), zona_giorno (senza anello: divano, tavolino e tappeto di
fronte alla parete TV, tavolo con posti_tavolo sedie vicino alla cucina, con distanza_porte_m liberi davanti alle porte
interne; "tavolo_contro_vano": tavolo addossato al muro in comune con quel vano, e parete TV, divano e tavolino spostati lungo
il loro muro di quanto serve).
Regole: il fronte di un mobile è il lato lungo verso il centro della stanza; la testata del letto è il lato corto contro
il muro; ogni pezzo sta sul pavimento del suo vano. Mobili parametrici, fatti di volumi semplici con spigoli smussati:
danno misure e proporzioni giuste; sedute e tessili andranno sostituiti con modelli di libreria per i render finali.
Punti luce ("luci": w_m2, colore): una sospensione per stanza (sul tavolo e sul tavolino in zona giorno), luce sotto i
pensili in cucina; nessuno dove c'è un controsoffitto con i suoi faretti. I pensili si fermano sotto la trave più bassa;
gli armadi hanno un'altezza unica sotto il punto più basso del tetto (al massimo 2,40 m); i comodini guardano dove
guarda il letto accanto.
Ogni oggetto porta la proprietà "ingombro" (anello in pianta): percorsi_camera.py la usa per non mettere la camera
dentro i mobili.
"""
import bmesh, bpy, json, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import avvio, svuota
import tessili
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

argv, opt, MOD, USCITA, log, scn = avvio("arredi_interni.log")
tessili.CACHE = os.path.join(USCITA, "cache_tessili")      # stessi ingressi → stesso tessile (la simulazione non è ripetibile)
A = json.load(open(os.path.join(MOD, "arredi.json"), encoding="utf-8"))
import materiali_arredo as MA
MA.configura(A.get("stile", {}))
from materiali_arredo import ST, RUV, TEX, mat
import ricette_arredo
tessili.LOG = log                                          # controlli automatici dei tessili nel log della filiera

radice = bpy.data.collections.get("PROGETTO") or scn.collection
ARR = bpy.data.collections.get("PRG_Arredi")
if not ARR: ARR = bpy.data.collections.new("PRG_Arredi"); radice.children.link(ARR)
svuota(bpy, ARR.objects)

# ------------------------------------------------------------------------------------------------ vani e infissi
vani = []
for ob in scn.objects:
    if "vano" not in ob or ob.type != "MESH": continue
    W = [ob.matrix_world @ v.co for v in ob.data.vertices]; z0 = min(w.z for w in W)
    base = [Polygon([W[i].xy[:] for i in pl.vertices]) for pl in ob.data.polygons if all(W[i].z < z0 + 0.05 for i in pl.vertices)]
    pol = unary_union([q for q in base if q.is_valid and q.area > 1e-6]).buffer(0.01)
    if pol.is_empty: continue
    if pol.geom_type != "Polygon": pol = max(pol.geoms, key=lambda q: q.area)
    vani.append({"nome": ob["vano"], "pol": pol, "z0": z0 + 0.004, "villa": int(ob.get("villa", 1))})
porte_, interne_, infissi_z = [], [], []                       # interne_: porte tra due stanze (rifatte da finiture_interni.py)
for ob in scn.objects:
    if ob.get("ifc_classe") in ("IfcWindow", "IfcDoor") and ob.type == "MESH" and ob.data.vertices:
        r_ = MultiPoint([(ob.matrix_world @ v.co).xy[:] for v in ob.data.vertices]).minimum_rotated_rectangle
        if r_.geom_type != "Polygon" or r_.length > 14: continue          # cancelli e recinzioni non contano
        zz = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]; infissi_z.append((r_, min(zz), max(zz)))
        if ob["ifc_classe"] == "IfcDoor": porte_.append(r_)
        if ob.get("sostituita"): interne_.append(r_)

# soffitto sopra un punto: la prima superficie di falde, travi a vista e controsoffitti che si incontra salendo
from mathutils.bvhtree import BVHTree
_V, _F = [], []
for ob in scn.objects:
    if ob.type != "MESH" or "vano" in ob or not (ob.name.startswith(("Falda", "Orditura", "Controsoffitto")) or ob.get("ifc_classe") in ("IfcRoof", "IfcSlab")): continue
    n0 = len(_V); _V += [ob.matrix_world @ v.co for v in ob.data.vertices]; _F += [[n0 + i for i in pl.vertices] for pl in ob.data.polygons]
TETTO = BVHTree.FromPolygons(_V, _F) if _F else None
def soffitto(x, y, z_da, pred=2.7):
    """quota del soffitto sopra (x, y) partendo da z_da; pred sopra z_da se non c'è niente."""
    h = TETTO.ray_cast(Vector((x, y, z_da)), Vector((0, 0, 1)), 12.0) if TETTO else (None,)
    return h[0].z if h[0] is not None else z_da + pred

# ------------------------------------------------------------------------------------------------ costruzione
POSATI = []   # un record per mobile o lampada: scritto in arredi_posati.json
class Pezzo:
    """un mobile: volumi rigidi (spigolo smussato 4 mm) e volumi morbidi (cuscini, materassi: smusso largo)."""
    def __init__(s, o, u, v, z0): s.o, s.u, s.v, s.z0 = Vector(o), Vector(u), Vector(v), z0; s.b = {"duro": ([], [], []), "morbido": ([], [], []), "liscio": ([], [], []), "tondo": ([], [], [])}; s.m = []
    def _m(s, k):
        if k not in s.m: s.m.append(k)
        return s.m.index(k)
    def P(s, a, b): q = s.o + s.u * a + s.v * b; return q.x, q.y
    def scat(s, u0, u1, v0, v1, z0, z1, k, tipo="duro"):
        V, F, M = s.b[tipo]; n = len(V)
        for z in (s.z0 + z0, s.z0 + z1):
            for a, b in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)): V.append((*s.P(a, b), z))
        F += [(n, n + 3, n + 2, n + 1), (n + 4, n + 5, n + 6, n + 7), (n, n + 1, n + 5, n + 4), (n + 1, n + 2, n + 6, n + 5),
              (n + 2, n + 3, n + 7, n + 6), (n + 3, n, n + 4, n + 7)]; M += [s._m(k)] * 6
    def poli(s, pts, z0, z1, k, tipo="duro"):
        """prisma su un poligono convesso in coordinate del pezzo (pts in senso antiorario), da z0 a z1."""
        V, F, M = s.b[tipo]; n = len(V); m_ = len(pts)
        for z in (s.z0 + z0, s.z0 + z1):
            for a, b in pts: V.append((*s.P(a, b), z))
        F.append(tuple(n + i for i in reversed(range(m_)))); F.append(tuple(n + m_ + i for i in range(m_)))
        for i in range(m_): j = (i + 1) % m_; F.append((n + i, n + j, n + m_ + j, n + m_ + i))
        M += [s._m(k)] * (m_ + 2)
    def grezzo(s, punti, facce, k, tipo="duro"):
        """mesh qualsiasi: punti (a, b, z) in coordinate del pezzo, facce come indici di punti; k un materiale o uno per faccia."""
        V, F, M = s.b[tipo]; n = len(V)
        for a, b, z in punti: V.append((*s.P(a, b), s.z0 + z))
        F += [tuple(n + i for i in f) for f in facce]; M += [s._m(x) for x in k] if isinstance(k, list) else [s._m(k)] * len(facce)
    def asta(s, a0, b0, z0, a1, b1, z1, r0, r1, k, seg=12, tipo="duro"):
        """cilindro rastremato da (a0, b0, z0) a (a1, b1, z1), anche inclinato (gambe divaricate)."""
        V, F, M = s.b[tipo]; n = len(V)
        p0 = Vector((*s.P(a0, b0), s.z0 + z0)); p1 = Vector((*s.P(a1, b1), s.z0 + z1)); ax = (p1 - p0).normalized()
        e1 = ax.cross(Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))).normalized(); e2 = ax.cross(e1)
        for q, r in ((p0, r0), (p1, r1)):
            for i in range(seg): t = 2 * math.pi * i / seg; V.append(tuple(q + (e1 * math.cos(t) + e2 * math.sin(t)) * r))
        for i in range(seg):
            j = (i + 1) % seg; F.append((n + i, n + j, n + seg + j, n + seg + i)); M.append(s._m(k))
        F += [tuple(n + i for i in reversed(range(seg))), tuple(n + seg + i for i in range(seg))]; M += [s._m(k)] * 2
    def tornio(s, a0, b0, prof, ks, seg=48, tipo="tondo"):
        """solido di rotazione attorno all'asse verticale in (a0, b0): prof = sezione chiusa [(r, z), ...] percorsa in un verso,
        ks = materiale di ogni lato della sezione (paralumi, globi, catino, piedi). Parte "tondo": liscia, senza smusso. Le r
        devono restare > 0 (niente punti sull'asse: facce degeneri)."""
        n = len(prof); pts = []; fac = []; mats = []
        for j in range(seg):
            t = 2 * math.pi * j / seg
            for r, z in prof: pts.append((a0 + r * math.cos(t), b0 + r * math.sin(t), z))
        for j in range(seg):
            j2 = (j + 1) % seg
            for i in range(n):
                i2 = (i + 1) % n; fac.append((j * n + i, j * n + i2, j2 * n + i2, j2 * n + i)); mats.append(ks[i] if isinstance(ks, list) else ks)
        s.grezzo(pts, fac, mats, tipo)
    def cil(s, a, b, r0, r1, z0, z1, k, seg=20):
        V, F, M = s.b["duro"]; n = len(V); cx, cy = s.P(a, b)
        for z, r in ((s.z0 + z0, r0), (s.z0 + z1, r1)):
            for i in range(seg): V.append((cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), z))
        for i in range(seg):
            j = (i + 1) % seg; F.append((n + i, n + j, n + seg + j, n + seg + i)); M.append(s._m(k))
        F += [tuple(n + i for i in reversed(range(seg))), tuple(n + seg + i for i in range(seg))]; M += [s._m(k)] * 2
    def fine(s, nome, villa, tipo, ingombro):
        # per Unreal (arredi_posati.json): dove sta il pezzo, com'è girato e quanto misura, per metterci un modello di libreria
        tutti = [Vector(q) for V, _, _ in s.b.values() for q in V]
        if tutti:
            aa = [(q.xy - s.o).dot(s.u) for q in tutti]; bb = [(q.xy - s.o).dot(s.v) for q in tutti]; zz = [q.z for q in tutti]
            cen = s.o + s.u * (min(aa) + max(aa)) / 2 + s.v * (min(bb) + max(bb)) / 2
            POSATI.append({"nome": None, "tipo": tipo, "villa": villa, "centro_m": [round(cen.x, 4), round(cen.y, 4), round(min(zz), 4)],
                           "lungo": [round(s.u.x, 5), round(s.u.y, 5)], "fronte": [round(s.v.x, 5), round(s.v.y, 5)],
                           "misure_m": [round(max(aa) - min(aa), 3), round(max(bb) - min(bb), 3), round(max(zz) - min(zz), 3)]})
            if getattr(s, "verso", None) is not None: POSATI[-1]["verso"] = [round(s.verso.x, 5), round(s.verso.y, 5)]
        for parte, (V, F, M) in s.b.items():
            if not V: continue
            me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F)
            bm_ = bmesh.new(); bm_.from_mesh(me); bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces); bm_.to_mesh(me); bm_.free()
            # solo i materiali che questa parte usa davvero: con slot inutili l'export USD legava una parte con un solo
            # materiale al primo slot (sedie e plaid in rovere in Unreal, 2026-11-16)
            # UV in metri / lato della texture. Facce orizzontali: U lungo il pezzo; verticali: U in quota per il legno (fibra
            # verticale), altrimenti in orizzontale
            uvl = me.uv_layers.new(name="UVMap")
            for pl in me.polygons:
                k_ = s.m[M[pl.index]]; lato, venato = (TEX[k_][1], TEX[k_][3]) if k_ in TEX else (1.0, False); nn = pl.normal
                th = Vector((-nn.y, nn.x)); th = th.normalized() if th.length > 1e-6 else s.u
                # fibra lungo il lato lungo della faccia (2026-11-17): verticale sulle ante, orizzontale sulla fascia del letto,
                # sulla testata larga e bassa, sui frontali dei cassetti (prima era verticale su ogni faccia verticale)
                qq = [Vector(V[me.loops[li].vertex_index]) for li in pl.loop_indices]
                lungo_or = (max(q.xy.dot(th) for q in qq) - min(q.xy.dot(th) for q in qq)) > (max(q.z for q in qq) - min(q.z for q in qq))
                if k_ in MA.FIBRA_VERTICALE: lungo_or = False                    # noce del bagno: fibra verticale come nella foto
                for li in pl.loop_indices:
                    q = Vector(V[me.loops[li].vertex_index])
                    if abs(nn.z) > 0.7: uv = (q.xy.dot(s.u), q.xy.dot(s.v))
                    elif venato and not lungo_or: uv = (q.z, q.xy.dot(th))
                    else: uv = (q.xy.dot(th), q.z)
                    uvl.data[li].uv = (uv[0] / lato, uv[1] / lato)
            usati = sorted(set(M)); per = {k_: i_ for i_, k_ in enumerate(usati)}
            for k_ in usati: me.materials.append(mat(s.m[k_]))
            me.polygons.foreach_set("material_index", [per[x] for x in M]); me.update()
            ob = bpy.data.objects.new(nome + {"duro": "", "morbido": " (tessili)", "liscio": " (liscio)", "tondo": " (tondo)"}[parte], me); ARR.objects.link(ob)
            if POSATI and POSATI[-1]["nome"] is None: POSATI[-1]["nome"] = ob.name     # il nome vero (Blender aggiunge .001 ai doppi)
            ob["villa"] = villa; ob["arredo"] = tipo; ob["ingombro"] = [c for q in ingombro.exterior.coords[:-1] for c in q]
            if parte == "tondo":                                   # curve lisce senza smusso (paralumi, globi, catino, mobile curvo)
                for pl in me.polygons: pl.use_smooth = True
                try: me.set_sharp_from_angle(angle=math.radians(35))
                except Exception: pass
                continue
            if parte == "liscio":                                  # imbottiti e forme organiche: gabbia + suddivisione
                sd = ob.modifiers.new("Liscio", "SUBSURF"); sd.levels = 2; sd.render_levels = 3
                for pl in me.polygons: pl.use_smooth = True
                if getattr(s, "rilievo", None):                   # superficie irregolare vera (gesso dei ciottoli): rumore di 2-3 mm
                    forza, grana = s.rilievo
                    tx = bpy.data.textures.get("Rilievo gesso") or bpy.data.textures.new("Rilievo gesso", "CLOUDS")
                    tx.noise_scale = grana; tx.noise_depth = 2
                    dp = ob.modifiers.new("Rilievo", "DISPLACE"); dp.texture = tx; dp.strength = forza; dp.mid_level = 0.5
                continue
            bv = ob.modifiers.new("Smusso", "BEVEL"); bv.limit_method = "ANGLE"
            bv.width, bv.segments = (0.004, 2) if parte == "duro" else (0.035, 4)
            if parte == "morbido":
                for pl in me.polygons: pl.use_smooth = True

def vano_di(villa, q):
    return next((v for v in vani if v["villa"] == villa and v["pol"].contains(Point(q))), None)
def libero(v, q):
    """distanza dai muri del punto q, -1 fuori dal vano."""
    return v["pol"].exterior.distance(Point(q)) if v["pol"].contains(Point(q)) else -1.0
def telaio(anello, v):
    """rettangolo minimo dell'ingombro: centro, asse lungo u, asse corto vv rivolto verso il centro della stanza, lati."""
    r = list(Polygon(anello).minimum_rotated_rectangle.exterior.coords)
    c = (Vector(r[0]) + Vector(r[2])) / 2; l1, l2 = Vector(r[1]) - Vector(r[0]), Vector(r[2]) - Vector(r[1])
    lu, lv = (l1, l2) if l1.length >= l2.length else (l2, l1); u, vv = lu.normalized(), lv.normalized()
    if libero(v, c - vv * (lv.length / 2 + 0.35)) > libero(v, c + vv * (lv.length / 2 + 0.35)): vv = -vv
    return c, u, vv, lu.length, lv.length

def sedia(p, c, verso):
    """sedia con il sedile in c e lo schienale dalla parte opposta a 'verso' (coordinate locali del pezzo p)."""
    cu, cv = c; du = Vector(verso).normalized(); dv = Vector((-du.y, du.x))
    def b(a0, a1, b0, b1, z0, z1, k, t="duro"):
        pts = [Vector((cu, cv)) + du * a + dv * bb for a, bb in ((a0, b0), (a1, b1))]
        p.scat(min(pts[0].x, pts[1].x), max(pts[0].x, pts[1].x), min(pts[0].y, pts[1].y), max(pts[0].y, pts[1].y), z0, z1, k, t)
    for sa in (-0.19, 0.16):
        for sb in (-0.19, 0.16): b(sa, sa + 0.03, sb, sb + 0.03, 0, 0.44, "legno")
    b(-0.22, 0.22, -0.22, 0.22, 0.44, 0.49, "tessuto", "morbido"); b(-0.22, -0.19, -0.21, 0.21, 0.49, 0.84, "legno")

def scatola_liscia(p, L_, aa, bb, zz, k, gonfio=0.0):
    """scatola con gli spigoli morbidi: reticolo aa × bb × zz (coordinate della sedia, anelli di sostegno vicino ai bordi)
    addolcito dalla suddivisione: cuscini e imbottiti."""
    A_, B_, Z_ = len(aa), len(bb), len(zz); idx, pts = {}, []
    def vid(i, j, q):
        if (i, j, q) not in idx:
            dz = gonfio * (1 if q == Z_ - 1 else -1 if q == 0 else 0) if 0 < i < A_ - 1 and 0 < j < B_ - 1 else 0.0   # cuscino gonfio
            idx[(i, j, q)] = len(pts); pts.append((*L_(aa[i], bb[j]), zz[q] + dz))
        return idx[(i, j, q)]
    fac = []
    for i in range(A_ - 1):
        for j in range(B_ - 1):
            fac.append((vid(i, j, 0), vid(i, j + 1, 0), vid(i + 1, j + 1, 0), vid(i + 1, j, 0)))
            fac.append((vid(i, j, Z_ - 1), vid(i + 1, j, Z_ - 1), vid(i + 1, j + 1, Z_ - 1), vid(i, j + 1, Z_ - 1)))
    for q in range(Z_ - 1):
        for i in range(A_ - 1):
            fac.append((vid(i, 0, q), vid(i + 1, 0, q), vid(i + 1, 0, q + 1), vid(i, 0, q + 1)))
            fac.append((vid(i, B_ - 1, q), vid(i, B_ - 1, q + 1), vid(i + 1, B_ - 1, q + 1), vid(i + 1, B_ - 1, q)))
        for j in range(B_ - 1):
            fac.append((vid(0, j, q), vid(0, j, q + 1), vid(0, j + 1, q + 1), vid(0, j + 1, q)))
            fac.append((vid(A_ - 1, j, q), vid(A_ - 1, j + 1, q), vid(A_ - 1, j + 1, q + 1), vid(A_ - 1, j, q + 1)))
    p.grezzo(pts, fac, k, "liscio")

def sedia_pranzo(p, c, verso):
    """sedia del riferimento di Andrea (2026-11-16): guscio imbottito unico a ferro di cavallo, alto 0,80 dietro, che scende
    senza salti fino ai braccioli bassi davanti; seduta a cuscino con gli spigoli morbidi; quattro gambe sottili in rovere,
    rastremate e un po' divaricate. Superfici lisce (suddivisione). Seduta in c, schienale dalla parte opposta a 'verso'."""
    cu, cv = c; du = Vector(verso).normalized(); dv = Vector((-du.y, du.x))
    def L_(a, b): q = Vector((cu, cv)) + du * a + dv * b; return (q.x, q.y)
    for sa, sb in ((-0.15, -0.165), (-0.15, 0.165), (0.16, -0.165), (0.16, 0.165)):
        p.asta(*L_(sa, sb), 0.41, *L_(sa * 1.22, sb * 1.20), 0.0, 0.015, 0.010, "rovere", seg=12)
    # seduta: cuscino 46 × 46, da 0,40 a 0,50, con anelli di sostegno a 3 cm dai bordi
    # dentro il guscio (raggio interno 0,215), angoli tondi in pianta: anelli di sostegno larghi in pianta, stretti in quota
    a0, a1, b0, b1 = -0.19, 0.25, -0.20, 0.20
    scatola_liscia(p, L_, [a0, a0 + 0.09, a1 - 0.09, a1], [b0, b0 + 0.09, b1 - 0.09, b1], [0.40, 0.415, 0.485, 0.50], "sabbia")
    # guscio: anelli di 4 punti (fuori sotto, fuori sopra, dentro sopra, dentro sotto) lungo un arco di 250° attorno alla
    # seduta; in cima segue h(t), alto dietro e basso sui fianchi; le due teste chiuse
    n = 16; t0 = math.radians(138); ro, ri = 0.265, 0.215
    def h(t): return 0.50 + 0.31 * ((1 + math.cos(t)) / 2) ** 0.8
    pts, fac = [], []
    for i in range(n + 1):
        t = -t0 + 2 * t0 * i / n; ct, st = math.cos(t), math.sin(t)
        for r_, z_ in ((ro, 0.40), (ro, h(t)), (ri, h(t) - 0.01), (ri, 0.47)):
            pts.append((*L_(-0.02 - r_ * ct * 0.95, r_ * st), z_))
    for i in range(n):
        o_, q_ = 4 * i, 4 * (i + 1)
        for k_ in range(4):
            k2 = (k_ + 1) % 4; fac.append((o_ + k_, q_ + k_, q_ + k2, o_ + k2))
    fac += [(0, 1, 2, 3), (4 * n + 3, 4 * n + 2, 4 * n + 1, 4 * n)]
    p.grezzo(pts, fac, "sabbia", "liscio")

def h_armadio(p, L, W, v, nome, H=2.40):
    """altezza unica dell'armadio: sotto il punto più basso di travi, travetti e falde sopra il suo ingombro, 2 cm d'aria,
    al massimo H (Andrea, 2026-11-16). Raggi ogni 5 cm (un travetto è largo 10) partendo da 1 m, sotto ogni trave."""
    na, nb = max(2, math.ceil(L / 0.05) + 1), max(2, math.ceil(W / 0.05) + 1)
    zt = min(soffitto(*p.P(-L / 2 + L * i / (na - 1), -W / 2 + W * j / (nb - 1)), v["z0"] + 1.0, 9.0) for i in range(na) for j in range(nb)) - v["z0"] - 0.02
    if zt < H: log(f"{nome}: alto {zt:.2f} m invece di {H:.2f}, sotto il tetto")
    if zt < 1.60: log(f"AVVISO {nome}: sotto il tetto c'è posto solo per {zt:.2f} m")
    return min(H, zt)

def armadio(p, L, W, H=2.40, vetro=False):
    """armadi dei riferimenti di Andrea (2026-11-16). Ante da circa 50 cm a tutta altezza, senza cornici.
    vetro=True (matrimoniale): ante in rovere e al centro una sezione di 2-3 ante in vetro fumé bronzo con telaio nero
    sottile; dentro fondo in rovere, ripiani, asta con camicie e LED verticali ai lati.
    vetro=False (singole): ante laccate greige con maniglie verticali nere sottili, LED nello zoccolo."""
    n = max(1, round(L / 0.5)); la = L / n; F2 = 0.0015
    ng = (3 if n >= 6 else 2 if n >= 4 else 0) if vetro else 0; g0 = (n - ng) // 2
    ga, gb = -L / 2 + g0 * la, -L / 2 + (g0 + ng) * la                    # tratto in vetro
    k_anta = "rovere" if vetro else "laccato_pensili"
    p.scat(-L / 2 + 0.01, L / 2 - 0.01, -W / 2, W / 2 - 0.07, 0, 0.07, "nero")                     # zoccolo arretrato, in ombra
    if not vetro: p.scat(-L / 2 + 0.02, L / 2 - 0.02, W / 2 - 0.075, W / 2 - 0.07, 0.003, 0.012, "led")   # luce radente sul pavimento
    fr = W / 2 - 0.022                                                                              # fronte della cassa
    if ng:
        for a0_, a1_ in ((-L / 2, ga), (gb, L / 2)):
            if a1_ - a0_ > 0.01: p.scat(a0_, a1_, -W / 2, fr, 0.07, H, "rovere")
        p.scat(ga, gb, -W / 2, -W / 2 + 0.02, 0.07, H, "rovere")                                 # schiena
        p.scat(ga, gb, -W / 2, fr, 0.07, 0.09, "rovere"); p.scat(ga, gb, -W / 2, fr, H - 0.02, H, "rovere")   # fondo e cielo
        za = min(H - 0.80, 1.75)                                                                    # asta appendiabiti
        ripiani = [zr for zr in (H - 0.32, H - 0.62) if zr > za + 0.12]
        for zr in ripiani: p.scat(ga + 0.01, gb - 0.01, -W / 2 + 0.02, fr - 0.03, zr, zr + 0.022, "rovere")         # ripiani
        p.scat(ga + 0.02, gb - 0.02, -0.012, 0.012, za - 0.02, za, "nero")                          # asta appendiabiti
        # camicie appese su grucce sottili nere (Andrea, 2026-11-17): qui le grucce; le camicie sono stoffa simulata
        # (ricette_arredo.armadio) dopo p.fine. Spalle della gruccia inclinate come quelle della camicia (tessili.camicia)
        p.camicie = [ga + (gb - ga) * x for x in (0.30, 0.38, 0.465, 0.55, 0.63)]
        for uc in p.camicie:
            zg = za - 0.075
            p.asta(uc, 0, zg, uc, 0, za + 0.004, 0.0022, 0.0022, "nero", seg=8)                              # gancio
            for sb in (-1, 1):
                p.asta(uc, sb * 0.05, zg, uc, sb * 0.20, zg - 0.22 * 0.14, 0.004, 0.004, "nero", seg=8)       # braccio
            p.asta(uc, -0.05, zg, uc, 0.05, zg, 0.004, 0.004, "nero", seg=8)
            p.asta(uc, -0.20, zg - 0.031, uc, 0.20, zg - 0.031, 0.0025, 0.0025, "nero", seg=8)             # barra
        p.za = za
        for ul in (ga + 0.012, gb - 0.022):                                                          # LED verticali ai lati
            p.scat(ul, ul + 0.01, fr - 0.05, fr - 0.035, 0.12, H - 0.04, "led")
        for zr in ripiani:                                                                          # biancheria piegata sui ripiani
            for kk, uu in enumerate([ga + (gb - ga) * x for x in (0.2, 0.5, 0.8)]):
                hh = 0.0
                for jj, (dh, mt_) in enumerate(((0.05, "lenzuolo"), (0.045, "cuscino"), (0.05, "plaid"))[: 2 + kk % 2]):
                    scatola_liscia(p, lambda a_, b_: (a_, b_), [uu - 0.17, uu - 0.15, uu + 0.15, uu + 0.17], [-0.20, -0.18, 0.13, 0.15],
                                   [zr + 0.022 + hh, zr + 0.03 + hh, zr + 0.014 + hh + dh, zr + 0.022 + hh + dh], mt_); hh += dh + 0.004
        p.luce_interna = (ga, gb, fr, H)
    else:
        p.scat(-L / 2, L / 2, -W / 2, fr, 0.07, H, k_anta)
    for i in range(n):
        u0, u1 = -L / 2 + i * la + F2, -L / 2 + (i + 1) * la - F2
        if g0 <= i < g0 + ng:                                                                       # anta in vetro con telaio nero
            p.scat(u0, u0 + 0.018, fr, W / 2, 0.07, H, "nero"); p.scat(u1 - 0.018, u1, fr, W / 2, 0.07, H, "nero")
            p.scat(u0, u1, fr, W / 2, 0.07, 0.088, "nero"); p.scat(u0, u1, fr, W / 2, H - 0.018, H, "nero")
            p.scat(u0 + 0.018, u1 - 0.018, fr + 0.008, fr + 0.014, 0.088, H - 0.018, "vetro_fume")
        else:
            p.scat(u0, u1, fr, W / 2, 0.07, H, k_anta)
            if not vetro and not (i % 2 == 0 and i == n - 1):                                       # maniglie a coppie, al centro di due ante
                um = u1 - 0.035 if i % 2 == 0 else u0 + 0.025
                p.scat(um, um + 0.01, W / 2, W / 2 + 0.025, 0.95, 1.35, "nero")

def letto(p, L, W, v, c, u, villa):
    """letto del riferimento di Andrea (2026-11-16): piattaforma in rovere che sporge su un basamento arretrato in ombra
    (sembra sospesa), materasso e piumone bianchi, plaid ai piedi, testata a pannello in rovere alta 1 m con il LED sopra
    che illumina il muro; nella matrimoniale la testata continua dietro i comodini."""
    testata_meno = libero(v, c - u * (L / 2 + 0.2)) <= libero(v, c + u * (L / 2 + 0.2)); s = 1 if testata_meno else -1
    p.verso = -u * s                                   # dai piedi alla testata
    def U(a, b): return (min(s * a, s * b), max(s * a, s * b))
    p.scat(*U(-L / 2 + 0.10, L / 2 - 0.22), -W / 2 + 0.20, W / 2 - 0.20, 0, 0.12, "nero")
    # tappeto sotto il letto (riferimento): sporge 0,6 m ai lati e 0,7 m ai piedi, se sta nella stanza
    for sp_ in (0.6, 0.45, 0.3):
        ret = Polygon([p.P(s * a_, b_) for a_, b_ in ((-L / 2 + 0.35, -W / 2 - sp_), (L / 2 + sp_ + 0.1, -W / 2 - sp_), (L / 2 + sp_ + 0.1, W / 2 + sp_), (-L / 2 + 0.35, W / 2 + sp_))])
        if v["pol"].buffer(-0.05).contains(ret):
            scatola_liscia(p, lambda a_, b_: (s * a_, b_), [-L / 2 + 0.35, -L / 2 + 0.37, L / 2 + sp_ + 0.08, L / 2 + sp_ + 0.1],
                           [-W / 2 - sp_, -W / 2 - sp_ + 0.02, W / 2 + sp_ - 0.02, W / 2 + sp_], [0.0, 0.003, 0.012, 0.015], "tappeto"); break
    imb = W <= 1.3 and villa in {int(x.get("villa", 1)) for x in A["arredi"]}
    if imb:
        # letto singolo tutto imbottito (Andrea, 2026-11-17: "il materasso è troppo piccolo, togli la cornice e fallo tutto il
        # letto, con la morbidezza dei tessuti"): base in tessuto e materasso a tutta larghezza, niente piattaforma in rovere
        p.scat(*U(-L / 2 + 0.05, L / 2), -W / 2, W / 2, 0.08, 0.27, "tessuto_letto", "morbido")         # base imbottita
        m0, m1, mw = -L / 2 + 0.06, L / 2 - 0.01, W / 2 - 0.01
        p.scat(*U(m0, m1), -mw, mw, 0.28, 0.48, "lenzuolo", "morbido")                                # materasso
        p.zm, p.zb = [0.28, 0.48], [0.08, 0.27]
    else:
        p.scat(*U(-L / 2 + 0.05, L / 2), -W / 2, W / 2, 0.12, 0.25, "rovere")
        m0, m1, mw = -L / 2 + 0.08, L / 2 - 0.16, W / 2 - 0.14
        p.scat(*U(m0, m1), -mw, mw, 0.25, 0.45, "lenzuolo", "morbido")                                    # materasso
        p.zm, p.zb = [0.25, 0.45], [0.12, 0.24]
    p.imbottito = imb
    # piumone, guanciali, cuscini e plaid: simulati come tessuti veri dopo p.fine (tessili_letto, modulo tessili.py)
    p.letto = (s, m0, m1, mw, L, W)
    # testata: la più larga che sta nella stanza senza toccare gli armadi
    armadi_ = [Polygon(x["anello"]).buffer(0.02) for x in A["arredi"] if x["tipo"] == "armadio" and x.get("anello") and int(x.get("villa", 1)) == villa]
    hw = W / 2 + 0.02
    for prova in ([W / 2 + 0.55 - 0.05 * k for k in range(11)] if W > 1.3 else []):
        ret = Polygon([p.P(s * a_, b_) for a_, b_ in ((-L / 2, -prova), (-L / 2 + 0.05, -prova), (-L / 2 + 0.05, prova), (-L / 2, prova))])
        if v["pol"].buffer(0.01).contains(ret) and not any(q.intersects(ret) for q in armadi_): hw = prova; break
    p.scat(*U(-L / 2, -L / 2 + 0.05), -hw, hw, 0, 1.00, "rovere")
    p.scat(*U(-L / 2 + 0.005, -L / 2 + 0.015), -hw + 0.02, hw - 0.02, 1.00, 1.004, "led")
    p.testata = (s, hw)

def tessili_letto(p, v, villa, nome):
    """piumone, plaid, guanciali e cuscini simulati come tessuti veri (ricette_arredo.letto, la stessa del banco di prova).
    La geometria della ricetta resta sull'oggetto del letto (proprieta' "ricetta") per banco_scena.py."""
    s, m0, m1, mw, L, W = p.letto
    R = {"tipo": "letto", "nome": nome, "villa": villa, "o": list(p.o[:2]), "us": list((p.u * s)[:2]), "vv": list(p.v[:2]), "m0": m0, "m1": m1, "mw": mw,
         "L": L, "W": W, "z0": v["z0"], "hw": p.testata[1], "zm": p.zm, "zb": p.zb, "imbottito": p.imbottito}
    ob_l = bpy.data.objects.get(nome)
    if ob_l: ob_l["ricetta"] = json.dumps(R)
    fatti, righe = ricette_arredo.letto(scn, R)
    for r_ in righe: log(r_)
    for ob in fatti:
        for c_ in list(ob.users_collection): c_.objects.unlink(ob)
        ARR.objects.link(ob); ob["villa"] = villa; ob["arredo"] = "letto"; ob["ingombro"] = []

def comodino(p, L, W, lume=True):
    """comodino sospeso in rovere (riferimento del letto, 2026-11-16) con un cassetto e una lampada piccola in ceramica.
    lume=False: senza abat-jour (camera matrimoniale: sospensioni sottili accanto al letto, 2026-11-17)."""
    p.scat(-L / 2, L / 2, -W / 2, W / 2, 0.30, 0.46, "rovere"); p.scat(-L / 2 + 0.01, L / 2 - 0.01, W / 2, W / 2 + 0.003, 0.315, 0.445, "rovere")
    if not lume: return
    p.cil(0, -0.05, 0.06, 0.045, 0.46, 0.60, "intonaco"); p.cil(0, -0.05, 0.006, 0.006, 0.60, 0.66, "metallo")
    p.cil(0, -0.05, 0.12, 0.095, 0.62, 0.82, "lenzuolo")

def lato_destro(c, villa, v):
    """True se il punto c sta alla destra del letto più vicino guardando dai piedi verso la testata."""
    letti = [q for q in POSATI if q["tipo"] == "letto" and q["villa"] == villa and q.get("verso") and v["pol"].contains(Point(q["centro_m"][:2]))]
    if not letti: return False
    b = min(letti, key=lambda q: (Vector(q["centro_m"][:2]) - c).length); f = Vector(b["verso"]).normalized()
    return (c - Vector(b["centro_m"][:2])).dot(Vector((f.y, -f.x))) > 0

def madia_tv(p, L, W):
    for su in (-L / 2 + 0.06, L / 2 - 0.09):
        for sv in (-W / 2 + 0.06, W / 2 - 0.09): p.scat(su, su + 0.03, sv, sv + 0.03, 0, 0.16, "metallo")
    p.scat(-L / 2, L / 2, -W / 2, W / 2 - 0.02, 0.16, 0.76, "legno")
    n = max(2, round(L / 0.45)); la = L / n
    for i in range(n): p.scat(-L / 2 + i * la + 0.0015, -L / 2 + (i + 1) * la - 0.0015, W / 2 - 0.02, W / 2, 0.16, 0.76, "legno")
    p.scat(-0.16, 0.16, -0.12, 0.08, 0.76, 0.775, "nero"); p.scat(-0.02, 0.02, -0.04, 0.0, 0.775, 0.84, "nero"); p.scat(-0.56, 0.56, -0.035, -0.005, 0.82, 1.46, "nero")

def scrivania(p, L, W):
    p.scat(-L / 2, L / 2, -W / 2, W / 2, 0.72, 0.75, "legno")
    for su in (-L / 2 + 0.04, L / 2 - 0.08):
        for sv in (-W / 2 + 0.04, W / 2 - 0.08): p.scat(su, su + 0.04, sv, sv + 0.04, 0, 0.72, "metallo")
    p.scat(-L / 2 + 0.10, -L / 2 + 0.50, -W / 2 + 0.05, W / 2 - 0.05, 0.60, 0.72, "legno")      # cassetto
    p.cil(L / 2 - 0.22, -W / 2 + 0.2, 0.07, 0.07, 0.75, 0.765, "metallo"); p.cil(L / 2 - 0.22, -W / 2 + 0.2, 0.008, 0.008, 0.765, 1.12, "metallo")
    p.cil(L / 2 - 0.22, -W / 2 + 0.2, 0.10, 0.07, 1.05, 1.20, "metallo")
    sedia_pranzo(p, (0.0, W / 2 + 0.20), (0, -1))                       # stessa sedia del tavolo (stile dei riferimenti)

def parete_tv(p, L, W):
    p.scat(-L / 2, L / 2, -W / 2, -W / 2 + 0.02, 0, 2.30, "legno")
    n = int(L / 0.06)
    for i in range(n): p.scat(-L / 2 + i * L / n + 0.01, -L / 2 + i * L / n + 0.04, -W / 2 + 0.02, -W / 2 + 0.038, 0, 2.30, "legno")
    p.scat(-L / 2, L / 2, -W / 2 + 0.038, -W / 2 + 0.45, 0.22, 0.52, "laccato")
    p.scat(-0.72, 0.72, -W / 2 + 0.045, -W / 2 + 0.075, 0.92, 1.74, "nero")
    p.scat(L / 2 - 1.05, L / 2 - 0.05, -W / 2 + 0.038, -W / 2 + 0.26, 1.95, 1.98, "legno")

n_luci_cucina = 0
def cucina(nome, anello, v, villa):
    pol = Polygon(anello).buffer(0); cc = list(pol.exterior.coords)
    k = max(range(len(cc) - 1), key=lambda i: math.dist(cc[i], cc[i + 1])); u = (Vector(cc[k + 1]) - Vector(cc[k])).normalized(); w = Vector((-u.y, u.x))
    o = Vector(cc[0]); loc = [((Vector(q) - o).dot(u), (Vector(q) - o).dot(w)) for q in cc[:-1]]
    def unici(vals):
        out = []
        for x in sorted(vals):
            if not out or x - out[-1] > 0.03: out.append(x)
        return out
    xs, ys = unici(q[0] for q in loc), unici(q[1] for q in loc); lp = Polygon(loc)
    piena = {(i, j) for i in range(len(xs) - 1) for j in range(len(ys) - 1) if lp.contains(Point((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2))}
    rett = []
    while piena:                                              # rettangoli massimi, prima lungo l'asse lungo
        i, j = min(piena); i1 = i
        while (i1 + 1, j) in piena: i1 += 1
        j1 = j
        while all((a, j1 + 1) in piena for a in range(i, i1 + 1)): j1 += 1
        for a in range(i, i1 + 1):
            for b in range(j, j1 + 1): piena.discard((a, b))
        rett.append((xs[i], xs[i1 + 1], ys[j], ys[j1 + 1]))
    p = Pezzo(o, u, w, v["z0"]); moduli = []
    for kr, (x0, x1, y0, y1) in enumerate(rett):
        lungo_x = (x1 - x0) >= (y1 - y0); lung, prof = (x1 - x0, y1 - y0) if lungo_x else (y1 - y0, x1 - x0)
        # lato muro: quello con meno spazio libero davanti
        if lungo_x: f0 = libero(v, o + u * ((x0 + x1) / 2) + w * (y0 - 0.3)); f1 = libero(v, o + u * ((x0 + x1) / 2) + w * (y1 + 0.3)); sg = 1 if f0 <= f1 else -1; m0 = y0 if sg == 1 else y1
        else: f0 = libero(v, o + u * (x0 - 0.3) + w * ((y0 + y1) / 2)); f1 = libero(v, o + u * (x1 + 0.3) + w * ((y0 + y1) / 2)); sg = 1 if f0 <= f1 else -1; m0 = x0 if sg == 1 else x1
        def pt(a_, d, lungo_x=lungo_x, x0=x0, y0=y0, m0=m0, sg=sg):       # a_ lungo la schiera, d in profondità (0 = muro) → locale
            return (x0 + a_, m0 + sg * d) if lungo_x else (m0 + sg * d, y0 + a_)
        def box(a0, a1, d0, d1, z0, z1, kk, pt=pt):
            (xa, ya), (xb, yb) = pt(a0, d0), pt(a1, d1); p.scat(min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb), z0, z1, kk)
        def mondo(a_, d, pt=pt): q = pt(a_, d); return o + u * q[0] + w * q[1]
        n = max(1, round(lung / 0.6)); la = lung / n
        for i in range(n):
            a0, a1 = i * la, (i + 1) * la; am = (a0 + a1) / 2
            dietro = Polygon([tuple(mondo(a0, -0.45)), tuple(mondo(a1, -0.45)), tuple(mondo(a1, 0.02)), tuple(mondo(a0, 0.02))])
            moduli.append({"box": box, "pt": pt, "a": (a0, a1), "am": am, "prof": prof, "lung": lung, "i": i, "n": n, "r": kr, "ruolo": None,
                           "angolo": lp.contains(Point(pt(am, prof + 0.3))),                     # fronte chiuso da un'altra schiera
                           "finestra": any(r_.intersects(dietro) and zb < v["z0"] + 2.15 and zt > v["z0"] + 1.0 for r_, zb, zt in infissi_z),
                           "al_muro": i in (0, n - 1) and libero(v, mondo(-0.25 if i == 0 else lung + 0.25, prof / 2)) < 0})
    # ruoli. Colonne (frigo, forno e microonde): due moduli in fondo a una schiera, meglio se contro un muro, senza finestra dietro.
    # Lavello e lavastoviglie sulla schiera con più moduli liberi; piano cottura su un'altra schiera, se c'è posto
    def di(r): return sorted((m for m in moduli if m["r"] == r), key=lambda m: m["i"])
    def libero_(m): return m["ruolo"] is None and not m["angolo"]
    coppie = []
    for r in {m["r"] for m in moduli}:
        mm = di(r)
        for capo, vicino in ((mm[0], mm[1] if len(mm) > 1 else None), (mm[-1], mm[-2] if len(mm) > 1 else None)):
            if vicino and libero_(capo) and libero_(vicino) and not capo["finestra"] and not vicino["finestra"]: coppie.append((capo, vicino))
    if coppie:
        capo, vicino = max(coppie, key=lambda c_: (c_[0]["al_muro"], -c_[0]["lung"])); capo["ruolo"], vicino["ruolo"] = "frigo", "forno"
    else:
        solo = next((m for m in moduli if libero_(m) and m["i"] in (0, m["n"] - 1) and not m["finestra"]), None)
        if solo: solo["ruolo"] = "frigo"
        log(f"AVVISO {nome}: non c'è posto per due colonne: forno sotto il piano cottura, niente microonde")
    conta_l = {r: sum(libero_(m) for m in di(r)) for r in {m["r"] for m in moduli}}; r_acqua = max(conta_l, key=lambda r: conta_l[r])
    lib = [m for m in di(r_acqua) if libero_(m)]
    if lib:
        lav = min(lib, key=lambda m: abs(m["am"] - m["lung"] / 2)); lav["ruolo"] = "lavello"
        acc = [m for m in lib if abs(m["i"] - lav["i"]) == 1 and libero_(m)]
        if acc: acc[0]["ruolo"] = "lavastoviglie"
    resto = [m for m in moduli if libero_(m) and not m["finestra"]] or [m for m in moduli if libero_(m)]
    if resto:
        pc = max(resto, key=lambda m: (m["r"] != r_acqua, not any(x["ruolo"] == "lavello" and x["r"] == m["r"] and abs(x["i"] - m["i"]) == 1 for x in moduli)))
        pc["ruolo"] = "cottura" if coppie else "cottura_forno"
    # Stile (riferimento di Andrea, 2026-11-16): senza maniglie, gola sotto il piano, basi e colonne in rovere chiaro, pensili
    # laccati greige opachi con LED sotto, piano in pietra chiara di 2 cm, paraschizzi in lastra di marmo, frigo e
    # lavastoviglie a scomparsa dietro le ante, cappa integrata nel pensile, piano a induzione a filo
    ZC, ZP, ZS, ZA, HP = 0.10, 0.88, 0.90, 1.45, 2.15                 # zoccolo, sotto il piano, sopra il piano, pensili da-a
    FG = 0.0015                                                        # mezza fuga tra le ante
    def forno(box, a0, a1, d, z0):                                     # forno in vetro nero, senza maniglia sporgente
        box(a0 + 0.003, a1 - 0.003, d, d + 0.02, z0, z0 + 0.595, "nero"); box(a0 + 0.003, a1 - 0.003, d + 0.02, d + 0.021, z0 + 0.555, z0 + 0.595, "metallo")
    def cassetti(box, a0, a1, f, prof, z_da, z_a, n_c):                 # cassetti in rovere, fughe orizzontali sottili
        h_ = (z_a - z_da) / n_c
        for j in range(n_c): box(a0 + FG, a1 - FG, f, prof, z_da + j * h_ + (FG if j else 0), z_da + (j + 1) * h_ - FG, "rovere")
    luci_led = {}                                                      # schiera → tratti con pensile (per la luce sotto)
    for m in moduli:
        box, (a0, a1), prof, am, ruolo = m["box"], m["a"], m["prof"], m["am"], m["ruolo"]; f = prof - 0.02
        if ruolo in ("frigo", "forno"):
            zt = min(soffitto(*tuple(o + u * q[0] + w * q[1]), v["z0"] + 1.8) for q in (m["pt"](a_, d_) for a_ in (a0 + 0.01, am, a1 - 0.01) for d_ in (0.02, prof / 2, prof))) - v["z0"] - 0.02
            if zt < HP: log(f"AVVISO {nome}: la colonna {ruolo} (2,15 m) tocca il tetto, che lì è a {zt:.2f} m")
            box(a0, a1, 0, prof - 0.06, 0, ZC, "rovere"); box(a0, a1, 0, f, ZC, HP, "rovere")
            if ruolo == "frigo":                               # frigo da incasso dietro due ante in rovere, a tutta altezza
                box(a0 + FG, a1 - FG, f, prof, ZC, 0.88 - FG, "rovere"); box(a0 + FG, a1 - FG, f, prof, 0.88 + FG, HP, "rovere")
            else:                                              # colonna: cassettone, forno, microonde, anta sopra
                cassetti(box, a0, a1, f, prof, ZC, 0.70, 1); forno(box, a0, a1, f, 0.715)
                box(a0 + FG, a1 - FG, f, prof, 1.325, 1.705, "rovere")                         # anta (niente microonde a vista)
                box(a0 + FG, a1 - FG, f, prof, 1.72, HP, "rovere")
            continue
        box(a0, a1, 0, prof - 0.06, 0, ZC, "rovere")                                                                # zoccolo arretrato
        box(a0, a1, 0, 0.015, ZS, ZA, "marmo")                                                                      # lastra di marmo
        alto = 0.66 if ruolo == "lavello" else ZP                                                                   # sotto il lavello il mobile è più basso: c'è la vasca
        box(a0, a1, 0, f, ZC, alto, "rovere")
        if ruolo == "lavello":                                 # vasca sottotop, rubinetto alto e sottile
            v0, v1, b0, b1 = am - 0.25, am + 0.25, 0.10, 0.50
            for q in ((a0, v0, 0, prof + 0.02), (v1, a1, 0, prof + 0.02), (v0, v1, 0, b0), (v0, v1, b1, prof + 0.02)): box(*q, ZP, ZS, "pietra")
            box(v0, v1, b0, b1, ZS - 0.19, ZS - 0.185, "inox")
            for q in ((v0 - 0.004, v0, b0, b1), (v1, v1 + 0.004, b0, b1), (v0, v1, b0 - 0.004, b0), (v0, v1, b1, b1 + 0.004)): box(*q, ZS - 0.19, ZP, "inox")
            p.cil(*m["pt"](am, 0.055), 0.011, 0.011, ZS, ZS + 0.34, "inox", seg=12); box(am - 0.008, am + 0.008, 0.055, 0.26, ZS + 0.325, ZS + 0.341, "inox")
            box(a0 + FG, a1 - FG, f, prof, ZC, 0.80, "rovere"); box(a0, a1, f - 0.03, f - 0.02, 0.66, ZP, "rovere")     # fondo della gola
        else:
            box(a0, a1, 0, prof + 0.02, ZP, ZS, "pietra")
            if ruolo == "lavastoviglie": box(a0 + FG, a1 - FG, f, prof, ZC, 0.80, "rovere")                           # a scomparsa
            elif ruolo == "cottura_forno": forno(box, a0, a1, f, 0.20); cassetti(box, a0, a1, f, prof, ZC, 0.195, 1)
            else: cassetti(box, a0, a1, f, prof, ZC, 0.80, 3)                                                        # tre cassetti sotto la gola
        if ruolo in ("cottura", "cottura_forno"):              # induzione a filo, cornice sottile
            box(am - 0.29, am + 0.29, 0.06, 0.56, ZS - 0.004, ZS + 0.001, "nero")
        if not m["finestra"]:
            # il pensile arriva sotto la trave o la falda più bassa che ha sopra (2 cm d'aria), al massimo a HP
            zt = min(soffitto(*tuple(o + u * q[0] + w * q[1]), v["z0"] + ZA) for q in (m["pt"](a_, d_) for a_ in (a0 + 0.01, am, a1 - 0.01) for d_ in (0.02, 0.18, 0.34))) - v["z0"] - 0.02
            if min(HP, zt) - ZA >= 0.35:
                zp = min(HP, zt); box(a0, a1, 0, 0.33, ZA, zp, "laccato_pensili")                                       # cassa
                for k_, (b0_, b1_) in enumerate(((a0, am), (am, a1))): box(b0_ + FG, b1_ - FG, 0.33, 0.35, ZA, zp, "laccato_pensili")   # due ante
                box(a0 + 0.01, a1 - 0.01, 0.29, 0.31, ZA - 0.004, ZA, "led")                                         # striscia LED sotto
                luci_led.setdefault(m["r"], []).append((a0, a1, m["pt"]))
            else: log(f"{nome}: modulo {m['r']}.{m['i']} senza pensile, il tetto è a {zt:.2f} m")
            if ruolo in ("cottura", "cottura_forno"): box(a0 + 0.02, a1 - 0.02, 0.012, 0.33, ZA - 0.02, ZA, "laccato_pensili")     # cappa integrata
    # luce della striscia LED: un'area stretta sotto ogni tratto di pensili, rivolta verso il piano
    global n_luci_cucina
    for r, tratti in luci_led.items():
        tratti.sort(key=lambda t: t[0]); a0, a1, pt_ = tratti[0][0], tratti[-1][1], tratti[0][2]
        c0, c1 = Vector(pt_(a0, 0.30)), Vector(pt_(a1, 0.30)); cm_ = (c0 + c1) / 2; d_ = (c1 - c0)
        q_ = o + u * cm_.x + w * cm_.y; dd = (u * d_.x + w * d_.y).normalized()
        ld = bpy.data.lights.new(f"LED pensili {nome} {r}", "AREA"); ld.shape = "RECTANGLE"; ld.size = max(0.2, (a1 - a0) - 0.02); ld.size_y = 0.02
        ld.energy = 8.0 * (a1 - a0); ld.color = (1.0, 0.92, 0.80)
        lo = bpy.data.objects.new(f"Luce LED pensili {nome} {r}", ld); lo.location = (q_.x, q_.y, v["z0"] + ZA - 0.006)
        lo.rotation_euler = (0, 0, math.atan2(dd.y, dd.x)); ARR.objects.link(lo); lo["villa"] = villa; lo["punto_luce"] = v["nome"]; n_luci_cucina += 1
    p.fine(nome, villa, "cucina", pol)
    log(f"{nome}: moduli", ", ".join(f"{m['ruolo'] or ('angolo' if m['angolo'] else 'base')}{'' if not m['finestra'] else ' (finestra)'}" for m in moduli))

def zona_giorno(a, v, villa, tv):
    """divano, tavolino e tappeto di fronte alla parete TV; tavolo da pranzo nel posto libero più ampio."""
    c, u, vv, L, W, nome_tv = tv; occupati = [Polygon(x["anello"]).buffer(0.05) for x in A["arredi"] if x.get("anello") and x["villa"] == villa]
    sue = [q for q in porte_ if q.distance(v["pol"]) < 0.3]              # porte della stanza
    cucine = [x["pol"] for x in vani if x["villa"] == villa and x["nome"].startswith("Cucina")]
    verso_cucina = min(sue, key=lambda q: min(q.distance(k_) for k_ in cucine)) if sue and cucine else None
    interne = [q for q in sue if any(q.equals(k_) for k_ in interne_)]; altre = [q for q in sue if q not in interne]
    d_porte = float(a.get("distanza_porte_m", 0.9)); n_p = int(a.get("posti_tavolo", 6)); lt = max(1.4, 0.6 * (n_p // 2)); wt = 0.45 if n_p > 4 else 0.40; x0, y0, x1, y1 = v["pol"].bounds
    # il divano sta di fronte alla TV a distanza d e può scostarsi di lato di sh (lo schermo resta davanti al divano)
    def divano_a(d, sh=0.0): return Polygon([tuple(c + vv * (W / 2 + d + sv) + u * (su + sh)) for su, sv in ((-1.15, -0.475), (1.15, -0.475), (1.15, 0.475), (-1.15, 0.475))])
    def zona_tv(d, sh=0.0): return MultiPoint([tuple(c + u * su) for su in (-0.75, 0.75)] + list(divano_a(d, sh).exterior.coords)).convex_hull
    stato = {"porte": Polygon(), "chiave": None, "fatti": {}}
    def tavolo_con(d, sh=0.0):
        """posto del tavolo (con le sedie), dato il divano a distanza d: vicino alla cucina, libero da mobili e porte."""
        if (d, sh, stato["chiave"]) in stato["fatti"]: return stato["fatti"][(d, sh, stato["chiave"])]
        occ = unary_union(occupati + ([divano_a(d, sh).buffer(0.15), zona_tv(d, sh)] if d else [])); meglio = None
        vietato = prep(unary_union([occ, stato["porte"]])); stanza = prep(v["pol"].buffer(-0.05))
        for asse in (u, vv):
            pa = Vector((-asse.y, asse.x)); i = 0
            while x0 + 0.1 * i < x1:
                j = 0
                while y0 + 0.1 * j < y1:
                    q = Vector((x0 + 0.1 * i, y0 + 0.1 * j)); j += 1
                    zona = Polygon([tuple(q + asse * sa + pa * sb) for sa, sb in ((-lt / 2 - 0.15, -wt - 0.5), (lt / 2 + 0.15, -wt - 0.5), (lt / 2 + 0.15, wt + 0.5), (-lt / 2 - 0.15, wt + 0.5))])
                    if not stanza.contains(zona) or vietato.intersects(zona): continue
                    # il tavolo sta vicino alla cucina; senza cucina accanto, nel punto più lontano da muri e mobili
                    voto = -verso_cucina.distance(Point(q)) if verso_cucina is not None else min(v["pol"].exterior.distance(Point(q)), occ.distance(Point(q)))
                    # il passaggio davanti alle altre porte interne (disimpegno) conta più della vicinanza alla cucina
                    voto += 2.0 * min([2.5] + [k_.distance(zona) for k_ in interne if k_ is not verso_cucina])
                    if meglio is None or voto > meglio[0]: meglio = (voto, q, asse, pa, zona)
                i += 1
        stato["fatti"][(d, sh, stato["chiave"])] = meglio; return meglio
    # divano: distanza dalla TV la più comoda (da 3,0 m a scendere) e scostamento laterale il più piccolo che lasciano posto al tavolo
    def possibili(sh): return [d for d in [3.0 - 0.1 * k for k in range(11)] if v["pol"].buffer(-0.08).contains(divano_a(d, sh))]
    scosti = [0.0] + [sg * 0.2 * k for k in (1, 2, 3) for sg in (1, -1)]
    dist, sh, meglio = (possibili(0.0)[0] if possibili(0.0) else None), 0.0, None
    contro = a.get("tavolo_contro_vano"); prove_ = None
    if contro:
        # tavolo addossato al muro in comune con un altro vano (scelta di chi arreda): lato lungo sul muro, sedie sul lato libero
        # e alle teste, nel tratto più lontano dalle porte interne. Parete TV, divano e tavolino si spostano lungo il loro muro
        # di quanto basta per lasciargli posto
        vicini = [x for x in vani if x["villa"] == villa and x is not v and x["nome"].startswith(contro) and x["pol"].distance(v["pol"]) < 0.45]
        def pezzi(g): return [t for t in ([g] if g.geom_type == "LineString" else getattr(g, "geoms", [])) if t.geom_type == "LineString"]
        tratti = [t for x in vicini for t in pezzi(v["pol"].simplify(0.05).exterior.intersection(x["pol"].buffer(0.45)))]
        if tratti:
            tr = max(tratti, key=lambda t: t.length); pa_, pb_ = Vector(tr.coords[0]), Vector(tr.coords[-1]); w = (pb_ - pa_).normalized()
            n = Vector((-w.y, w.x)); n = n if v["pol"].contains(Point(tuple((pa_ + pb_) / 2 + n * 0.5))) else -n
            def zona_muro(s_): return Polygon([tuple(pa_ + w * (s_ + sa) + n * sb) for sa, sb in ((-lt / 2 - 0.5, 0.02), (lt / 2 + 0.5, 0.02), (lt / 2 + 0.5, 0.05 + 2 * wt + 0.5), (-lt / 2 - 0.5, 0.05 + 2 * wt + 0.5))])
            vietato = unary_union([q.buffer(d_porte) for q in interne] + [q.buffer(0.3) for q in altre] + [o_ for o_ in occupati if not o_.intersects(Polygon([tuple(c + u * su + vv * sv) for su, sv in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))]).buffer(-0.05))])
            cand = [s_ for s_ in [0.05 * k for k in range(int(tr.length / 0.05) + 1)] if v["pol"].buffer(0.02).contains(zona_muro(s_)) and not zona_muro(s_).intersects(vietato)]
            if cand:
                s_ = max(cand, key=lambda s_: (round(min([3.0] + [q.distance(zona_muro(s_)) for q in interne]), 1), -abs(s_ - tr.length / 2)))
                zona = zona_muro(s_); meglio = (0, pa_ + w * s_ + n * (0.03 + wt), w, n, zona, True)
                ud = u if u.dot(n) > 0 else -u; tv0 = Polygon([tuple(c + u * su + vv * sv) for su, sv in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))]); c0 = c.copy(); mossa = None
                for k in range(40):
                    c = c0 + ud * 0.1 * k; tvk = Polygon([tuple(q + ud * 0.1 * k) for q in map(Vector, tv0.exterior.coords[:-1])])
                    if not v["pol"].buffer(0.06).contains(tvk): break
                    dd = next((d for d in possibili(0.0) if not divano_a(d).buffer(0.15).intersects(zona) and not zona_tv(d).intersects(zona)), None)
                    if dd and not tvk.intersects(zona.buffer(0.1)): mossa = (0.1 * k, dd); break
                if mossa:
                    dist, sh = mossa[1], 0.0
                    for o_ in ARR.objects:
                        if o_.name.startswith(nome_tv):
                            o_.location.x += ud.x * mossa[0]; o_.location.y += ud.y * mossa[0]
                            o_["ingombro"] = [c_ for q in tv0.exterior.coords[:-1] for c_ in (q[0] + ud.x * mossa[0], q[1] + ud.y * mossa[0])]
                    log(f"zona giorno villa {villa}: tavolo contro il muro verso {vicini[0]['nome']}; parete TV, divano e tavolino spostati di {mossa[0]:.1f} m; divano a {dist:.1f} m dalla TV")
                    prove_ = []
                else: c = c0; meglio = None; log(f"AVVISO villa {villa}: con il tavolo contro il muro verso {contro} parete TV e divano non trovano posto; tavolo con le regole generali")
        if prove_ is None and not meglio: log(f"AVVISO villa {villa}: nessun tratto di muro libero verso {contro}; tavolo con le regole generali")
    # passaggio libero davanti alle porte: quello chiesto davanti alle porte interne (verso disimpegno e cucina), che non si
    # tocca finché c'è un'altra soluzione; davanti alle portefinestre si riduce via via finché il tavolo trova posto
    prove = [(d_porte, d_porte - 0.1 * k) for k in range(int(round((d_porte - 0.1) / 0.1)) + 1)] + [(d_porte - 0.1 * k, 0.1) for k in range(1, 5)]
    for di, dp in (prove if prove_ is None else prove_):
        stato["chiave"] = (di, dp); stato["porte"] = unary_union([q.buffer(di) for q in interne] + [q.buffer(dp) for q in altre]) if sue else Polygon()
        trovato = next(((d, s_) for s_ in scosti for d in possibili(s_) if d >= 2.4 and tavolo_con(d, s_)), None) or next(((d, s_) for s_ in scosti for d in possibili(s_) if tavolo_con(d, s_)), None)
        if trovato:
            dist, sh = trovato; meglio = tavolo_con(dist, sh)
            log(f"zona giorno villa {villa}: divano a {dist:.1f} m dalla TV, scostato di {sh:.1f} m; {di:.1f} m liberi davanti alle porte interne, {dp:.1f} m davanti alle portefinestre"); break
    fatti = []
    if dist:
        cs = c + vv * (W / 2 + dist) + u * sh
        fronte_tv, fronte_div = -W / 2 + 0.45, W / 2 + dist - 0.475          # il tavolino sta a metà tra mobile TV e divano
        ct = c + vv * ((fronte_tv + fronte_div) / 2) + u * sh; pt = min(0.30, max(0.20, (fronte_div - fronte_tv) / 2 - 0.42))
        rt = min(0.42, pt + 0.12)                                             # tavolino tondo
        # divano componibile del riferimento di Andrea (2026-11-16): bouclé avorio, basso e squadrato, cuscini dello schienale
        # sciolti, bracciolo pieno da una parte e chaise longue verso la TV dall'altra, se c'è posto (stanza, tavolo, tavolino)
        tav = meglio[4] if meglio else Polygon(); cerchio = Point(tuple(ct)).buffer(rt + 0.30)
        def chaise(sd):
            a0, a1 = sorted((sd * 1.15, sd * 0.30))
            return Polygon([tuple(cs + u * a_ - vv * b_) for a_, b_ in ((a0, 0.475), (a1, 0.475), (a1, 1.15), (a0, 1.15))])
        lato = next((sd for sd in (1, -1) if v["pol"].buffer(-0.05).contains(chaise(sd)) and not chaise(sd).intersects(tav)
                     and not chaise(sd).intersects(cerchio)), 0)
        p = Pezzo(cs, u, -vv, v["z0"])                                        # il divano guarda la TV: fronte = -vv
        bracci = [-lato] if lato else [1, -1]
        p.scat(-1.10, 1.10, -0.44, 0.42, 0, 0.05, "nero")                                           # zoccolo in ombra
        p.scat(-1.15, 1.15, -0.475, 0.475, 0.05, 0.30, "boucle", "morbido")                          # base
        p.scat(-1.15, 1.15, -0.475, -0.26, 0.30, 0.60, "boucle", "morbido")                          # schienale basso
        for sd in bracci:
            a0, a1 = sorted((sd * 1.15, sd * 0.93)); p.scat(a0, a1, -0.475, 0.475, 0.30, 0.56, "boucle", "morbido")
        sx0 = -0.93 if -1 in bracci else -1.15; sx1 = 0.93 if 1 in bracci else 1.15
        if lato:
            a0, a1 = sorted((lato * 1.15, lato * 0.30))
            p.scat(a0 + 0.03, a1 - 0.03, 0.42, 1.10, 0, 0.05, "nero")
            p.scat(a0, a1, 0.475, 1.15, 0.05, 0.30, "boucle", "morbido")
        # cuscini gonfiati come tessuti veri (ricette_arredo.divano, la stessa del banco di prova): sedute, chaise, schienali,
        # decorativi a bordo cucito che si appoggiano con la gravita' (2026-11-17)
        R_div = {"tipo": "divano", "villa": villa, "cs": list(cs[:2]), "u": list(u[:2]), "vv": list(vv[:2]), "sx0": sx0, "sx1": sx1,
                 "lato": lato, "a0": a0 if lato else None, "a1": a1 if lato else None, "cz": v["z0"]}
        cus_ob, righe = ricette_arredo.divano(scn, R_div)
        for r_ in righe: log(r_)
        for ob in cus_ob:
            for c_ in list(ob.users_collection): c_.objects.unlink(ob)
            ARR.objects.link(ob); ob["villa"] = villa; ob["arredo"] = "divano"; ob["ingombro"] = []
        ing = Polygon([tuple(cs + u * su - vv * sv) for su, sv in ((-1.15, -0.475), (1.15, -0.475), (1.15, 0.475), (-1.15, 0.475))])
        if lato: ing = unary_union([ing, chaise(lato)])
        if ing.geom_type != "Polygon": ing = ing.convex_hull
        p.fine(f"Divano v{villa}", villa, "divano", ing); fatti.append(ing)
        if bpy.data.objects.get(f"Divano v{villa}"): bpy.data.objects[f"Divano v{villa}"]["ricetta"] = json.dumps(R_div)
        log(f"divano villa {villa}: " + (f"chaise longue dal lato {'+' if lato > 0 else '-'}" if lato else "senza chaise longue, non c'è posto"))
        # tavolino tondo in rovere su un piede pieno (riferimento del divano)
        p = Pezzo(ct, u, vv, v["z0"])
        p.scat(-1.4, 1.4, -0.95, 0.95, 0, 0.012, "tappeto")
        p.cil(0, 0, rt, rt, 0.33, 0.38, "rovere", seg=48); p.cil(0, 0, rt * 0.62, rt * 0.62, 0.012, 0.33, "rovere", seg=40)
        ing = Point(tuple(ct)).buffer(rt, 16)
        p.fine(f"Tavolino e tappeto v{villa}", villa, "tavolino", ing); fatti.append(ing)
    else: log(f"AVVISO villa {villa}: il divano non entra di fronte alla parete TV")
    if meglio:
        _, q, asse, pa, zona = meglio[:5]; al_muro = len(meglio) > 5; p = Pezzo(q, asse, pa, v["z0"])
        # tavolo del riferimento di Andrea (2026-11-16): piano in rovere spesso 6 cm su un blocco pieno in rovere, arretrato
        # dai bordi quanto serve alle ginocchia (30 cm sui lati lunghi liberi, 25 cm alle teste)
        p.scat(-lt / 2, lt / 2, -wt, wt, 0.70, 0.76, "rovere")
        bv0 = -wt + (0.06 if al_muro else 0.18); p.scat(-lt / 2 + 0.25, lt / 2 - 0.25, bv0, wt - 0.18, 0, 0.70, "rovere")
        lato = (n_p - 2 if al_muro else n_p // 2); passo_s = lt / lato
        for i in range(lato):
            cu = -lt / 2 + passo_s * (i + 0.5); sedia_pranzo(p, (cu, wt + 0.20), (0, -1))
            if not al_muro: sedia_pranzo(p, (cu, -wt - 0.20), (0, 1))
        if al_muro: sedia_pranzo(p, (lt / 2 + 0.20, 0), (-1, 0)); sedia_pranzo(p, (-lt / 2 - 0.20, 0), (1, 0))
        p.fine(f"Tavolo da {n_p} v{villa}", villa, "tavolo", zona.buffer(-0.2) if not al_muro else zona.buffer(-0.12))
    else: log(f"AVVISO villa {villa}: nessun posto libero per il tavolo da {n_p}")
    return bool(dist), bool(meglio)

# ------------------------------------------------------------------------------------------------ pezzi
# ------------------------------------------------------------------------------------------------ pezzi del 2026-11-17 sera
# Riferimenti di Andrea in modello/riferimenti_arredo/: mobile_tv.jpg, sospensione_camere.webp, abatjour_travertino.jpg,
# sospensioni_letto_vetro.jpg, bagno.jpg. Solo nelle ville arredate.
def _contorno_tondo(L, W, sl, R):
    """rettangolo L × W (fronte a +W/2) con l'angolo fronte-estremo sl (±1) arrotondato di raggio R: punti in senso antiorario."""
    from shapely.geometry import box as sbox
    from shapely.geometry.polygon import orient
    cx, cy = sl * (L / 2 - R), W / 2 - R
    angolo = sbox(cx if sl > 0 else -L / 2, cy, L / 2 if sl > 0 else cx, W / 2)
    pol = sbox(-L / 2, -W / 2, L / 2, W / 2).difference(angolo).union(Point(cx, cy).buffer(R, 24).intersection(angolo))
    return orient(pol.simplify(0.0005), 1.0)

def _prismi(p, pol, z0, z1, k, tipo="tondo"):
    """prisma di un poligono convesso (shapely, coordinate del pezzo)."""
    from shapely.geometry.polygon import orient
    if pol.is_empty: return
    for g in ([pol] if pol.geom_type == "Polygon" else list(pol.geoms)):
        if g.area < 1e-6: continue
        p.poli(list(orient(g, 1.0).exterior.coords)[:-1], z0, z1, k, tipo)

def madia_tv_curva(p, L, W, v):
    """mobile TV della camera matrimoniale (riferimento mobile_tv.jpg, 2026-11-17): cassettiera bassa laccata greige opaca,
    due colonne per tre file di cassetti senza maniglie, fughe sottili scure, zoccolo arretrato in ombra; un capo ha l'angolo sul
    fronte arrotondato (le file girano attorno alla curva). Andrea, 2026-11-17 sera: la curva dal lato della porta d'ingresso,
    il capo dritto allungato fino al muro (lato del comodino), 10 cm meno profondo (il retro resta al muro), la TV appesa al muro
    con lo schermo lucido. Alto 0,76 m come prima."""
    from shapely.geometry import box as sbox
    from shapely import affinity
    # capo con la curva: quello più vicino a una porta della stanza
    def d_porta(sgn):
        q = Point(*p.P(sgn * L / 2, 0)); return min([r_.distance(q) for r_ in porte_ if r_.distance(q) < 2.5] or [9.0])
    sl = 1 if d_porta(1) <= d_porta(-1) else -1
    # capo dritto fino al muro: distanza dal capo al bordo del vano lungo l'asse del mobile (a metà profondità)
    q0 = Vector(p.P(-sl * L / 2, -W / 2 + 0.2)); dirz = Vector(p.P(-sl, 0)) - Vector(p.P(0, 0)); dirz.normalize()
    raggio = LineString([tuple(q0), tuple(q0 + dirz * 3.0)]); x_ = raggio.intersection(v["pol"].buffer(-0.012, join_style=2).exterior)
    pts_ = [Vector(g.coords[0]) for g in ([x_] if x_.geom_type == "Point" else getattr(x_, "geoms", [])) if g.geom_type == "Point"]
    allunga = min(((q - q0).length for q in pts_), default=0.0)
    if allunga > 1.2: allunga = 0.0                                     # nessun muro vicino: resta com'era
    W2 = W - 0.10; a0, a1 = (-L / 2, L / 2 + allunga) if sl < 0 else (-L / 2 - allunga, L / 2); ac, bc = (a0 + a1) / 2, -W / 2 + W2 / 2
    L2 = a1 - a0; R = min(0.24, W2 * 0.45, L2 * 0.25); g = 0.004
    pol = affinity.translate(_contorno_tondo(L2, W2, sl, R), ac, bc)
    _prismi(p, pol.buffer(-0.045, join_style=2), 0.0, 0.06, "nero", "duro")                    # zoccolo arretrato
    _prismi(p, pol.buffer(-0.012, join_style=2), 0.06, 0.755, "nero")                          # anima scura dietro le fughe (sotto il piano)
    file_ = [(0.06, 0.33), (0.33 + g, 0.60), (0.60 + g, 0.76)]                                 # cassetti: due alti, uno basso in cima
    for z0_, z1_ in file_:
        for meta in (sbox(-9, -9, ac - g / 2, 9), sbox(ac + g / 2, -9, 9, 9)):
            _prismi(p, pol.intersection(meta), z0_, z1_, "laccato_tv")
    # TV da 55" appesa al muro sopra il mobile: cornice sottile nera e schermo nero lucido
    wt, ht, zt = 1.23, 0.71, 1.02; bw = -W / 2
    p.scat(ac - wt / 2, ac + wt / 2, bw + 0.004, bw + 0.034, zt, zt + ht, "nero")
    p.scat(ac - wt / 2 + 0.008, ac + wt / 2 - 0.008, bw + 0.034, bw + 0.036, zt + 0.008, zt + ht - 0.008, "schermo")
    log(f"mobile TV della matrimoniale: lungo {L2:.2f} m (allungato di {allunga:.2f} fino al muro), profondo {W2:.2f}, curva dal lato {'+' if sl > 0 else '-'}")

def sospensione_camera(p, zb, zs):
    """sospensione delle camere (riferimento sospensione_camere.webp, 2026-11-17): tre paralumi metallici neri opachi a cupola,
    bianchi dentro, sovrapposti (grande 40 cm in alto, medio, piccolo cilindrico in basso), cannotto nero, cavo e rosone neri."""
    t = 0.003
    def cupola(r0, r1, z0, z1, esp, n=10):
        est = [(r0 + (r1 - r0) * i / n, z0 - (z0 - z1) * (i / n) ** esp) for i in range(n + 1)]
        inn = [(r, z - t) for r, z in reversed(est)]
        prof = est + inn; ks = ["nero"] * n + ["nero"] + ["interno_bianco"] * n + ["nero"]
        p.tornio(0, 0, [(r, zb + z) for r, z in prof], ks, seg=64)
    cupola(0.035, 0.200, 0.215, 0.120, 1.7)              # grande
    cupola(0.040, 0.135, 0.150, 0.070, 1.5)              # medio
    cupola(0.068, 0.082, 0.072, 0.000, 1.0, n=4)         # piccolo, quasi cilindrico
    p.tornio(0, 0, [(0.004, zb + 0.20), (0.030, zb + 0.20), (0.030, zb + 0.33), (0.004, zb + 0.33)], "nero", seg=32)   # cannotto
    p.tornio(0, 0, [(0.004, zb + 0.085), (0.028, zb + 0.085), (0.028, zb + 0.125), (0.004, zb + 0.125)], "lampadina", seg=24)
    p.cil(0, 0, 0.002, 0.002, zb + 0.33, zs - 0.015, "nero", seg=8); p.cil(0, 0, 0.05, 0.05, zs - 0.02, zs, "nero", seg=32)
    return zb + 0.10                                      # quota della luce, sotto il paralume grande

def abatjour_travertino(p, a, b, z):
    """abat-jour del riferimento abatjour_travertino.jpg (2026-11-17): fusto cilindrico in travertino (Ø 11, alto 22 cm),
    paralume a tamburo in lino chiaro (Ø 29, alto 15) che di sera si accende, cappello in travertino. Restituisce la quota della luce."""
    p.tornio(a, b, [(0.004, z), (0.055, z), (0.055, z + 0.22), (0.004, z + 0.22)], "travertino", seg=40)
    p.tornio(a, b, [(0.142, z + 0.155), (0.145, z + 0.155), (0.145, z + 0.305), (0.142, z + 0.305)], "paralume", seg=64)
    p.tornio(a, b, [(0.004, z + 0.295), (0.045, z + 0.295), (0.045, z + 0.32), (0.004, z + 0.32)], "travertino", seg=40)
    return z + 0.23

def globo_vetro(p, a, b, zc, R, zs):
    """sospensione piccola del riferimento sospensioni_letto_vetro.jpg (2026-11-17): globo in vetro fumé con la lampadina
    dentro, cannotto nero lungo sopra il globo, cavo e rosone neri."""
    t = 0.003; n = 16; f0, f1 = 0.16 * math.pi, 0.985 * math.pi
    est = [(R * math.sin(f0 + (f1 - f0) * i / n), zc + R * math.cos(f0 + (f1 - f0) * i / n)) for i in range(n + 1)]
    inn = [((R - t) * math.sin(f0 + (f1 - f0) * i / n), zc + (R - t) * math.cos(f0 + (f1 - f0) * i / n)) for i in reversed(range(n + 1))]
    p.tornio(a, b, est + inn, "vetro_globo", seg=48)        # fumé chiaro: con il vetro dell'armadio era un disco scuro in Unreal
    p.tornio(a, b, [(0.004, zc - 0.022), (0.016, zc - 0.012), (0.018, zc + 0.012), (0.004, zc + 0.03)], "lampadina", seg=24)
    zt = zc + R * math.cos(f0)
    p.tornio(a, b, [(0.003, zt - 0.01), (0.011, zt - 0.01), (0.011, zt + 0.13), (0.003, zt + 0.13)], "nero", seg=24)   # cannotto
    p.cil(a, b, 0.0016, 0.0016, zt + 0.13, zs - 0.012, "nero", seg=6); p.cil(a, b, 0.035, 0.035, zs - 0.012, zs, "nero", seg=24)

LUCI_SPECCHIO = []    # LED sotto gli specchi dei bagni: (punto, asse lungo, larghezza, quota, villa, vano)
def lavabo(p, L, W, v, villa, nome):
    """mobile del bagno (riferimento bagno.jpg, 2026-11-17) al posto del lavabo IFC: cassettone sospeso in noce scuro a fibra
    verticale fine con due frontali senza maniglia, piano spesso in pietra beige, catino tondo da appoggio opaco, rubinetto a
    parete in bronzo scuro con la leva a parte, specchio con cornice scura sottile e LED dietro il bordo basso.
    Ingombro del lavabo IFC (90 × 45 cm); il catino sta sul lato destro guardando il muro, come nella foto."""
    zp = 0.855; bw = -W / 2                                             # piano; muro
    p.scat(-L / 2 + 0.005, L / 2 - 0.005, bw, W / 2 - 0.02, 0.40, 0.80, "noce")
    sa = -L / 2 + 0.62 * L
    for u0, u1 in ((-L / 2 + 0.006, sa - 0.0015), (sa + 0.0015, L / 2 - 0.006)):
        p.scat(u0, u1, W / 2 - 0.02, W / 2, 0.402, 0.798, "noce")
    p.scat(-L / 2 + 0.03, L / 2 - 0.03, bw, W / 2 - 0.05, 0.80, 0.806, "nero")                 # ombra sotto il piano
    p.scat(-L / 2 - 0.01, L / 2 + 0.01, bw, W / 2 + 0.025, 0.806, zp, "piano_bagno")
    # catino dal lato della doccia (Andrea, 2026-11-17: "il lavabo più vicino alla doccia, il mobile specchiato")
    lato_d = 1.0
    for ob_d in scn.objects:
        if ob_d.get("ifc_classe") != "IfcBuildingElementProxy" or ob_d.type != "MESH" or not ob_d.data.vertices or ob_d.hide_render: continue
        W_ = [ob_d.matrix_world @ q_.co for q_ in ob_d.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W_]).minimum_rotated_rectangle
        if v["pol"].contains(r_.centroid) and max(w.z for w in W_) - min(w.z for w in W_) >= 1.8 and r_.area >= 0.6:
            lato_d = 1.0 if (Vector(r_.centroid.coords[0]) - p.o).dot(p.u) >= 0 else -1.0
    ab = lato_d * (L / 2 - 0.25) if L > 0.75 else 0.0; bb = 0.015
    cat = [(0.012, zp + 0.002), (0.17, zp + 0.002), (0.193, zp + 0.016), (0.201, zp + 0.075), (0.199, zp + 0.135), (0.193, zp + 0.142),
           (0.187, zp + 0.135), (0.180, zp + 0.085), (0.150, zp + 0.045), (0.080, zp + 0.027), (0.012, zp + 0.024)]
    p.tornio(ab, bb, cat, "catino", seg=64)
    zr = zp + 0.215; w0 = bw + 0.009                                      # rubinetto a parete, sopra il rivestimento
    p.asta(ab, w0, zr, ab, w0 + 0.012, zr, 0.03, 0.03, "rubinetto", seg=24)
    p.asta(ab, w0 + 0.012, zr, ab, w0 + 0.165, zr, 0.011, 0.011, "rubinetto", seg=16)
    p.asta(ab, w0 + 0.160, zr + 0.004, ab, w0 + 0.168, zr - 0.04, 0.011, 0.0095, "rubinetto", seg=16)
    ah = ab - lato_d * 0.14                                               # leva verso il centro del mobile
    p.asta(ah, w0, zr, ah, w0 + 0.012, zr, 0.028, 0.028, "rubinetto", seg=24)
    p.asta(ah, w0 + 0.012, zr, ah, w0 + 0.07, zr - 0.004, 0.006, 0.005, "rubinetto", seg=12)
    # specchio con cornice scura, sotto il soffitto (bagno B: falda a 2,0 m)
    q = Vector(p.P(ab, bw)); zt = min(1.18 + 0.82, soffitto(q.x, q.y, v["z0"] + 1.0) - v["z0"] - 0.10); zb_ = 1.18; wm = 0.62
    # specchio sopra il catino ma dentro la larghezza del mobile: centrato sul catino sporgeva oltre il mobile e toccava il muro
    a0, a1 = max(-L / 2, ab - wm / 2), min(L / 2, ab + wm / 2)
    if a1 - a0 < wm: a0, a1 = (a1 - wm, a1) if lato_d < 0 else (a0, a0 + wm)
    a0, a1 = max(-L / 2, a0), min(L / 2, a1)
    p.scat(a0, a1, w0, w0 + 0.024, zb_, zt, "nero")
    p.scat(a0 + 0.008, a1 - 0.008, w0 + 0.024, w0 + 0.028, zb_ + 0.008, zt - 0.008, "specchio")
    p.scat(a0 + 0.03, a1 - 0.03, w0 + 0.004, w0 + 0.02, zb_ - 0.004, zb_, "led")                  # luce radente sotto lo specchio
    LUCI_SPECCHIO.append((Vector(p.P(ab, w0 + 0.012)), Vector(p.u[:2]), wm - 0.06, v["z0"] + zb_ - 0.01, villa, v["nome"]))

def rubinetto_bidet(ob_b, v, villa, nome):
    """miscelatore monocomando sul bordo del bidet, abbinato al rubinetto del lavabo (bronzo scuro, Andrea 2026-11-17: "manca la
    rubinetteria nel bidet, cerca qualcosa di abbinato"): corpo cilindrico, bocca corta in avanti, leva sottile sopra."""
    W_ = [ob_b.matrix_world @ q_.co for q_ in ob_b.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W_]).minimum_rotated_rectangle
    cc = [Vector(c_) for c_ in list(r_.exterior.coords)[:4]]
    lati = sorted(((cc[k], cc[(k + 1) % 4]) for k in range(4)), key=lambda e: v["pol"].exterior.distance(Point(*((e[0] + e[1]) / 2))))
    a_, b_ = lati[0]; mid = (a_ + b_) / 2; u_ = (b_ - a_).normalized(); n_ = Vector((-u_.y, u_.x))
    if (Vector(r_.centroid.coords[0]) - mid).dot(n_) < 0: n_ = -n_                     # verso il davanti del bidet
    q = mid + n_ * 0.075; zt = max([w.z for w in W_ if (w.xy - q).length < 0.05] or [max(w.z for w in W_)]) - v["z0"]
    p = Pezzo(q, u_, n_, v["z0"])
    p.tornio(0, 0, [(0.004, zt - 0.002), (0.025, zt - 0.002), (0.025, zt + 0.062), (0.021, zt + 0.072), (0.004, zt + 0.074)], "rubinetto", seg=32)
    p.asta(0, 0.0, zt + 0.05, 0, 0.10, zt + 0.045, 0.0085, 0.0078, "rubinetto", seg=16)                # bocca
    p.asta(0, 0.095, zt + 0.047, 0, 0.102, zt + 0.032, 0.008, 0.0075, "rubinetto", seg=16)
    # leva sopra il corpo, rivolta in avanti in posizione neutra (Andrea, 2026-11-17: "la levetta sul davanti")
    p.asta(0, 0.0, zt + 0.074, 0, 0.012, zt + 0.084, 0.010, 0.008, "rubinetto", seg=16)
    p.asta(0, 0.012, zt + 0.084, 0, 0.068, zt + 0.092, 0.0055, 0.0045, "rubinetto", seg=12)
    p.fine(nome, villa, "rubinetto", Point(q.x, q.y).buffer(0.03))
    for o_ in ARR.objects:
        if o_.name.startswith(nome): o_["ingombro"] = []

def _retro(ob_, v):
    """lato del sanitario contro il muro: (centro del lato, asse lungo il muro, verso la stanza, rettangolo)."""
    W_ = [ob_.matrix_world @ q_.co for q_ in ob_.data.vertices]; r_ = MultiPoint([w.xy[:] for w in W_]).minimum_rotated_rectangle
    cc = [Vector(c_) for c_ in list(r_.exterior.coords)[:4]]
    a_, b_ = min(((cc[k], cc[(k + 1) % 4]) for k in range(4)), key=lambda e: v["pol"].exterior.distance(Point(*((e[0] + e[1]) / 2))))
    mid = (a_ + b_) / 2; u_ = (b_ - a_).normalized(); n_ = Vector((-u_.y, u_.x))
    if (Vector(r_.centroid.coords[0]) - mid).dot(n_) < 0: n_ = -n_
    return mid, u_, n_, r_

def accessori_wc(ob_wc, ob_bid, v, villa, nome):
    """accessori del bagno (Andrea, 2026-11-17: "placca dello scarico a muro, portascopino, portarotolo, portasciugamani vicino
    al wc: dettagli che rendano la casa vissuta"), nel bronzo scuro della rubinetteria. Placca sopra il wc; portarotolo e
    portascopino a muro dal lato opposto al bidet (o oltre il bidet se lì non c'è posto); barra con l'asciugamano sopra il bidet.
    A 9 mm dal muro: sopra il rivestimento."""
    mid, u_, n_, r_ = _retro(ob_wc, v); w0 = 0.009
    p = Pezzo(mid, u_, n_, v["z0"])
    p.scat(-0.12, 0.12, w0, w0 + 0.008, 0.98, 1.14, "rubinetto")                                         # placca di scarico
    p.scat(-0.110, -0.003, w0 + 0.008, w0 + 0.011, 0.99, 1.13, "rubinetto"); p.scat(0.003, 0.110, w0 + 0.008, w0 + 0.011, 0.99, 1.13, "rubinetto")
    p.scat(-0.002, 0.002, w0 + 0.008, w0 + 0.010, 0.99, 1.13, "nero")                                   # fessura tra i due tasti
    # lato degli accessori: quello opposto al bidet. Se lì il wc è a ridosso di un muro (meno di 30 cm liberi), portarotolo e
    # portascopino vanno sul muro laterale, a 30 e 15 cm dal muro di fondo (2026-11-17: finivano tra wc e bidet)
    lato = 1.0
    if ob_bid: lato = -1.0 if (_retro(ob_bid, v)[0] - mid).dot(u_) > 0 else 1.0
    cen_w = Vector(r_.centroid.coords[0]); raggio = LineString([tuple(cen_w), tuple(cen_w + u_ * lato * 3.0)])
    bordi = [v["pol"].buffer(-0.01, join_style=2).exterior]
    for ob_d in scn.objects:                                              # anche la doccia è un ostacolo (bagno B: era dietro il vetro)
        if ob_d.get("ifc_classe") != "IfcBuildingElementProxy" or ob_d.type != "MESH" or not ob_d.data.vertices or ob_d.hide_render: continue
        W_ = [ob_d.matrix_world @ q_.co for q_ in ob_d.data.vertices]; rd = MultiPoint([w.xy[:] for w in W_]).minimum_rotated_rectangle
        if v["pol"].contains(rd.centroid) and max(w.z for w in W_) - min(w.z for w in W_) >= 1.8 and rd.area >= 0.6: bordi.append(rd.exterior)
    pts_ = []
    for bd in bordi:
        x_ = raggio.intersection(bd)
        pts_ += [Vector(g_.coords[0]) for g_ in ([x_] if x_.geom_type == "Point" else getattr(x_, "geoms", [])) if g_.geom_type == "Point"]
    dist = min(((q_ - cen_w).length for q_ in pts_), default=3.0); semi = 0.19
    if dist - semi >= 0.30:
        s = lato * min(0.38, semi + (dist - semi) / 2); acc = [(p, s, w0, lato)]           # il rotolo si allunga verso fuori
    else:                                                                 # muro laterale: origine all'angolo, asse lungo il muro
        angolo = cen_w + u_ * lato * (dist - 0.0) - n_ * (cen_w - mid).dot(n_)
        q2 = Pezzo(angolo, n_, -u_ * lato, v["z0"]); acc = [(q2, 0.30, w0, -1.0)]
    for pz, s, w0_, dir_ in acc:
        # portarotolo: rosetta, braccio a L, rotolo di carta
        pz.asta(s, w0_, 0.72, s, w0_ + 0.008, 0.72, 0.022, 0.022, "rubinetto", seg=24)
        pz.asta(s, w0_ + 0.008, 0.72, s, 0.075, 0.72, 0.0055, 0.0055, "rubinetto", seg=12)
        pz.asta(s, 0.075, 0.72, s + dir_ * 0.13, 0.075, 0.72, 0.0055, 0.0055, "rubinetto", seg=12)
        # rotolo vero (2026-11-17: "sembra un cilindro bianco"): carta, anima in cartone e foro ai lati, lembo che pende davanti
        pz.asta(s + dir_ * 0.016, 0.075, 0.72, s + dir_ * 0.114, 0.075, 0.72, 0.055, 0.055, "carta", seg=48)
        for xe in (s + dir_ * 0.0155, s + dir_ * 0.1145):
            pz.asta(xe - dir_ * 0.0004, 0.075, 0.72, xe + dir_ * 0.0004, 0.075, 0.72, 0.022, 0.022, "cartone", seg=32)
            pz.asta(xe - dir_ * 0.0008, 0.075, 0.72, xe + dir_ * 0.0008, 0.075, 0.72, 0.018, 0.018, "nero", seg=32)
        pz.scat(*sorted((s + dir_ * 0.018, s + dir_ * 0.112)), 0.129, 0.1305, 0.62, 0.72, "carta")             # lembo libero
        # portascopino a muro, 15 cm più verso il fondo (o verso il wc): staffa, coppa, manico dello scopino
        sb = s - dir_ * 0.15 if pz is not p else s
        pz.scat(sb - 0.02, sb + 0.02, w0_, w0_ + 0.004, 0.36, 0.46, "rubinetto")
        pz.asta(sb, w0_ + 0.004, 0.42, sb, 0.07, 0.42, 0.006, 0.006, "rubinetto", seg=12)
        pz.tornio(sb, 0.085, [(0.040, 0.30), (0.045, 0.30), (0.045, 0.43), (0.040, 0.43)], "rubinetto", seg=32)
        pz.tornio(sb, 0.085, [(0.004, 0.30), (0.045, 0.30), (0.045, 0.305), (0.004, 0.305)], "rubinetto", seg=32)
        pz.asta(sb, 0.085, 0.43, sb, 0.085, 0.66, 0.007, 0.007, "nero", seg=12); pz.asta(sb, 0.085, 0.43, sb, 0.085, 0.436, 0.034, 0.034, "rubinetto", seg=24)
        if pz is not p:
            pz.fine(nome + " a muro", villa, "accessori_bagno", Point(*pz.P(s, 0.05)).buffer(0.05))
            for o_ in ARR.objects:
                if o_.name.startswith(nome + " a muro"): o_["ingombro"] = []
    p.fine(nome, villa, "accessori_bagno", r_)
    for o_ in ARR.objects:
        if o_.name.startswith(nome): o_["ingombro"] = []
    if ob_bid:                                                            # barra con l'asciugamano sopra il bidet
        mb, ub, nb_, _ = _retro(ob_bid, v); q = Pezzo(mb, ub, nb_, v["z0"]); zb = 0.97; lb = 0.46
        for sx in (-lb / 2, lb / 2): q.asta(sx, w0, zb, sx, 0.06, zb, 0.008, 0.008, "rubinetto", seg=16)
        q.asta(-lb / 2 - 0.01, 0.06, zb, lb / 2 + 0.01, 0.06, zb, 0.009, 0.009, "rubinetto", seg=20)
        nome_b = nome + " barra asciugamano"; q.fine(nome_b, villa, "accessori_bagno", Point(mb.x, mb.y).buffer(0.02))
        for o_ in ARR.objects:
            if o_.name.startswith(nome_b): o_["ingombro"] = []
        cen = Vector((*q.P(0, 0.06), v["z0"] + zb))
        tw = tessili.asciugamano(scn, f"{nome} asciugamano (tessili)", cen, ub, nb_, 0.40, 0.42, 0.36, mat("spugna"), TEX["spugna"][1],
                                 r_barra=0.009, muro=0.06 - w0, seme=len(nome))
        for c_ in list(tw.users_collection): c_.objects.unlink(tw)
        ARR.objects.link(tw); tw["villa"] = villa; tw["arredo"] = "accessori_bagno"; tw["ingombro"] = []

def verso_comodino(c, u, vv, L, W, v, villa, anello):
    """il comodino guarda dove guarda il letto accanto, nella stessa stanza (dalla testata ai piedi). Senza un letto entro
    1,5 m resta com'è."""
    letti = [q for q in POSATI if q["tipo"] == "letto" and q["villa"] == villa and q.get("verso") and v["pol"].contains(Point(q["centro_m"][:2]))]
    if not letti: return c, u, vv, L, W
    b = min(letti, key=lambda q: (Vector(q["centro_m"][:2]) - c).length)
    if Polygon(anello).distance(Point(b["centro_m"][:2])) > max(b["misure_m"][:2]) / 2 + 1.5: return c, u, vv, L, W
    f = -Vector(b["verso"]).normalized(); u2 = Vector((-f.y, f.x)); pts = [Vector(q) for q in Polygon(anello).exterior.coords]
    aa = [(q - c).dot(u2) for q in pts]; bb = [(q - c).dot(f) for q in pts]
    c2 = c + u2 * (min(aa) + max(aa)) / 2 + f * (min(bb) + max(bb)) / 2
    return c2, u2, f, max(aa) - min(aa), max(bb) - min(bb)

conta = {}; tele_tv = {}
LED_TESTATE = []   # LED sopra le testate: (punto, asse lungo la testata, lunghezza, quota del pavimento, nome, villa, vano)
SOSP_LETTO = []  # sospensioni sottili accanto al letto matrimoniale: (centro del comodino, assi, vano, villa, nome)
ABAT = []      # abat-jour dei comodini: (punto in pianta, quota del pavimento, nome del comodino, villa, vano)
for a in sorted(A["arredi"], key=lambda a: a.get("tipo") == "comodino"):     # i comodini dopo i letti: ne prendono il verso
    if not a.get("anello"): continue
    villa = int(a.get("villa", 1)); pol = Polygon(a["anello"]); v = vano_di(villa, pol.representative_point().coords[0])
    if v is None: log("AVVISO: fuori da ogni vano:", a["tipo"], a.get("vano")); continue
    t = a["tipo"]; conta[t] = conta.get(t, 0) + 1; nome = f"{t} {v['nome']} v{villa} {conta[t]}"
    if t == "cucina": cucina(nome, a["anello"], v, villa); continue
    c, u, vv, L, W = telaio(a["anello"], v)
    if t == "comodino": c, u, vv, L, W = verso_comodino(c, u, vv, L, W, v, villa, a["anello"])
    p = Pezzo(c, u, vv, v["z0"])
    if t == "armadio": armadio(p, L, W, h_armadio(p, L, W, v, nome), vetro=v["nome"].startswith("Camera Matrimoniale"))
    elif t == "letto":
        letto(p, L, W, v, c, u, villa); s_, hw_ = p.testata
        LED_TESTATE.append((Vector(p.P(s_ * (-L / 2 + 0.01), 0)), Vector(p.P(0, 1)) - Vector(p.P(0, 0)), 2 * hw_, v["z0"], nome, villa, v["nome"]))
    elif t == "comodino":
        # ville arredate (Andrea, 2026-11-17 sera): abat-jour in travertino con il tamburo in lino sui comodini delle camere
        # singole e sul comodino di sinistra della matrimoniale; sopra quello di destra due globi in vetro fumé appesi
        arr = villa in {int(x.get("villa", 1)) for x in A["arredi"]}
        globi = arr and v["nome"].startswith("Camera Matrimoniale") and lato_destro(c, villa, v)
        comodino(p, L, W, lume=not arr)
        if not arr: ABAT.append((Vector(p.P(0, -0.05)), v["z0"], nome, villa, v["nome"], 0.72))
        elif not globi: ABAT.append((Vector(p.P(0, -0.05)), v["z0"], nome, villa, v["nome"], abatjour_travertino(p, 0, -0.05, 0.46)))
        else: SOSP_LETTO.append((Vector(c), Vector(u), Vector(vv), v, villa, nome))
    elif t == "madia_tv":
        if v["nome"].startswith("Camera Matrimoniale") and villa in {int(x.get("villa", 1)) for x in A["arredi"]}: madia_tv_curva(p, L, W, v)
        else: madia_tv(p, L, W)
    elif t == "accessori_wc":
        ob_w = bpy.data.objects.get(a.get("su", "")); ob_b = bpy.data.objects.get(a.get("bidet", ""))
        if ob_w: accessori_wc(ob_w, ob_b, v, villa, nome)
        else: log(f"AVVISO {nome}: non trovo il wc {a.get('su')}")
        continue
    elif t == "rubinetto_bidet":
        ob_b = bpy.data.objects.get(a.get("su", ""))
        if ob_b: rubinetto_bidet(ob_b, v, villa, nome)
        else: log(f"AVVISO {nome}: non trovo il bidet {a.get('su')}")
        continue
    elif t == "lavabo":
        # mobile del bagno al posto del lavabo IFC ("sostituisce" in arredi.json): il blocco IFC resta nel file ma nascosto
        for nome_s in ([a["sostituisce"]] if isinstance(a.get("sostituisce"), str) else a.get("sostituisce", [])):
            ob_s = bpy.data.objects.get(nome_s)
            if ob_s: ob_s.hide_render = True; ob_s.hide_viewport = True; ob_s["sostituita"] = True
            else: log(f"AVVISO {nome}: non trovo {nome_s} da sostituire")
        lavabo(p, L, W, v, villa, nome)
    elif t == "scrivania": scrivania(p, L, W)
    elif t == "parete_tv": parete_tv(p, L, W); tele_tv[(villa, v["nome"])] = (c, u, vv, L, W, nome)
    else: log("AVVISO: tipo non previsto:", t); continue
    p.fine(nome, villa, t, pol)
    if t == "letto": tessili_letto(p, v, villa, nome)
    if t == "armadio" and getattr(p, "camicie", None):
        ga_, gb_, fr_, H_ = p.luce_interna
        R = {"tipo": "armadio", "nome": nome, "villa": villa, "o": list(p.o[:2]), "u": list(p.u[:2]), "v": list(p.v[:2]), "z0": v["z0"],
             "za": p.za, "posti": p.camicie, "ga": ga_, "gb": gb_, "W": W, "fr": fr_}
        if bpy.data.objects.get(nome): bpy.data.objects[nome]["ricetta"] = json.dumps(R)
        fatti_, righe_ = ricette_arredo.armadio(scn, R)
        for r_ in righe_: log(r_)
        for ob in fatti_:
            for c_ in list(ob.users_collection): c_.objects.unlink(ob)
            ARR.objects.link(ob); ob["villa"] = villa; ob["arredo"] = "armadio"; ob["ingombro"] = []
    if t == "armadio" and getattr(p, "luce_interna", None):
        ga, gb, fr, H_ = p.luce_interna; q = Vector(p.P((ga + gb) / 2, (fr - W / 2) / 2))
        ld = bpy.data.lights.new("Luce interna " + nome, "AREA"); ld.shape = "RECTANGLE"; ld.size = gb - ga - 0.06; ld.size_y = W - 0.12
        ld.energy = 25.0; ld.color = (1.0, 0.82, 0.62)
        lo = bpy.data.objects.new("Luce interna " + nome, ld); lo.location = (q.x, q.y, v["z0"] + H_ - 0.04)
        lo.rotation_euler = (0, 0, math.atan2(p.u.y, p.u.x)); lo.visible_camera = False; lo.visible_glossy = False
        ARR.objects.link(lo); lo["villa"] = villa; lo["punto_luce"] = v["nome"]
for a in A["arredi"]:
    if a["tipo"] != "zona_giorno": continue
    villa = int(a.get("villa", 1)); chiave = next((k for k in tele_tv if k[0] == villa and k[1].startswith(a["vano"])), None)
    if not chiave: log("AVVISO: zona giorno senza parete TV in", a["vano"]); continue
    v = next((x for x in vani if x["villa"] == villa and x["nome"] == chiave[1] and x["pol"].contains(Point(tele_tv[chiave][0]))), None)
    if v is None: log("AVVISO: parete TV fuori dal vano", chiave[1]); continue
    ok = zona_giorno(a, v, villa, tele_tv[chiave]); conta["zona_giorno"] = conta.get("zona_giorno", 0) + 1
    log("zona giorno villa", villa, "| divano", ok[0], "| tavolo", ok[1])
# ------------------------------------------------------------------------------------------------ punti luce
# Una sospensione al centro di ogni stanza; in zona giorno una sul tavolo e una sul tavolino; in cucina anche la luce sotto i
# pensili. Niente nei vani con controsoffitto (hanno i faretti). La potenza totale di ogni stanza è w_m2 × superficie:
# percorsi_camera.py non aggiunge la sua luce dove trova questi punti luce.
LU = {"w_m2": 14.0, "colore": [1.0, 0.86, 0.70], "esterni": ["Cortile", "Balcone", "Veranda", "Terrazza", "Portico", "Giardino"], **A.get("luci", {})}
ribassati = [Polygon(list(zip(list(o_["controsoffitto_anello"])[0::2], list(o_["controsoffitto_anello"])[1::2]))) for o_ in scn.objects if "controsoffitto_anello" in o_]
n_luci = 0
VILLE_ARREDATE = {int(a.get("villa", 1)) for a in A["arredi"]}
def ciottolo(p, zb, zs, R, seme):
    """lampadario a ciottolo del riferimento di Andrea (2026-11-16): guscio di gesso irregolare, largo 2R, alto circa 0,6R,
    aperto sotto con il bordo inclinato e l'interno che si accende caldo; cavo sottile chiaro fino al soffitto."""
    nt, nf = 24, 8                            # gabbia: la suddivisione la rende liscia
    def forma(t, f, k):                       # punto della superficie: azimut t, angolo dalla cima f; k = 1 fuori, 0,94 dentro
        r = R * (1 + 0.16 * math.cos(2 * t + seme) + 0.08 * math.cos(3 * t + 2 * seme) + 0.04 * math.cos(5 * t + seme)) * k
        gonfio = 1 + 0.18 * math.sin(f) * math.cos(t - seme)                   # più pieno da un lato: forma di ciottolo
        z = 0.85 * R * math.cos(f) * (1 if k == 1 else 0.94) + 0.10 * R * math.sin(f) ** 2 * math.cos(t + 0.5 * seme)
        return (r * gonfio * math.sin(f) * math.cos(t), r * 0.80 * math.sin(f) * math.sin(t), z)
    fmax = [math.radians(112 + 24 * math.cos(2 * math.pi * i / nt - seme)) for i in range(nt)]   # apertura storta
    def anello(k, j): return [forma(2 * math.pi * i / nt, fmax[i] * j / nf, k) for i in range(nt)]
    zmin = min(forma(2 * math.pi * i / nt, fmax[i], 1)[2] for i in range(nt)); dz = zb - zmin
    # una sola maglia: esterno (gesso), bordo (gesso) e interno (caldo), uniti al bordo perché la suddivisione non apra fessure
    pts, fac, mats = [], [], []
    for k in (1.0, 0.94):
        pts += [(0.0, 0.0, 0.85 * R * (1 if k == 1 else 0.94) + dz)] + [(a, b, z + dz) for j in range(1, nf + 1) for a, b, z in anello(k, j)]
    off = 1 + nf * nt                                       # primo punto dell'interno
    for k, o0, mat_ in ((1.0, 0, "gesso"), (0.94, off, "lume_dentro")):
        for i in range(nt):
            fac.append((o0, o0 + 1 + (i + 1) % nt, o0 + 1 + i) if k == 1 else (o0, o0 + 1 + i, o0 + 1 + (i + 1) % nt)); mats.append(mat_)
        for j in range(nf - 1):
            for i in range(nt):
                a_, b_ = o0 + 1 + j * nt + i, o0 + 1 + j * nt + (i + 1) % nt; c_, d_ = a_ + nt, b_ + nt
                fac.append((a_, b_, d_, c_) if k == 1 else (a_, c_, d_, b_)); mats.append(mat_)
    base, dentro = 1 + (nf - 1) * nt, off + 1 + (nf - 1) * nt
    for i in range(nt): fac.append((base + i, base + (i + 1) % nt, dentro + (i + 1) % nt, dentro + i)); mats.append("gesso")
    p.grezzo(pts, fac, mats, "liscio")
    p.cil(0, 0, 0.003, 0.003, 0.85 * R + dz, zs - 0.02, "intonaco", seg=8); p.cil(0, 0, 0.04, 0.04, zs - 0.02, zs, "intonaco")
    return zb + 0.10                          # quota della luce, dentro il guscio

def sospensione(v, villa, q, z_sotto, nome_l, watt, raggio=0.19):
    """paralume a campana appeso al soffitto con il bordo inferiore a z_sotto dal pavimento, e la sua luce. In soggiorno
    lampadari a ciottolo (Andrea, 2026-11-16)."""
    global n_luci
    zs = soffitto(q.x, q.y, v["z0"] + 1.9) - v["z0"]; p = Pezzo(q, Vector((1, 0)), Vector((0, 1)), v["z0"])
    if v["nome"].startswith("Camera") and villa in VILLE_ARREDATE:
        # camere: sospensione a tre paralumi neri (Andrea, 2026-11-17 sera, al posto della plafoniera in rattan di libreria che
        # di sera faceva ombre brutte); tipo "lampada_camera": sostituisci_arredi.py non la scambia
        zb_ = min(z_sotto, zs - 0.55); z_luce = sospensione_camera(p, zb_, zs)
        p.fine(nome_l, villa, "lampada_camera", Point(q.x, q.y).buffer(0.01))
        for o_ in ARR.objects:
            if o_.name.startswith(nome_l): o_["ingombro"] = []
        ld = bpy.data.lights.new(nome_l, "POINT"); ld.energy = watt; ld.color = LU["colore"]; ld.shadow_soft_size = 0.05
        lo = bpy.data.objects.new("Luce " + nome_l, ld); lo.location = (q.x, q.y, v["z0"] + z_luce); ARR.objects.link(lo)
        lo["villa"] = villa; lo["punto_luce"] = v["nome"]; n_luci += 1
        return
    if v["nome"].startswith("Soggiorno") and villa in VILLE_ARREDATE:      # le ville non arredate restano com'erano
        k_ = int(nome_l.split()[-1]); z_luce = ciottolo(p, z_sotto, zs, 0.30 if k_ == 1 else 0.24, 0.7 + 1.9 * k_)
        p.rilievo = (0.010, 0.012)                                 # gesso grezzo, come nel riferimento
        p.fine(nome_l, villa, "lampada", Point(q.x, q.y).buffer(0.01))
        for o_ in ARR.objects:
            if o_.name.startswith(nome_l): o_["ingombro"] = []
        ld = bpy.data.lights.new(nome_l, "POINT"); ld.energy = watt; ld.color = (1.0, 0.62, 0.30); ld.shadow_soft_size = 0.08
        lo = bpy.data.objects.new("Luce " + nome_l, ld); lo.location = (q.x, q.y, v["z0"] + z_luce); ARR.objects.link(lo)
        lo["villa"] = villa; lo["punto_luce"] = v["nome"]; n_luci += 1
        return
    p.cil(0, 0, 0.05, 0.05, zs - 0.025, zs, "laccato"); p.cil(0, 0, 0.003, 0.003, z_sotto + 0.2, zs - 0.02, "metallo", seg=8)
    p.cil(0, 0, raggio, raggio * 0.28, z_sotto, z_sotto + 0.2, "tessuto"); p.cil(0, 0, 0.035, 0.035, z_sotto + 0.03, z_sotto + 0.11, "lampadina")
    p.fine(nome_l, villa, "lampada", Point(q.x, q.y).buffer(0.01))
    for o_ in ARR.objects:
        if o_.name.startswith(nome_l): o_["ingombro"] = []                      # appesa: non ingombra il pavimento
    ld = bpy.data.lights.new(nome_l, "POINT"); ld.energy = watt; ld.color = LU["colore"]; ld.shadow_soft_size = 0.06
    lo = bpy.data.objects.new("Luce " + nome_l, ld); lo.location = (q.x, q.y, v["z0"] + z_sotto - 0.03); ARR.objects.link(lo)
    lo["villa"] = villa; lo["punto_luce"] = v["nome"]; n_luci += 1
ST["lampadina"] = "#FFF0D8"; RUV["lampadina"] = 0.5
for v in vani:
    c_ = v["pol"].representative_point()
    if v["nome"].startswith(tuple(LU["esterni"])) or any(q.contains(c_) for q in ribassati): continue
    villa = v["villa"]; watt = LU["w_m2"] * v["pol"].area; qui = [o_ for o_ in ARR.objects if o_.get("villa") == villa and len(o_.get("ingombro", [])) >= 6 and "(tessili)" not in o_.name and "(liscio)" not in o_.name and "(tondo)" not in o_.name
                                                               and v["pol"].contains(Point(sum(list(o_["ingombro"])[0::2]) / (len(o_["ingombro"]) / 2), sum(list(o_["ingombro"])[1::2]) / (len(o_["ingombro"]) / 2)))]
    def centro_di(o_): i_ = list(o_["ingombro"]); return Vector((sum(i_[0::2]) / (len(i_) / 2), sum(i_[1::2]) / (len(i_) / 2)))
    punti = [(centro_di(o_), 1.50, 0.22) for o_ in qui if o_["arredo"] == "tavolo"] + [(centro_di(o_), 2.05, 0.19) for o_ in qui if o_["arredo"] == "tavolino"]
    if not punti:                                             # centro della parte libera della stanza
        lib_ = v["pol"].difference(unary_union([Polygon(list(zip(list(o_["ingombro"])[0::2], list(o_["ingombro"])[1::2]))).buffer(0) for o_ in qui] or [Polygon()]))
        lib_ = max(([lib_] if lib_.geom_type == "Polygon" else list(lib_.geoms)), key=lambda g: g.area); cc = lib_.centroid if lib_.contains(lib_.centroid) else lib_.representative_point()
        punti = [(Vector((cc.x, cc.y)), 2.10, 0.19)]
    cucine_qui = [o_ for o_ in qui if o_["arredo"] == "cucina"]; quota_sosp = 0.6 if cucine_qui else 1.0
    for k, (q, zb, rg) in enumerate(punti): sospensione(v, villa, q, zb, f"Sospensione {v['nome']} v{villa} {k + 1}", watt * quota_sosp / len(punti), rg)
    for o_ in cucine_qui:                                     # luce sotto i pensili: una striscia per ogni tratto di cucina, verso il piano
        i_ = list(o_["ingombro"]); an = list(zip(i_[0::2], i_[1::2])); lati = [(Vector(an[k]), Vector(an[(k + 1) % len(an)])) for k in range(len(an))]
        muro = [(a_, b_) for a_, b_ in lati if (b_ - a_).length > 0.9 and v["pol"].exterior.distance(Point(tuple((a_ + b_) / 2))) < 0.08]
        for a_, b_ in muro:
            d_ = (b_ - a_).normalized(); n_ = Vector((-d_.y, d_.x)); n_ = n_ if v["pol"].contains(Point(tuple((a_ + b_) / 2 + n_ * 0.5))) else -n_
            ld = bpy.data.lights.new("Sottopensile", "AREA"); ld.shape = "RECTANGLE"; ld.size = max(0.3, (b_ - a_).length - 1.3); ld.size_y = 0.02
            ld.energy = watt * 0.4 / len(muro); ld.color = LU["colore"]
            lo = bpy.data.objects.new(f"Luce sottopensile {v['nome']} v{villa}", ld); m_ = (a_ + b_) / 2 + n_ * 0.2
            lo.location = (m_.x, m_.y, v["z0"] + 1.44); lo.rotation_euler = (0, 0, math.atan2(d_.y, d_.x)); ARR.objects.link(lo); lo["villa"] = villa; lo["punto_luce"] = v["nome"]; n_luci += 1
# abat-jour (Andrea, 2026-11-16: di sera le lampade sui comodini non facevano luce): una luce a punto dentro il paralume
# di comodino() (centro a 0,72 m), potenza abatjour_w; sostituisci_arredi.py la porta nel paralume del modello di libreria
for q, z0_, nome_c, villa, vano, zl in ABAT:                 # zl = quota della luce, dentro il paralume
    ld = bpy.data.lights.new("Abat-jour " + nome_c, "POINT"); ld.energy = LU.get("abatjour_w", 25.0); ld.color = LU["colore"]; ld.shadow_soft_size = 0.04
    lo = bpy.data.objects.new("Luce abat-jour " + nome_c, ld); lo.location = (q.x, q.y, z0_ + zl); ARR.objects.link(lo)
    lo["villa"] = villa; lo["punto_luce"] = vano; n_luci += 1
# sospensioni sottili accanto al letto (riferimento del letto, 2026-11-17): filo nero dal soffitto, calotta nera piccola,
# lampadina allungata calda; due, sfalsate in quota (1,45 e 1,30 m) e in pianta, sopra il comodino. Tipo "lampada_letto":
# sostituisci_arredi.py non le scambia con la plafoniera di libreria
for c_, u_, vv_, v, villa, nome_c in SOSP_LETTO:
    # globi in vetro fumé del riferimento sospensioni_letto_vetro.jpg (2026-11-17 sera): grande in alto, piccolo più in basso
    for k, (sa, sb, zb, rg) in enumerate(((-0.07, 0.02, 1.50, 0.085), (0.08, -0.04, 1.26, 0.068))):
        p = Pezzo(c_, u_, vv_, v["z0"]); q = Vector(p.P(sa, sb)); zs = soffitto(q.x, q.y, v["z0"] + 1.9) - v["z0"]
        globo_vetro(p, sa, sb, zb, rg, zs)
        nome_l = f"Sospensione letto {v['nome']} v{villa} {k + 1}"
        p.fine(nome_l, villa, "lampada_letto", Point(q.x, q.y).buffer(0.01))
        for o_ in ARR.objects:
            if o_.name.startswith(nome_l): o_["ingombro"] = []
        ld = bpy.data.lights.new(nome_l, "POINT"); ld.energy = LU.get("abatjour_w", 25.0) * 0.6; ld.color = LU["colore"]; ld.shadow_soft_size = 0.015
        lo = bpy.data.objects.new("Luce " + nome_l, ld); lo.location = (q.x, q.y, v["z0"] + zb); ARR.objects.link(lo)
        lo["villa"] = villa; lo["punto_luce"] = v["nome"]; n_luci += 1
    log(f"sospensioni accanto al letto: 2 sopra {nome_c}")
for q, ax, lg, zl, villa, vano in LUCI_SPECCHIO:            # LED sotto gli specchi dei bagni: luce radente verso il basso
    ld = bpy.data.lights.new("LED specchio " + vano, "AREA"); ld.shape = "RECTANGLE"; ld.size = lg; ld.size_y = 0.02
    ld.energy = 5.0 * lg; ld.color = LU["colore"]
    lo = bpy.data.objects.new(f"Luce LED specchio {vano} v{villa}", ld); lo.location = (q.x, q.y, zl)
    lo.rotation_euler = (0, 0, math.atan2(ax.y, ax.x)); ARR.objects.link(lo); lo["villa"] = villa; lo["punto_luce"] = vano; n_luci += 1
for q, ax, lg, z0_, nome_l, villa, vano in LED_TESTATE:   # luce radente verso l'alto sul muro dietro la testata
    ld = bpy.data.lights.new("LED testata " + nome_l, "AREA"); ld.shape = "RECTANGLE"; ld.size = lg - 0.04; ld.size_y = 0.02
    ld.energy = 6.0 * lg; ld.color = LU["colore"]
    lo = bpy.data.objects.new("Luce LED testata " + nome_l, ld); lo.location = (q.x, q.y, z0_ + 1.01)
    lo.rotation_euler = (math.pi, 0, math.atan2(ax.y, ax.x)); ARR.objects.link(lo); lo["villa"] = villa; lo["punto_luce"] = vano; n_luci += 1
log("punti luce:", n_luci, f"| {LU['w_m2']} W/m² per stanza | abat-jour", len(ABAT), f"da {LU.get('abatjour_w', 25.0):g} W",
    "| LED sotto i pensili", n_luci_cucina)

# nessun mobile nello spazio spazzato dalle ante (proprietà "battuta" scritta da finiture_interni.py)
for o in scn.objects:
    if "battuta" not in o: continue
    bt = Polygon(list(zip(list(o["battuta"])[0::2], list(o["battuta"])[1::2]))).buffer(-0.03)
    for m_ in ARR.objects:
        if len(m_.get("ingombro", [])) < 6: continue
        ing = Polygon(list(zip(list(m_["ingombro"])[0::2], list(m_["ingombro"])[1::2]))).buffer(0)
        if int(m_.get("villa", 1)) == int(o.get("villa", 1)) and ing.intersects(bt) and not m_.name.endswith(("(tessili)", "(liscio)", "(tondo)")):
            log(f"AVVISO: {o.name} aprendosi urta {m_.name} ({ing.intersection(bt).area:.2f} m² di sovrapposizione)")
log("arredi:", json.dumps(conta, ensure_ascii=False), "| oggetti", len(ARR.objects))
json.dump({"_nota": "mobili e lampade posati da arredi_interni.py, coordinate locali del contesto in metri (x Est, y Nord, z quota). "
                    "centro_m = centro in pianta e quota d'appoggio (per le lampade: punto più basso); lungo = asse lungo; fronte = lato verso la stanza; verso = direzione principale se il pezzo ne ha una (letto: dai piedi alla testata); "
                    "misure_m = [lungo, profondo, alto]. In Unreal: x = x*100, y = -y*100, z = z*100.", "arredi": POSATI},
          open(os.path.join(USCITA, "arredi_posati.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log("arredi_posati.json:", len(POSATI), "pezzi")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend")); log("fine")
