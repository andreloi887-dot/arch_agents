"""Ricette dei tessili degli arredi (2026-11-17): le stesse funzioni per la filiera (arredi_interni.py) e per il banco di
prova in scena (skills/arredo-da-riferimento/scripts/banco_scena.py). Ogni ricetta riceve:
  scn    la scena
  R      la geometria del pezzo (dizionario semplice, salvato anche come proprietà "ricetta" sull'oggetto del mobile)
  O      le regolazioni (dizionario; quelle mancanti prendono i valori buoni scritti qui). Il banco le cambia da riga di
         comando (chiave=valore) senza toccare il codice; quando una prova piace, il valore diventa il predefinito qui.
e restituisce l'elenco degli oggetti fatti (nomi che finiscono con "(tessili)") e le righe di log.
"""
import math
from mathutils import Vector
import tessili
from materiali_arredo import mat, TEX


def _o(O, k, d):
    v = O.get(k, d)
    return type(d)(v) if d is not None and not isinstance(v, type(d)) else v


# ------------------------------------------------------------------------------------------------------------------- letto
def letto(scn, R, O=None):
    """piumone che cade sul materasso e sulla piattaforma, plaid ai piedi, guanciali e cuscini decorativi che si
    appoggiano davvero (gravità, testata, materasso). R: o, us (dai piedi verso... asse lungo con il segno della testata), vv,
    m0, m1, mw, L, W, z0, hw (mezza larghezza della testata), nome."""
    O = O or {}; log = []
    o, us, vv_ = Vector(R["o"]), Vector(R["us"]), Vector(R["vv"]); m0, m1, mw, L, W, z0 = (R[k] for k in ("m0", "m1", "mw", "L", "W", "z0"))
    nome = R["nome"]; hw = R.get("hw", W / 2)
    def P_(a, b): return o + us * a + vv_ * b
    # quote del materasso e della base (R["zm"], R["zb"]): il letto singolo imbottito (2026-11-17) è più alto e senza cornice
    zm, zb = R.get("zm", [0.25, 0.45]), R.get("zb", [0.12, 0.24]); imb = R.get("imbottito", False)
    materasso = (P_((m0 + m1) / 2, 0), us, vv_, m1 - m0, 2 * mw, z0 + zm[0], z0 + zm[1])
    piatta = (P_(0.025, 0), us, vv_, L - 0.05, W, z0 + zb[0], z0 + zb[1])          # 1 cm sotto il materasso: niente facce coincidenti
    # testata come ostacolo spesso 35 cm (verso il muro): con i suoi 5 cm veri il guanciale che ci cade sopra la attraversava
    testata = (P_(-L / 2 - 0.15, 0), us, vv_, 0.35, 2 * hw, z0, z0 + 1.0)
    pavimento = (P_(0, 0), us, vv_, L + 1.5, W + 1.5, z0 - 0.05, z0)
    fatti = []
    # piumone: involucro gonfiato che cade sul materasso e sulla piattaforma
    # letto imbottito: il piumone è più largo del materasso e ricade sui fianchi e ai piedi
    a0, a1 = m0 + _o(O, "pium_testa", 0.42), (L / 2 + 0.10 if imb else L / 2 - 0.03)
    pium = tessili.trapunta(scn, f"{nome} piumone (tessili)", P_((a0 + a1) / 2, 0), us, vv_, a1 - a0, (2 * mw + 0.40 if imb else W - 0.04), z0 + zm[1] + 0.05,
                            [materasso, piatta, pavimento], mat("lenzuolo"), TEX["lenzuolo"][1], spessore=_o(O, "pium_sp", 0.06),
                            pressione=_o(O, "pium_pr", 1.5), piega=_o(O, "pium_piega", 0.05), grinze=_o(O, "pium_gr", 0.002),
                            tensione=_o(O, "pium_te", 6.0), passo=_o(O, "pium_passo", 0.03), fotogrammi=int(_o(O, "pium_fot", 110)),
                            peso=_o(O, "pium_peso", 0.6))
    fatti.append(pium)
    # plaid: cade sul piumone stesso (collisore); più spesso e pesante, largo quanto basta per ricadere sui fianchi.
    # 2026-11-17 (Andrea: "tessuti troppo rigidi"): cade da vicino (0,64), poco attrito (4) e piega di un plaid in maglia (1,0):
    # fascia morbida con poche pieghe lunghe invece della lastra accartocciata; piumone meno gonfio (1,5) e senza bozze
    # 2026-11-17, secondo giro (Andrea: "il plaid è pietoso"): non si lascia più cadere dall'alto. Nasce già steso sul piumone
    # simulato, con i lembi che pendono lungo i fianchi, e la simulazione lo assesta soltanto (tessili.telo_appoggiato)
    b0, b1 = L / 2 - _o(O, "plaid_da", 0.62), L / 2 - 0.08
    plaid = tessili.telo_appoggiato(scn, f"{nome} plaid (tessili)", P_((b0 + b1) / 2, 0), us, vv_, b1 - b0,
                                    2 * mw + (0.78 if W > 1.3 else 0.50), pium, mat("plaid"), TEX["plaid"][1],
                                    spessore=_o(O, "plaid_sp", 0.015), peso=_o(O, "plaid_peso", 0.006), piega=_o(O, "plaid_piega", 1.0),
                                    fotogrammi=int(_o(O, "plaid_fot", 50)), passo=_o(O, "plaid_passo", 0.02), pieghe=_o(O, "plaid_pieghe", 0.008),
                                    ostacoli=[pavimento], attrito=_o(O, "plaid_attrito", 4.0))
    fatti.append(plaid)
    import bpy
    zz = [q.co.z - z0 for q in plaid.data.vertices]
    log.append(f"{nome}: plaid da {min(zz):.2f} a {max(zz):.2f} m sul pavimento" + ("" if min(zz) > 0.1 else " — AVVISO: è caduto oltre il letto"))
    # guanciali in piedi contro la testata, cuscini decorativi davanti (riferimento): bordo cucito, ognuno un po' diverso,
    # poi lasciati cadere con la gravità sulla testata e sul materasso (Andrea, 2026-11-17: "troppo rigidi, tutti uguali")
    n = 2 if W > 1.3 else 1; lc = min(0.68, 2 * mw / n - 0.06)
    perp = Vector((-vv_.y, vv_.x)); sg = 1 if perp.dot(-us) > 0 else -1                    # +perp(vv_ × sg) = verso la testata
    seme0 = int(_o(O, "seme", 7)); guanciali = []
    for i in range(n):
        cv = -mw + (i + 0.5) * 2 * mw / n
        g = tessili.cuscino(scn, f"{nome} guanciale {i + 1} (tessili)", (*P_(m0 + _o(O, "g_da", 0.07), cv), z0 + zm[1]), vv_ * sg, lc, 0.50, 0.17,
                            mat("lenzuolo"), TEX["lenzuolo"][1], pressione=_o(O, "g_pr", 1.1), in_piedi=_o(O, "g_in", 0.55),
                            coltello=True, maglia=_o(O, "g_maglia", 0.02), morbido=_o(O, "g_morb", 2.0), rughe=_o(O, "g_rughe", 1.0),
                            seme=seme0 + 11 * i, varia=_o(O, "varia", 1.0), assesta=int(_o(O, "g_ass", 40)), via=tuple(us),
                            ostacoli=[materasso, testata], gonfio_assesta=_o(O, "g_gonfio", 1.0), massa_assesta=_o(O, "g_ma", 0.006))
        fatti.append(g); guanciali.append(g)
    cols = [tessili.collisore(scn, g, f"appoggio {g.name}") for g in guanciali]
    for i in range(n):
        cv = -mw + (i + 0.5) * 2 * mw / n
        fatti.append(tessili.cuscino(scn, f"{nome} cuscino {i + 1} (tessili)", (*P_(m0 + _o(O, "c_da", 0.33), cv), z0 + zm[1] + 0.02), vv_ * sg, lc - 0.16, 0.40, 0.13,
                                     mat("cuscino"), TEX["cuscino"][1], pressione=_o(O, "c_pr", 1.3), in_piedi=_o(O, "c_in", 0.40),
                                     coltello=True, maglia=_o(O, "c_maglia", 0.018), morbido=_o(O, "c_morb", 2.0), rughe=_o(O, "c_rughe", 1.0),
                                     seme=seme0 + 5 + 11 * i, varia=_o(O, "varia", 1.0), assesta=int(_o(O, "c_ass", 40)), via=tuple(us),
                                     ostacoli=[materasso], gonfio_assesta=_o(O, "c_gonfio", 1.0), massa_assesta=_o(O, "c_ma", 0.006)))
    for c_ in cols: bpy.data.objects.remove(c_, do_unlink=True)
    log.append(f"{nome}: tessili simulati {len(fatti)} (piumone, {n} guanciali, {n} cuscini, plaid)")
    return fatti, log


