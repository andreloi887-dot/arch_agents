"""Prepara la scena di Unreal per i render fissi (fase 5 di PROCEDIMENTO.md), dopo importa_usd.py e sostituisci_arredi.py.

  UnrealEditor-Cmd.exe <progetto>.uproject -run=pythonscript -script="<repo>/skills/rilievo-urbano/scripts/unreal/prepara_render.py <cartella modello> [giorno|sera] [ev=9]" -unattended -nosplash -nop4 -stdout -FullStdOutLogOutput

Cosa fa (si può rilanciare):
  1. Nanite sulle mesh importate sopra NANITE_DA triangoli (prato, contesto): senza, 62 milioni di triangoli pesano su
     ogni fotogramma.
  2. Luce: "giorno" (predefinito) = solo luce naturale, sole e cielo fisici (sole 100 000 lux, quello esportato da
     Blender con data e ora del lotto), luci artificiali spente; "sera" = luci artificiali accese, sole spento. Esposizione fissa: ev=<EV100> (giorno 10,
     sera 5): più alto = più scuro. Ogni camera ha la sua esposizione: quella di uscita_blender/ev_viste_<luce>.json
     (scritto da filiera.py --taratura) se la vista c'è, altrimenti ev.
  2b. Materiali: gres del pavimento con formato e fuga del progetto (dalle UV in metri), perlinato del soffitto con
     le doghe di Blender (dalle UV in metri dell'intradosso), vetro traslucido sulle finestre, legno degli arredi con la venatura di una texture del
     progetto; gli altri restano le tinte di Blender.
  3. Camere fisse dalle viste di <modello>/viste_controllo.txt (le stesse di Blender: nome:x,y,h,tx,ty,th[,focale],
     h sul pavimento, coordinate di Blender in metri) → CineCamera "VISTA_<nome>" nella cartella "Viste".
  4. Level Sequence /Game/Progetto/Viste/LS_viste: un'inquadratura di un fotogramma per camera (la Movie Render Queue
     rende ogni inquadratura come uno scatto, con il suo riscaldamento).
  5. Configurazione della Movie Render Queue /Game/Progetto/Viste/MRQ_viste: PNG 1920×1080, 8 campioni, riscaldamento a
     ogni scatto, uscita in <modello>/uscita_blender/render_unreal/<nome camera>.png.
Controllo: usd/controllo_render.json (mesh con Nanite, luci accese e spente, camere). Il render, sulla scheda grafica:
  UnrealEditor-Cmd.exe <progetto>.uproject /Game/Progetto/Scena -game -LevelSequence="/Game/Progetto/Viste/LS_viste"
      -MoviePipelineConfig="/Game/Progetto/Viste/MRQ_viste" -windowed -ResX=1280 -ResY=720 -notexturestreaming -unattended -log
"""
import json, os, sys
import unreal

argv = [a for a in " ".join(sys.argv[1:]).strip().split(" ") if a]
LUCE = "sera" if "sera" in argv else "giorno"
EV = next((float(a[3:]) for a in argv if a.startswith("ev=")), 10.0 if LUCE == "giorno" else 5.0)
MOD = " ".join(a for a in argv if a not in ("giorno", "sera") and not a.startswith("ev=")).strip('"')
NANITE_DA = 50000
RADICE = "/Game/Progetto"
f_viste = os.path.join(MOD, "viste_controllo.txt"); f_pos = os.path.join(MOD, "uscita_blender", "arredi_posati.json")
if not os.path.isfile(f_viste): raise SystemExit(f"manca {f_viste}")

lib = unreal.EditorAssetLibrary
livelli = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
attori = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not livelli.load_level(RADICE + "/Scena"): raise SystemExit("livello /Game/Progetto/Scena non aperto: lanciare importa_usd.py")

