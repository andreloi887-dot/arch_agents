#!/usr/bin/env python3
"""VERIFICA: confronta il modello SketchUp (inventario.json + viste esportate) con la scheda.

  confronta.py --scheda scheda.json --inventario inventario.json \
               [--manifest _rif_google/manifest_riprese.json --riprese _rif_google --export export_verifica] \
               --out verifica/

Output: report.json, report.md, e per ogni ripresa <ID>_affiancato.png e <ID>_sovrapposto.png.
Tolleranze: references/05-verifica.md. Richiede Pillow solo per le immagini.
"""
import argparse
import json
import math
import os
import re

TOL_H = {"alta": 0.30, "media": 0.75, "bassa": 1.50}
TOL_DE_TINTA, TOL_DE_TEXTURE = 5.0, 10.0
CATEGORIE = ("edifici", "recinzioni", "arredo", "pavimentazioni", "vegetazione")
RE_C = re.compile(r"^C\d{2,3}$")


# ------------------------------------------------------------------ colore
def srgb_to_lab(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(v)) for v in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / 1.00000
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if C1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if C2p else 0.0
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hpm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hpm = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hpm = (h1p + h2p + 360) / 2
    else:
        hpm = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hpm - 30)) + 0.24 * math.cos(math.radians(2 * hpm))
         + 0.32 * math.cos(math.radians(3 * hpm + 6)) - 0.20 * math.cos(math.radians(4 * hpm - 63)))
    dtheta = 30 * math.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / math.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ scheda
def colori_citati(obj):
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in ("riprese", "fonte"):
                out |= colori_citati(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= colori_citati(v)
    elif isinstance(obj, str) and RE_C.match(obj):
        out.add(obj)
    return out


def quota_target(el):
    """Restituisce (valore, confidenza, cosa, solo_minimo)."""
    q = el.get("quote", {})
    if "colmo" in q:
        return q["colmo"]["m"], q["colmo"].get("confidenza", "media"), "colmo", False
    if "gronda" in q:
        piana = el.get("copertura", {}).get("forma", "piana").startswith("pian")
        return q["gronda"]["m"], q["gronda"].get("confidenza", "media"), "gronda", not piana
    if isinstance(el.get("h"), dict):
        return el["h"]["m"], el["h"].get("confidenza", "media"), "h", False
    return None, None, None, False


# ------------------------------------------------------------------ verifica
def verifica(scheda, inv):
    el_inv = {}
    for e in inv.get("elementi", []):
        el_inv.setdefault(e["id"], []).append(e)
    mat_inv = {m["nome"]: m for m in inv.get("materiali", [])}
    righe, palette_out = [], []

    for c in scheda.get("palette", []):
        nomi = [n for n in mat_inv if n.split("_")[0] == c["id"]]
        if not nomi:
            palette_out.append({"id": c["id"], "esito": "❌", "nota": "materiale C##_… assente"})
            continue
        for n in nomi:
            m = mat_inv[n]
            de = delta_e2000(srgb_to_lab(hex_to_rgb(c["hex"])), srgb_to_lab(m["rgb"]))
            tol = TOL_DE_TEXTURE if m.get("texture") else TOL_DE_TINTA
            palette_out.append({"id": c["id"], "materiale": n, "hex_scheda": c["hex"],
                                "rgb_modello": m["rgb"], "texture": bool(m.get("texture")),
                                "deltaE2000": round(de, 1), "tolleranza": tol,
                                "esito": "✅" if de <= tol else "❌"})

    ids_scheda = set()
    for cat in CATEGORIE:
        for el in scheda.get(cat, []):
            if el.get("stato") == "eliminato":
                continue
            ids_scheda.add(el["id"])
            r = {"id": el["id"], "categoria": cat, "problemi": []}
            inst = el_inv.get(el["id"], [])
            if not inst:
                r.update(presenza="❌", esito="❌")
                r["problemi"].append("elemento assente nel modello (nessun gruppo/componente con questo ID)")
                righe.append(r)
                continue
            r["presenza"] = "✅"
            n_att = el.get("n")
            if n_att and len(inst) != n_att:
                r["problemi"].append(f"istanze {len(inst)} vs {n_att} in scheda")
            h_mod = max(e["altezza"] for e in inst)
            val, conf, cosa, solo_min = quota_target(el)
            r["altezza_modello"] = round(h_mod, 2)
            if val is not None:
                tol = TOL_H.get(conf, 0.75)
                r.update(altezza_scheda=val, quota=cosa, confidenza=conf, tolleranza=tol)
                if solo_min:
                    if h_mod < val - tol:
                        r["problemi"].append(f"altezza {h_mod:.2f} m < gronda {val} m")
                    r["note"] = "colmo non in scheda: verificata solo la gronda come minimo"
                elif abs(h_mod - val) > tol:
                    r["problemi"].append(f"altezza {h_mod:.2f} m vs {cosa} {val} m (±{tol}, {conf})")
            usati = {m.split("_")[0] for e in inst for m in e.get("materiali", [])}
            mancanti = sorted(colori_citati(el) - usati)
            r["materiali_mancanti"] = mancanti
            if mancanti:
                r["problemi"].append("materiali non usati sull'elemento: " + ", ".join(mancanti))
            if not r["problemi"]:
                r["esito"] = "✅"
            elif any(p.startswith(("istanze", "materiali")) for p in r["problemi"]):
                r["esito"] = "❌"
            elif any(p.startswith("altezza") for p in r["problemi"]):
                r["esito"] = "⚠️" if conf == "bassa" else "❌"
            else:
                r["esito"] = "⚠️"
            righe.append(r)

    extra = sorted(set(el_inv) - ids_scheda)
    n = {k: sum(1 for r in righe if r["esito"] == k) for k in ("✅", "⚠️", "❌")}
    n_pal_ko = sum(1 for p in palette_out if p["esito"] == "❌")
    globale = ("NON CONFORME" if n["❌"] or n_pal_ko else "CONFORME CON RISERVE" if n["⚠️"] or extra else "CONFORME")
    return {"esito_globale": globale, "conteggi": n, "elementi": righe, "palette": palette_out,
            "id_non_in_scheda": extra, "senza_id": inv.get("senza_id", 0)}


# ------------------------------------------------------------------ immagini
def immagini(manifest, dir_riprese, dir_export, out):
    from PIL import Image, ImageChops, ImageFilter
    fatti = []
    for r in manifest.get("riprese", []):
        sv_p = os.path.join(dir_riprese, r["file"])
        su_p = os.path.join(dir_export, f"{r['id']}.png")
        if not (os.path.exists(sv_p) and os.path.exists(su_p)):
            fatti.append({"id": r["id"], "stato": "mancante", "sv": os.path.exists(sv_p), "su": os.path.exists(su_p)})
            continue
        sv = Image.open(sv_p).convert("RGB")
        su = Image.open(su_p).convert("RGB").resize(sv.size, Image.LANCZOS)
        aff = Image.new("RGB", (sv.width * 2 + 10, sv.height), (255, 255, 255))
        aff.paste(sv, (0, 0)); aff.paste(su, (sv.width + 10, 0))
        aff.save(os.path.join(out, f"{r['id']}_affiancato.png"))
        edges = su.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 25 else 0)
        cornice = Image.new("L", sv.size, 0)
        cornice.paste(edges.crop((2, 2, sv.width - 2, sv.height - 2)), (2, 2))  # toglie il bordo spurio
        edges = cornice
        rosso = Image.new("RGB", sv.size, (255, 0, 0))
        base = ImageChops.multiply(sv, Image.new("RGB", sv.size, (200, 200, 200)))
        base.paste(rosso, (0, 0), edges)
        base.save(os.path.join(out, f"{r['id']}_sovrapposto.png"))
        fatti.append({"id": r["id"], "stato": "ok", "inquadra": r.get("inquadra", "")})
    return fatti