# ------------------------------------------------------------------------------------------------------------------ divano
def divano(scn, R, O=None):
    """cuscini del divano componibile: sedute e chaise a scatola, schienali in piedi, cuscini decorativi a bordo cucito,
    ognuno un po' diverso, che si appoggiano davvero sugli schienali e sulle sedute. R: cs, u, vv, sx0, sx1, lato, a0, a1,
    cz, villa."""
    import bpy
    O = O or {}; log = []
    cs, u, vv = Vector(R["cs"]), Vector(R["u"]), Vector(R["vv"]); sx0, sx1, lato, cz, villa = R["sx0"], R["sx1"], R["lato"], R["cz"], R["villa"]
    a0, a1 = R.get("a0"), R.get("a1"); mid = (sx0 + sx1) / 2; nb = 3; wb = (sx1 - sx0) / nb
    def W_(a_, b_): q = cs + u * a_ - vv * b_; return (q.x, q.y)
    perp = Vector((-u.y, u.x)); sg = 1 if perp.dot(vv) > 0 else -1          # verso lo schienale nel riferimento del cuscino
    seme0 = int(_o(O, "seme", 3)); varia = _o(O, "varia", 1.0)
    # (nome, punto, quota, lungo, largo, alto, inclinazione, materiale, pressione, a scatola)
    cus = [("seduta 1", W_((sx0 + mid) / 2, 0.105), 0.285, mid - sx0 - 0.01, 0.72, 0.13, 0.0, "boucle", 0.35, True),
           ("seduta 2", W_((mid + sx1) / 2, 0.105), 0.285, sx1 - mid - 0.01, 0.72, 0.13, 0.0, "boucle", 0.35, True)]
    if lato: cus.append(("chaise", W_((a0 + a1) / 2, 0.81), 0.285, abs(a1 - a0) - 0.02, 0.66, 0.13, 0.0, "boucle", 0.35, True))
    # in piedi contro il blocco dello schienale (faccia davanti a b = -0.26)
    cus += [(f"schienale {i + 1}", W_(sx0 + (i + 0.5) * wb, -0.265), 0.40, wb - 0.03, 0.40, 0.22, math.radians(22), "boucle", 4.0, False) for i in range(nb)]
    fatti = []
    for k, (nome_c, q_, zq, lu_, lv_, h_, inc, mt, pr, sc) in enumerate(cus):
        in_p = nome_c.startswith("schienale"); uc = Vector(u[:2]) * (sg if in_p else 1)   # +perp(uc) = verso lo schienale
        fatti.append(tessili.cuscino(scn, f"Divano v{villa} {nome_c} (tessili)", (q_[0], q_[1], cz + zq), uc, lu_, lv_, h_, mat(mt), TEX[mt][1],
                                     pressione=pr, scatolato=sc, in_piedi=inc if in_p else None,
                                     morbido=1.6 if sc else 6.0, seme=seme0 + 13 * k, varia=_o(O, "varia_imbottiti", 0.5)))
    # cuscini decorativi: bordo cucito, ognuno diverso, appoggiati agli schienali con la gravità (Andrea, 2026-11-17)
    base = [(Vector(W_(0, 0)), u, vv, 2.30, 0.95, cz + 0.05, cz + 0.30), (Vector(W_(0, -0.3675)), u, vv, 2.30, 0.215, cz + 0.30, cz + 0.60)]
    cols = [tessili.collisore(scn, ob, f"appoggio {ob.name}") for ob in fatti]
    posti = [(sx0 + _o(O, "d_bordo", 0.26), "sabbia"), (sx0 + _o(O, "d_bordo", 0.26) + _o(O, "d_coppia", 0.30), "boucle"),
             (sx1 - _o(O, "d_bordo", 0.26), "sabbia")] if _o(O, "d_tre", 0.0) else [(sx0 + 0.26, "sabbia"), (sx1 - 0.26, "sabbia")]
    for k, (a_, mt) in enumerate(posti):
        lato_c = _o(O, "d_lato", 0.42) * (1.0 if mt == "sabbia" else 0.92)
        fatti.append(tessili.cuscino(scn, f"Divano v{villa} cuscino {k + 1} (tessili)", (*W_(a_, -0.10), cz + 0.43), Vector(u[:2]) * sg, lato_c, lato_c, 0.10,
                                     mat(mt), TEX[mt][1], pressione=_o(O, "d_pr", 1.3), in_piedi=math.radians(_o(O, "d_in", 14.0)),
                                     coltello=True, maglia=_o(O, "d_maglia", 0.018), morbido=_o(O, "d_morb", 2.0), rughe=_o(O, "d_rughe", 1.0),
                                     seme=seme0 + 101 + 7 * k, varia=varia, assesta=int(_o(O, "d_ass", 45)), ostacoli=base, via=tuple(-vv),
                                     gonfio_assesta=_o(O, "d_gonfio", 1.0), massa_assesta=_o(O, "d_ma", 0.006)))
    for c_ in cols: bpy.data.objects.remove(c_, do_unlink=True)
    log.append(f"divano villa {villa}: cuscini simulati {len(fatti)} ({len(posti)} decorativi)")
    return fatti, log