# ------------------------------------------------------------------------------------------------ 1. Nanite
n_nan, tri_nan = 0, 0
# le mesh si prendono dai componenti del livello: in commandlet list_assets non elenca gli asset importati (visto il
# 2026-11-15). I triangoli stanno quasi tutti negli alberi di libreria (1,76 milioni l'uno, una mesh per albero)
uniche = {}
for a in attori.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if sm and sm.get_path_name().startswith(RADICE + "/scena"): uniche[sm.get_path_name()] = sm
for sm in uniche.values():
    t = sm.get_num_triangles(0); ns = sm.get_editor_property("nanite_settings")
    if ns.enabled: n_nan += 1; continue             # già attivo: get_num_triangles(0) ora dà la mesh di ripiego, non l'originale
    if t < NANITE_DA: continue          # StaticMeshEditorSubsystem in commandlet è None: si usa la proprietà
    if not ns.enabled:
        ns.enabled = True
        for nome_p in ("preserve_area", "shape_preservation"):          # fogliame: il nome della proprietà cambia con la versione
            try: ns.set_editor_property(nome_p, True if nome_p == "preserve_area" else unreal.NaniteShapePreservation.PRESERVE_AREA); break
            except Exception: pass
        sm.set_editor_property("nanite_settings", ns); lib.save_loaded_asset(sm)      # il cambio di proprietà ricostruisce la mesh
    n_nan += 1; tri_nan += t
unreal.log(f"CONTROLLO Nanite: {n_nan} mesh con Nanite (soglia {NANITE_DA} triangoli; attivati in questo giro {tri_nan} triangoli)")

# ------------------------------------------------------------------------------------------------ 2. luce
accese = spente = 0
for a in attori.get_all_level_actors():
    for c in a.get_components_by_class(unreal.LightComponentBase):
        if isinstance(c, unreal.DirectionalLightComponent):
            # di sera il sole è spento: con i vetri trasparenti (2026-11-16) il sole del giorno entrava e la "sera" era giorno
            c.set_intensity(100000.0)                                         # lux: sole pieno; il cielo viene dall'atmosfera
            c.set_visibility(LUCE == "giorno"); accese += LUCE == "giorno"; spente += LUCE != "giorno"
        elif isinstance(c, unreal.SkyLightComponent): c.set_visibility(True); accese += 1
        else:
            c.set_visibility(LUCE == "sera"); accese += LUCE == "sera"; spente += LUCE != "sera"
# esposizione fissa: nel render quella automatica non si adatta al sole fisico e l'immagine esce bianca (visto il
# 2026-11-15). Manuale, senza i valori della camera fisica: conta solo il bias, EV100 = -bias.
for a in attori.get_all_level_actors():
    if not isinstance(a, unreal.PostProcessVolume): continue
    ps = a.get_editor_property("settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", -EV)):
        ps.set_editor_property(k, v)
    a.set_editor_property("settings", ps)
unreal.log(f"CONTROLLO luce {LUCE}: {accese} accese, {spente} spente | esposizione fissa EV {EV:g}")

