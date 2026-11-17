"""Filiera Blender → Unreal in un comando, con riepilogo compatto (fasi 3-5 di PROCEDIMENTO.md).

  python skills/rilievo-urbano/scripts/filiera.py <cartella modello> [--da finiture] [--fino usd] [--villa 1]
         [--progetto-ue <file.uproject>] [--viste viste.txt] [--campioni 32] [--scala 50 (viste in % di 1920×1080)] [--prova]
  (--prova: il passo libreria non salva il livello, per controllare posizioni e misure di una scelta di asset)

Passi, in ordine (--da / --fino per farne solo una parte; dopo "progetto" vanno rifatti tutti quelli dopo):
  contesto   importa_contesto.py   contesto.json → contesto.blend
  progetto   importa_progetto.py   IFC nella scena → contesto_progetto.blend
  finiture   finiture_interni.py   pavimento, battiscopa, porte, soffitto
  arredi     arredi_interni.py     mobili da arredi.json
  percorsi   percorsi_camera.py    camere (--solo interni --villa N) → scena_percorsi.blend
  usd        esporta_usd.py        usd/scena.usdc, usd/camere.usdc, usd/riferimento.json
  viste      controlli/viste.py    solo con --viste <file>: una riga "nome:x,y,h,tx,ty,th[,focale]" per vista
  unreal     unreal/importa_usd.py import in UE 5.8 (commandlet) e confronto con riferimento.json
  libreria   unreal/sostituisci_arredi.py  solo se <modello>/arredi_unreal.json ha delle scelte: modelli di libreria al
                                   posto dei mobili e delle lampade parametrici (posizioni da arredi_posati.json)
  prepara    unreal/prepara_render.py  Nanite, luce (--luce giorno|sera, --ev <EV100>), materiali di gres e legno, camere
                                   dalle viste di <modello>/viste_controllo.txt, sequenza e configurazione MRQ
  render     Movie Render Queue    sulla scheda grafica (-game): un PNG per camera in uscita_blender/render_unreal/
             --taratura: dopo il render misura la chiave di ogni immagine (media geometrica della luminanza, senza i
                                   pixel bruciati), scrive l'EV di ogni vista in uscita_blender/ev_viste_<luce>.json e rifà prepara
                                   e render (al massimo 3 giri). Chiave voluta: --chiave, giorno 0.20, sera 0.09. I giri dopo
                                   usano il file da soli
I passi prepara e render si chiedono con --fino render (senza, la filiera si ferma a libreria).

Per ogni passo: esito, tempo, avvisi. Un avviso già in <modello>/avvisi_noti.txt (una riga per avviso accettato,
testo esatto) conta come noto; gli altri si stampano per intero. Riepilogo anche in uscita_blender/riepilogo_filiera.json.
Eseguibili: variabili BLENDER e UE_EDITOR, altrimenti la versione più recente nelle cartelle standard di Windows.
Progetto Unreal: --progetto-ue, variabile UE_PROGETTO o lotto.json → progetto_ue (cartella in Documenti/Unreal Projects); se
manca tutto si usa o si crea vuoto Documenti/Unreal Projects/<zona>, e lo si scrive.
Esce con codice 1 se un passo fallisce o se il confronto con Unreal non torna.
"""
import glob, json, math, os, re, subprocess, sys, time

QUI = os.path.dirname(os.path.abspath(__file__))
BL = os.path.join(QUI, "blender")
PASSI = ["contesto", "progetto", "finiture", "arredi", "percorsi", "usd", "viste", "unreal", "libreria", "prepara", "render"]
LOG = {"contesto": "importa.log", "progetto": "importa_progetto.log", "finiture": "finiture_interni.log",
       "arredi": "arredi_interni.log", "percorsi": "percorsi.log", "usd": "esporta_usd.log", "unreal": "unreal.log"}