# ----------------------------------------------------------------------------------------------------------------- armadio
def armadio(scn, R, O=None):
    """camicie appese nell'armadio con le ante in vetro (Andrea, 2026-11-17: "una camicia morbida, appesa"). R: o, u (lungo
    l'armadio, l'asta), v (verso le ante), z0, za (quota dell'asta sul pavimento), posti (ascisse delle grucce lungo u), ga,
    gb (tratto in vetro), W, fr (fronte della cassa), nome, villa."""
    O = O or {}; log = []
    o, u, v = Vector(R["o"]), Vector(R["u"]), Vector(R["v"]); z0, za, W = R["z0"], R["za"], R["W"]
    def P(a, b): return o + u * a + v * b
    colori = str(O.get("colori", "lenzuolo,camicia_cielo,lenzuolo,camicia_sabbia,camicia_cielo")).split(",")
    lunga = min(_o(O, "lunga", 0.72), za - 0.075 - 0.20)
    gm = (R["ga"] + R["gb"]) / 2; lg = R["gb"] - R["ga"]
    # solo il fondo: le camicie (44 cm, girate di 16°) stanno dentro senza toccare schiena e vetro; con quei due ostacoli le
    # maniche ci strisciavano e si accartocciavano (2026-11-17)
    ostacoli = [(P(gm, 0), u, v, lg, W, z0 + 0.07, z0 + 0.09)]                                    # fondo
    fatti = []
    for k, uc in enumerate(R["posti"]):
        mt = colori[k % len(colori)]
        fatti += tessili.camicia(scn, f"{R['nome']} camicia {k + 1}", (*P(uc, 0), z0 + za - 0.075), v, mat(mt), TEX[mt][1],
                                 larga=_o(O, "larga", 0.44), lunga=lunga, manica=min(_o(O, "manica", 0.56), lunga - 0.08),
                                 seme=int(_o(O, "seme", 21)) + 17 * k, pressione=_o(O, "pr", 0.06), pressione_manica=_o(O, "pr_manica", 0.3), fotogrammi=int(_o(O, "fot", 70)),
                                 passo=_o(O, "passo", 0.016), ostacoli=ostacoli, piega=_o(O, "piega", 0.7), ruota=_o(O, "ruota", 0.0))
    log.append(f"{R['nome']}: {len(R['posti'])} camicie simulate (lunghe {lunga:.2f} m, asta a {za:.2f} m)")
    return fatti, log