# ------------------------------------------------------------------------------------------------ 2b. materiali
# I materiali procedurali di Blender arrivano come tinte unite. Qui si rifanno quelli che contano di più negli interni:
#  - gres del pavimento: reticolo di piastrelle e fughe dalle UV in metri del pavimento (finiture_interni.py), con formato,
#    fuga e colore di lotto.json → progetto_ifc → finiture → pavimento;
#  - legno degli arredi: venatura di una texture del progetto proiettata nello spazio (i mobili parametrici non hanno UV),
#    con la tinta del legno di arredi.json → stile.
mel = unreal.MaterialEditingLibrary; MP = unreal.MaterialProperty
def colore(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return unreal.LinearColor(*[x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c], 1.0)
def nuovo_materiale(nome):
    p = RADICE + "/Materiali/" + nome
    if lib.does_asset_exist(p): lib.delete_asset(p)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(nome, RADICE + "/Materiali", unreal.Material, unreal.MaterialFactoryNew())
def nodo(m, classe, x, y, **prop):
    n = mel.create_material_expression(m, classe, x, y)
    for k, v in prop.items(): n.set_editor_property(k, v)
    return n
def lega(a, b, ingresso="", uscita=""): mel.connect_material_expressions(a, uscita, b, ingresso)
def maschera(m, sorgente, x, y, canali):
    n = nodo(m, unreal.MaterialExpressionComponentMask, x, y, r="r" in canali, g="g" in canali, b="b" in canali, a=False); lega(sorgente, n); return n
LJ = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8")) if os.path.isfile(os.path.join(MOD, "lotto.json")) else {}
PAV = {"colore": "#BDB6A8", "formato_m": [0.6, 0.6], "fuga_mm": 2.0, "ruvidita": 0.45, **LJ.get("progetto_ifc", {}).get("finiture", {}).get("pavimento", {})}
AJ = json.load(open(os.path.join(MOD, "arredi.json"), encoding="utf-8")) if os.path.isfile(os.path.join(MOD, "arredi.json")) else {}
LEGNO = {"legno": "#C8A47A", **AJ.get("stile", {})}["legno"]

m = nuovo_materiale("M_Gres"); m.set_editor_property("two_sided", True)
uv = nodo(m, unreal.MaterialExpressionTextureCoordinate, -1400, 0)
sc = nodo(m, unreal.MaterialExpressionConstant2Vector, -1400, 150, r=1.0 / PAV["formato_m"][0], g=1.0 / PAV["formato_m"][1])
mu = nodo(m, unreal.MaterialExpressionMultiply, -1200, 0); lega(uv, mu, "A"); lega(sc, mu, "B")
fr = nodo(m, unreal.MaterialExpressionFrac, -1050, 0); lega(mu, fr)
om = nodo(m, unreal.MaterialExpressionOneMinus, -900, 100); lega(fr, om)
mi = nodo(m, unreal.MaterialExpressionMin, -750, 0); lega(fr, mi, "A"); lega(om, mi, "B")
dm = nodo(m, unreal.MaterialExpressionMin, -450, 0); lega(maschera(m, mi, -600, -50, "r"), dm, "A"); lega(maschera(m, mi, -600, 80, "g"), dm, "B")
# dm = distanza dal bordo della piastrella, in frazione di formato: sotto mezza fuga è fuga (0), sopra è piastrella (1)
soglia = nodo(m, unreal.MaterialExpressionConstant, -450, 150, r=PAV["fuga_mm"] / 2000.0 / PAV["formato_m"][0])
st = nodo(m, unreal.MaterialExpressionStep, -300, 0); lega(soglia, st, "Y"); lega(dm, st, "X")
cp = nodo(m, unreal.MaterialExpressionConstant3Vector, -300, 200, constant=colore(PAV["colore"]))
cf = nodo(m, unreal.MaterialExpressionMultiply, -150, 300); lega(cp, cf, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -300, 380, r=0.55), cf, "B")
le = nodo(m, unreal.MaterialExpressionLinearInterpolate, 0, 100); lega(cf, le, "A"); lega(cp, le, "B"); lega(st, le, "Alpha")
mel.connect_material_property(le, "", MP.MP_BASE_COLOR)
ru = nodo(m, unreal.MaterialExpressionLinearInterpolate, 0, 350)
lega(nodo(m, unreal.MaterialExpressionConstant, -150, 450, r=0.9), ru, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -150, 520, r=PAV["ruvidita"]), ru, "B"); lega(st, ru, "Alpha")
mel.connect_material_property(ru, "", MP.MP_ROUGHNESS)
mel.recompile_material(m); lib.save_loaded_asset(m); M_GRES = m

ROVERE = {"rovere": "#CBB495", **AJ.get("stile", {})}["rovere"]
MARMO, VENA = ({"marmo": "#E4DDD2", "vena": "#B9AE9F", **AJ.get("stile", {})}[k] for k in ("marmo", "vena"))
T_ALB = "/Game/JapaneseFurniture_Modern/Materials/Textures/T_Wooden_Albedo"
def legno(nome, tinta):
    """venatura di una texture del progetto proiettata nello spazio (i mobili parametrici non hanno UV), sulla tinta."""
    m = nuovo_materiale(nome); m.set_editor_property("two_sided", True)
    wp = nodo(m, unreal.MaterialExpressionWorldPosition, -1300, 0)
    # proiezione semplice, adatta a un mobile: (x + y) di traverso alla venatura, z lungo; una texture ogni 1,2 m
    su = nodo(m, unreal.MaterialExpressionAdd, -800, -70); lega(maschera(m, wp, -1000, -120, "r"), su, "A"); lega(maschera(m, wp, -1000, -20, "g"), su, "B")
    ap = nodo(m, unreal.MaterialExpressionAppendVector, -650, 0); lega(su, ap, "A"); lega(maschera(m, wp, -1000, 80, "b"), ap, "B")
    uvw = nodo(m, unreal.MaterialExpressionMultiply, -500, 0); lega(ap, uvw, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -650, 150, r=1.0 / 120.0), uvw, "B")
    tx = nodo(m, unreal.MaterialExpressionTextureSample, -350, 0, texture=lib.load_asset(T_ALB)); lega(uvw, tx, "UVs")
    ds = nodo(m, unreal.MaterialExpressionDesaturation, -150, 0); lega(tx, ds, "", "RGB")
    # la venatura in grigio, portata attorno a 1, moltiplica la tinta del progetto
    g2 = nodo(m, unreal.MaterialExpressionMultiply, 0, 0); lega(ds, g2, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -150, 120, r=2.2), g2, "B")
    fi = nodo(m, unreal.MaterialExpressionMultiply, 150, 100); lega(g2, fi, "A"); lega(nodo(m, unreal.MaterialExpressionConstant3Vector, 0, 200, constant=colore(tinta)), fi, "B")
    mel.connect_material_property(fi, "", MP.MP_BASE_COLOR)
    mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, 150, 300, r=0.5), "", MP.MP_ROUGHNESS)
    mel.recompile_material(m); lib.save_loaded_asset(m); return m
