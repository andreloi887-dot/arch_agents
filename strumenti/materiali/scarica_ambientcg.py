"""Scarica materiali CC0 da ambientCG (https://ambientcg.com, licenza CC0) in libreria_materiali/<id>/, con gli stessi nomi
di file di scarica_polyhaven.py (colore, ruvidita, normali, rilievo) più info.json.

  python strumenti/materiali/scarica_ambientcg.py <id> [<id> ...] [--ris 2K] [--anteprime]

--anteprime: scarica solo l'immagine di anteprima di ogni id (per scegliere) in libreria_materiali/_anteprime/.
"""
import io, json, os, sys, urllib.request, zipfile

QUI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.normpath(os.path.join(QUI, "..", "..", "libreria_materiali"))
UA = {"User-Agent": "arch-agents-texture-downloader"}
MAPPE = {"_Color": "colore", "_Roughness": "ruvidita", "_NormalGL": "normali", "_Displacement": "rilievo"}


def leggi(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def dati(aid):
    d = json.loads(leggi(f"https://ambientcg.com/api/v2/full_json?id={aid}&include=downloadData,previewData,dimensionsData"))
    return d["foundAssets"][0]


def anteprima(aid):
    a = dati(aid); cart = os.path.join(DEST, "_anteprime"); os.makedirs(cart, exist_ok=True)
    img = a.get("previewImage", {}); url = img.get("512-PNG") or img.get("256-PNG") or next(iter(img.values()), None)
    if url: open(os.path.join(cart, aid + ".png"), "wb").write(leggi(url))
    return url


def scarica(aid, ris="2K"):
    a = dati(aid); cart = os.path.join(DEST, aid); os.makedirs(cart, exist_ok=True)
    zips = [z for f in a["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"] for z in [f]]
    z = next(z for z in zips if z["attribute"] == f"{ris}-JPG")
    zf = zipfile.ZipFile(io.BytesIO(leggi(z["fullDownloadPath"]))); fatti = {}
    for n in zf.namelist():
        for suf, nome in MAPPE.items():
            if suf in n and n.lower().endswith((".jpg", ".png")):
                f = os.path.join(cart, nome + os.path.splitext(n)[1].lower()); open(f, "wb").write(zf.read(n)); fatti[nome] = os.path.basename(f)
    meta = {"id": aid, "nome": a.get("displayName"), "licenza": "CC0 (ambientCG)", "pagina": f"https://ambientcg.com/view?id={aid}",
            "dimensioni_mm": [a.get("dimensionX"), a.get("dimensionY")] if a.get("dimensionX") else None, "risoluzione": ris, "mappe": fatti}
    json.dump(meta, open(os.path.join(cart, "info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return meta


if __name__ == "__main__":
    arg = sys.argv[1:]; ris = arg[arg.index("--ris") + 1] if "--ris" in arg else "2K"
    for x in [x for x in arg if not x.startswith("--") and x != ris]:
        if "--anteprime" in arg: print(x, anteprima(x))
        else: m = scarica(x, ris); print(x, "|", m["nome"], "|", m["dimensioni_mm"], "|", ", ".join(m["mappe"]))