def markdown(rep):
    L = [f"# Verifica automatica – esito: **{rep['esito_globale']}**", "",
         f"Elementi: ✅ {rep['conteggi']['✅']} · ⚠️ {rep['conteggi']['⚠️']} · ❌ {rep['conteggi']['❌']}"
         f" · ID non in scheda: {', '.join(rep['id_non_in_scheda']) or '—'} · contenitori senza ID: {rep['senza_id']}", "",
         "## Elementi", "", "| ID | Presenza | Altezza mod / scheda | Esito | Problemi |", "|---|---|---|---|---|"]
    for r in rep["elementi"]:
        h = f"{r.get('altezza_modello', '–')} / {r.get('altezza_scheda', '–')} ({r.get('quota', '')})"
        L.append(f"| {r['id']} | {r['presenza']} | {h} | {r['esito']} | {'; '.join(r['problemi']) or '—'} |")
    L += ["", "## Palette", "", "| C## | Materiale | Scheda | Modello (RGB) | ΔE2000 / tol | Esito |", "|---|---|---|---|---|---|"]
    for p in rep["palette"]:
        L.append(f"| {p['id']} | {p.get('materiale', '—')} | {p.get('hex_scheda', '')} | {p.get('rgb_modello', '')} | "
                 f"{p.get('deltaE2000', '–')} / {p.get('tolleranza', '–')} | {p['esito']} |")
    if rep.get("viste"):
        L += ["", "## Viste camera-matched (da valutare a vista, vedi 05-verifica.md §2)", ""]
        for v in rep["viste"]:
            L.append(f"- {v['id']}: {v['stato']} {v.get('inquadra', '')}")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scheda", required=True); ap.add_argument("--inventario", required=True)
    ap.add_argument("--manifest"); ap.add_argument("--riprese"); ap.add_argument("--export")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.scheda, encoding="utf-8") as f:
        scheda = json.load(f)
    with open(a.inventario, encoding="utf-8") as f:
        inv = json.load(f)
    os.makedirs(a.out, exist_ok=True)
    rep = verifica(scheda, inv)
    if a.export:
        man_p = a.manifest or os.path.join(a.riprese, "manifest_riprese.json")
        with open(man_p, encoding="utf-8") as f:
            rep["viste"] = immagini(json.load(f), a.riprese, a.export, a.out)
    with open(os.path.join(a.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    with open(os.path.join(a.out, "report.md"), "w", encoding="utf-8") as f:
        f.write(markdown(rep))
    print(f"{rep['esito_globale']} – {os.path.join(a.out, 'report.md')}")


if __name__ == "__main__":
    main()
