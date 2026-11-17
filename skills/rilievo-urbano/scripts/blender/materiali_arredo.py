"""Materiali degli arredi (estratti da arredi_interni.py il 2026-11-17 perché i banchi di prova usino gli stessi materiali
della filiera): tinte ST, ruvidità RUV, forza delle normali NORMALE, texture vere TEX (CC0 in libreria_materiali/), mat(k).

  import materiali_arredo as MA; MA.configura(stile_di_arredi_json); m = MA.mat("rovere")
"""
import bpy, os
import numpy as np
from comune import lin

ST = {"legno": "#C8A47A", "laccato": "#EDE7DA", "tessuto": "#D9D0C1", "tessuto_accento": "#B98466", "piano_cucina": "#DAD5CC",
      "metallo": "#3A3632", "nero": "#141414", "tappeto": "#CFC4B2", "inox": "#C4C4C0",
      # cucina e tavolo nello stile del riferimento di Andrea (2026-11-16): rovere chiaro, laccato greige opaco, piano in pietra
      # chiara sottile, paraschizzi in marmo chiaro venato, sedie a scocca imbottita color sabbia, LED sotto i pensili
      "rovere": "#C6B093", "laccato_pensili": "#CEC5B8", "pietra": "#E7E1D7", "marmo": "#E4DDD2", "vena": "#CEC5B8",
      "sabbia": "#CBBBA3", "led": "#FFD9A8",
      # camere e soggiorno (riferimenti di Andrea, 2026-11-16): vetro fumé bronzo dell'armadio, bouclé avorio del divano,
      # biancheria, gesso dei lampadari a ciottolo con l'interno caldo
      "vetro_fume": "#3B2E24", "boucle": "#E9E4DA", "lenzuolo": "#F1EEE8", "plaid": "#8A8076", "cuscino": "#A39A90", "intonaco": "#E6E1D8",
      "lume_dentro": "#E2CDAE", "gesso": "#E3DED5"}

# forza del rilievo delle normali (predefinita 0.8). 0 = niente mappa: l'USD non porta la forza e Unreal la usa piena, sul
# rovere faceva un legno "martellato" (2026-11-17); la venatura del colore basta
NORMALE = {"gesso": 2.5, "boucle": 1.2, "tappeto": 1.2, "rovere": 1.0, "legno": 1.0, "marmo": 0.0, "pietra": 0.0,
           "sabbia": 0.0, "lenzuolo": 0.3, "cuscino": 0.4, "camicia_cielo": 0.3, "camicia_sabbia": 0.3, "tessuto_letto": 0.4}
# ruvidità delle foto ritarata nel file (media, scala dello scarto): la mappa del rovere aveva media 0,48, lucido da laminato;
# un rovere oliato o verniciato opaco sta attorno a 0,7. Scritta nel file perché l'USD e Unreal vedano lo stesso valore
RUV_TEX = {"rovere": (0.70, 0.6), "legno": (0.70, 0.6), "noce": (0.62, 0.6), "travertino": (0.75, 0.5), "piano_bagno": (0.72, 0.5), "pietra_bagno": (0.78, 0.5)}                # stoffe lisce: in Unreal la trama piena faceva bolle
RUV = {"legno": 0.45, "laccato": 0.35, "tessuto": 0.95, "tessuto_accento": 0.95, "piano_cucina": 0.3, "metallo": 0.4, "nero": 0.25, "tappeto": 1.0, "inox": 0.3,
       "rovere": 0.5, "laccato_pensili": 0.6, "pietra": 0.35, "marmo": 0.22, "sabbia": 0.95, "led": 0.5,
       "vetro_fume": 0.05, "gesso": 0.95, "boucle": 1.0, "lenzuolo": 0.9, "plaid": 1.0, "cuscino": 0.95, "intonaco": 0.95, "lume_dentro": 0.8}