M_LEGNO = legno("M_Legno", LEGNO) if lib.does_asset_exist(T_ALB) else None
# rovere di cucina, tavolo, letti, comodini e armadi (Andrea, 2026-11-16): come in Blender, fibra verticale sottile da un rumore
# stirato lungo z (la texture della libreria dava nodi grandi, venatura orizzontale e una cucitura a 1,2 m)
m = nuovo_materiale("M_Rovere"); m.set_editor_property("two_sided", True)
wp = nodo(m, unreal.MaterialExpressionWorldPosition, -1300, 0)
st_ = nodo(m, unreal.MaterialExpressionMultiply, -1100, 0); lega(wp, st_, "A")
lega(nodo(m, unreal.MaterialExpressionConstant3Vector, -1300, 150, constant=unreal.LinearColor(0.7, 0.7, 0.015, 1)), st_, "B")
nz = nodo(m, unreal.MaterialExpressionNoise, -900, 0, scale=1.0, levels=4, output_min=0.0, output_max=1.0); lega(st_, nz, "Position")
c0 = colore(ROVERE)
cr = nodo(m, unreal.MaterialExpressionLinearInterpolate, -600, 0)
lega(nodo(m, unreal.MaterialExpressionConstant3Vector, -800, -100, constant=unreal.LinearColor(c0.r * 0.88, c0.g * 0.88, c0.b * 0.88, 1)), cr, "A")
lega(nodo(m, unreal.MaterialExpressionConstant3Vector, -800, 100, constant=unreal.LinearColor(min(1, c0.r * 1.04), min(1, c0.g * 1.04), min(1, c0.b * 1.04), 1)), cr, "B")
lega(nz, cr, "Alpha")
mel.connect_material_property(cr, "", MP.MP_BASE_COLOR)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -600, 200, r=0.5), "", MP.MP_ROUGHNESS)
mel.recompile_material(m); lib.save_loaded_asset(m); M_ROVERE = m
# LED e interno dei lampadari: emissivi anche in Unreal (in Blender hanno l'emissione, dall'USD arrivava solo la tinta)
def emissivo(nome, tinta, forza):
    m = nuovo_materiale(nome); m.set_editor_property("two_sided", True)
    c_ = colore(tinta); mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant3Vector, -300, 0, constant=c_), "", MP.MP_BASE_COLOR)
    mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant3Vector, -300, 150,
                                       constant=unreal.LinearColor(c_.r * forza, c_.g * forza, c_.b * forza, 1)), "", MP.MP_EMISSIVE_COLOR)
    mel.recompile_material(m); lib.save_loaded_asset(m); return m
