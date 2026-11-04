# Scheda di rilievo: struttura

La scheda esiste in due forme **sempre allineate**:
- `scheda.json` – fonte di verità, letta dagli script (`confronta.py`) e dall'agente SketchUp;
- `scheda.md` – la stessa cosa in prosa tecnica, con le immagini, per la lettura umana.

Esempio completo: `templates/scheda.json`. Piano di riprese: `templates/piano_riprese.json`.

## Codifica degli ID
| Prefisso | Categoria | Note |
|---|---|---|
| `E##` | Edifici | In senso orario da NO, per isolato. Corpi distinti dello stesso edificio: `E03a`, `E03b` |
| `R##` | Recinzioni, muri, cancelli | Un ID per tratto omogeneo |
| `A##` | Arredo urbano | Un ID per tipologia in serie (es. 6 lampioni uguali = un A## con `n: 6`) |
| `P##` | Pavimentazioni e suolo | Per superficie omogenea |
| `V##` | Vegetazione | Per filare/gruppo omogeneo |
| `C##` | Palette materiale-colore | Ogni superficie del modello rimanda a un C## |
| `SV-##` | Riprese Street View | Dal `manifest_riprese.json` |

Gli ID non si rinumerano mai tra una revisione e l'altra: un elemento eliminato resta come
`"stato": "eliminato"`.

## Campi obbligatori

### Testata `zona`
`nome`, `comune`, `perimetro` (poligono lat/lng), `origine` (lat/lng + descrizione: è l'origine
anche in SketchUp), `scopo`, `lod_default`, `revisione`, `data_rilievo`, `date_streetview`
(intervallo), `fonti_geometria`.

### `lacune`
Elenco di ciò che non si è potuto vedere o verificare e dei rischi (date vecchie, cantieri, retri).

### `palette` (C##)
`id`, `materiale`, `finitura`, `hex`, `intervallo` (hex min/max campionati), `ral_indicativo`
(facoltativo, sempre "indicativo"), `texture` (`tipo` + `modulo_mm` reale, es. mattone 250×60 + giunto
10 → modulo 260×70), `confidenza`, `fonte` (ID riprese).

### Valore misurato
Ogni misura è un oggetto: `{"m": 15.6, "fonte": "DBT|LiDAR|OSM|stima-piani|stima-riferimento", "confidenza": "alta|media|bassa", "metodo": "…"}`.
`metodo` è obbligatorio quando la fonte è una stima.

### `edifici` (E##)
`id`, `indirizzo`, `lod`, `tipologia`, `epoca`, `impronta` (fonte + riferimento), `piani_ft`,
`quote` (`piano_terra`, `gronda`, `colmo`), `copertura` (`forma`, `pendenza_pct`, `manto` → C##,
`sporto_cm`, `elementi`), `facciate[]` (`fronte`, `orientamento`, `visibile`, `materiale` → C##,
`basamento`, `partitura`, `aperture`, `aggetti`, `riprese[]`), `note`.

`aperture`: `assi`, `passo_m`, `allineate`, `tipo[]` (`codice`, `l_m`, `h_m`, `davanzale_m`,
`mazzetta_cm`, `serramento` → C##, `oscurante` + C##, `cornice` + C##), `piano_terra` (vetrine, portoni).

### `recinzioni` (R##), `arredo` (A##), `pavimentazioni` (P##), `vegetazione` (V##)
`id`, `tipo`, `posizione` (descrittiva + coordinate indicative se utili), misure come valore
misurato (`h`, `l`, `passo`), `materiali` → C##, `n` per le serie, `riprese[]`, `lod`.

## Struttura di `scheda.md`
1. Testata: zona, scopo, LOD, origine, date delle immagini, fonti.
2. **Lacune e rischi** (in alto, non in fondo).
3. Mappa annotata (`mappa_annotata.png`) e tavola della palette (`palette.png`).
4. Una sezione per edificio: tabella sintetica (quote, piani, copertura, palette) + descrizione per
   fronte + foto annotate di riferimento.
5. Recinzioni, arredo, pavimentazioni, vegetazione: tabelle.
6. Indice delle riprese (ID, data, posizione, heading, cosa inquadra).

Esempio di descrizione per fronte (registro richiesto):

> **E02 – fronte su Via Garibaldi (S), LOD3.** 5 p.f.t. + attico arretrato 2,2 m. Gronda 16,2 m
> (DBT, alta). Basamento a bugnato liscio in intonaco grigio C04, h 3,9 m (stima: 3 corsi da 1,3 m
> rispetto al portone h 2,8 m; media). Piani 1–4: intonaco civile ocra C01, marcapiano a +3,9 m
> (h 20 cm, sporgenza 6 cm, C02). 6 assi a passo 3,35 m allineati; finestre 1,10 × 1,60 m,
> davanzale 0,90 m, cornice piatta 12 cm C02; persiane alla genovese verde C07; balconi solo al 1° e
> al 3° piano sugli assi 2–5, sbalzo 0,90 m, ringhiera a piatti verticali C08. Cornicione modanato
> sporgenza 45 cm. Riprese: SV-04 (frontale), SV-05 (angolo).