MATS = {}
# camicie dell'armadio della matrimoniale (2026-11-17): bianco, azzurro chiaro, sabbia, sulla trama della biancheria
ST.update({"camicia_cielo": "#C7D2DD", "camicia_sabbia": "#D9CCB6"}); RUV.update({"camicia_cielo": 0.9, "camicia_sabbia": 0.9})
# asciugamani in spugna e carta igienica (2026-11-17 sera)
ST.update({"spugna": "#E9E3D7", "carta": "#F3F1EC", "cartone": "#B59A78"}); RUV.update({"spugna": 1.0, "carta": 0.9, "cartone": 0.95})
# base imbottita dei letti singoli (2026-11-17): lino greige
ST["tessuto_letto"] = "#CFC6B8"; RUV["tessuto_letto"] = 0.95
STOFFE = ("sabbia", "lenzuolo", "cuscino", "plaid", "boucle", "tappeto", "camicia_cielo", "camicia_sabbia", "tessuto_letto", "spugna")
# arredi del 2026-11-17 sera (riferimenti mobile_tv, bagno, abatjour_travertino, sospensioni): tinte campionate sulle foto con
# PIL e schiarite di circa il 15 % perché le foto sono in ombra (ipotesi: la luce delle foto non è nota). I nomi non devono
# cominciare con legno, rovere, marmo, led, lampadina, vetro_fume, lume_dentro (regole di prepara_render.py in Unreal)
ST.update({"laccato_tv": "#BFB1A0", "noce": "#5E3B22", "piano_bagno": "#D3C4AE", "pietra_bagno": "#C9B597", "fuga_bagno": "#B4A388",
           "catino": "#D6C9B6", "travertino": "#CCB696", "paralume": "#E9DECB", "rubinetto": "#3B3530", "specchio": "#C8CCCC",
           "interno_bianco": "#EFEBE3", "schermo": "#050506", "vetro_globo": "#7A6650"})
RUV.update({"laccato_tv": 0.55, "noce": 0.6, "piano_bagno": 0.75, "pietra_bagno": 0.8, "fuga_bagno": 0.9, "catino": 0.55, "travertino": 0.75,
            "paralume": 0.9, "rubinetto": 0.35, "specchio": 0.03, "interno_bianco": 0.7, "schermo": 0.04, "vetro_globo": 0.04})
METALLI = ("metallo", "inox", "rubinetto", "specchio")
FIBRA_VERTICALE = {"noce"}
NORMALE.update({"spugna": 1.0, "noce": 1.0, "pietra_bagno": 0.0, "piano_bagno": 0.0, "travertino": 0.8})   # pietra levigata: col rilievo pieno sembrava intonaco grezzo           # fibra sempre verticale sulle facce verticali (foto del bagno), anche se la faccia è larga
# Materiali con texture vere (2026-11-16, dopo il giudizio di Andrea: "materiali e consistenze come nei riferimenti"). Texture CC0
# di Poly Haven e ambientCG in <repo>/libreria_materiali/ (strumenti/materiali/scarica_*.py). Ogni texture si ritinge con la
# tinta del progetto (luminanza della foto × tinta, in lineare) in un file nuovo, così Blender, l'USD e Unreal vedono la stessa
# immagine; le UV dei pezzi sono in metri diviso la misura reale della texture (fine() di Pezzo).
# chiave → (id della texture, misura reale del lato in m, contrasto del disegno, venatura: la U della texture è la fibra)
LIBMAT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "libreria_materiali"))
# rovere: oak_veneer_03 (fibra fine e dritta con fiamme leggere, il più vicino ai riferimenti; scelto il 2026-11-17 sul mosaico
# dei candidati, prima washed_grey_oak_veneer aveva la fibra ondulata), contrasto 1,3 perché la venatura si legga
# 2026-11-17 (Andrea: "il legno dei letti sembra plastica"): contrasto 1,3 → 1,8, ruvidità tarata opaca (RUV_TEX) e poro
# dalla mappa delle normali piena (questa mappa è debolissima: deviazione 0,013)
TEX = {"rovere": ("oak_veneer_03", 1.0, 1.8, True), "legno": ("oak_veneer_03", 1.0, 1.8, True),
       "marmo": ("Marble018", 1.6, 1.0, False),            # misura reale non dichiarata da ambientCG: 1,6 m è un'ipotesi
       "pietra": ("Marble025", 1.6, 1.0, False), "boucle": ("curly_teddy_natural", 0.336, 1.0, False),
       "sabbia": ("terlenka", 0.266, 1.0, False), "lenzuolo": ("terlenka", 0.266, 0.6, False), "cuscino": ("rough_linen", 0.271, 1.0, False),
       "plaid": ("knitted_fleece", 0.27, 1.0, False), "camicia_cielo": ("terlenka", 0.266, 0.6, False),
       "noce": ("oak_veneer_03", 1.0, 1.6, True), "piano_bagno": ("pietra_sabbia", 1.5, 0.35, False), "pietra_bagno": ("pietra_sabbia", 1.5, 0.4, False),   # pietra generata sulla foto (strumenti/materiali/pietra_sabbia.py): beige_wall_002 era un intonaco a onde
       "travertino": ("Travertine009", 0.6, 1.0, False), "spugna": ("curly_teddy_natural", 0.12, 0.7, False), "tessuto_letto": ("rough_linen", 0.271, 1.0, False), "camicia_sabbia": ("terlenka", 0.266, 0.6, False), "intonaco": ("white_stucco", 2.0, 1.0, False), "gesso": ("white_stucco", 0.45, 1.2, False), "tappeto": ("curly_teddy_natural", 0.336, 0.8, False)}