def chiave(png):
    """chiave dell'immagine: media geometrica della luminanza lineare, senza i pixel bruciati (finestre al sole)."""
    from PIL import Image
    im = Image.open(png).convert("RGB"); im.thumbnail((480, 270))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    px = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
    L = [0.2126 * lin(r / 255) + 0.7152 * lin(g / 255) + 0.0722 * lin(b / 255) for r, g, b in px]
    L = [x for x in L if x < 0.95] or L
    return math.exp(sum(math.log(max(x, 1e-4)) for x in L) / len(L))


def opzione(argv, nome, pred=None):
    return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else pred


def eseguibile(var, schema):
    if os.environ.get(var): return os.environ[var]
    trovati = sorted(glob.glob(schema), key=lambda p: [int(n) for n in re.findall(r"\d+", p)])
    if not trovati: raise SystemExit(f"non trovo {schema}: impostare la variabile {var}")
    return trovati[-1]


def progetto_ue(argv, mod):
    p = opzione(argv, "--progetto-ue") or os.environ.get("UE_PROGETTO")
    if p: return p
    # nome del progetto in lotto.json → progetto_ue (cartella in Documenti/Unreal Projects). Senza, la filiera del
    # 2026-11-16 ha creato un progetto vuoto accanto a quello vero, senza i pacchetti di libreria: 0 arredi sostituiti.
    f_lotto = os.path.join(mod, "lotto.json")
    nome = json.load(open(f_lotto, encoding="utf-8")).get("progetto_ue") if os.path.isfile(f_lotto) else None
    if not nome:
        nome = os.path.basename(os.path.dirname(os.path.abspath(mod))).replace("-", "_")
        print(f"ATTENZIONE: lotto.json non ha 'progetto_ue': uso o creo il progetto Unreal '{nome}'")
    cart = os.path.join(os.path.expanduser("~"), "Documents", "Unreal Projects", nome)
    p = os.path.join(cart, nome + ".uproject")
    if not os.path.isfile(p):
        os.makedirs(os.path.join(cart, "Content"), exist_ok=True); os.makedirs(os.path.join(cart, "Config"), exist_ok=True)
        json.dump({"FileVersion": 3, "EngineAssociation": "", "Plugins": [{"Name": n, "Enabled": True} for n in
                   ("USDImporter", "PythonScriptPlugin", "EditorScriptingUtilities", "MovieRenderPipeline")]}, open(p, "w"), indent=1)
        # Lumen con ray tracing hardware, ombre virtuali (vogliono Shader Model 6 e DX12), Nanite
        open(os.path.join(cart, "Config", "DefaultEngine.ini"), "w").write(
            "[/Script/Engine.RendererSettings]\nr.DynamicGlobalIlluminationMethod=1\nr.ReflectionMethod=1\n"
            "r.Shadow.Virtual.Enable=1\nr.GenerateMeshDistanceFields=True\nr.Nanite.ProjectEnabled=True\nr.RayTracing=True\n"
            "r.Lumen.HardwareRayTracing=True\nr.SkinCache.CompileShaders=True\nr.DefaultFeature.AutoExposure=False\n\n"
            "[/Script/WindowsTargetPlatform.WindowsTargetSettings]\nDefaultGraphicsRHI=DefaultGraphicsRHI_DX12\n"
            "+D3D12TargetedShaderFormats=PCD3D_SM6\n")
        print(f"creato il progetto Unreal {p}")
    return p


def avvisi(percorso, noti):
    if not os.path.isfile(percorso): return [], []
    righe = [r.strip() for r in open(percorso, encoding="utf-8", errors="replace") if "AVVISO" in r]
    return [r for r in righe if r in noti], [r for r in righe if r not in noti]


