"""Mette i modelli di libreria (Fab/Megascans gratuiti, Poly Haven CC0, libreria di studio) al posto dei mobili e delle
lampade parametrici arrivati da Blender. Fase 5 di PROCEDIMENTO.md; dopo importa_usd.py.

  UnrealEditor-Cmd.exe <progetto>.uproject -run=pythonscript -script="<repo>/skills/rilievo-urbano/scripts/unreal/sostituisci_arredi.py <cartella modello> [--prova]" -unattended -nosplash -nop4 -stdout -FullStdOutLogOutput

Legge:
  <modello>/uscita_blender/arredi_posati.json   scritto da arredi_interni.py: per ogni pezzo centro, asse lungo, fronte, misure
  <modello>/arredi_unreal.json                  la scelta degli asset, per tipo o per nome del pezzo (il nome vince):
      {"divano": {"asset": "/Game/Libreria/Arredi/Divano_3p", "adatta": "uniforme", "ruota_gradi": 0, "appoggio": "basso"},
       "Tavolo da 4 v1": {"asset": "..."}}
    asset        percorso dello Static Mesh nel progetto (deve esistere: lo script non scarica niente)
    adatta       "uniforme" (predefinito: stessa scala sui tre assi, il pezzo entra nell'ingombro in pianta), "esatta"
                 (scala per asse: solo per pezzi che si possono deformare, armadi e pareti attrezzate), "nessuna",
                 "altezza" (stessa scala sui tre assi perché l'altezza torni, mai sopra 1 né sotto scala_min, 0.6:
                 lampade a sospensione, che non devono pendere più in basso del previsto)
    ruota_gradi  rotazione dell'asset attorno a Z perché il suo lato lungo sia su X e il fronte su +Y; se il pezzo ha un
                 "verso" (letto: dai piedi alla testata), perché quella direzione dell'asset sia su +X
    appoggio     "basso" (a pavimento) o "alto" (lampade: appese, la cima resta dov'era)
    con          altri asset messi nello stesso punto, con la stessa rotazione e scala: [{"asset": "...", "z_cm": 20}]
                 (materasso sul letto, lampada sul comodino); z_cm è l'altezza sull'origine dell'asset principale
Per ogni pezzo con un asset: toglie gli attori parametrici con quel nome, mette l'asset nella stessa posizione e con lo
stesso orientamento, in una cartella "Arredi di libreria". I pezzi senza asset restano parametrici e finiscono
nell'elenco. Coordinate: Unreal = (x, -y, z) × 100 rispetto a Blender.
Controllo: usd/controllo_arredi.json con sostituiti, rimasti parametrici e scarti di misura oltre il 15 % (con "nessuna" e
"altezza" solo se il modello è più grande del posto in pianta).
--prova: non salva il livello (serve a verificare posizioni e scale).
"""
import json, math, os, re, sys
import unreal

argv = " ".join(sys.argv[1:]).strip()
PROVA = "--prova" in argv
MOD = argv.replace("--prova", "").strip().strip('"')
f_pos = os.path.join(MOD, "uscita_blender", "arredi_posati.json"); f_map = os.path.join(MOD, "arredi_unreal.json")
if not os.path.isfile(f_pos): raise SystemExit(f"manca {f_pos}: lanciare arredi_interni.py (filiera, passo arredi)")
POSATI = json.load(open(f_pos, encoding="utf-8"))["arredi"]
MAPPA = {k: v for k, v in (json.load(open(f_map, encoding="utf-8")) if os.path.isfile(f_map) else {}).items() if not k.startswith("_")}

livelli = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
attori = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not livelli.load_level("/Game/Progetto/Scena"): raise SystemExit("livello /Game/Progetto/Scena non aperto: lanciare importa_usd.py")

def pulito(nome): return re.sub(r"[^A-Za-z0-9]", "_", nome)        # come l'export USD scrive i nomi
tutti = attori.get_all_level_actors()
for a in tutti:                                                    # rilancio: i modelli messi la volta prima si rifanno
    if str(a.get_folder_path()) == "Arredi di libreria": attori.destroy_actor(a)
tutti = attori.get_all_level_actors()

MESH = [c for a in tutti if a.get_class().get_name() == "Actor" for c in a.get_components_by_class(unreal.StaticMeshComponent)]
PREFISSI = {pulito(p["nome"].split(" v")[0]) for p in POSATI}
for c in MESH:                                                     # rilancio: tornano visibili i volumi nascosti la volta prima
    if not c.is_visible() and any(c.get_name().startswith(k) for k in PREFISSI): c.set_visibility(True); c.set_hidden_in_game(False)