ACC = 1.0 if LUCE == "sera" else 0.0                      # di giorno le luci artificiali sono spente, anche i LED
M_LED = emissivo("M_Led", "#FFD9A8", 40.0 * ACC); M_LUME = emissivo("M_LumeDentro", "#E9A65C", 3.0 * ACC)
# marmo del paraschizzi: come in Blender, onde distorte dal rumore → venature sottili sulla tinta
m = nuovo_materiale("M_Marmo"); m.set_editor_property("two_sided", True)
wp = nodo(m, unreal.MaterialExpressionWorldPosition, -1400, 0)
ns = nodo(m, unreal.MaterialExpressionNoise, -1150, 150, scale=0.006, levels=6, output_min=-1.0, output_max=1.0); lega(wp, ns, "Position")
lin_ = nodo(m, unreal.MaterialExpressionAdd, -1000, -50); lega(maschera(m, wp, -1200, -100, "r"), lin_, "A"); lega(maschera(m, wp, -1200, 0, "b"), lin_, "B")
t1 = nodo(m, unreal.MaterialExpressionMultiply, -1000, 60); lega(lin_, t1, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -1150, 60, r=0.045), t1, "B")
t2 = nodo(m, unreal.MaterialExpressionMultiply, -1000, 200); lega(ns, t2, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -1150, 260, r=1.4), t2, "B")
fase = nodo(m, unreal.MaterialExpressionAdd, -850, 100); lega(t1, fase, "A"); lega(t2, fase, "B")
sn = nodo(m, unreal.MaterialExpressionSine, -700, 100, period=6.283185); lega(fase, sn)
ab = nodo(m, unreal.MaterialExpressionAbs, -580, 100); lega(sn, ab)
ve = nodo(m, unreal.MaterialExpressionMultiply, -460, 100); lega(ab, ve, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -580, 180, r=22.0), ve, "B")
sa = nodo(m, unreal.MaterialExpressionSaturate, -340, 100); lega(ve, sa)
cm = nodo(m, unreal.MaterialExpressionLinearInterpolate, -180, 100)
lega(nodo(m, unreal.MaterialExpressionConstant3Vector, -340, 0, constant=colore(VENA)), cm, "A"); lega(nodo(m, unreal.MaterialExpressionConstant3Vector, -340, 220, constant=colore(MARMO)), cm, "B"); lega(sa, cm, "Alpha")
mel.connect_material_property(cm, "", MP.MP_BASE_COLOR)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -180, 300, r=0.22), "", MP.MP_ROUGHNESS)
mel.recompile_material(m); lib.save_loaded_asset(m); M_MARMO = m
# perlinato del soffitto (Andrea, 2026-11-16: "il soffitto lo voglio con le perline"): in Blender è un Brick procedurale
# sulle UV in metri dell'intradosso (finiture_interni.py: u lungo le doghe, v lungo la pendenza) e in USD arriva come
# tinta unita. Qui lo stesso disegno: doghe larghe doga_m e continue (Andrea, 2026-11-16: nessuna giunzione trasversale
# in vista, i tagli stanno nascosti sopra le travi), fuga longitudinale di 4 mm al 70 % della tinta, due toni (1 e 0,96)
# che cambiano da una doga all'altra.
SOF = {"colore": "#EFE8D6", "doga_m": 0.12, **LJ.get("progetto_ifc", {}).get("finiture", {}).get("soffitto", {})}
DW, FU = SOF["doga_m"], 0.004
m = nuovo_materiale("M_Perlinato"); m.set_editor_property("two_sided", True)
def k(v, x, y): return nodo(m, unreal.MaterialExpressionConstant, x, y, r=v)
def op(classe, a, b, x, y):
    n = nodo(m, classe, x, y); lega(a, n, "A"); lega(b, n, "B"); return n
def uno(classe, a, x, y):
    n = nodo(m, classe, x, y); lega(a, n); return n
