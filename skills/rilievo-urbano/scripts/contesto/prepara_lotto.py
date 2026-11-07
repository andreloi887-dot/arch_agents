#!/usr/bin/env python3
"""Prepara la cartella di un lotto nuovo in Sardegna, pronta per scena.py / contesto.py.

  python prepara_lotto.py --cartella rilievi/zona-<nome> --origine 39.25240,9.11527 [--lotto lat,lng]
                          [--nome "Via X / Via Y"] [--semilato 75]

--origine  punto (0,0) del modello: di solito un incrocio o lo spigolo del lotto. È anche il punto base
           da dare in Edificius.
--lotto    un punto qualsiasi DENTRO la particella del progetto (default: l'origine).

Fa, senza interventi:
 1. catasto AdE (WMS) dell'area → geometria/*.geojson (con ../catasto.py);
 2. DTM LiDAR 1 m della Regione Sardegna (WCS) 200 m più largo dell'area → modello/dtm_lidar_1m.tif + .json;
 3. tendenza del terreno per i bordi fuori dal DTM, stimata dal DTM stesso → modello/terreno_tendenza.json;
 4. individua la particella del lotto e scrive modello/lotto.json con valori standard;
 5. se manca, una scheda.json minima (solo palette): edifici, muri e arredo li aggiunge l'agente rilievo-urbano.
Non sovrascrive lotto.json né scheda.json se esistono già (usa --forza per lotto.json).
"""
import argparse, json, math, os, subprocess, sys, urllib.parse, urllib.request
import numpy as np, tifffile
from pyproj import Transformer
from shapely.geometry import Polygon, Point

HERE = os.path.dirname(os.path.abspath(__file__))
WCS = ("https://webgis.regione.sardegna.it/geoserverraster/ows?service=WCS&version=2.0.1&request=GetCoverage"
       "&CoverageId=raster__DTM_1M_MOSAICO_ALTIMETRIA&format=image/tiff&subset=E({e0},{e1})&subset=N({n0},{n1})")
CRS_DTM = "EPSG:7791"
PALETTE = [  # colori neutri di partenza; l'agente rilievo-urbano li sostituisce con quelli campionati
    ("C04", "intonaco chiaro", "#D9D2C5"), ("C15", "calcestruzzo", "#A8A49C"), ("C16", "asfalto", "#4A4A48"),
    ("C17", "marmette chiare", "#BDB8AE"), ("C18", "marmette scure", "#8C877E"), ("C19", "cordolo in pietra", "#9E9A92"),
    ("C20", "acciaio zincato", "#9AA0A3"), ("C24", "prato secco", "#A99A62"), ("C25", "terra battuta", "#8E7B5C"),
    ("C27", "vegetazione", "#5E6E3A")]

def ll(s):
    a, b = (float(v) for v in s.split(",")); return a, b

