# Motore del contesto (generico)

Costruisce il contesto 3D di un lotto da dati aperti (catasto AdE, DTM LiDAR 1 m della Regione Sardegna, tendenza Copernicus) e
dalla scheda di rilievo. Gli script non contengono valori di un lotto: questi stanno tutti nel file `lotto.json`, nella cartella
del modello. Le uscite vengono scritte nella stessa cartella.

| Script | Ingresso → uscita |
|---|---|
| `terreno_tendenza.py <cartella> <Copernicus.tif>` | facoltativo: tendenza del terreno per le zone fuori dal DTM |
| `scena.py <cartella>` | `lotto.json` + dati → `scena.json` |
| `contesto.py <cartella>` | rilancia `scena.py`, poi → `contesto.json` + `texture/` (letto da `../sketchup/costruisci_contesto.rb`, e poi da Blender) |

Esempio, dalla cartella del repository:
```
python skills/rilievo-urbano/scripts/contesto/contesto.py rilievi/zona-cagliari-menta-tamburino/modello
```
Servono numpy, shapely, triangle, pyproj, tifffile, imagecodecs e Pillow.

## Cosa va in `lotto.json`
L'esempio completo è `rilievi/zona-cagliari-menta-tamburino/modello/lotto.json`.
- `origine` (lat, lng), `semilato_m` dell'area quadrata modellata, `seme_casuale`.
- `dati`: percorsi di DTM, tendenza, scheda, geojson del catasto (particelle e fabbricati) e manifest delle riprese.
- `strade`: larghezza e rialzo del marciapiede, particelle catastali che in realtà sono strada, materiali.
- `lotto`: indice della particella del progetto, materiali, muro sul fronte strada (altezze minima e massima, scarpata),
  recinzione sul fronte (tratto in cui c'è), regola per l'arredo.
- `muri_contorno`: muri di cinta degli edifici vicini (id della scheda, edificio, altezza, eventuale ringhiera o doghe sopra).
- `edifici`: altezza e materiale degli edifici non descritti in scheda, piattaforme da togliere.
- `arredo` e `vegetazione`: posizione con `xy`, `lungo_fronte_m`, `fronte_y` o `da_punta`, più `offset` dal fronte.

Per un lotto nuovo: copia la cartella di esempio, sostituisci dati e scheda, aggiorna `lotto.json`, lancia `contesto.py` e
verifica come descritto in `../../references/05-verifica.md`.
