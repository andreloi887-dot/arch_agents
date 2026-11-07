# Motore del contesto (generico)

Costruisce il contesto 3D di un lotto da dati aperti (catasto AdE, DTM LiDAR 1 m della Regione Sardegna, tendenza Copernicus) e
dalla scheda di rilievo. Gli script non contengono valori di un lotto: questi stanno tutti nel file `lotto.json`, nella cartella
del modello. Le uscite vengono scritte nella stessa cartella.

| Script | Ingresso → uscita |
|---|---|
| `prepara_lotto.py --cartella <zona> --origine lat,lng --lotto lat,lng` | scarica catasto, DTM LiDAR, Database Geotopografico (strade, assi, recinzioni, muri, edifici), DSM LiDAR (superficie, edifici, vegetazione) e ortofoto 2022; trova la particella, scrive `lotto.json` e una scheda minima |
| `verifica_contesto.py <cartella>` | controlli automatici di qualità (arredo in carreggiata, muri sulla sede, fronti scoperti, quote non misurate, balconi non dichiarati) → `verifica_contesto.md` |
| `dsm.py <cartella>` | mosaico e ritaglio delle tavole DSM sull'area (lanciato da `prepara_lotto.py`) |
| `terreno_tendenza.py <cartella> <Copernicus.tif>` | facoltativo: tendenza del terreno per le zone fuori dal DTM |
| `scena.py <cartella>` | `lotto.json` + dati → `scena.json` |
| `contesto.py <cartella>` | rilancia `scena.py`, poi → `contesto.json` + `texture/` (letto da `../sketchup/costruisci_contesto.rb`, e poi da Blender) |

Esempio, dalla cartella del repository (lotto nuovo):
```
python skills/rilievo-urbano/scripts/contesto/prepara_lotto.py --cartella rilievi/zona-<nome> --origine 39.25240,9.11527 --lotto 39.252625,9.115154
python skills/rilievo-urbano/scripts/contesto/contesto.py rilievi/zona-<nome>/modello
```
`--origine` è il punto (0,0) del modello, da usare anche come punto base in Edificius; `--lotto` è un punto qualsiasi dentro la
particella del progetto. Già così esce un contesto completo, con terreno, strade, marciapiedi, edifici LOD1 e muro sul fronte.
Poi l'agente rilievo-urbano completa la scheda: altezze, materiali, muri di cinta, arredo, e le particelle che in realtà sono
strada (`strade.punti_aggiunti_al_sedime`) o che a catasto sono staccate dal lotto ma ne fanno parte
(`lotto.punti_aggiunti_al_lotto`). Le particelle si indicano con un punto [lat, lng] al loro interno, non con il numero
d'ordine, che cambia se si riscarica il catasto.

Per rigenerare un lotto esistente:
```
python skills/rilievo-urbano/scripts/contesto/contesto.py rilievi/zona-cagliari-menta-tamburino/modello
```
Servono numpy, shapely, triangle, pyproj, tifffile, imagecodecs, Pillow e opencv-python-headless (per il catasto).

## Cosa va in `lotto.json`
Se c'è il progetto IFC, `lotto.perimetro_progetto` (scritto da `../blender/importa_progetto.py`) sostituisce il lotto
catastale: il motore porta la sede stradale fino al filo del progetto.
L'esempio completo è `rilievi/zona-cagliari-menta-tamburino/modello/lotto.json`.
- `origine` (lat, lng), `semilato_m` dell'area quadrata modellata, `seme_casuale`.
- `dati`: percorsi di DTM, tendenza, scheda, geojson del catasto (particelle e fabbricati) e manifest delle riprese.
- `strade`: larghezza e rialzo del marciapiede, particelle catastali che in realtà sono strada, materiali.
- `lotto`: `punto` dentro la particella del progetto, eventuali particelle da unire, materiali, muro sul fronte strada (altezze minima e massima, scarpata),
  recinzione sul fronte (tratto in cui c'è), regola per l'arredo.
- `muri_contorno`: muri di cinta degli edifici vicini (id della scheda, edificio, altezza, eventuale ringhiera o doghe sopra).
- `edifici`: altezza e materiale degli edifici non descritti in scheda, piattaforme da togliere, e `per_edificio`
  (per id, anche CTXnn): altezza di gronda, colmo, copertura (`piana`, `a padiglione`, `a capanna`), pendenza, manto.
  I tetti a falde li genera `contesto.py`, con una regola valida per qualsiasi pianta.
- `confini_interni`: muri di confine tra i giardini (altezza, spessore, materiale). Vengono ricavati dai lati delle
  particelle edificate lontani dalla strada; le osservazioni vengono da Google Earth 3D, solo come descrizione.
- `arredo` e `vegetazione`: posizione con `xy`, `lungo_fronte_m`, `fronte_y` o `da_punta`, più `offset` dal fronte.

Dopo ogni modifica: lancia `contesto.py` e verifica come descritto in `../../references/05-verifica.md`.
Limiti: il DTM LiDAR regionale copre la Sardegna (fuori copertura lo script si ferma); l'origine non deve cadere a più di
`semilato_m` dal lotto.

## Dettagli generati (regole generali, dati dal rilievo)
- Fronti su strada: muro + `sopra` (ringhiera a bacchette, doghe, grigliato, telo), pilastri a passo, copertina,
  cancelli e cancelletti (`cancelli`: tipo, larghezza, posizione 0–1 lungo il fronte, stile, pensilina) che
  interrompono il muro. Ogni tratto di bordo stradale va alla particella edificata più vicina e, dentro la
  particella, all'edificio più vicino.
- Facciate: infissi completi (telaio, vetro, davanzale, persiane o avvolgibile con cassonetto), balconi per piano
  (`balconi_piani`, `balcone_frazione`), portoncino al piano terra del fronte principale.
- Coperture: falde, sporti, timpani, parapetti dei tetti piani, moduli fotovoltaici rettangolari 1,0 × 1,7 m sulle
  falde rivolte a sud e a file inclinate sui tetti piani, torrette (`volumi`).
- Strade: profilo lisciato lungo gli assi, mezzeria tratteggiata (3 + 4,5 m), linee di margine, strisce pedonali solo
  dove rilevate (`strada`, `lato`, `incrocio`), cartelli di attraversamento ai due capi.
- Segnaletica verticale (`segnaletica_verticale`): divieto di sosta (+ pannello), divieto di fermata, senso vietato,
  attraversamento pedonale, dare precedenza, frecce di direzione, targhe delle vie; piastra orientata sul traffico.
- Lampioni: palo conico zincato su plinto, sbraccio e armatura verso la carreggiata, passo e lato da `lampioni`.
- Controlli: nessun muro di sostegno DBGT sulla sede stradale o sul fronte del lotto.

## Blender
`../blender/importa_contesto.py`: `blender -b -P importa_contesto.py -- <cartella modello> [--render] [--samples 16]`
→ `uscita_blender/contesto.blend` (+ `viste/` con le camere delle riprese e le viste aeree). Gli oggetti destinati a
modelli di libreria hanno la proprietà `asset` (lampione_stradale, segnale_*, albero, palma, palma_alta).
Opzioni del sole: `--data AAAA-MM-GG --ora HH:MM --fuso 2`. Erbe del lotto incolto con Geometry Nodes (`libreria.json → sostituzioni.prato_lotto`).
Non usare mai `read_factory_settings` negli script (vedi `references/08-lezioni-apprese.md`).
