# Modellazione: strumenti, inferenze, VCB

## Scorciatoie di default (Windows; su macOS Ctrl → Cmd, Alt → Option/Cmd secondo i casi)
| Tasto | Strumento | | Tasto | Strumento |
|---|---|---|---|---|
| Spazio | Select | | M | Move (Ctrl = copia, Alt = auto-fold) |
| Shift+Spazio | Lasso | | Q | Rotate (Ctrl = copia) |
| L | Line | | S | Scale (Ctrl = dal centro, Shift = uniforme) |
| R | Rectangle | | F | Offset |
| C | Circle | | T | Tape Measure (Ctrl = senza linea guida) |
| A | Arc (2 punti) | | B | Paint Bucket (Alt = campiona) |
| P | Push/Pull (Ctrl = nuova faccia, doppio clic = ripeti) | | E | Eraser (Shift = nascondi, Ctrl = ammorbidisci) |
| O | Orbit | | H | Pan |
| Z | Zoom | | Shift+Z | Zoom Extents |
| G | Make Component | | K | Back Edges |
| Shift+S | Search | | — | Flip (2023): assegnare un tasto *(default da verificare)* |

Le scorciatoie si personalizzano in *Preferences › Shortcuts*. Consiglio: assegnare *Flip*, *Make
Group*, *Hide Rest of Model*, *Section Plane*, *Reverse Faces* e il toggle *Ambient Occlusion*.
Se un tasto non corrisponde, verificare lì o con Search.

## Inferenze
- **Shift** blocca l'inferenza corrente (asse, parallelo, punto).
- **Frecce**: → asse rosso, ← asse verde, ↑ asse blu, ↓ parallelo/perpendicolare.
- Passare sopra un punto per "caricarlo" come riferimento, poi tracciare.
- Con molta geometria: *Hide Rest of Model* o modificare dentro il gruppo.

## VCB (barra misure)
- Rettangolo: `4000;3000` (`;` se il separatore decimale è la virgola).
- Dopo Move/copia: `5x` = 5 copie alla stessa distanza; `/5` = 5 copie distribuite. Vale anche per
  Rotate (array polari).
- Cerchi/archi/poligoni: `24s` = 24 segmenti. Con Photoreal e AO le curve a pochi segmenti si
  notano di più: 24–48 per gli oggetti in vista.
- Move: `[x,y,z]` coordinate assolute, `<x,y,z>` relative.

## Strumenti chiave e cosa è cambiato
- **Search** (Shift+S): cerca comandi nativi ed estensioni; il modo più veloce per trovare le voci
  spostate dopo la migrazione.
- **Lasso** e **Tag tool** (dalla 2022): invariati.
- **Flip** (2023): specchia lungo piani rosso/verde/blu allineati agli assi del contenitore.
  Sostituisce *Flip Along* del menu contestuale: chi arriva dalla 2022 lo cerca lì e non lo trova.
- **Follow Me**: prima il percorso, poi lo strumento, poi il profilo. Il profilo va perpendicolare
  all'inizio del percorso.
- **Intersect Faces** (tasto destro › *Intersect Faces › With Model / Selection / Context*).
- **Solid Tools**: Outer Shell, Union, Subtract, Trim, Intersect, Split. Funzionano solo su
  **solidi** (Entity Info: "Solid Group/Component").
- **Sandbox**: From Contours, From Scratch, Smoove, Stamp, Drape, Flip Edge. Per terreni da nuvola
  di punti: *Scan Essentials › Ground Mesh* (Studio).
- **Match Photo**: modellare da foto per rilievi speditivi.
- **Section Plane** con *Section Fill* (richiede solidi).
- **Soften/Smooth Edges** (*Window › Soften Edges*): 20–30° per superfici curve. Con il nuovo motore
  e AO gli spigoli duri si notano di più.

## Buone pratiche
- Ogni elemento costruttivo è un gruppo o componente; si modifica entrando nel contesto, non
  esplodendo.
- Muri: un gruppo per livello oppure un gruppo per muro se servono quantità e IFC. Bucature con
  componenti *Cut opening* o Solid Tools.
- Facce: il lato front verso l'esterno (stile Monochrome per controllarle). Con i Photoreal
  Materials le facce invertite sono ancora più evidenti; sono critiche per Lumion e i render engine.
- Niente geometria duplicata sovrapposta (z-fighting).
