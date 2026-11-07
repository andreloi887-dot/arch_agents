"""Importatore di contesto.json in Blender (fase 3 della filiera, vedi PROCEDIMENTO.md).

  blender -b -P importa_contesto.py -- <cartella modello> [--uscita uscita_blender] [--render] [--samples 16]
                                      [--data 2026-04-15] [--ora 11:00] [--fuso 2] [--senza-libreria]

Sole: posizione calcolata (NOAA) da origine del lotto, data e ora locali (fuso: +1 inverno, +2 ora legale).

Legge <modello>/contesto.json (prodotto da skills/rilievo-urbano/scripts/contesto/contesto.py) e costruisce, in
coordinate locali in metri (x = Est, y = Nord, origine = lotto.json → origine):
  terreno / strade / marciapiedi / lotto (mesh 2.5D), muri (sweep di sezioni), recinzioni a rete, edifici (estrusione
  + coperture, timpani, sporti), dettagli di facciata e di strada (scatole orientate, fuse per materiale), arredo
  (lampioni, cartelli), vegetazione (alberi, palme, siepi), materiali PBR dalla palette.
Ogni elemento ha nome e collezione per categoria; le proprietà personalizzate conservano origine e fonti.
Con --render: camere delle riprese Street View (manifest_riprese.json) e viste aeree, render EEVEE in
<uscita>/viste/. Salva <uscita>/contesto.blend.

Il mesh è volutamente semplice dove arriveranno modelli di libreria (lampioni, cartelli, alberi): gli oggetti hanno
la proprietà `asset` con il tipo, così la sostituzione con asset di qualità è automatica.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
def opt(nome, default=None):
    return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else default
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
RENDER = "--render" in argv
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
LIB = os.path.abspath(opt("--libreria", os.path.join(REPO, "libreria")))
LIBJ = json.load(open(os.path.join(LIB, "libreria.json"), encoding="utf-8")) if os.path.exists(os.path.join(LIB, "libreria.json")) and "--senza-libreria" not in argv else None
SAMPLES = int(opt("--samples", "16"))
os.makedirs(USCITA, exist_ok=True)
C = json.load(open(os.path.join(MOD, "contesto.json"), encoding="utf-8"))
LOG = open(os.path.join(USCITA, "importa.log"), "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.write(s + "\n"); LOG.flush()

# ------------------------------------------------------------------------------------------------ scena pulita
# ATTENZIONE: mai bpy.ops.wm.read_factory_settings() / read_homefile(): riportano le preferenze di fabbrica e Blender
# rimuove le librerie delle estensioni (Bonsai, ifcopenshell...) dalla cartella utente. Si svuota solo la scena.
scn = bpy.context.scene
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob, do_unlink=True)
for c_ in list(bpy.data.collections): bpy.data.collections.remove(c_)
for blocco in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.images):
    for d_ in list(blocco):
        if d_.users == 0: blocco.remove(d_)
scn.unit_settings.system = "METRIC"; scn.unit_settings.scale_length = 1.0
scn["origine_lat"] = C["origine"]["lat"]; scn["origine_lng"] = C["origine"]["lng"]
scn["fonti"] = "; ".join(C.get("fonti", []))

COLL = {}
def coll(nome):
    if nome not in COLL:
        c = bpy.data.collections.new(nome); scn.collection.children.link(c); COLL[nome] = c
    return COLL[nome]

# ------------------------------------------------------------------------------------------------ materiali
def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hex2rgb(h):
    h = h.lstrip("#"); return tuple(srgb2lin(int(h[i:i+2], 16) / 255) for i in (0, 2, 4))
RUVIDITA = {"asfalto": 0.85, "cls": 0.8, "calcestruzzo": 0.8, "intonaco": 0.9, "tegole": 0.7, "coppi": 0.7,
            "acciaio": 0.35, "alluminio": 0.3, "vetro": 0.05, "VETRO": 0.03, "FV": 0.15, "SEGN": 0.4}
METALLO = ("acciaio", "alluminio", "zincato", "PALO_LUCE", "ARMATURA")
MATS = {}
def mat(nome):
    if not nome: nome = "GENERICO"
    if nome in MATS: return MATS[nome]
    d = C["materiali"].get(nome, {"hex": "#B0B0B0"})
    m = bpy.data.materials.new(nome); m.use_nodes = True
    nt = m.node_tree
    # per tipo, non per nome: con l'interfaccia in italiano il nodo si chiama "BSDF Principled"
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None:
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out_ = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(b.outputs[0], out_.inputs[0])
    rgb = hex2rgb(d.get("hex", "#B0B0B0"))
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    rough = next((v for k, v in RUVIDITA.items() if k.lower() in nome.lower()), 0.75)
    b.inputs["Roughness"].default_value = rough
    if any(k.lower() in nome.lower() for k in METALLO): b.inputs["Metallic"].default_value = 0.8
    if nome == "VETRO":
        b.inputs["Roughness"].default_value = 0.03
        if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = 0.8
    if "alpha" in d:
        b.inputs["Alpha"].default_value = d["alpha"]
        try: m.surface_render_method = "BLENDED"
        except Exception: m.blend_method = "BLEND"
    if d.get("texture"):
        tp = os.path.join(MOD, d["texture"])
        if os.path.exists(tp):
            img = bpy.data.images.load(tp, check_existing=True)
            tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img
            tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
            mod = d.get("modulo_mm", [1000, 1000]); s_ = 2000.0 / mod[0]   # la texture contiene 2×2 moduli
            mp.inputs["Scale"].default_value = (s_ / 2, s_ / 2, 1)
            nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
            nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    if LIBJ and not d.get("texture"):
        asg = next((a for a in LIBJ.get("assegnazioni", []) if any(w.lower() in nome.lower() for w in a["parole"])), None)
        if asg: pbr(nt, b, asg, rgb)
    m.diffuse_color = (*rgb, d.get("alpha", 1.0))
    MATS[nome] = m
    return m

def pbr(nt, b, asg, rgb):
    """mappe della libreria: colore (tinto con il colore rilevato), normale, ruvidità; proiezione a cubo, lato reale."""
    M_ = LIBJ["materiali"].get(asg["materiale"], {})
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    s_ = 1.0 / asg.get("lato_m", 2.0); mp.inputs["Scale"].default_value = (s_, s_, s_)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def img(chiave, colore):
        if chiave not in M_: return None
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(os.path.join(LIB, M_[chiave]), check_existing=True)
        if not colore: tx.image.colorspace_settings.name = "Non-Color"
        tx.projection = "BOX"; tx.projection_blend = 0.25
        nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"]); return tx
    col = img("colore", True)
    if col:
        if asg.get("modo") == "tinta":      # grana della texture, colore rilevato: luminanza normalizzata × palette
            bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(col.outputs["Color"], bw.inputs["Color"])
            mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 1.8
            nt.links.new(bw.outputs["Val"], mul.inputs[0])
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            mix.inputs[6].default_value = (*rgb, 1.0)
            cr = nt.nodes.new("ShaderNodeCombineColor")
            for i in range(3): nt.links.new(mul.outputs[0], cr.inputs[i])
            nt.links.new(cr.outputs[0], mix.inputs[7]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        else:                               # colore della texture, tinto in parte verso il colore rilevato
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "COLOR"
            mix.inputs["Factor"].default_value = asg.get("tinta", 0.3)
            nt.links.new(col.outputs["Color"], mix.inputs[6]); mix.inputs[7].default_value = (*rgb, 1.0)
            nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    ru = img("ruvidita", False)
    if ru: nt.links.new(ru.outputs["Color"], b.inputs["Roughness"])
    no = img("normale", False)
    if no:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.8
        nt.links.new(no.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])

# ------------------------------------------------------------------------------------------------ costruzione mesh
def oggetto_mesh(nome, verts, faces, mats_idx, materiali, collezione, smooth_deg=None, props=None):
    me = bpy.data.meshes.new(nome)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(clean_customdata=False)
    for m_ in materiali: me.materials.append(mat(m_))
    if mats_idx and len(me.polygons) == len(mats_idx):
        me.polygons.foreach_set("material_index", mats_idx)
    me.update()
    ob = bpy.data.objects.new(nome, me); coll(collezione).objects.link(ob)
    if smooth_deg:
        for p in me.polygons: p.use_smooth = False
    for k, v in (props or {}).items(): ob[k] = v
    return ob

def tag2coll(tag): return {"10_Edifici": "Edifici", "20_Recinzioni": "Recinzioni", "30_Arredo": "Arredo",
                           "40_Pavimentazioni": "Strade", "50_Vegetazione": "Vegetazione", "60_Terreno": "Terreno"}.get(tag, tag or "Altro")

def superficie(s):
    V = s["vertici"]; F, MI = [], []
    for t in s["triangoli"]:
        a, b, c = t[:3]
        pa, pb, pc = Vector(V[a]), Vector(V[b]), Vector(V[c])
        n = (pb - pa).cross(pc - pa)
        if n.length < 1e-6: continue
        if n.z < -0.3 * n.length: b, c = c, b
        F.append((a, b, c)); MI.append(1 if abs(n.z) < 0.3 * n.length else 0)
    mats_ = s["materiali"] if len(s["materiali"]) > 1 else s["materiali"] * 2
    oggetto_mesh(s["nome"], V, F, MI, mats_, tag2coll(s.get("tag")))

def sweep(w):
    sez = [[Vector(p) for p in st] for st in w["stazioni"]]
    if len(sez) < 2: return
    k = len(sez[0]); V = [p for st in sez for p in st]; F = []
    for i in range(len(sez) - 1):
        for j in range(k):
            a0, b0 = i * k + j, i * k + (j + 1) % k; a1, b1 = a0 + k, b0 + k
            F += [(a0, a1, b1), (a0, b1, b0)]
    F.append(tuple(range(k))[::-1]); F.append(tuple(range((len(sez) - 1) * k, len(sez) * k)))
    oggetto_mesh(w["nome"], V, F, None, [w["materiale"]], tag2coll(w.get("tag")))

def recinzione(r):
    """rete su paletti: pannello (materiale trasparente) + paletti come scatole."""
    pts = [Vector(p) for p in r["asse"]]; h = r["h"]; gap = r.get("gap", 0.0); passo = r.get("passo", 2.5)
    V, F = [], []
    for a, b in zip(pts, pts[1:]):
        i = len(V); V += [a + Vector((0, 0, gap)), b + Vector((0, 0, gap)), b + Vector((0, 0, gap + h)), a + Vector((0, 0, gap + h))]
        F.append((i, i + 1, i + 2, i + 3))
    if F: oggetto_mesh(r["nome"], V, F, None, [r["materiale_rete"]], tag2coll(r.get("tag")))
    pali = []
    for a, b in zip(pts, pts[1:]):
        L_ = (b - a).xy.length; n = max(1, math.ceil(L_ / passo)); rot = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        for j in range(n + (1 if b is pts[-1] else 0)):
            p = a.lerp(b, j / n); pali.append({"c": [p.x, p.y, p.z], "dim": [r.get("lato_palo", 0.04)] * 2 + [h + gap], "rot_deg": rot,
                                               "materiale": r["materiale_palo"]})
    scatole(pali, r["nome"] + " – paletti", tag2coll(r.get("tag")))

# scatole orientate (formato comune di elementi e dettagli), fuse per materiale in un solo oggetto
def matrice_scatola(x):
    c = x["c"]; M_ = Matrix.Translation(Vector(c)) @ Matrix.Rotation(math.radians(x.get("rot_deg", 0.0)), 4, "Z")
    if x.get("incl_deg"): M_ = M_ @ Matrix.Rotation(math.radians(x["incl_deg"]), 4, "X")
    return M_
CUBO = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0), (-.5, -.5, 1), (.5, -.5, 1), (.5, .5, 1), (-.5, .5, 1)]
CUBO_F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
def scatole(lista, nome, collezione, props=None):
    if not lista: return None
    per_mat = {}
    for x in lista: per_mat.setdefault(x["materiale"], []).append(x)
    V, F, MI, MATL = [], [], [], []
    for mi, (m_, xs) in enumerate(per_mat.items()):
        MATL.append(m_)
        for x in xs:
            l, d, h = x["dim"]
            if l < 1e-3 or d < 1e-3 or h < 1e-3: continue
            M_ = matrice_scatola(x); i = len(V)
            V += [tuple(M_ @ Vector((p[0] * l, p[1] * d, p[2] * h))) for p in CUBO]
            F += [tuple(i + q for q in f) for f in CUBO_F]; MI += [mi] * 6
    return oggetto_mesh(nome, V, F, MI, MATL, collezione, props=props)

def edificio(e):
    imp = e["impronta"]; zb = e["z_base"]; zt = zb + e["altezza"]; n = len(imp)
    # verso antiorario
    area = sum(imp[i][0] * imp[(i + 1) % n][1] - imp[(i + 1) % n][0] * imp[i][1] for i in range(n))
    if area < 0: imp = imp[::-1]
    V = [(x, y, zb) for x, y in imp] + [(x, y, zt) for x, y in imp]
    F = [tuple(range(n))[::-1]] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    MI = [0] * (n + 1)
    t = e.get("tetto")
    if not t or t.get("sporto"):
        F.append(tuple(range(n, 2 * n))); MI.append(1)
    if t:
        base = len(V); V += [tuple(v) for v in t["vertici"]]
        for a, b, c in t["triangoli"]: F.append((base + a, base + b, base + c)); MI.append(1)
        for a, b, c in t.get("timpani", []): F.append((base + a, base + b, base + c)); MI.append(0)
    ob = oggetto_mesh(e["nome"], V, F, MI, [e["materiale"], e["materiale_copertura"]], tag2coll(e.get("tag")),
                      props={"lod": e.get("lod", 1)})
    if e.get("fotovoltaico"):
        fv = e["fotovoltaico"]; oggetto_mesh(e["nome"] + " – fotovoltaico", fv["vertici"], [tuple(t) for t in fv["triangoli"]],
                                             None, ["FV"], "Edifici")
    if e.get("elementi"):
        sc_ = scatole(e["elementi"], e["nome"] + " – dettagli", "Dettagli edifici")
        if sc_: sc_.parent = ob

# ------------------------------------------------------------------------------------------------ arredo e verde
def cilindro(r0, r1, h, seg=12, z0=0.0):
    V = [(r0 * math.cos(2 * math.pi * k / seg), r0 * math.sin(2 * math.pi * k / seg), z0) for k in range(seg)] + \
        [(r1 * math.cos(2 * math.pi * k / seg), r1 * math.sin(2 * math.pi * k / seg), z0 + h) for k in range(seg)]
    F = [tuple(range(seg))[::-1], tuple(range(seg, 2 * seg))] + [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
    return V, F
def unisci(parti):
    """parti = [(V, F, indice materiale, matrice)] → V, F, MI"""
    V, F, MI = [], [], []
    for v, f, mi, M_ in parti:
        i = len(V); V += [tuple(M_ @ Vector(p)) for p in v]; F += [tuple(i + q for q in ff) for ff in f]; MI += [mi] * len(f)
    return V, F, MI
def box_vf(l, d, h, cx=0, cy=0, z=0):
    return [(cx + p[0] * l, cy + p[1] * d, z + p[2] * h) for p in CUBO], CUBO_F

def lampione(o):
    l = o["lampione"]; h = l["h"]; pl = l["plinto"]; sb = l["sbraccio"]; a = l["armatura"]
    M0 = Matrix.Translation(Vector((o["xy"][0], o["xy"][1], o["z"]))) @ Matrix.Rotation(math.radians(o.get("rot_deg", 0)), 4, "Z")
    I = Matrix.Identity(4)
    parti = [(*box_vf(pl[0], pl[1], pl[2] + 0.05, z=-0.05), 0, M0),
             (*cilindro(l["d_base"] / 2, l["d_cima"] / 2, h - pl[2], 12, pl[2]), 1, M0),
             (*box_vf(sb + 0.05, 0.05, 0.05, cx=sb / 2, z=h - 0.05), 1, M0),
             (*box_vf(a[0], a[1], a[2], cx=sb + a[0] / 2 - 0.05, z=h - 0.12), 2, M0)]
    V, F, MI = unisci(parti)
    oggetto_mesh(o["nome"], V, F, MI, ["PLINTO", "PALO_LUCE", "ARMATURA"], "Arredo", props={"asset": "lampione_stradale", "h": h})

def segnale(o):
    s = o["segnale"]; h = o["dim"][2]
    M0 = Matrix.Translation(Vector((o["xy"][0], o["xy"][1], o["z"]))) @ Matrix.Rotation(math.radians(o.get("rot_deg", 0)), 4, "Z")
    d = s["d"] if isinstance(s["d"], list) else [s["d"], s["d"]]
    zc = h - d[1] / 2
    Rx = Matrix.Rotation(math.radians(90), 4, "X")       # disco con normale lungo -y
    parti = [(*cilindro(0.03, 0.03, h + 0.1, 8), 0, M0)]
    if s["forma"] == "tondo":
        parti += [(*cilindro(d[0] / 2, d[0] / 2, 0.012, 24), 1, M0 @ Matrix.Translation((0, -0.03, zc)) @ Rx),
                  (*cilindro(d[0] / 2 * 0.78, d[0] / 2 * 0.78, 0.006, 24), 2, M0 @ Matrix.Translation((0, -0.042, zc)) @ Rx)]
        if s.get("simbolo") in ("diagonale", "croce"):
            for ang in ((45,) if s["simbolo"] == "diagonale" else (45, -45)):
                parti.append((*box_vf(d[0] * 0.78, 0.004, 0.08, z=-0.04), 1,
                              M0 @ Matrix.Translation((0, -0.047, zc)) @ Matrix.Rotation(math.radians(ang), 4, "Y")))
        if s.get("simbolo") == "barra":
            parti.append((*box_vf(d[0] * 0.55, 0.004, 0.11, z=zc - 0.055), 3, M0 @ Matrix.Translation((0, -0.047, 0))))
    else:
        parti += [(*box_vf(d[0], 0.012, d[1], z=zc - d[1] / 2), 1, M0 @ Matrix.Translation((0, -0.03, 0))),
                  (*box_vf(d[0] - 0.03, 0.006, d[1] - 0.03, z=zc - d[1] / 2 + 0.015), 2, M0 @ Matrix.Translation((0, -0.04, 0)))]
    if s.get("pannello"):
        w, hh = s["pannello"]["dim"]
        parti.append((*box_vf(w, 0.012, hh, z=zc - d[1] / 2 - 0.05 - hh), 3, M0 @ Matrix.Translation((0, -0.03, 0))))
    V, F, MI = unisci(parti)
    oggetto_mesh(o["nome"], V, F, MI, ["PALO_LUCE", s["bordo"], s["campo"], "SEGN_BIANCO"], "Arredo",
                 props={"asset": "segnale_" + s["forma"]})

def arredo_generico(o):
    w, d, h = o["dim"]
    x = {"c": [o["xy"][0], o["xy"][1], o["z"]], "dim": [w, d, h], "rot_deg": o.get("rot_deg", 0), "materiale": o["materiale"]}
    scatole([x], o["nome"], "Arredo", props={"asset": o.get("testa") or "arredo"})

MODELLI = {}
def modello(nome):
    """collezione del modello di libreria (append una volta, poi istanze); altezza del modello per la scala."""
    if nome in MODELLI: return MODELLI[nome]
    info = LIBJ["modelli"].get(nome) if LIBJ else None
    if not info: MODELLI[nome] = None; return None
    with bpy.data.libraries.load(os.path.join(LIB, info["blend"]), link=False) as (src, dst):
        dst.objects = [o for o in src.objects]
    cl = bpy.data.collections.new("ASSET_" + nome)
    zmin, zmax, rmax = 1e9, -1e9, 0.0
    for o in dst.objects:
        if o is None: continue
        cl.objects.link(o)
        if o.type == "MESH":
            for c in o.bound_box:
                w_ = o.matrix_world @ Vector(c); zmin, zmax = min(zmin, w_.z), max(zmax, w_.z); rmax = max(rmax, w_.xy.length)
    MODELLI[nome] = (cl, max(0.1, zmax - zmin), max(0.1, rmax), zmin)
    return MODELLI[nome]
import random as _rnd
_rnd.seed(7)
def istanza(nome_mod, nome, xyz, h, collezione, chioma=None):
    m_ = modello(nome_mod)
    if not m_: return None
    cl, hm, rm, zmin = m_
    e = bpy.data.objects.new(nome, None); e.instance_type = "COLLECTION"; e.instance_collection = cl
    sz = h / hm; sxy = (chioma / 2 / rm) if chioma else sz
    e.scale = (sxy, sxy, sz); e.location = (xyz[0], xyz[1], xyz[2] - zmin * sz); e.rotation_euler = (0, 0, _rnd.uniform(0, 6.283))
    coll(collezione).objects.link(e); return e

def albero(v):
    if LIBJ and v.get("forma", "albero") == "albero" and "albero" in LIBJ.get("sostituzioni", {}):
        e = istanza(LIBJ["sostituzioni"]["albero"]["modello"], v["nome"], (v["xy"][0], v["xy"][1], v["z"]), v["h"], "Vegetazione",
                    v.get("chioma"))
        if e:
            e["asset"] = "albero"; e["h"] = v["h"]; return
    h = v["h"]; r = v["chioma"] / 2; forma = v.get("forma", "albero")
    M0 = Matrix.Translation(Vector((v["xy"][0], v["xy"][1], v["z"])))
    parti = []
    if forma in ("palma", "palma_alta"):
        fusto = h * 0.75 if forma == "palma_alta" else 0.3
        if forma == "palma_alta": parti.append((*cilindro(0.22, 0.18, fusto, 10), 0, M0))
        Vf, Ff = [], []
        nf = 18
        for k in range(nf):   # fronde arcuate (6 tratti) con foglioline alternate
            a = 2 * math.pi * k / nf + (0.17 if k % 2 else 0); c, s_ = math.cos(a), math.sin(a)
            alza = 0.25 + 0.35 * ((k * 7) % 5) / 4          # inclinazioni diverse: ciuffo pieno
            pts = []
            for j in range(7):
                t = j / 6; rr = r * t; zz = fusto + (h - fusto) * (alza * math.sin(math.pi * t * 0.9) + 0.15 * (1 - t)) + 0.3
                pts.append((rr * c, rr * s_, zz))
            px, py = -s_, c
            for j in range(6):
                (x0, y0, z0), (x1, y1, z1) = pts[j], pts[j + 1]; w0 = 0.35 * math.sin(math.pi * (j + 0.5) / 6.5) + 0.05
                i = len(Vf); Vf += [(x0, y0, z0), (x1 + px * w0, y1 + py * w0, z1 - 0.12), (x1, y1, z1), (x1 - px * w0, y1 - py * w0, z1 - 0.12)]
                Ff += [(i, i + 1, i + 2), (i, i + 2, i + 3)]
        parti.append((Vf, Ff, 1, M0))
        if forma == "palma_alta":   # anelli del fusto (cicatrici delle foglie)
            for j in range(int(fusto / 0.35)):
                parti.append((*cilindro(0.24, 0.20, 0.08, 10, j * 0.35 + 0.1), 0, M0))
        mats_ = ["FUSTO", v.get("materiale", "C27")]
    else:
        hf = max(h * 0.35, 0.8)
        parti.append((*cilindro(0.14, 0.10, hf + 0.3, 8), 0, M0))
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        Vc = [(p.co.x * r, p.co.y * r, p.co.z * (h - hf) / 2 + hf + (h - hf) / 2) for p in bm.verts]
        Fc = [tuple(q.index for q in f.verts) for f in bm.faces]; bm.free()
        parti.append((Vc, Fc, 1, M0))
        mats_ = ["FUSTO", "CHIOMA"]
    V, F, MI = unisci(parti)
    oggetto_mesh(v["nome"], V, F, MI, mats_, "Vegetazione", props={"asset": forma, "h": h, "chioma": v["chioma"]})

# ------------------------------------------------------------------------------------------------ costruzione
for k in ("VETRO", "FV", "PLINTO", "PALO_LUCE", "ARMATURA", "FUSTO", "CHIOMA", "SEGN_BIANCO"):
    C["materiali"].setdefault(k, {"hex": {"VETRO": "#2E3A42", "FV": "#1C2A44", "PLINTO": "#9C9890", "PALO_LUCE": "#A9AEB1",
                                          "ARMATURA": "#5E6366", "FUSTO": "#6B5A48", "CHIOMA": "#556B35", "SEGN_BIANCO": "#F4F4F2"}[k]})
conta = {}
def fatto(k): conta[k] = conta.get(k, 0) + 1
for s in C["superfici"]: superficie(s); fatto("superfici")
def ciuffo(nome, colore, n_fili=11, curva=0.25):
    """ciuffo low-poly alto 1 m: fili triangolari inclinati a raggiera (scalato dalle particelle)."""
    V, F = [], []
    for k in range(n_fili):
        a = 2 * math.pi * k / n_fili + _rnd.uniform(-0.2, 0.2); inc = _rnd.uniform(0.15, 0.55); hh = _rnd.uniform(0.55, 1.0)
        c, s_ = math.cos(a), math.sin(a); px, py = -s_ * 0.02, c * 0.02
        i = len(V)
        V += [(px, py, 0), (-px, -py, 0), (c * inc * 0.5 * hh, s_ * inc * 0.5 * hh, hh * 0.55), (c * inc * hh, s_ * inc * hh, hh)]
        F += [(i, i + 1, i + 2), (i + 1, i + 3, i + 2)]
    C["materiali"].setdefault(nome, {"hex": colore})
    me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F); me.materials.append(mat(nome))
    ob = bpy.data.objects.new(nome, me); return ob
def prato_lotto():
    """erbe spontanee fitte sul lotto incolto: particelle (istanze, leggere da rendere) di ciuffi verdi e secchi."""
    cfg = (LIBJ or {}).get("sostituzioni", {}).get("prato_lotto")
    if not cfg: return
    ob = next((o for o in bpy.data.objects if o.name.startswith(cfg.get("superficie", "P03"))), None)
    if not ob: return
    cl = bpy.data.collections.new("ASSET_ciuffi_lotto")
    for k, (nome, col) in enumerate(cfg.get("ciuffi", [["ERBA_VERDE", "#6F8A3A"], ["ERBA_SECCA", "#B9A86A"], ["ERBA_FIORITA", "#8E9A4A"]])):
        for j in range(2): cl.objects.link(ciuffo(f"{nome}_{j}", col, n_fili=cfg.get("fili", 11)))
    area_ = sum(p.area for p in ob.data.polygons if p.normal.z > 0.5)
    # Geometry Nodes: punti distribuiti sulle facce orizzontali → istanze casuali dei ciuffi (scala e rotazione casuali)
    ng = bpy.data.node_groups.new("Erbe spontanee", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes; Lk = ng.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    nrm = N.new("GeometryNodeInputNormal"); sep = N.new("ShaderNodeSeparateXYZ"); cmp_ = N.new("FunctionNodeCompare")
    cmp_.data_type = "FLOAT"; cmp_.operation = "GREATER_THAN"; cmp_.inputs[1].default_value = 0.5
    Lk.new(nrm.outputs[0], sep.inputs[0]); Lk.new(sep.outputs[2], cmp_.inputs[0])
    dist = N.new("GeometryNodeDistributePointsOnFaces"); dist.distribute_method = "RANDOM"
    dist.inputs["Density"].default_value = cfg.get("densita_m2", 3.0); dist.inputs["Seed"].default_value = 11
    Lk.new(gi.outputs[0], dist.inputs["Mesh"]); Lk.new(cmp_.outputs[0], dist.inputs["Selection"])
    ci = N.new("GeometryNodeCollectionInfo"); ci.inputs["Collection"].default_value = cl
    ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
    iop = N.new("GeometryNodeInstanceOnPoints"); iop.inputs["Pick Instance"].default_value = True
    def casuale(tipo, mn, mx):
        """Random Value: i socket attivi dipendono dal tipo; si scelgono per tipo, non per posizione."""
        rv = N.new("FunctionNodeRandomValue"); rv.data_type = tipo
        st_ = {"INT": "INT", "FLOAT": "VALUE", "FLOAT_VECTOR": "VECTOR"}[tipo]
        ins = [i for i in rv.inputs if i.type == st_ and i.name in ("Min", "Max") and i.enabled]
        ins[0].default_value = mn; ins[1].default_value = mx
        out = next(o for o in rv.outputs if o.type == st_ and o.enabled)
        return out
    h0 = cfg.get("altezza_m", 0.85)
    o_i = casuale("INT", 0, 100); o_s = casuale("FLOAT", h0 * 0.55, h0 * 1.35); o_r = casuale("FLOAT_VECTOR", (0, 0, 0), (0.15, 0.15, 6.283))
    Lk.new(dist.outputs["Points"], iop.inputs["Points"]); Lk.new(ci.outputs[0], iop.inputs["Instance"])
    Lk.new(o_i, iop.inputs["Instance Index"]); Lk.new(o_s, iop.inputs["Scale"]); Lk.new(o_r, iop.inputs["Rotation"])
    jo = N.new("GeometryNodeJoinGeometry"); Lk.new(gi.outputs[0], jo.inputs[0]); Lk.new(iop.outputs[0], jo.inputs[0])
    Lk.new(jo.outputs[0], go.inputs[0])
    md = ob.modifiers.new("Erbe spontanee", "NODES"); md.node_group = ng
    class _St: pass
    st = _St(); st.count = int(area_ * cfg.get("densita_m2", 3.0))
    log("prato del lotto:", st.count, "ciuffi a particelle su", round(area_), "m²")
def erba_lotto():
    sst = (LIBJ or {}).get("sostituzioni", {}).get("erba_lotto")
    if not sst: return
    s = next((x for x in C["superfici"] if x["nome"].startswith(sst.get("superficie", "P03"))), None)
    if not s: return
    V = s["vertici"]; tri = []
    for t in s["triangoli"]:
        a, b, c = (Vector(V[i]) for i in t[:3]); ar = (b - a).cross(c - a).length / 2
        if ar > 1e-4 and abs(((b - a).cross(c - a)).normalized().z) > 0.5: tri.append((a, b, c, ar))
    tot = sum(t[3] for t in tri); n = int(tot * sst.get("densita_m2", 0.3)); acc = []
    for t in tri: acc.append((acc[-1] if acc else 0) + t[3])
    import bisect
    for k in range(n):
        a, b, c, _ = tri[bisect.bisect(acc, _rnd.uniform(0, tot))]
        u, w = _rnd.random(), _rnd.random()
        if u + w > 1: u, w = 1 - u, 1 - w
        p_ = a + (b - a) * u + (c - a) * w
        ha, hb = sst.get("altezza_m", [0.6, 1.1]); da, db = sst.get("diametro_m", [0.8, 1.4])
        istanza(sst["modello"], f"erba lotto {k}", (p_.x, p_.y, p_.z), _rnd.uniform(ha, hb), "Vegetazione", _rnd.uniform(da, db))
    log("erba nel lotto:", n, "ciuffi")
erba_lotto()
prato_lotto()
for w in C["muri"]: sweep(w); fatto("muri")
for r in C["recinzioni"]: recinzione(r); fatto("recinzioni")
for e in C["edifici"]: edificio(e); fatto("edifici")
for o in C["oggetti"]:
    if o.get("lampione"): lampione(o); fatto("lampioni")
    elif o.get("segnale"): segnale(o); fatto("cartelli")
    else: arredo_generico(o); fatto("arredo")
for v in C["vegetazione"]: albero(v); fatto("vegetazione")
if C.get("dettagli"):
    per_tipo = {}
    for x in C["dettagli"]:
        k = {"SEGNALETICA": "Segnaletica orizzontale", "SIEPE": "Siepi", "CANNETO": "Canneti"}.get(x["materiale"], "Recinzioni e cancelli – dettagli")
        per_tipo.setdefault(k, []).append(x)
    for k, xs in per_tipo.items(): scatole(xs, k, "Dettagli strada"); fatto("gruppi di dettagli")
log("costruiti:", json.dumps(conta, ensure_ascii=False))

# ------------------------------------------------------------------------------------------------ luce, cielo, camere
def posizione_sole(lat, lng, data, ora, fuso_h):
    """azimut (da Nord, orario) ed elevazione del sole in gradi – algoritmo NOAA, precisione ~0,1°."""
    import datetime as _dt
    y, mo, d = (int(x) for x in data.split("-")); hh, mm = (int(x) for x in ora.split(":"))
    t = _dt.datetime(y, mo, d, hh, mm) - _dt.timedelta(hours=fuso_h)
    jd = (t - _dt.datetime(2000, 1, 1, 12)).total_seconds() / 86400 + 2451545.0; T = (jd - 2451545.0) / 36525
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360; M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T); Mr = math.radians(M)
    C_ = math.sin(Mr) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * Mr) * (0.019993 - 0.000101 * T) + math.sin(3 * Mr) * 0.000289
    lam = L0 + C_ - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * T))
    eps = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * T))
    dec = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    yv = math.tan(math.radians(eps / 2)) ** 2
    eqt = 4 * math.degrees(yv * math.sin(2 * math.radians(L0)) - 2 * e * math.sin(Mr) + 4 * e * yv * math.sin(Mr) * math.cos(2 * math.radians(L0))
                           - 0.5 * yv * yv * math.sin(4 * math.radians(L0)) - 1.25 * e * e * math.sin(2 * Mr))
    tst = (t.hour * 60 + t.minute + eqt + 4 * lng) % 1440; ha = tst / 4 - 180
    la, de, h_ = math.radians(lat), math.radians(dec), math.radians(ha)
    cz = math.sin(la) * math.sin(de) + math.cos(la) * math.cos(de) * math.cos(h_); zen = math.acos(max(-1, min(1, cz)))
    az = math.degrees(math.atan2(math.sin(h_), math.cos(h_) * math.sin(la) - math.tan(de) * math.cos(la))) + 180
    return az % 360, 90 - math.degrees(zen)
DATA = opt("--data", "2026-04-15"); ORA = opt("--ora", "11:00"); FUSO = float(opt("--fuso", "2"))   # aprile: ora legale UTC+2
AZ, EL = posizione_sole(C["origine"]["lat"], C["origine"]["lng"], DATA, ORA, FUSO)
log(f"sole {DATA} {ORA} (UTC+{FUSO:g}): azimut {AZ:.1f}°, elevazione {EL:.1f}°")
scn["sole"] = {"data": DATA, "ora": ORA, "azimut": AZ, "elevazione": EL}
sun = bpy.data.lights.new("Sole", "SUN"); sun.energy = 3.8; sun.angle = math.radians(0.53)
so = bpy.data.objects.new("Sole", sun); coll("Luci").objects.link(so)
# la luce SUN illumina lungo il suo -Z: inclinazione = 90° - elevazione, rotazione = verso opposto all'azimut
so.rotation_euler = (math.radians(90 - EL), 0, math.radians(180 - AZ))
w = bpy.data.worlds.new("Cielo"); scn.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
try:
    sky = w.node_tree.nodes.new("ShaderNodeTexSky")
    for tipo in ("MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
        try: sky.sky_type = tipo; break
        except Exception: pass
    if hasattr(sky, "sun_elevation"):
        sky.sun_elevation = math.radians(EL); sky.sun_rotation = math.radians(180 - AZ - 90)
        sky.sun_disc = False
    if hasattr(sky, "altitude"): sky.altitude = 40.0
    w.node_tree.links.new(sky.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.35
except Exception:
    bg.inputs["Color"].default_value = (0.55, 0.7, 0.95, 1)

def camera(nome, eye, target=None, fov=60, heading=None, pitch=0.0, res=(1280, 720)):
    cd = bpy.data.cameras.new(nome); cd.lens_unit = "FOV"; cd.angle = math.radians(fov); cd.clip_end = 2000
    co = bpy.data.objects.new(nome, cd); coll("Camere").objects.link(co); co.location = eye
    if heading is not None:   # heading 0 = Nord, orario; pitch positivo verso l'alto
        co.rotation_euler = (math.radians(90 + pitch), 0, math.radians(-heading))
    else:
        d = Vector(target) - Vector(eye); co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    co["res"] = list(res)
    return co

O = C["origine"]
def locale(lat, lng):
    """equirettangolare sull'ellissoide (errore < 1 cm entro 200 m)."""
    a, e2 = 6378137.0, 0.00669437999014; la = math.radians(O["lat"])
    Mr = a * (1 - e2) / (1 - e2 * math.sin(la) ** 2) ** 1.5; Nr = a / math.sqrt(1 - e2 * math.sin(la) ** 2)
    return (math.radians(lng - O["lng"]) * Nr * math.cos(la), math.radians(lat - O["lat"]) * Mr)