def scarica(url, out):
    req = urllib.request.Request(url, headers={"User-Agent": "arch_agents-prepara_lotto"})
    with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f: f.write(r.read())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cartella", required=True)
    ap.add_argument("--origine", required=True, type=ll)
    ap.add_argument("--lotto", type=ll)
    ap.add_argument("--nome", default="")
    ap.add_argument("--semilato", type=float, default=75.0)
    ap.add_argument("--forza", action="store_true", help="riscrive lotto.json")
    a = ap.parse_args()
    O = a.origine; PL = a.lotto or O; EXT = a.semilato
    Z = os.path.abspath(a.cartella); MOD = os.path.join(Z, "modello"); GEO = os.path.join(Z, "geometria")
    os.makedirs(MOD, exist_ok=True); os.makedirs(GEO, exist_ok=True)
    aeqd = f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +ellps=WGS84 +units=m +no_defs"
    to_ll = Transformer.from_crs(aeqd, "EPSG:4326", always_xy=True)
    to_loc = Transformer.from_crs("EPSG:4326", aeqd, always_xy=True)

    # 1. catasto: area modellata + 15 m di margine
    m = EXT + 15
    lo0, la0 = to_ll.transform(-m, -m); lo1, la1 = to_ll.transform(m, m)
    if not os.path.exists(os.path.join(GEO, "catasto_strade_particelle.geojson")):
        print("catasto…", flush=True)
        subprocess.run([sys.executable, os.path.join(HERE, "..", "catasto.py"),
                        "--bbox", f"{la0:.6f},{lo0:.6f},{la1:.6f},{lo1:.6f}", "--out", GEO], check=True)

    # 2. DTM LiDAR: quadrato di lato 2·EXT + 50 m in UTM 32N
    tif = os.path.join(MOD, "dtm_lidar_1m.tif")
    E0, N0 = Transformer.from_crs("EPSG:4326", CRS_DTM, always_xy=True).transform(O[1], O[0])
    h = int(math.ceil(EXT + 25))
    url = WCS.format(e0=int(E0) - h, e1=int(E0) + h, n0=int(N0) - h, n1=int(N0) + h)
    if not os.path.exists(tif):
        print("DTM LiDAR…", flush=True); scarica(url, tif)
    with tifffile.TiffFile(tif) as t:
        pg = t.pages[0]; dtm = pg.asarray().astype(float)
        tags = {k.name: k.value for k in pg.tags.values()}
    if "ModelTransformationTag" in tags:     # il WCS regionale usa la matrice 4×4
        M = tags["ModelTransformationTag"]; passo = float(M[0]); E_left, N_top = float(M[3]), float(M[7])
    else:
        passo = float(tags["ModelPixelScaleTag"][0]); E_left, N_top = tags["ModelTiepointTag"][3:5]
    nod = tags.get("GDAL_NODATA")
    if nod is not None: dtm[dtm == float(str(nod).strip("\x00"))] = np.nan
    dtm[dtm < -100] = np.nan
    if np.isnan(dtm).mean() > 0.2:
        sys.exit("DTM: più del 20 % senza dati. Il lotto è fuori dalla copertura LiDAR regionale?")
    json.dump({"fonte": "Regione Autonoma della Sardegna – DTM 1 m da LiDAR (raster__DTM_1M_MOSAICO_ALTIMETRIA), WCS geoserverraster",
               "crs": "EPSG:7791 (RDN2008 / UTM 32N)", "bordo_sinistro_E": float(E_left), "bordo_superiore_N": float(N_top),
               "passo": passo, "origine_E": E0, "origine_N": N0, "url": url},
              open(os.path.join(MOD, "dtm_lidar_1m.json"), "w", encoding="utf-8"), indent=1)

    # 3. tendenza del terreno (polinomio di 2° grado) dal DTM stesso: serve solo fuori copertura
    to_utm = Transformer.from_crs(aeqd, CRS_DTM, always_xy=True)
    pts = []
    for y in np.arange(-EXT, EXT + 0.1, 5.0):
        for x in np.arange(-EXT, EXT + 0.1, 5.0):
            E, N = to_utm.transform(x, y)
            c = int((E - E_left) / passo); r = int((N_top - N) / passo)
            if 0 <= r < dtm.shape[0] and 0 <= c < dtm.shape[1] and not np.isnan(dtm[r, c]): pts.append((x, y, dtm[r, c]))
    P = np.array(pts); X = np.c_[np.ones(len(P)), P[:, 0], P[:, 1], P[:, 0]**2, P[:, 0]*P[:, 1], P[:, 1]**2]
    coef = np.linalg.lstsq(X, P[:, 2], rcond=None)[0]
    json.dump({"tipo": "polinomio 2° grado sul DTM LiDAR (campioni ogni 5 m)", "coef": list(map(float, coef)),
               "z_incrocio_slm": float(coef[0]), "n_punti": len(P), "base": f"x=E, y=N in metri dall'origine {O[0]}, {O[1]}",
               "fonte": "derivata dal DTM LiDAR; per una tendenza Copernicus usare terreno_tendenza.py"},
              open(os.path.join(MOD, "terreno_tendenza.json"), "w", encoding="utf-8"), indent=1)

    # 3b. Database Geotopografico regionale (WFS): sede stradale, assi, recinzioni, muri di sostegno, edifici
    WFS = "https://webgis.regione.sardegna.it/geoserver/ows"
    bb = f"{la0:.6f},{lo0:.6f},{la1:.6f},{lo1:.6f},urn:ogc:def:crs:EPSG::4326"
    DBL = {"strade": "dbgt_10k_22_v05_01_area_stradale", "assi": "dbgt_10k_22_v05_01_elemento_stradale",
           "recinzioni": "dbgt_10k_22_v05_02_elemento_divisorio", "muri_sostegno": "dbgt_10k_22_v05_02_muro_sostegno_arc",
           "edifici": "dbgt_10k_22_v05_02_edificio_ingombro_suolo"}
    dbgt = {}
    for k, lay in DBL.items():
        out = os.path.join(GEO, f"dbgt_{lay.split('_v05_')[1][3:]}.geojson")
        if not os.path.exists(out):
            scarica(WFS + "?" + urllib.parse.urlencode({"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                    "typeNames": f"dbu:{lay}", "outputFormat": "application/json", "srsName": "EPSG:4326", "bbox": bb}), out)
        dbgt[k] = "../geometria/" + os.path.basename(out)
    print("DBGT:", ", ".join(dbgt))

    # 3c. DSM LiDAR 1 m (superficie, solo edifici, solo vegetazione): tavole dai quadri d'unione regionali
    dsm = {"superficie": [], "edifici": [], "vegetazione": [], "json": "dsm_2008.json"}
    DSMD = os.path.join(GEO, "dsm"); os.makedirs(DSMD, exist_ok=True)
    for qu, anno in (("QU2k_DTM_DSM1m_centri_urbani_2013", 2013), ("QU2k_fasciacostiera2008_DTM_DSM1m", 2008)):
        fn = os.path.join(DSMD, qu + ".json")
        scarica(WFS + "?" + urllib.parse.urlencode({"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                "typeNames": f"dbu:{qu}", "outputFormat": "application/json", "srsName": "EPSG:4326", "bbox": bb}), fn)
        tav = json.load(open(fn, encoding="utf-8")).get("features", [])
        if not tav: continue
        import zipfile
        for f in tav:
            pr = f["properties"]
            for k, chiave in (("dsm", "superficie"), ("dsm_buildi", "edifici"), ("dsm_vegeta", "vegetazione")):
                url = pr.get(k)
                if not url: continue
                zp = os.path.join(DSMD, os.path.basename(url))
                if not os.path.exists(zp): scarica(url, zp)
                dest = os.path.join(DSMD, os.path.splitext(os.path.basename(url))[0])
                with zipfile.ZipFile(zp) as z: z.extractall(dest)
                asc = [x for x in os.listdir(dest) if x.upper().endswith(".ASC")]
                if asc: dsm[chiave].append("../geometria/dsm/" + os.path.basename(dest) + "/" + asc[0])
        dsm["anno"] = anno; dsm["json"] = f"dsm_{anno}.json"
        break   # la copertura più recente
    if dsm["superficie"]:
        print(f"DSM {dsm['anno']}: {len(dsm['superficie'])} tavole")
    # 3d. ortofoto regionale più recente (WMS), 10 cm/pixel sull'area
    ORT = os.path.join(GEO, "ortofoto"); os.makedirs(ORT, exist_ok=True)
    Eo, No = Transformer.from_crs("EPSG:4326", CRS_DTM, always_xy=True).transform(O[1], O[0]); hh = EXT + 5
    q = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": "raster:Mosaico_2022_GB", "STYLES": "", "CRS": CRS_DTM,
         "BBOX": f"{Eo-hh},{No-hh},{Eo+hh},{No+hh}", "WIDTH": int(2*hh/0.1), "HEIGHT": int(2*hh/0.1), "FORMAT": "image/jpeg"}
    if not os.path.exists(os.path.join(ORT, "ortofoto.jpg")):
        scarica("https://webgis.regione.sardegna.it/geoserverraster/ows?" + urllib.parse.urlencode(q), os.path.join(ORT, "ortofoto.jpg"))
    json.dump({"crs": CRS_DTM, "layer": q["LAYERS"], "bbox": [Eo-hh, No-hh, Eo+hh, No+hh], "px": q["WIDTH"], "m_px": 0.1,
               "file": "ortofoto.jpg", "fonte": "Regione Autonoma della Sardegna – ortofoto 2022 (WMS)"},
              open(os.path.join(ORT, "ortofoto.json"), "w", encoding="utf-8"), indent=1)

    # 4. particella del lotto
    feats = json.load(open(os.path.join(GEO, "catasto_strade_particelle.geojson"), encoding="utf-8"))["features"]
    px, py = to_loc.transform(PL[1], PL[0])
    idx = None
    for i, f in enumerate(feats):
        if f["properties"]["tipo"] != "particella": continue
        g = Polygon([to_loc.transform(*q) for q in f["geometry"]["coordinates"][0]]).buffer(0)
        if g.contains(Point(px, py)): idx = i; area_lotto = g.area; break
    if idx is None:
        sys.exit("Nessuna particella contiene il punto --lotto: spostalo dentro il lotto (non sulla strada).")
    print(f"particella del lotto: indice {idx}, {area_lotto:.0f} m²")

    lp = os.path.join(MOD, "lotto.json")
    if os.path.exists(lp) and not a.forza:
        print("lotto.json esiste già: non lo tocco (usa --forza)")
    else:
        lotto = {
            "_nota": "Scritto da prepara_lotto.py con valori standard. Da completare: particelle che sono strada, muri, arredo.",
            "nome": a.nome, "origine": {"lat": O[0], "lng": O[1]}, "semilato_m": EXT, "seme_casuale": idx,
            "dati": {"terreno_tendenza": "terreno_tendenza.json", "dtm_json": "dtm_lidar_1m.json", "dtm_tif": "dtm_lidar_1m.tif",
                     "crs_dtm": CRS_DTM, "scheda": "../scheda.json",
                     "particelle": "../geometria/catasto_strade_particelle.geojson",
                     "fabbricati": "../geometria/catasto_fabbricati.geojson",
                     "manifest": ["../_rif_google/manifest_riprese.json", "manifest_riprese.json"],
                     "dbgt": dbgt, "ortofoto": "../geometria/ortofoto/ortofoto.json",
                     **({"dsm": dsm} if dsm["superficie"] else {})},
            "strade": {"punti_aggiunti_al_sedime": [], "marciapiede_m": 1.5, "rialzo_marciapiede_m": 0.10,
                       "lisciatura_profilo_m": 9, "pendenza_trasversale": 0.02, "raccordo_assi_m": 8.0,
                       "eccesso_muro_max_m": 0.3, "distanza_fronte_particella_m": 6.0,
                       "pendenza_marciapiede": 0.015, "raccordo_angoli_m": 2.0, "raccordo_lotto_m": 4.0,
                       "materiale_carreggiata": "C16", "materiale_marciapiede": "C17", "materiale_cordolo": "C19",
                       "texture_marciapiede": {"materiale": "C17", "alternato": "C18", "modulo_mm": [800, 800]}},
            "lotto": {"id": "LOTTO", "punto": [PL[0], PL[1]], "punti_aggiunti_al_lotto": [], "particella": "", "nome": "Lotto di progetto",
                      "raggio_angoli_m": 0.0, "materiale": "C24", "materiale_fasce": "C25", "rumore_superficie_m": 0.0,
                      "nota": "superficie dal DTM LiDAR 1 m",
                      "muro_fronte": {"id": "M01", "nome": "M01 – muro sul fronte strada", "materiale": "C15", "spessore": 0.25,
                                      "campionamento_interno_m": 1.6, "altezza_minima_m": 0.20,
                                      "altezza_massima_m": 1.30, "scarpata_m": 2.5}},
            "muri_contorno": [], "edifici": {"altezza_generica_m": 6.5, "materiale_generico": "C04", "piattaforma_m": {},
                                             "per_edificio": {}},
            # valori appresi nei test (references/08-lezioni-apprese.md); il rilievo li sostituisce lotto per lotto
            "confini_interni": {"altezza": 1.8, "spessore": 0.2, "materiale": "C04", "rete_oltre_m": 12.0,
                                "cordolo_rete_m": 0.3, "altezza_rete_m": 1.5},
            "lampioni": {"passo_m": 27, "h": 8.5, "materiale": "C20", "d_base_m": 0.16, "d_cima_m": 0.08, "sbraccio_m": 0.5,
                         "armatura": [0.75, 0.32, 0.12], "plinto": [0.35, 0.35, 0.2], "dal_cordolo_m": 0.5},
            "segnaletica_stradale": {"mezzeria": True, "mezzeria_tratto_m": 3.0, "mezzeria_intervallo_m": 4.5,
                                     "mezzeria_stop_incrocio_m": 10, "margini": True, "margine_dal_cordolo_m": 0.3,
                                     "margine_stop_incrocio_m": 12, "larghezza_linee_m": 0.12, "distanza_incrocio_m": 6.0,
                                     "cartelli_attraversamento": True, "strisce_pedonali": []},
            "segnaletica_verticale": [],
            "alberi_dsm": {"usa": True, "altezza_min_m": 2.5, "distanza_da_palme_m": 3.0, "verde_min": 0.085, "luminosita_max": 115},
            "arredo": [], "vegetazione": [],
            "punti_controllo": {"NE": [EXT - 15, EXT - 15], "SO": [15 - EXT, 15 - EXT]}}
        json.dump(lotto, open(lp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    # 5. scheda minima
    sp = os.path.join(Z, "scheda.json")
    if not os.path.exists(sp):
        json.dump({"_nota": "scheda minima di prepara_lotto.py: da completare con l'agente rilievo-urbano",
                   "edifici": [], "recinzioni": [],
                   "palette": [{"id": i, "materiale": n, "hex": h} for i, n, h in PALETTE]},
                  open(sp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if dsm["superficie"]:
        subprocess.run([sys.executable, os.path.join(HERE, "dsm.py"), MOD], check=True)
    print("dopo il rilievo: contesto.py, poi verifica_contesto.py (controlli automatici)")
    print(f"pronto: {MOD}\npoi: python {os.path.join(HERE, 'contesto.py')} \"{MOD}\"")

if __name__ == "__main__":
    main()