uv = nodo(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
vv = maschera(m, uv, -2050, 100, "g")                                                        # v: lungo la pendenza
vr = op(unreal.MaterialExpressionMultiply, vv, k(1.0 / DW, -2050, 200), -1900, 100)          # v in doghe
fila = uno(unreal.MaterialExpressionFloor, vr, -1750, 200)
fr = uno(unreal.MaterialExpressionFrac, vr, -1000, 150)
mi = op(unreal.MaterialExpressionMin, fr, uno(unreal.MaterialExpressionOneMinus, fr, -900, 230), -800, 150)
dmin = op(unreal.MaterialExpressionMultiply, mi, k(DW, -800, 250), -650, 150)               # distanza dalla fuga, in metri
st = nodo(m, unreal.MaterialExpressionStep, -350, 0); lega(k(FU / 2, -500, 120), st, "Y"); lega(dmin, st, "X")   # 1 doga, 0 fuga
# tono della doga: hash dell'indice della fila → 1 o 0,96
hx = op(unreal.MaterialExpressionMultiply, fila, k(78.233, -1000, 600), -850, 550)
sn = nodo(m, unreal.MaterialExpressionSine, -550, 450, period=6.283185); lega(hx, sn)
hs = uno(unreal.MaterialExpressionFrac, op(unreal.MaterialExpressionMultiply, sn, k(43758.5453, -550, 550), -400, 450), -250, 450)
tono = nodo(m, unreal.MaterialExpressionLinearInterpolate, -100, 450); lega(k(0.96, -250, 550), tono, "A"); lega(k(1.0, -250, 620), tono, "B")
sh = nodo(m, unreal.MaterialExpressionStep, -250, 700); lega(k(0.5, -400, 750), sh, "Y"); lega(hs, sh, "X"); lega(sh, tono, "Alpha")
cp = nodo(m, unreal.MaterialExpressionConstant3Vector, -350, 200, constant=colore(SOF["colore"]))
cd = op(unreal.MaterialExpressionMultiply, cp, tono, -150, 200)
cf = op(unreal.MaterialExpressionMultiply, cp, k(0.7, -350, 320), -150, 320)
le = nodo(m, unreal.MaterialExpressionLinearInterpolate, 50, 100); lega(cf, le, "A"); lega(cd, le, "B"); lega(st, le, "Alpha")
mel.connect_material_property(le, "", MP.MP_BASE_COLOR)
mel.connect_material_property(k(0.55, 50, 300), "", MP.MP_ROUGHNESS)
mel.recompile_material(m); lib.save_loaded_asset(m); M_PERL = m
# vetro (Andrea, 2026-11-16: in Unreal faceva da specchio). I vetri dell'IFC arrivano come istanze di UsdPreviewSurface
# con Opacity 0,2, ma il materiale base è opaco e l'opacità si perde: lastra bianca lucida che riflette la stanza.
# Qui un vetro traslucido vero: quasi incolore, riflesso di Fresnel basso, niente ombra (il sole entra come in Blender).
m = nuovo_materiale("M_Vetro"); m.set_editor_property("two_sided", True)
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
tlm = [k for k in dir(unreal.TranslucencyLightingMode) if "FORWARD" in k.upper()]      # il nome cambia tra versioni
unreal.log(f"modi di luce del traslucido: {[k for k in dir(unreal.TranslucencyLightingMode) if k.isupper()]}")
if tlm: m.set_editor_property("translucency_lighting_mode", getattr(unreal.TranslucencyLightingMode, tlm[0]))
fre = nodo(m, unreal.MaterialExpressionFresnel, -400, 300)
op_ = nodo(m, unreal.MaterialExpressionLinearInterpolate, -150, 300)
lega(nodo(m, unreal.MaterialExpressionConstant, -400, 200, r=0.06), op_, "A"); lega(nodo(m, unreal.MaterialExpressionConstant, -400, 420, r=0.5), op_, "B"); lega(fre, op_, "Alpha")
mel.connect_material_property(op_, "", MP.MP_OPACITY)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant3Vector, -150, 0, constant=unreal.LinearColor(0.85, 0.9, 0.88, 1)), "", MP.MP_BASE_COLOR)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -150, 120, r=0.02), "", MP.MP_ROUGHNESS)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -150, 180, r=0.5), "", MP.MP_SPECULAR)
mel.recompile_material(m); lib.save_loaded_asset(m); M_VETRO = m
# vetro fumé bronzo dell'armadio della matrimoniale (riferimento di Andrea, 2026-11-16): traslucido scuro, riflesso medio
m = nuovo_materiale("M_VetroFume"); m.set_editor_property("two_sided", True)
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
if tlm: m.set_editor_property("translucency_lighting_mode", getattr(unreal.TranslucencyLightingMode, tlm[0]))
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant3Vector, -150, 0, constant=colore("#3E2C1F")), "", MP.MP_BASE_COLOR)
# bronzo che si vede (2026-11-17: con 0,42 il vetro spariva e l'armadio sembrava aperto) e riflesso pieno del vetro
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -150, 100, r=0.62), "", MP.MP_OPACITY)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -150, 160, r=0.03), "", MP.MP_ROUGHNESS)
mel.connect_material_property(nodo(m, unreal.MaterialExpressionConstant, -150, 220, r=0.8), "", MP.MP_SPECULAR)
mel.recompile_material(m); lib.save_loaded_asset(m); M_FUME = m
def con_texture(mm):
    """istanza USD con la texture del colore (materiali con texture vere di arredi_interni.py, 2026-11-17): si lascia com'è."""
    try: return isinstance(mm, unreal.MaterialInstance) and mel.get_material_instance_scalar_parameter_value(mm, "UseBaseColorTexture") > 0.5
    except Exception: return False
def opacita(mm):
    try: return mel.get_material_instance_scalar_parameter_value(mm, "Opacity") if isinstance(mm, unreal.MaterialInstance) else 1.0
    except Exception: return 1.0