deps = None
def quota_terreno(x, y):
    global deps
    deps = deps or bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = scn.ray_cast(deps, Vector((x, y, 500)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0
camere = []
man_p = next((p for p in [os.path.join(os.path.dirname(MOD), "_rif_google", "manifest_riprese.json"),
                          os.path.join(MOD, "manifest_riprese.json")] if os.path.exists(p)), None)
if man_p:
    man = json.load(open(man_p, encoding="utf-8")); eh = man.get("eye_height_m", 2.5)
    for r in man["riprese"]:
        x, y = locale(r["lat"], r["lng"]); z = r.get("z_occhio_m") or (quota_terreno(x, y) + eh)
        camere.append((camera(r["id"], (x, y, z), fov=r["fov"], heading=r["heading"], pitch=r.get("pitch", 0), res=(640, 640)), r["id"]))
camere.append((camera("VISTA_aerea_SO", (-60, -45, 40), (5, 20, 2), 55), "vista_aerea_SO"))
camere.append((camera("VISTA_aerea_NE", (55, 75, 38), (0, 15, 2), 55), "vista_aerea_NE"))
camere.append((camera("VISTA_angolo", (-12, 4, 2.6), (2, 16, 2.0), 75), "vista_angolo"))
scn.camera = camere[-3][0]

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto.blend"))
log("salvato", os.path.join(USCITA, "contesto.blend"))

if RENDER:
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: scn.render.engine = eng; break
        except Exception: pass
    try: scn.eevee.taa_render_samples = SAMPLES
    except Exception: pass
    try: scn.eevee.shadow_pool_size = "1024"     # molte ombre (erbe, ringhiere): pool più grande
    except Exception: pass
    scn.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scn.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    # anteprima di controllo: trasformazione "Standard" (colori fedeli alla palette), esposizione leggermente ridotta
    # AgX regge le luci forti del sole di mezzogiorno; "Punchy" restituisce la saturazione delle foto
    try: scn.view_settings.view_transform = "AgX"
    except Exception: pass
    for look in ("AgX - Punchy", "Punchy", "AgX - High Contrast"):
        try: scn.view_settings.look = look; break
        except Exception: pass
    scn.view_settings.exposure = -0.2
    os.makedirs(os.path.join(USCITA, "viste"), exist_ok=True)
    for co, nome in camere:
        scn.camera = co; scn.render.resolution_x, scn.render.resolution_y = co["res"]
        scn.render.filepath = os.path.join(USCITA, "viste", nome + ".png")
        bpy.ops.render.render(write_still=True); log("render", nome)
log("fine")
