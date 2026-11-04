# Setup del modello (2025)

## Template
- Partire da un template *Architectural – Millimeters* oppure *Meters*. Per esecutivi e IFC i
  millimetri evitano arrotondamenti nelle quote.
- **Template di studio 2025** (*File › Save As Template*) con: unità, stili di studio (tecnico,
  presentazione con AO, photoreal, sezione), tag e cartelle di tag standard, scene base, componenti
  ricorrenti, materiali di studio (decidere classici o PBR, vedi `09-visualizzazione.md`), un
  environment di default se si usa la vista photoreal.
- Il template predefinito si imposta in *Preferences › Template* (macOS: *SketchUp › Settings*).

## Model Info (*Window › Model Info*)
- **Units**: formato Decimal, mm, precisione 0 mm per gli esecutivi (0,0 per i dettagli). Angoli:
  snapping a 15°, precisione 0,0°.
- **Dimensions**: font e frecce coerenti. Per le tavole quotare in LayOut.
- **Geo-location**: *Add Location*, nel workflow rinnovato dalla 2024 con freccia del Nord vero
  visibile e opzioni di import migliori. Serve per ombre reali, contesto e Lumion.
- **Statistics**: controllo delle entità e *Purge Unused* prima della consegna.
- **Classifications**: schema IFC caricato se il modello va in BIM.

## Preferences
- **Graphics**:
  - **motore grafico**: lasciare il nuovo motore (default dalla 2024). Il classico solo per
    diagnosi, perché senza nuovo motore non ci sono Photoreal Materials, Environments né AO. Il
    cambio di motore richiede un riavvio.
  - multisample anti-aliasing a 4x (8x con una GPU buona);
  - opzione di conversione automatica dei materiali in PBR: decidere secondo il flusso di lavoro
    (vedi `00-novita-e-migrazione.md`).
- **Performance** (dalla 2024): **Draft Mode** per navigare i modelli pesanti con qualità ridotta.
- **General**: backup ON e auto-save ogni 5–10 minuti (`.skb` su Windows, `~.skp` su macOS).
- **Shortcuts**: esportare e importare il proprio set tra macchine e versioni.
- **Files**: percorsi della libreria di studio (modelli, componenti, materiali, stili).

## Origine, scala, coordinate
- Modellare **vicino all'origine**. Un DWG in coordinate UTM o Gauss-Boaga causa clipping e
  imprecisioni: importare, spostare vicino all'origine e annotare l'offset.
- Allineare gli assi all'edificio con *Axes tool* se l'edificio non è ortogonale al Nord.
- SketchUp è impreciso sotto ~1 mm: per i dettagli piccoli usare il **trucco della scala** (gruppo
  x100 o x1000, modellare, poi riscalare).

## Convenzione di nomi (consigliata)
- Tag con prefisso numerico (`00_Riferimenti`, `10_Esistente`, `20_Progetto_Muri`, `30_Solai`,
  `40_Serramenti`, `50_Arredi`, `60_Contesto`, `90_Entourage`) e cartelle di tag. Con l'import IFC
  2025 vengono creati tag per classe IFC: tenerli in una cartella `IFC_` separata.
- Componenti: `CAT_Descrizione_Dimensione` (es. `FIN_Battente_120x150`).
- Materiali: `CAT_Descrizione` (es. `PAV_Rovere_Spina`, `INT_Bianco`). Fondamentale per Lumion e
  per gli aggiornamenti con *Import & Update*.
- Scene: `P01_Pianta_PT`, `S01_Sezione_AA`, `V01_Vista_Ingresso`.