n_gres = n_legno = n_perl = n_vetro = n_rovere = n_marmo = n_fume = n_led = n_tex = 0; vetri_nomi = set(); vuoti = set()
for a in attori.get_all_level_actors():
    if a.get_class().get_name() != "Actor": continue
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        for i in range(c.get_num_materials()):
            mm = c.get_material(i); nm = mm.get_name() if mm else ""
            if nm.startswith("MI_Pavimento") or nm == "M_Gres": c.set_material(i, M_GRES); n_gres += 1
            elif nm.startswith(("MI_Arredo_legno", "MI_Arredo_rovere", "MI_Arredo_marmo")) and con_texture(mm): n_tex += 1
            elif M_LEGNO and (nm.startswith("MI_Arredo_legno") or nm == "M_Legno"): c.set_material(i, M_LEGNO); n_legno += 1
            elif M_ROVERE and (nm.startswith("MI_Arredo_rovere") or nm == "M_Rovere"): c.set_material(i, M_ROVERE); n_rovere += 1
            elif nm.startswith("MI_Arredo_marmo") or nm == "M_Marmo": c.set_material(i, M_MARMO); n_marmo += 1
            elif nm.startswith("MI_Arredo_led") or nm == "M_Led": c.set_material(i, M_LED); n_led += 1
            elif nm.startswith("MI_Arredo_lume_dentro") or nm == "M_LumeDentro": c.set_material(i, M_LUME); n_led += 1
            elif nm.startswith("MI_Perlinato") or nm == "M_Perlinato": c.set_material(i, M_PERL); n_perl += 1
            elif nm.startswith("MI_Arredo_vetro_fume") or nm == "M_VetroFume": c.set_material(i, M_FUME); n_fume += 1
            elif nm == "M_Vetro" or (nm.startswith("MI_") and 0.0 < opacita(mm) < 0.99): c.set_material(i, M_VETRO); n_vetro += 1; vetri_nomi.add(nm)
            elif nm.startswith("MI_") and opacita(mm) <= 0.0: vuoti.add(nm)
unreal.log(f"CONTROLLO materiali: gres su {n_gres} parti (formato {PAV['formato_m']}, fuga {PAV['fuga_mm']} mm), legno su {n_legno} parti, "
           f"con texture dall'USD {n_tex}, rovere procedurale su {n_rovere}, marmo procedurale su {n_marmo}, vetro fumé su {n_fume}, luminosi su {n_led}, perlinato su {n_perl} parti (doga {DW * 100:.0f} cm), vetro su {n_vetro} parti ({', '.join(sorted(vetri_nomi))})")
if not n_vetro: unreal.log_warning("AVVISO vetro su 0 parti: le finestre restano opache")
if vuoti: unreal.log(f"materiali con opacità 0 lasciati come sono: {', '.join(sorted(vuoti))}")
if not n_perl: unreal.log_warning("AVVISO perlinato su 0 parti: il soffitto resta liscio")

# ------------------------------------------------------------------------------------------------ 3. camere
f_ev = os.path.join(MOD, "uscita_blender", f"ev_viste_{LUCE}.json")       # scritto da filiera.py --taratura
EV_VISTE = {k: v for k, v in json.load(open(f_ev, encoding="utf-8")).items() if not k.startswith("_")} if os.path.isfile(f_ev) else {}
EV_USATI = {}
z0 = 0.0
if os.path.isfile(f_pos):   # quota del pavimento: appoggio dei mobili (4 mm sopra il vano)
    zz = [a["centro_m"][2] for a in json.load(open(f_pos, encoding="utf-8"))["arredi"] if a["tipo"] != "lampada" and a["villa"] == 1]
    if zz: z0 = min(zz) - 0.004
for a in attori.get_all_level_actors():
    if str(a.get_folder_path()) == "Viste": attori.destroy_actor(a)
camere = []
for r in open(f_viste, encoding="utf-8"):
    r = r.strip()
    if not r or r.startswith("#"): continue
    nome, val = r.split(":"); n = [float(x) for x in val.split(",")]
    occhio = unreal.Vector(n[0] * 100, -n[1] * 100, (z0 + n[2]) * 100); mira = unreal.Vector(n[3] * 100, -n[4] * 100, (z0 + n[5]) * 100)
    cam = attori.spawn_actor_from_class(unreal.CineCameraActor, occhio, unreal.MathLibrary.find_look_at_rotation(occhio, mira))
    cam.set_actor_label("VISTA_" + nome); cam.set_folder_path("Viste")
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback"); fb.sensor_width = 36.0; fb.sensor_height = 20.25; cc.set_editor_property("filmback", fb)
    cc.set_editor_property("current_focal_length", n[6] if len(n) > 6 else 16.0)
    fs = cc.get_editor_property("focus_settings"); fs.focus_method = unreal.CameraFocusMethod.DISABLE; cc.set_editor_property("focus_settings", fs)
    # esposizione della vista: EV tarato (filiera.py --taratura) se c'è, altrimenti quello generale. La camera vince sul volume
    ev_c = EV_VISTE.get("VISTA_" + nome, EV); EV_USATI["VISTA_" + nome] = ev_c
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", -ev_c)):
        pp.set_editor_property(k, v)
    cc.set_editor_property("post_process_settings", pp); cc.set_editor_property("post_process_blend_weight", 1.0)
    camere.append(cam)
