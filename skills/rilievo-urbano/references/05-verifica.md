# Protocollo di VERIFICA

Obiettivo: stabilire, elemento per elemento, se il modello SketchUp coincide con la scheda, con
criteri ripetibili e non "a occhio".

## Input richiesti dall'agente SketchUp
(vedi `06-consegna-sketchup.md`)
- `inventario.json` prodotto da `scripts/sketchup/inventario_modello.rb`;
- cartella `export_verifica/` con i PNG generati da `scripts/sketchup/scene_da_manifest.rb`
  (stessi ID delle riprese: `SV-01.png`…);
- eventuali viste di progetto e note su ciò che non ha potuto modellare.

## 1. Controllo automatico
```
python3 scripts/confronta.py --scheda scheda.json --inventario inventario.json \
  --riprese _rif_google/ --export export_verifica/ --out verifica/
```
Produce `verifica/report.json`, `verifica/report.md` e per ogni ripresa
`verifica/SV-xx_affiancato.png` (Street View | SketchUp) e `SV-xx_sovrapposto.png` (bordi del modello
in rosso sopra la foto).

Controlli e tolleranze:
| Controllo | Criterio | Tolleranza |
|---|---|---|
| Presenza | ogni ID della scheda (non eliminato) esiste nel modello; nessun ID sconosciuto | 0 mancanti |
| Altezza massima | quota più alta dell'elemento sopra la sua base vs `colmo` (o `gronda`, o `h`) | alta ±0,30 m · media ±0,75 m · bassa ±1,50 m |
| Palette | ogni C## esiste come materiale `C##_…`; ΔE2000 tra colore del materiale e `hex` | tinta unita ≤ 5 · texture ≤ 10 (colore medio) |
| Materiali per elemento | i C## citati dall'elemento compaiono tra i materiali usati dall'elemento | tutti presenti |
| Posizione (se georeferenziato) | baricentro dell'elemento entro il perimetro della zona | dentro |

ΔE2000 ≤ 2 è indistinguibile a occhio, 2–5 percettibile, > 10 colore diverso. Le soglie sono
larghe di proposito: il colore della scheda è già una stima da foto.

## 2. Controllo visivo camera-matched
Per ogni ripresa apri l'affiancato e il sovrapposto (Read) e valuta, in quest'ordine:
1. **Allineamento della camera** – se orizzonte e spigoli a terra non coincidono, il problema è di
   camera (origine, nord, quota occhio), non di modello: segnalalo e non giudicare il resto.
   Correzioni tipiche: quota occhio ±0,3 m, nord sbagliato (rotazione costante di tutte le viste),
   origine traslata (errore uguale in tutte le viste).
2. **Profilo e skyline** – linee di gronda e colmo, attici, volumi tecnici.
3. **Partizione** – numero di piani, basamento, marcapiani, cornicione.
4. **Ritmo delle aperture** – numero di assi, allineamenti, larghezze relative.
5. **Materiali e colori** – corrispondenza al C## (non al tono della foto, che è influenzato dalla luce).
6. **Recinzioni, arredo, vegetazione** – presenza, posizione relativa, altezza rispetto ai riferimenti.

## 3. Esiti
- ✅ **Conforme** – entro tolleranza in tutti i controlli.
- ⚠️ **Scostamento minore** – fuori tolleranza solo in un controllo con confidenza bassa, o dettaglio
  LOD3 non determinante per le viste di progetto.
- ❌ **Non conforme** – manca, quota fuori tolleranza su dato alto/medio, colore errato, numero di piani
  o assi errato, tipologia di copertura/recinzione errata.
- 🔁 **Da rivedere la scheda** – il confronto con la foto mostra che sbagliava la scheda: correggi
  `scheda.json`, incrementa `revisione`, comunicalo.

## 4. Verbale
```
# Verbale di verifica – <zona> – rev. scheda N – ciclo K
Esito globale: CONFORME | CONFORME CON RISERVE | NON CONFORME   (✅ n · ⚠️ n · ❌ n · 🔁 n)

## Correzioni richieste (ordinate per impatto sulle viste di progetto)
1. ❌ E02 – mancano gli abbaini lato S (scheda §E02, SV-04): 3 abbaini a capanna L 1,2 m…
2. ❌ C01 – colore troppo saturo (ΔE 12,4): portare a #D8B98C…
…
## Tabella per elemento
| ID | Presenza | Altezza (mod/scheda) | Materiali | Visivo | Esito | Note |
## Revisioni della scheda
## Camera: note sull'allineamento
```
Ogni correzione deve essere **azionabile** in SketchUp: elemento, cosa, misura/colore target,
ripresa di riferimento.

## 5. Cicli
Massimo 3 cicli DESCRIVI→MODELLA→VERIFICA. Al terzo ciclo con ❌ residui, fermati e porta la
decisione all'utente con le opzioni (accettare, approfondire con rilievo in sito, ridurre il LOD).
