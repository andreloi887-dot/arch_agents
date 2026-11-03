# Setup del modello

## Template
- Partire da un template *Architectural – Millimeters* oppure *Meters*. Per esecutivi e IFC i
  millimetri evitano arrotondamenti nelle quote.
- Creare un **template di studio** (*File › Save As Template*) che contenga: unità, stili di studio
  (presentazione, tecnico B/N, sezione), tag standard, scene base (piante, sezioni, prospetti,
  assonometria), componenti ricorrenti (porte, finestre, arredi base), materiali di studio puliti.
- Il template predefinito si imposta in *Window › Preferences › Template* (macOS: *SketchUp ›
  Settings*).

## Model Info (*Window › Model Info*)
- **Units**: formato Decimal, mm, precisione 0 mm per gli esecutivi (0,0 per i dettagli). Attivare
  *Enable length snapping* solo se serve (1 mm). Angoli: snapping a 15°, precisione 0,0°.
- **Dimensions**: font e dimensione coerenti con le tavole e stile delle frecce. Per lavorare in
  LayOut conviene quotare in LayOut, non in SketchUp.
- **Geo-location**: *Add Location* per ombre reali e contesto (immagine satellitare + terreno). Il
  Nord si imposta qui (Solar North). Serve anche per Lumion e per lo studio delle ombre.
- **Statistics**: controllare il conteggio di entità, componenti e materiali e lanciare *Purge
  Unused* prima della consegna.
- **Rendering**: *Use anti-aliased textures*.
- **File**: descrizione e tipo di allineamento per i file da usare come componenti.

## Preferences
- **Graphics/OpenGL**: hardware acceleration attiva, multisample anti-aliasing a 4x (8x solo con una
  GPU buona). *Use fast feedback* attivo.
- **General**: backup ON e auto-save ogni 5–10 minuti. Il backup è il file `.skb` (macOS `~.skp`)
  nella stessa cartella.
- **Shortcuts**: esportare il proprio set (*Export*) per portarlo su altre macchine.
- **Files**: definire percorsi per modelli, componenti, materiali e stili (utile per la libreria di
  studio condivisa).

## Origine, scala, coordinate
- Modellare **vicino all'origine**. Geometria a chilometri dall'origine (es. DWG in coordinate UTM
  o Gauss-Boaga) causa clipping della camera e imprecisioni. Importare il DWG, spostare tutto
  vicino all'origine e annotare l'offset (o usare un punto di riferimento come componente).
- Allineare gli assi all'edificio con *Axes tool* (tasto destro sugli assi › *Place*) se l'edificio
  non è ortogonale al Nord. Gli assi dei componenti si impostano in modo indipendente.
- SketchUp è impreciso sotto ~1 mm (facce piccole non si chiudono). Per dettagli piccoli usare il
  **trucco della scala**: lavorare in un gruppo scalato x100 (o x1000), modellare e poi
  riscalare. Vedi `07-prestazioni-troubleshooting.md`.

## Convenzione di nomi (consigliata)
- Tag: prefisso numerico per ordinarli (`00_Riferimenti`, `10_Esistente`, `20_Progetto_Muri`,
  `30_Solai`, `40_Serramenti`, `50_Arredi`, `60_Contesto`, `90_Entourage`) e cartelle di tag
  (disponibili dalla 2021) per macro-categorie.
- Componenti: `CAT_Descrizione_Dimensione` (es. `FIN_Battente_120x150`).
- Scene: `P01_Pianta_PT`, `S01_Sezione_AA`, `V01_Vista_Ingresso`. Il prefisso aiuta in LayOut e
  nell'export batch.