unreal.log(f"CONTROLLO camere: {[c.get_actor_label() for c in camere]} | pavimento a {z0:.3f} m | EV {EV_USATI}"
           + (f" (tarati da {os.path.basename(f_ev)})" if EV_VISTE else ""))

# ------------------------------------------------------------------------------------------------ 4. sequenza
cart = RADICE + "/Viste"; p_seq = cart + "/LS_viste"
if lib.does_asset_exist(p_seq): lib.delete_asset(p_seq)
seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset("LS_viste", cart, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(25, 1)); seq.set_playback_start(0); seq.set_playback_end(len(camere))
taglio = seq.add_track(unreal.MovieSceneCameraCutTrack)
for i, cam in enumerate(camere):
    b = seq.add_possessable(cam)
    s = taglio.add_section(); s.set_range(i, i + 1)
    s.set_camera_binding_id(seq.get_binding_id(b))
lib.save_loaded_asset(seq)

# ------------------------------------------------------------------------------------------------ 5. Movie Render Queue
# Configurazione salvata nel progetto: il render parte da riga di comando con -game (usa la scheda grafica e si chiude
# da solo). -ExecutePythonScript non va bene: l'editor esegue lo script ed esce subito (provato il 2026-11-15).
# giorno in render_unreal/, sera in render_unreal_sera/: un giro non cancella l'altro
USCITA_R = os.path.join(MOD, "uscita_blender", "render_unreal" + ("" if LUCE == "giorno" else "_" + LUCE)).replace("\\", "/"); os.makedirs(USCITA_R, exist_ok=True)
cfg = unreal.MoviePipelinePrimaryConfig()
out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_directory = unreal.DirectoryPath(USCITA_R); out.file_name_format = "{camera_name}"
out.output_resolution = unreal.IntPoint(1920, 1080); out.override_existing_output = True; out.zero_pad_frame_numbers = 0
cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.spatial_sample_count = 8; aa.temporal_sample_count = 1
aa.override_anti_aliasing = True; aa.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE
# riscaldamento a ogni scatto: Lumen e l'esposizione automatica si assestano prima del fotogramma buono
aa.use_camera_cut_for_warm_up = False; aa.engine_warm_up_count = 96; aa.render_warm_up_count = 64; aa.render_warm_up_frames = True
cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting).cinematic_quality_settings = True
p_cfg = cart + "/MRQ_viste"
if lib.does_asset_exist(p_cfg): lib.delete_asset(p_cfg)
# il primo argomento è il percorso completo del pacchetto: passando solo la cartella l'asset finisce un livello più su
unreal.MoviePipelineEditorLibrary.export_config_to_asset(cfg, p_cfg, "MRQ_viste", True)
if lib.does_asset_exist(RADICE + "/MRQ_viste"): lib.delete_asset(RADICE + "/MRQ_viste")        # avanzo della prima prova
unreal.log(f"CONTROLLO configurazione render {p_cfg}: {lib.does_asset_exist(p_cfg)} | uscita {USCITA_R}")
livelli.save_current_level(); unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
json.dump({"luce": LUCE, "ev": EV, "gres_parti": n_gres, "legno_parti": n_legno, "perlinato_parti": n_perl, "vetro_parti": n_vetro, "rovere_parti": n_rovere, "marmo_parti": n_marmo, "fume_parti": n_fume, "texture_usd_parti": n_tex, "luminosi_parti": n_led, "ev_viste": EV_USATI, "ev_tarati": bool(EV_VISTE), "nanite_mesh": n_nan, "nanite_triangoli": tri_nan, "luci_accese": int(accese), "luci_spente": int(spente),
           "camere": [c.get_actor_label() for c in camere], "sequenza": p_seq, "configurazione": p_cfg, "uscita": USCITA_R},
          open(os.path.join(MOD, "uscita_blender", "usd", "controllo_render.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
unreal.log("CONTROLLO sequenza " + p_seq + " salvata")
