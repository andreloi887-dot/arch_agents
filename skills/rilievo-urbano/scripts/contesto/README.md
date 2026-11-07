# Motore del contesto (generico)

Costruisce il contesto 3D di un lotto da dati aperti (catasto AdE, DTM LiDAR 1 m della Regione Sardegna, tendenza Copernicus) e
dalla scheda di rilievo. Gli script non contengono valori di un lotto: questi stanno tutti nel file `lotto.json`, nella cartella
del modello. Le uscite vengono scritte nella stessa cartella.

| Script | Ingresso → uscita |
|---|---|
| `prepara_lotto.py --cartella <zona> --origine lat,lng --lotto lat,lng` | scarica catasto e DTM LiDAR, trova la particella, scrive `lotto.json` e una scheda minima |
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
L'esempio completo è `rilievi/zona-cagliari-menta-tamburino/modello/lotto.json`.
- `origine` (lat, lng), `semilato_m` dell'area quadrata modellata, `seme_casuale`.
- `dati`: percorsi di DTM, tendenza, scheda, geojson del catasto (particelle e fabbricati) e manifest delle riprese.
- `strade`: larghezza e rialzo del marciapiede, particelle catastali che in realtà sono strada, materiali.
- `lotto`: `punto` dentro la particella del progetto, eventuali particelle da unire, materiali, muro sul fronte strada (altezze minima e massima, scarpata),
  recinzione sul fronte (tratto in cui c'è), regola per l'arredo.
- `muri_contorno`: muri di cinta degli edifici vicini (id della scheda, edificio, altezza, eventuale ringhiera o doghe sopra).
- `edifici`: altezza e materiale degli edifici non descritti in scheda, piattaforme da togliere.
- `arredo` e `vegetazione`: posizione con `xy`, `lungo_fronte_m`, `fronte_y` o `da_punta`, più `offset` dal fronte.

Dopo ogni modifica: lancia `contesto.py` e verifica come descritto in `../../references/05-verifica.md`.
Limiti: il DTM LiDAR regionale copre la Sardegna (fuori copertura lo script si ferma); l'origine non deve cadere a più di
`semilato_m` dal lotto.