def confronta(rif, ue):
    """voci di riferimento.json (Blender) contro controllo_unreal.json (Unreal): [(voce, atteso, trovato, ok)]."""
    out = [("luci", rif["luci"], ue["luci"], rif["luci"] == ue["luci"]),
           # Unreal scarta i triangoli degeneri: tolleranza 0,01 %
           ("triangoli", rif["triangoli"], ue["triangoli"], abs(rif["triangoli"] - ue["triangoli"]) <= rif["triangoli"] * 1e-4),
           ("materiali", rif["materiali_distinti"], ue["materiali"], rif["materiali_distinti"] == ue["materiali"]),
           ("ingombro cm", rif["ingombro_cm"], ue["ingombro_cm"],
            all(abs(a - b) <= 2 for p, q in zip(rif["ingombro_cm"], ue["ingombro_cm"]) for a, b in zip(p, q)))]
    if "camere" in rif:
        out += [("camere", rif["camere"], ue["camere"], rif["camere"] == ue["camere"]),
                ("fps", rif["fps"], ue.get("fps"), ue.get("fps") is not None and abs(rif["fps"] - ue["fps"]) < 1e-6),
                ("fotogrammi", rif["fotogrammi"], ue.get("fotogrammi"), rif["fotogrammi"] == ue.get("fotogrammi"))]
    return out