TINTA_DI = {"legno": "rovere"}                               # il legno degli altri mobili prende il rovere chiaro dei riferimenti
def mappa(tid, nome):
    d = os.path.join(LIBMAT, tid)
    f = next((x for x in sorted(os.listdir(d)) if x.startswith(nome + ".")), None) if os.path.isdir(d) else None
    return os.path.join(d, f) if f else None
def ritinta(tid, hexc, contrasto):
    """colore della texture ritinto: luminanza normalizzata alla media, elevata al contrasto, per la tinta (in lineare)."""
    src = mappa(tid, "colore"); out = os.path.join(LIBMAT, tid, "tinte", f"colore_{hexc.strip('#')}_{contrasto:g}.jpg")
    if not src: return None
    if os.path.isfile(out): return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im = bpy.data.images.load(src); w, h = im.size; px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4)
    li = np.where(px[:, :3] <= 0.04045, px[:, :3] / 12.92, ((px[:, :3] + 0.055) / 1.055) ** 2.4)
    L = li @ np.array([0.2126, 0.7152, 0.0722], np.float32); f = (L / max(float(L.mean()), 1e-4)) ** contrasto
    t = np.array(lin(hexc)[:3], np.float32); o = np.clip(f[:, None] * t[None, :], 0, 1)
    o = np.where(o <= 0.0031308, o * 12.92, 1.055 * o ** (1 / 2.4) - 0.055)
    nu = bpy.data.images.new("tinta " + os.path.basename(out), w, h); nu.pixels.foreach_set(np.concatenate([o, px[:, 3:]], 1).ravel())
    nu.filepath_raw = out; nu.file_format = "JPEG"; nu.save(); bpy.data.images.remove(nu); bpy.data.images.remove(im)
    return out
def ruvidita_tarata(tid, media, scala):
    """mappa della ruvidità con la media portata a 'media' e lo scarto moltiplicato per 'scala', in un file nuovo."""
    src = mappa(tid, "ruvidita")
    if not src: return None
    out = os.path.join(LIBMAT, tid, "tinte", f"ruvidita_{media:g}_{scala:g}.jpg")
    if os.path.isfile(out): return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im = bpy.data.images.load(src); im.colorspace_settings.name = "Non-Color"; w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4)
    m0 = float(px[:, 0].mean()); px[:, :3] = np.clip(media + (px[:, :3] - m0) * scala, 0, 1)
    nu = bpy.data.images.new("ruvidita " + os.path.basename(out), w, h); nu.colorspace_settings.name = "Non-Color"
    nu.pixels.foreach_set(px.ravel()); nu.filepath_raw = out; nu.file_format = "JPEG"; nu.save()
    bpy.data.images.remove(nu); bpy.data.images.remove(im)
    return out
def normali_attenuate(tid, forza):
    """mappa delle normali attenuata nel file (mescolata con la normale piatta 0.5, 0.5, 1): l'USD non porta la forza del nodo
    e Unreal la usa piena; così Blender e Unreal vedono lo stesso rilievo."""
    src = mappa(tid, "normali")
    if not src or forza >= 0.999: return src
    out = os.path.join(LIBMAT, tid, "tinte", f"normali_{forza:g}.jpg")
    if os.path.isfile(out): return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im = bpy.data.images.load(src); im.colorspace_settings.name = "Non-Color"; w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4)
    piatta = np.array([0.5, 0.5, 1.0], np.float32); px[:, :3] = piatta + (px[:, :3] - piatta) * forza
    nu = bpy.data.images.new("normali " + os.path.basename(out), w, h); nu.colorspace_settings.name = "Non-Color"
    nu.pixels.foreach_set(px.ravel()); nu.filepath_raw = out; nu.file_format = "JPEG"; nu.save()
    bpy.data.images.remove(nu); bpy.data.images.remove(im)
    return out
