#!/usr/bin/env python3
"""Instradatore verso modelli LLM gratuiti (livello 0 di CLAUDE.md).

Sceglie il primo modello disponibile del livello richiesto (semplice, medio, complesso, visione)
tra i provider di cui c'è la chiave, e passa al successivo in caso di errore o limite superato.
Usa solo la libreria standard.

Esempi:
  python llm_gratis.py --livello semplice "Traduci in inglese: intonaco a calce"
  python llm_gratis.py --livello medio --file didascalie.txt --sistema "Traduci in inglese, una riga per riga"
  python llm_gratis.py --immagine facciata.jpg "Elenca materiali e colori visibili"
  python llm_gratis.py --livello semplice --per-riga materiali.txt \
      --sistema "Normalizza il nome del materiale in italiano tecnico, una riga" > out.jsonl
  python llm_gratis.py --stato

Chiavi: variabili d'ambiente (GROQ_API_KEY, GEMINI_API_KEY, ...) oppure il file .env accanto
a questo script (ignorato da git). Il modello che ha risposto viene scritto su stderr.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

QUI = Path(__file__).resolve().parent
CATALOGO = json.loads((QUI / "modelli.json").read_text(encoding="utf-8"))
TIMEOUT = 120


def carica_env():
    f = QUI / ".env"
    if not f.exists():
        return
    for riga in f.read_text(encoding="utf-8-sig").splitlines():  # -sig: Blocco note può aggiungere il BOM
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            k, v = riga.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# Nelle sessioni cloud di Claude Code le chiavi non sono in variabili: le aggiunge il proxy di rete.
# Lì si manda un segnaposto, che il proxy sostituisce per i provider con un segreto salvato.
CLOUD = os.environ.get("CLAUDE_CODE_REMOTE") == "true"
SEGNAPOSTO = "proxy-injected"


def chiave(provider):
    k = os.environ.get(CATALOGO["provider"][provider]["chiave"], "").strip()
    return k or (SEGNAPOSTO if CLOUD else "")


def http(metodo, url, key, corpo=None):
    dati = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dati, method=metodo, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "arch-agents-llm-gratis/1.0",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def contenuto(testo, immagini):
    if not immagini:
        return testo
    parti = [{"type": "text", "text": testo}]
    for p in immagini:
        mime = mimetypes.guess_type(p)[0] or "image/jpeg"
        b64 = base64.b64encode(Path(p).read_bytes()).decode()
        parti.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    return parti


# Esclusioni valide per tutta l'esecuzione: con --per-riga evitano di ripetere a ogni riga una richiesta
# che fallirà di sicuro (chiave rifiutata → tutto il provider; modello ritirato → solo quel modello).
ESCLUSI = set()
NOTA_NVIDIA = " (la chiave NVIDIA dura 12 mesi)"


def chiedi(livello, testo, sistema=None, immagini=(), provider=None, temperatura=0.2, max_token=None):
    """Ritorna (risposta, 'provider/modello'). Solleva RuntimeError se nessun candidato risponde."""
    candidati = CATALOGO["livelli"][livello]
    if provider:
        candidati = [c for c in candidati if c[0] == provider]
        if not candidati:
            raise RuntimeError(f"il provider {provider} non ha candidati per il livello {livello}")
    messaggi = ([{"role": "system", "content": sistema}] if sistema else []) + \
               [{"role": "user", "content": contenuto(testo, list(immagini))}]
    errori = []
    for prov, modello in candidati:
        if prov in ESCLUSI or (prov, modello) in ESCLUSI:
            errori.append(f"{prov}/{modello}: escluso dopo un errore precedente")
            continue
        key = chiave(prov)
        if not key:
            errori.append(f"{prov}: manca {CATALOGO['provider'][prov]['chiave']}")
            continue
        corpo = {"model": modello, "messages": messaggi, "temperature": temperatura}
        if max_token:
            corpo["max_tokens"] = max_token
        url = CATALOGO["provider"][prov]["base_url"].rstrip("/") + "/chat/completions"
        try:
            try:
                r = http("POST", url, key, corpo)
            except urllib.error.HTTPError as e:
                if e.code != 503:  # 503 = sovraccarico momentaneo: un secondo tentativo dopo una pausa
                    raise
                time.sleep(4)
                r = http("POST", url, key, corpo)
            scelta = r["choices"][0]
            msg = (scelta["message"].get("content") or "").strip()
            troncata = scelta.get("finish_reason") == "length"
            limite = f"--max-token {max_token}" if max_token else "il limite predefinito del modello"
            if msg:
                if troncata:
                    print(f"attenzione: risposta di {prov}/{modello} troncata da {limite}; "
                          "alza --max-token o toglilo (con Gemini il limite conta anche il ragionamento)",
                          file=sys.stderr)
                return msg, f"{prov}/{modello}"
            errori.append(f"{prov}/{modello}: risposta vuota"
                          + (f" ({limite} esaurito dal ragionamento: alzalo o toglilo)" if troncata else ""))
        except urllib.error.HTTPError as e:
            dettaglio = e.read().decode("utf-8", "replace")[:200]
            nota = NOTA_NVIDIA if prov == "nvidia" else ""
            if CLOUD and key == SEGNAPOSTO and e.code in (400, 401, 403):
                dettaglio = "segreto mancante, errato o scaduto nell'ambiente cloud" + nota
                ESCLUSI.add(prov)
            elif e.code in (401, 403):
                dettaglio = f"chiave non valida o scaduta{nota} – " + dettaglio
                ESCLUSI.add(prov)
            elif e.code in (404, 410):
                ESCLUSI.add((prov, modello))  # modello ritirato: va corretto modelli.json
            errori.append(f"{prov}/{modello}: HTTP {e.code} {dettaglio}")
        except urllib.error.URLError as e:
            motivo = "sito non abilitato nella rete dell'ambiente cloud" if CLOUD and "403" in str(e) else e
            errori.append(f"{prov}/{modello}: {motivo}")
        except OSError as e:  # timeout (in 3.9 socket.timeout non è TimeoutError), connessione chiusa o azzerata
            errori.append(f"{prov}/{modello}: errore di rete: {e!r}")
        except (KeyError, IndexError, TypeError, ValueError) as e:  # risposta non nel formato OpenAI
            errori.append(f"{prov}/{modello}: risposta inattesa: {e!r}")
    raise RuntimeError("nessun modello gratuito ha risposto:\n  " + "\n  ".join(errori))


def stato():
    """Elenca i provider configurati e controlla che i modelli del catalogo esistano ancora."""
    print("Provider configurati:")
    modelli_vivi = {}
    for prov, cfg in CATALOGO["provider"].items():
        key = chiave(prov)
        if not key:
            print(f"  -  {prov:10s} manca {cfg['chiave']}  (chiave: {cfg['chiave_url']}, carta: {cfg['carta']})")
            continue
        try:
            r = http("GET", cfg["base_url"].rstrip("/") + "/models", key)
            ids = {m.get("id", "").removeprefix("models/") for m in r.get("data", [])}
            modelli_vivi[prov] = ids
            print(f"  ok {prov:10s} {len(ids)} modelli")
        except Exception as e:  # noqa: BLE001 - è un report
            print(f"  !! {prov:10s} errore: {e}")
    print("\nCandidati per livello (ok = presente nell'elenco del provider):")
    for liv, cand in CATALOGO["livelli"].items():
        print(f"  {liv}")
        for prov, modello in cand:
            if prov not in modelli_vivi:
                segno = "  -"
            else:
                segno = " ok" if modello in modelli_vivi[prov] else " ??"
            print(f"   {segno} {prov}/{modello}")


def leggi(percorso):
    return Path(percorso).read_text(encoding="utf-8-sig")


def main():
    # Su Windows, con l'uscita rediretta su file (es. "> out.jsonl"), Python usa cp1252 e si ferma al primo
    # carattere fuori tabella (≈, →, emoji). L'uscita è sempre UTF-8.
    for flusso in (sys.stdout, sys.stderr):
        flusso.reconfigure(encoding="utf-8")
    carica_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", help="testo della richiesta (altrimenti --file o stdin)")
    ap.add_argument("--livello", choices=list(CATALOGO["livelli"]), default="medio")
    ap.add_argument("--sistema", help="istruzioni di sistema")
    ap.add_argument("--file", help="aggiunge il contenuto del file alla richiesta")
    ap.add_argument("--immagine", action="append", default=[], help="immagine da allegare (forza il livello visione)")
    ap.add_argument("--per-riga", metavar="FILE", help="applica la richiesta a ogni riga del file, uscita JSONL")
    ap.add_argument("--provider", choices=list(CATALOGO["provider"]), help="usa solo questo provider")
    ap.add_argument("--temperatura", type=float, default=0.2)
    ap.add_argument("--max-token", type=int)
    ap.add_argument("--pausa", type=float, default=0.0, help="secondi tra le righe in --per-riga")
    ap.add_argument("--stato", action="store_true", help="mostra chiavi presenti e verifica i modelli")
    a = ap.parse_args()

    if a.stato:
        stato()
        return 0
    livello = "visione" if a.immagine else a.livello
    opz = dict(sistema=a.sistema, immagini=a.immagine, provider=a.provider,
               temperatura=a.temperatura, max_token=a.max_token)

    if a.per_riga:
        righe = [r for r in leggi(a.per_riga).splitlines() if r.strip()]
        falliti = di_fila = 0
        for i, riga in enumerate(righe, 1):
            testo = f"{a.prompt}\n\n{riga}" if a.prompt else riga
            try:
                risp, chi = chiedi(livello, testo, **opz)
                print(json.dumps({"ingresso": riga, "uscita": risp, "modello": chi}, ensure_ascii=False), flush=True)
                di_fila = 0
            except RuntimeError as e:
                falliti += 1
                di_fila += 1
                print(json.dumps({"ingresso": riga, "errore": str(e)}, ensure_ascii=False), flush=True)
            print(f"[{i}/{len(righe)}]", file=sys.stderr)
            if di_fila >= 3 and i < len(righe):
                # di solito limiti esauriti su tutti i provider: continuare consuma richieste senza risultati
                print(f"interrotto: 3 righe fallite di fila, {len(righe) - i} righe non elaborate; "
                      "rilancia più tardi sulle righe mancanti", file=sys.stderr)
                return 1
            if a.pausa:
                time.sleep(a.pausa)
        return 1 if falliti else 0

    parti = [a.prompt] if a.prompt else []
    if a.file:
        parti.append(leggi(a.file))
    if not parti and not sys.stdin.isatty():
        da_stdin = sys.stdin.read()
        if da_stdin.strip():
            parti.append(da_stdin)
    if not parti:
        ap.error("serve un prompt, --file o testo su stdin")
    try:
        risp, chi = chiedi(livello, "\n\n".join(parti), **opz)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2
    print(f"[{livello} → {chi}]", file=sys.stderr)
    print(risp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
