#!/usr/bin/env python3
"""Controlli automatici di qualità sul contesto generato (scena.json + contesto.json): gli errori trovati nei test
(references/08-lezioni-apprese.md) diventano controlli. Scrive verifica_contesto.md nella cartella del modello ed
esce con codice 1 se ci sono errori bloccanti.

  python verifica_contesto.py <cartella modello>
"""
import json, math, os, sys
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union

M = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sc = json.load(open(os.path.join(M, "scena.json"), encoding="utf-8"))
cx = json.load(open(os.path.join(M, "contesto.json"), encoding="utf-8"))
carr = unary_union([Polygon([p[:2] for p in s["anello"]]).buffer(0) for s in sc["strade"]])
marc = unary_union([Polygon([p[:2] for p in s["anello"]], [[q[:2] for q in h] for h in s.get("fori", [])]).buffer(0)
                    for s in sc["marciapiedi"]])
sede = carr.union(marc)
edif = unary_union([Polygon(e["impronta"]).buffer(0) for e in sc["edifici"]])
err, avv, ok = [], [], []

# 1. arredo e cartelli mai in carreggiata
fuori = [o["nome"] for o in cx["oggetti"] if carr.buffer(0.2).contains(Point(o["xy"]))]
(err if fuori else ok).append(f"arredo in carreggiata: {len(fuori)}" + (f" ({', '.join(fuori[:6])})" if fuori else ""))
# 2. cartelli quasi sovrapposti
seg = [o for o in cx["oggetti"] if o.get("testa") == "segnale"]
dup = sum(1 for i, a in enumerate(seg) for b in seg[i+1:] if math.dist(a["xy"], b["xy"]) < 0.8)
(avv if dup else ok).append(f"cartelli a meno di 0,8 m l'uno dall'altro: {dup}")
# 3. muri: nessuno in carreggiata; muri interni e di sostegno non sulla sede
in_carr = [m["id"] for m in sc["muri"] if LineString([p[:2] for p in m["punti"]]).intersection(carr.buffer(-0.1)).length > 0.3]
(err if in_carr else ok).append(f"muri in carreggiata: {len(in_carr)} {sorted(set(in_carr))[:8] if in_carr else ''}")
in_sede = [m["id"] for m in sc["muri"] if m["id"].startswith(("CI", "MS"))
           and LineString([p[:2] for p in m["punti"]]).intersection(sede.buffer(-0.3)).length > 0.5]
(err if in_sede else ok).append(f"confini interni o muri di sostegno sulla sede stradale: {len(in_sede)} {sorted(set(in_sede))[:8] if in_sede else ''}")
# 4. muri su strada troppo alti rispetto al rilievo (o anomali)
alti = []
for m in sc["muri"]:
    if not m.get("su_strada"): continue
    h = max(t - b for t, b in zip(m["z_sommita"], m["z_base"]))
    if h > 3.5: alti.append(f"{m['id']} {h:.1f} m")
(avv if alti else ok).append(f"muri su strada oltre 3,5 m: {len(alti)} {alti[:6] if alti else ''}")
# 5. fronti su strada di lotti edificati senza muro (bordo della sede scoperto vicino a un edificio)
bd = sede.boundary; coperto = unary_union([LineString([p[:2] for p in m["punti"]]).buffer(1.5) for m in sc["muri"]] +
                                         [LineString([p[:2] for p in c["punti"]]).buffer(1.0) for c in sc.get("cancelli", [])])
scoperti = 0.0; esempi = []
for e in sc["edifici"]:
    P = Polygon(e["impronta"])
    vicino = bd.intersection(P.buffer(15))
    if vicino.is_empty: continue
    resto = vicino.difference(coperto)
    L_ = resto.length
    if L_ > 6: scoperti += L_; esempi.append(f"{e['id']} {L_:.0f} m")
(avv if esempi else ok).append(f"bordo stradale senza muro entro 15 m dagli edifici: {scoperti:.0f} m" + (f" ({', '.join(esempi[:8])})" if esempi else ""))
# 6. edifici: fonte delle quote
stime = [e["id"] for e in sc["edifici"] if not str(e.get("quote_fonte", "")).startswith("DSM")]
(avv if stime else ok).append(f"edifici con quote stimate (non misurate dal DSM): {len(stime)} {stime}")
# 7. edifici di scheda senza facciate o senza balconi espliciti
senza = [e["id"] for e in sc["edifici"] if e.get("lod", 1) >= 2 and not e.get("facciate")]
(avv if senza else ok).append(f"edifici di scheda senza facciate descritte: {len(senza)} {senza}")
nobal = [e["id"] for e in sc["edifici"] if e.get("facciate") and not any("balconi_piani" in f for f in e["facciate"])]
(avv if nobal else ok).append(f"edifici con facciate ma senza `balconi_piani` esplicito: {len(nobal)} {nobal}")
# 8. alberi in carreggiata o dentro edifici
alb = [v["nome"] for v in cx["vegetazione"] if carr.contains(Point(v["xy"])) or edif.contains(Point(v["xy"]))]
(err if alb else ok).append(f"alberi in carreggiata o dentro edifici: {len(alb)}")
# 9. cancelli fuori dal fronte (non su un muro su strada)
canc_out = [c["id"] for c in sc.get("cancelli", []) if sede.distance(LineString(c["punti"])) > 2.5]
(avv if canc_out else ok).append(f"cancelli lontani dalla sede stradale: {len(canc_out)} {canc_out}")

righe = ["# Verifica automatica del contesto", "", f"Cartella: `{M}`", "",
         f"**Errori: {len(err)} · Avvisi: {len(avv)} · Controlli superati: {len(ok)}**", ""]
for tit, lst, s_ in (("Errori", err, "❌"), ("Avvisi", avv, "⚠️"), ("Superati", ok, "✅")):
    if lst: righe += [f"## {tit}"] + [f"- {s_} {x}" for x in lst] + [""]
open(os.path.join(M, "verifica_contesto.md"), "w", encoding="utf-8").write("\n".join(righe))
print("\n".join(righe))
sys.exit(1 if err else 0)