def mat_texture(k):
    tid, lato, contrasto, _ = TEX[k]; col = ritinta(tid, ST[TINTA_DI.get(k, k)], contrasto)
    if not col: return None
    m = bpy.data.materials.get("Arredo " + k) or bpy.data.materials.new("Arredo " + k); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = bpy.data.images.load(col, check_existing=True); nt.links.new(tc.outputs["Color"], b.inputs["Base Color"])
    # stoffe: ruvidità costante opaca; la mappa delle foto le faceva lucide come pelle in Unreal (sedie, 2026-11-17)
    r_ = (ruvidita_tarata(tid, *RUV_TEX[k]) if k in RUV_TEX else mappa(tid, "ruvidita")) if k not in STOFFE else None
    if r_:
        tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = bpy.data.images.load(r_, check_existing=True); tr.image.colorspace_settings.name = "Non-Color"
        nt.links.new(tr.outputs["Color"], b.inputs["Roughness"])
    else: b.inputs["Roughness"].default_value = RUV[k]
    if k in STOFFE and "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.5                 # velo delle stoffe (solo Blender)
    n_ = normali_attenuate(tid, min(1.0, NORMALE.get(k, 0.8))) if NORMALE.get(k, 0.8) > 0 else None
    if n_:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(n_, check_existing=True); tn.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = max(1.0, NORMALE.get(k, 0.8))   # sotto 1 è già nel file
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m
def mat(k):
    if k not in MATS and k in TEX:
        mt = mat_texture(k)
        if mt: MATS[k] = mt; return mt
    if k not in MATS:
        m = bpy.data.materials.get("Arredo " + k) or bpy.data.materials.new("Arredo " + k); m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = lin(ST[k]); b.inputs["Roughness"].default_value = RUV[k]
        b.inputs["Metallic"].default_value = 1.0 if k in METALLI else 0.0; MATS[k] = m
        if k in ("lampadina", "led", "lume_dentro", "paralume"):
            b.inputs["Emission Color"].default_value = lin(ST[k]); b.inputs["Emission Strength"].default_value = {"lume_dentro": 0.08, "paralume": 0.6}.get(k, 8.0)
        if k in ("vetro_fume", "vetro_globo"):               # trasparente: in Unreal M_VetroFume / M_VetroGlobo (prepara_render.py)
            b.inputs["Alpha"].default_value = 0.38 if k == "vetro_fume" else 0.30
            try: m.surface_render_method = "BLENDED"
            except Exception: m.blend_method = "BLEND"
        if k == "rovere":                                    # fibra verticale sottile: rumore stirato lungo z (in Unreal M_Rovere)
            nt = m.node_tree; tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (70.0, 70.0, 1.5); nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
            nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 4.0
            nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
            cr = nt.nodes.new("ShaderNodeValToRGB"); c0 = lin(ST[k]); cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.65
            cr.color_ramp.elements[0].color = [x * 0.88 for x in c0[:3]] + [1]; cr.color_ramp.elements[1].color = [min(1, x * 1.04) for x in c0[:3]] + [1]
            nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
        if k == "marmo":                                     # venature: onde distorte dal rumore, sottili e chiare
            nt = m.node_tree; tc = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave")
            wv.inputs["Scale"].default_value = 1.6; wv.inputs["Distortion"].default_value = 14.0; wv.inputs["Detail"].default_value = 6.0
            wv.inputs["Detail Scale"].default_value = 1.5; nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
            cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = lin(ST["vena"])
            cr.color_ramp.elements[1].position = 0.035; cr.color_ramp.elements[1].color = lin(ST["marmo"])
            nt.links.new(wv.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    return MATS[k]


def configura(stile):
    """tinte del progetto da arredi.json ("stile") sopra quelle predefinite; azzera i materiali già fatti."""
    ST.update(stile or {}); MATS.clear()
