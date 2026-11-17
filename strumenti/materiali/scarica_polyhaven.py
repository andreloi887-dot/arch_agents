"""Scarica texture CC0 da Poly Haven (https://polyhaven.com, licenza CC0: uso libero, anche commerciale, senza obbligo di
citazione) nella cartella libreria_materiali/ del repo (fuori da git: si riscarica con questo script).

  python strumenti/materiali/scarica_polyhaven.py <id> [<id> ...] [--ris 2k]

Per ogni id scarica in libreria_materiali/<id>/ le mappe Diffuse, Rough, nor_gl (normali per OpenGL/Blender) e
Displacement in JPG alla risoluzione chiesta (predefinita 2k), più info.json con nome, autori, licenza e misura reale
(dimensions in mm, se Poly Haven la dà). Non riscarica i file che ci sono già.
"""
import json, os, sys, urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.normpath(os.path.join(QUI, "..", "..", "libreria_materiali"))
UA = {"User-Agent": "arch-agents-texture-downloader"}
MAPPE = {"Diffuse": "colore", "Rough": "ruvidita", "nor_gl": "normali", "Displacement": "rilievo"}


def leggi(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def scarica(aid, ris="2k"):
    cart = os.path.join(DEST, aid); os.makedirs(cart, exist_ok=True)
    info = json.loads(leggi(f"https://api.polyhaven.com/info/{aid}"))
    files = json.loads(leggi(f"https://api.polyhaven.com/files/{aid}"))
    fatti = {}
    for chiave, nome in MAPPE.items():
        v = files.get(chiave, {}).get(ris, {}).get("jpg") or files.get(chiave, {}).get(ris, {}).get("png")
        if not v: continue
        est = os.path.splitext(v["url"])[1]; f = os.path.join(cart, nome + est)
        if not os.path.isfile(f) or os.path.getsize(f) != v.get("size", -1):
            open(f, "wb").write(leggi(v["url"]))
        fatti[nome] = os.path.basename(f)
    meta = {"id": aid, "nome": info.get("name"), "autori": list(info.get("authors", {}).keys()), "licenza": "CC0 (Poly Haven)",
            "pagina": f"https://polyhaven.com/a/{aid}", "dimensioni_mm": info.get("dimensions"), "risoluzione": ris, "mappe": fatti}
    json.dump(meta, open(os.path.join(cart, "info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return meta


if __name__ == "__main__":
    arg = sys.argv[1:]; ris = arg[arg.index("--ris") + 1] if "--ris" in arg else "2k"
    for a in [a for a in arg if not a.startswith("--") and a != ris]:
        m = scarica(a, ris); print(a, "|", m["nome"], "|", m["dimensioni_mm"], "mm |", ", ".join(m["mappe"]))