def main(argv):
    if not argv or argv[0].startswith("--"): raise SystemExit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console Windows cp1252: ✓ ✗ non passano
    mod = os.path.abspath(argv[0]); U = os.path.join(mod, "uscita_blender"); os.makedirs(U, exist_ok=True)
    da, fino = opzione(argv, "--da", "contesto"), opzione(argv, "--fino", "libreria")
    for nome_p in (da, fino):
        if nome_p not in PASSI: raise SystemExit(f"passo sconosciuto: {nome_p}. Passi: {', '.join(PASSI)}")
    if "--fino" not in argv and PASSI.index(da) > PASSI.index(fino): fino = "render"      # --da prepara|render senza --fino
    scelti = PASSI[PASSI.index(da):PASSI.index(fino) + 1]
    if not scelti: raise SystemExit(f"nessun passo da fare: --da {da} viene dopo --fino {fino}")
    villa = opzione(argv, "--villa", "1"); viste = opzione(argv, "--viste")
    if not viste and "viste" in scelti: scelti.remove("viste")
    noti_f = os.path.join(mod, "avvisi_noti.txt")
    noti = {r.strip() for r in open(noti_f, encoding="utf-8")} if os.path.isfile(noti_f) else set()
    blender = eseguibile("BLENDER", r"C:\Program Files\Blender Foundation\Blender*\blender.exe")
    # --python-exit-code 1: senza, blender esce con 0 anche se lo script va in errore. Mai --factory-startup (toglie Bonsai)
    b = lambda blend, script, *extra: [blender, "-b"] + ([os.path.join(U, blend)] if blend else []) + \
        ["--python-exit-code", "1", "-P", os.path.join(BL, script), "--", mod, *extra]
    comandi = {
        "contesto": b(None, "importa_contesto.py"),
        "progetto": b("contesto.blend", "importa_progetto.py"),
        "finiture": b("contesto_progetto.blend", "finiture_interni.py"),
        "arredi": b("contesto_progetto.blend", "arredi_interni.py"),
        "percorsi": b("contesto_progetto.blend", "percorsi_camera.py", "--solo", "interni", "--villa", villa),
        "usd": b("scena_percorsi.blend", "esporta_usd.py"),
    }
    if viste:
        righe = [r.strip() for r in open(viste, encoding="utf-8") if r.strip() and not r.startswith("#")]
        comandi["viste"] = [blender, "-b", "--python-exit-code", "1", "-P", os.path.join(BL, "controlli", "viste.py"), "--",
                            os.path.join(U, "scena_percorsi.blend"), os.path.join(U, "viste_controllo"),
                            opzione(argv, "--campioni", "32"), *righe]
    f_arr = os.path.join(mod, "arredi_unreal.json")
    if "libreria" in scelti and not (os.path.isfile(f_arr) and any(not k.startswith("_") for k in json.load(open(f_arr, encoding="utf-8")))):
        scelti.remove("libreria")
    if {"unreal", "libreria", "prepara", "render"} & set(scelti):
        ue = eseguibile("UE_EDITOR", r"C:\Program Files\Epic Games\UE_*\Engine\Binaries\Win64\UnrealEditor-Cmd.exe")
        script = os.path.join(QUI, "unreal", "importa_usd.py").replace("\\", "/")
        # -FullStdOutLogOutput: senza, i messaggi di Python non arrivano su stdout
        comandi["unreal"] = [ue, progetto_ue(argv, mod), "-run=pythonscript",
                             f"-script={script} {os.path.join(U, 'usd')}".replace("\\", "/"),
                             "-unattended", "-nosplash", "-nop4", "-stdout", "-FullStdOutLogOutput"]
        comandi["libreria"] = comandi["unreal"][:3] + [f"-script={script.replace('importa_usd', 'sostituisci_arredi')} {mod}".replace("\\", "/") + (" --prova" if "--prova" in argv else "")] + comandi["unreal"][4:]
        luce = opzione(argv, "--luce", "giorno"); ev = opzione(argv, "--ev")
        comandi["prepara"] = comandi["unreal"][:3] + [f"-script={script.replace('importa_usd', 'prepara_render')} {mod} {luce}".replace("\\", "/")
                                                      + (f" ev={ev}" if ev else "")] + comandi["unreal"][4:]
        # il render vuole la scheda grafica: -game (non il commandlet), finestra piccola, la risoluzione vera è nella
        # configurazione MRQ salvata da prepara_render.py. Si chiude da solo alla fine
        comandi["render"] = [ue, comandi["unreal"][1], "/Game/Progetto/Scena", "-game", "-LevelSequence=/Game/Progetto/Viste/LS_viste",
                             "-MoviePipelineConfig=/Game/Progetto/Viste/MRQ_viste", "-windowed", "-ResX=1280", "-ResY=720",
                             "-notexturestreaming", "-unattended", "-log"]

    f_rif, f_ue = os.path.join(U, "usd", "riferimento.json"), os.path.join(U, "usd", "controllo_unreal.json")
    f_ren = os.path.join(U, "usd", "controllo_render.json")
    impronta_prima = json.load(open(f_rif)).get("impronta") if os.path.isfile(f_rif) else None
    if "render" in scelti and "prepara" not in scelti and not os.path.isfile(f_ren):
        raise SystemExit("render senza preparazione: lanciare prima --da prepara (manca usd/controllo_render.json)")
    esito, ok_tutto = {"modello": mod, "passi": []}, True
    taratura = "--taratura" in argv; luce_t = opzione(argv, "--luce", "giorno")
    bersaglio = float(opzione(argv, "--chiave", "0.20" if luce_t == "giorno" else "0.09")); GIRI_T = 3
    f_ev_t = os.path.join(U, f"ev_viste_{luce_t}.json")
    if taratura and "render" not in scelti: raise SystemExit("--taratura vuole il render: --da prepara --fino render")
    coda, giro_t = list(scelti), 0
    while coda:
        p = coda.pop(0)
        t0 = time.time(); print(f"== {p} ...", flush=True)
        for f in {"usd": [f_rif, f_ue], "unreal": [f_ue]}.get(p, []):     # mai confrontare file di un giro prima
            if os.path.isfile(f): os.remove(f)
        r = subprocess.run(comandi[p], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, VILLA=villa, VISTE_SCALA=opzione(argv, "--scala", "50")))
        dt = time.time() - t0
        if p == "unreal": open(os.path.join(U, "unreal.log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
        uscita = r.stdout + r.stderr
        errore = r.returncode != 0 or "Traceback" in uscita or "Python script executed with errors" in uscita
        n_noti, nuovi = avvisi(os.path.join(U, LOG[p]), noti) if p in LOG else ([], [])
        voce = {"passo": p, "secondi": round(dt, 1), "avvisi_noti": len(n_noti), "avvisi_nuovi": nuovi}
        if p == "usd" and not errore:
            if os.path.isfile(f_rif):
                rj = json.load(open(f_rif)); voce["impronta"] = rj.get("impronta"); voce["porte_nascoste"] = rj.get("porte_nascoste", [])
                voce["porte"] = rj.get("porte")
                if voce["porte_nascoste"]: errore = True; uscita += "\nError: porte nascoste " + ", ".join(voce["porte_nascoste"])
            else: errore = True; uscita += "\nError: riferimento.json non scritto (pxr mancante?)"
        if p == "unreal" and not errore and not os.path.isfile(f_ue):
            errore = True; uscita += "\nError: controllo_unreal.json non scritto"
        voce["ok"] = not errore
        if p == "percorsi" and os.path.isfile(os.path.join(U, "percorsi.json")):
            voce["avvisi_percorso"] = {q["nome"]: len(q.get("avvisi", [])) for q in json.load(open(os.path.join(U, "percorsi.json"), encoding="utf-8"))["percorsi"]}
        if p == "viste": voce["viste"] = re.findall(r"FATTO (\S+) ([\d.]+) s", uscita); voce["dispositivo"] = (re.findall(r"Cycles su (.*)", uscita) or ["?"])[0]
        if p == "libreria" and not errore:
            ca = json.load(open(os.path.join(U, "usd", "controllo_arredi.json"), encoding="utf-8"))
            voce["libreria"] = {"di_libreria": len(ca["sostituiti"]), "parametrici": ca["parametrici"], "scarti_di_misura": ca["scarti_di_misura"],
                                "volumi_non_trovati": ca.get("volumi_non_trovati", []), "luci_in_scena": ca.get("luci_in_scena")}
            # le luci non devono cambiare: riferimento.json (sole, punti, faretti, rettangolari) + la luce del cielo
            attese = sum(json.load(open(f_rif))["luci"].values()) + 1
            if voce["libreria"]["luci_in_scena"] != attese or voce["libreria"]["volumi_non_trovati"]:
                errore = True; voce["ok"] = False
                uscita += f"\nError: luci {voce['libreria']['luci_in_scena']} invece di {attese}, volumi non trovati {voce['libreria']['volumi_non_trovati']}"
        if p == "prepara" and not errore:
            cr = json.load(open(f_ren, encoding="utf-8")) if os.path.isfile(f_ren) else None
            if cr is None: errore = True; voce["ok"] = False; uscita += "\nError: controllo_render.json non scritto"
            else: voce["prepara"] = cr
        if p == "render" and not errore:
            # un'immagine per camera, scritta in questo giro
            cr = json.load(open(f_ren, encoding="utf-8")); cart = cr["uscita"]
            fatte = [c for c in cr["camere"] if os.path.isfile(os.path.join(cart, c + ".png")) and os.path.getmtime(os.path.join(cart, c + ".png")) >= t0]
            voce["render"] = {"cartella": cart, "immagini": fatte, "mancanti": [c for c in cr["camere"] if c not in fatte], "luce": cr.get("luce"), "ev": cr.get("ev")}
            if voce["render"]["mancanti"]: errore = True; voce["ok"] = False; uscita += "\nError: immagini non scritte: " + ", ".join(voce["render"]["mancanti"])
        if p == "render" and not errore and taratura and giro_t < GIRI_T:
            # taratura dell'esposizione: chiave di ogni immagine → EV che la porta alla chiave voluta; poi prepara e render
            cr = json.load(open(f_ren, encoding="utf-8")); usati = cr.get("ev_viste") or {}
            nuovi_ev, delta = {}, {}
            for c in cr["camere"]:
                k = chiave(os.path.join(cr["uscita"], c + ".png")); e0 = usati.get(c, cr.get("ev"))
                d = max(-4.0, min(4.0, math.log2(max(k, 1e-4) / bersaglio)))   # immagine troppo chiara → EV più alto
                nuovi_ev[c] = round(max(-2.0, min(16.0, e0 + d)), 2); delta[c] = (round(k, 3), round(d, 2))
            giro_t += 1
            voce["taratura"] = {"giro": giro_t, "chiave_voluta": bersaglio, "chiave_e_correzione": delta, "ev": nuovi_ev}
            print(f"      taratura giro {giro_t}: chiave voluta {bersaglio}, " + ", ".join(f"{c[6:]} {k}→{d:+}" for c, (k, d) in delta.items()))
            if any(abs(d) > 0.25 for _, d in delta.values()):
                json.dump({"_nota": f"EV100 per vista, luce {cr.get('luce')}, chiave {bersaglio}: filiera.py --taratura del {time.strftime('%Y-%m-%d')}", **nuovi_ev},
                          open(f_ev_t, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                coda = ["prepara", "render"] + coda
        if p == "unreal" and not errore:
            voce["confronto"] = [{"voce": v, "atteso": a, "trovato": t, "ok": k} for v, a, t, k in
                                 confronta(json.load(open(f_rif)), json.load(open(f_ue)))]
            if not all(c["ok"] for c in voce["confronto"]): voce["ok"] = False
        esito["passi"].append(voce)
        segno = "ok " if voce["ok"] else "ERR"
        extra = f", percorso {voce['avvisi_percorso']}" if "avvisi_percorso" in voce else ""
        print(f"{segno} {p:9s} {dt:7.1f} s  avvisi noti {len(n_noti)}, nuovi {len(nuovi)}{extra}")
        for a in nuovi: print("      NUOVO", a)
        if "impronta" in voce:   # impronta della geometria (esporta_usd): dice se una modifica al codice ha cambiato il risultato
            stato = ("primo giro" if not impronta_prima else "uguale al giro prima" if voce["impronta"] == impronta_prima
                     else f"CAMBIATA (prima {impronta_prima})")
            print(f"      impronta geometria {voce['impronta']}: {stato}")
            print(f"      porte in scena {voce.get('porte')}, nascoste {len(voce.get('porte_nascoste', []))}")
        for v, t in voce.get("viste", []): print(f"      vista {v}: {t} s ({voce['dispositivo']})")
        for c in voce.get("confronto", []):
            print(f"      {'✓' if c['ok'] else '✗'} {c['voce']}: Blender {c['atteso']} | Unreal {c['trovato']}")
        if "libreria" in voce:
            print(f"      modelli di libreria {voce['libreria']['di_libreria']}, ancora parametrici {len(voce['libreria']['parametrici'])}, "
                  f"luci in scena {voce['libreria']['luci_in_scena']}, volumi non trovati {len(voce['libreria']['volumi_non_trovati'])}")
            for x in voce["libreria"]["scarti_di_misura"]: print("      misura:", x)
        if "prepara" in voce:
            c = voce["prepara"]
            print(f"      luce {c['luce']}, EV {c.get('ev')}, Nanite su {c['nanite_mesh']} mesh, luci accese {c['luci_accese']} / spente {c['luci_spente']}, "
                  f"camere {len(c['camere'])}, gres su {c.get('gres_parti')} parti, legno su {c.get('legno_parti')}")
        if "render" in voce:
            evv = cr.get("ev_viste") or {}; ev_t = f"EV per vista da {min(evv.values()):g} a {max(evv.values()):g}" if cr.get("ev_tarati") and evv else f"EV {voce['render']['ev']}"
            print(f"      {len(voce['render']['immagini'])} immagini in {voce['render']['cartella']} (luce {voce['render']['luce']}, {ev_t})")
        if errore:
            coda = [r for r in uscita.splitlines() if re.search(r"Error|Traceback|AVVISO|SystemExit", r)][-15:]
            print("\n".join("      " + r[-300:] for r in coda)); ok_tutto = False; break
        ok_tutto &= voce["ok"]
    json.dump(esito, open(os.path.join(U, "riepilogo_filiera.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("FILIERA", "OK" if ok_tutto else "CON ERRORI", "| riepilogo:", os.path.join(U, "riepilogo_filiera.json"))
    return 0 if ok_tutto else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