fatti, parametrici, scarti, senza_volume, luci_spostate = [], [], [], [], []
LUCI = [l for a in tutti for l in a.get_components_by_class(unreal.PointLightComponent)]    # anche le spot: sottoclasse
for p in POSATI:
    scelta = MAPPA.get(p["nome"]) or MAPPA.get(p["tipo"])
    if not scelta: parametrici.append(p["nome"]); continue
    sm = unreal.EditorAssetLibrary.load_asset(scelta["asset"]) if unreal.EditorAssetLibrary.does_asset_exist(scelta["asset"]) else None
    if not isinstance(sm, unreal.StaticMesh):
        unreal.log_warning(f"AVVISO {p['nome']}: asset {scelta['asset']} non trovato o non è uno Static Mesh"); parametrici.append(p["nome"]); continue
    bb = sm.get_bounding_box(); dim = bb.max - bb.min; cen = (bb.max + bb.min) * 0.5      # cm, riferimento dell'asset
    r0 = math.radians(scelta.get("ruota_gradi", 0)); c0, s0 = abs(math.cos(r0)), abs(math.sin(r0))
    dx, dy = dim.x * c0 + dim.y * s0, dim.x * s0 + dim.y * c0                              # misure dopo la rotazione propria
    L, W, H = (m * 100 for m in p["misure_m"])
    modo = scelta.get("adatta", "uniforme")
    if modo == "esatta": sx, sy, sz = L / dx, W / dy, H / dim.z
    elif modo == "nessuna": sx = sy = sz = 1.0
    elif modo == "altezza": sx = sy = sz = max(scelta.get("scala_min", 0.6), min(1.0, H / dim.z))
    else: sx = sy = sz = min(L / dx, W / dy)
    for asse, voluto, avuto in (("lungo", L, dx * sx), ("profondo", W, dy * sy), ("alto", H, dim.z * sz)):
        # con "nessuna" e "altezza" il modello ha le sue misure: conta solo se in pianta è più grande del posto
        fuori = avuto > 1.15 * voluto and asse != "alto" if modo in ("nessuna", "altezza") else abs(avuto - voluto) > 0.15 * voluto
        if fuori: scarti.append(f"{p['nome']}: {asse} {avuto:.0f} cm invece di {voluto:.0f}")
    # orientamento: asse lungo su X; se il fronte finisce dalla parte opposta di +Y si gira di 180°
    ux, uy = p["lungo"][0], -p["lungo"][1]; fx, fy = p["fronte"][0], -p["fronte"][1]
    if p.get("verso"): ux, uy = p["verso"][0], -p["verso"][1]              # direzione principale: X del pezzo, senza controllo del fronte
    yaw = math.degrees(math.atan2(uy, ux))
    if not p.get("verso") and -math.sin(math.radians(yaw)) * fx + math.cos(math.radians(yaw)) * fy < 0: yaw += 180.0
    yaw_tot = yaw + scelta.get("ruota_gradi", 0)
    # posizione: il centro in pianta dell'asset sul centro del pezzo; base a terra, oppure cima dov'era (lampade)
    x, y, z = p["centro_m"][0] * 100, -p["centro_m"][1] * 100, p["centro_m"][2] * 100
    if modo == "esatta" and scelta.get("ruota_gradi", 0) % 180: sx, sy = sy, sx       # la scala è negli assi dell'asset
    rt = math.radians(yaw_tot); ox, oy = cen.x * sx, cen.y * sy            # scala nel riferimento dell'asset, poi rotazione
    px = x - (ox * math.cos(rt) - oy * math.sin(rt)); py = y - (ox * math.sin(rt) + oy * math.cos(rt))
    pz = z - bb.min.z * sz if scelta.get("appoggio", "basso") == "basso" else z + H - bb.max.z * sz
    # via il volume parametrico (anche la parte tessile). L'import USD mette tutte le mesh come componenti dell'attore
    # "scena", con nomi un po' diversi da quelli di Blender, e le luci delle lampade hanno lo stesso nome del pezzo: si
    # nascondono solo i componenti mesh che cominciano con il nome del pezzo (senza villa e numero) e stanno dentro il suo
    # ingombro. Mai le luci (errore del 2026-11-15: cercando per nome dell'attore si erano cancellate le 29 luci a punto).
    inizio = pulito(p["nome"].split(" v")[0]); raggio = max(L, W) / 2 + 10; n_via = 0
    for c in MESH:
        if not c.get_name().startswith(inizio): continue
        o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
        if math.hypot(o.x - x, o.y - y) <= raggio and z - 30 <= o.z <= z + H + 30:
            c.set_visibility(False); c.set_hidden_in_game(True); c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION); n_via += 1
    if not n_via: senza_volume.append(p["nome"])
    # spawn_actor_from_object in commandlet restituisce None (provato 2026-11-15): attore vuoto e mesh assegnata
    n = attori.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(px, py, pz), unreal.Rotator(0, 0, yaw_tot))
    n.static_mesh_component.set_static_mesh(sm)
    n.set_actor_scale3d(unreal.Vector(sx, sy, sz)); n.set_actor_label("LIB_" + pulito(p["nome"])); n.set_folder_path("Arredi di libreria")
    lume = None                                                                # lampada da tavolo messa con "con"
    for k, extra in enumerate(scelta.get("con", [])):
        sm2 = unreal.EditorAssetLibrary.load_asset(extra["asset"]) if unreal.EditorAssetLibrary.does_asset_exist(extra["asset"]) else None
        if not isinstance(sm2, unreal.StaticMesh): unreal.log_warning(f"AVVISO {p['nome']}: asset {extra['asset']} non trovato"); continue
        n2 = attori.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(px, py, pz + extra.get("z_cm", 0) * sz), unreal.Rotator(0, 0, yaw_tot))
        n2.static_mesh_component.set_static_mesh(sm2); n2.set_actor_scale3d(unreal.Vector(sx, sy, sz))
        n2.set_actor_label(f"LIB_{pulito(p['nome'])}_{k + 1}"); n2.set_folder_path("Arredi di libreria")
        if "lamp" in extra["asset"].lower(): lume = n2
    o, e = n.get_actor_bounds(False)
    if p["tipo"] == "lampada":
        # la luce di Blender sta 3 cm sotto il bordo del paralume parametrico: con il modello di libreria resterebbe fuori,
        # sotto la sfera (controllo del 2026-11-16: 27 sospensioni su 29 da 3 a 16 cm sotto, 2 fuori centro). Va al centro del
        # paralume: in pianta al centro del modello, in quota a metà larghezza sopra il fondo.
        dentro = unreal.Vector(o.x, o.y, o.z - e.z + min(e.x, e.y, e.z))
        vicine = [l for l in LUCI if math.hypot(l.get_world_location().x - x, l.get_world_location().y - y) < 30
                  and z - 40 <= l.get_world_location().z <= z + H + 10]
        for l in vicine: l.set_world_location(dentro, False, False)
        if len(vicine) != 1: unreal.log_warning(f"AVVISO {p['nome']}: {len(vicine)} luci trovate vicino alla lampada invece di 1")
        luci_spostate.append({"nome": p["nome"], "luci": len(vicine), "a_cm": [round(dentro.x, 1), round(dentro.y, 1), round(dentro.z, 1)]})
    if lume:
        # abat-jour (2026-11-16): la luce di arredi_interni.py sta nel paralume parametrico, 72 cm sul pavimento e 5 cm
        # dietro il centro del comodino; va nel paralume della lampada di libreria, a un terzo dell'altezza sotto la cima
        o2, e2 = lume.get_actor_bounds(False)
        dentro = unreal.Vector(o2.x, o2.y, o2.z + e2.z - 2 * e2.z / 3)
        vicine = [l for l in LUCI if math.hypot(l.get_world_location().x - x, l.get_world_location().y - y) < 40
                  and z <= l.get_world_location().z <= z + H + 40]
        for l in vicine: l.set_world_location(dentro, False, False)
        if len(vicine) != 1: unreal.log_warning(f"AVVISO {p['nome']}: {len(vicine)} luci trovate vicino all'abat-jour invece di 1")
        luci_spostate.append({"nome": p["nome"] + " (abat-jour)", "luci": len(vicine), "a_cm": [round(dentro.x, 1), round(dentro.y, 1), round(dentro.z, 1)]})
    fatti.append({"nome": p["nome"], "asset": scelta["asset"], "scala": [round(sx, 3), round(sy, 3), round(sz, 3)],
                  "centro_cm": [round(o.x, 1), round(o.y, 1), round(o.z - e.z, 1)], "voluto_cm": [round(x, 1), round(y, 1), round(z, 1)],
                  "ingombro_cm": [round(2 * e.x), round(2 * e.y), round(2 * e.z)]})

for n_ in senza_volume: unreal.log_warning(f"AVVISO {n_}: volume parametrico non trovato, resta insieme al modello di libreria")
luci = sum(len(a.get_components_by_class(unreal.LightComponentBase)) for a in attori.get_all_level_actors())
esito = {"sostituiti": fatti, "parametrici": parametrici, "scarti_di_misura": scarti, "volumi_non_trovati": senza_volume, "luci_in_scena": luci,
         "luci_nei_paralumi": luci_spostate}
json.dump(esito, open(os.path.join(MOD, "uscita_blender", "usd", "controllo_arredi.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
unreal.log(f"CONTROLLO arredi: {len(fatti)} di libreria, {len(parametrici)} ancora parametrici, {len(scarti)} scarti di misura")
for s_ in scarti: unreal.log_warning("AVVISO misura " + s_)
if not PROVA:
    livelli.save_current_level(); unreal.log("livello salvato")
