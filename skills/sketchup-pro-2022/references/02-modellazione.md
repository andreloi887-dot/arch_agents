# Modellazione: strumenti, inferenze, VCB

## Scorciatoie di default (Windows; su macOS Ctrl → Cmd, Alt → Option/Cmd secondo i casi)
| Tasto | Strumento | | Tasto | Strumento |
|---|---|---|---|---|
| Spazio | Select | | M | Move (Ctrl = copia, Alt = auto-fold) |
| Shift+Spazio | **Lasso** (2022) | | Q | Rotate (Ctrl = copia) |
| L | Line | | S | Scale (Ctrl = dal centro, Shift = uniforme) |
| R | Rectangle | | F | Offset |
| C | Circle | | T | Tape Measure (Ctrl = senza linea guida) |
| A | Arc (2 punti) | | B | Paint Bucket (Alt = campiona) |
| P | Push/Pull (Ctrl = nuova faccia, doppio clic = ripeti) | | E | Eraser (Shift = nascondi, Ctrl = ammorbidisci) |
| O | Orbit | | H | Pan |
| Z | Zoom | | Shift+Z | Zoom Extents |
| G | Make Component | | K | Back Edges |
| Alt+X | X-ray (da verificare) | | Shift+S | **Search** (2022) |

Le scorciatoie si personalizzano in *Preferences › Shortcuts*. Consiglio: assegnare *Make Group*,
*Hide Rest of Model*, *Section Plane* e *Reverse Faces*. Se un tasto non corrisponde, verificare lì.

## Inferenze
- **Shift** blocca l'inferenza corrente (asse, parallelo, punto).
- **Frecce**: → asse rosso, ← asse verde, ↑ asse blu, ↓ parallelo/perpendicolare all'ultimo spigolo
  di riferimento.
- Passare sopra un punto per "caricarlo" come riferimento, poi tracciare (linee tratteggiate
  colorate).
- Con molta geometria le inferenze rallentano o confondono: isolare con *Hide Rest of Model* o
  modificare dentro il gruppo.

## VCB (barra misure) – input utili
- Rettangolo: `4000;3000` (separatore `;` se il decimale è la virgola, `,` se è il punto). Con una
  terza cifra si ottiene un rettangolo inclinato.
- Dopo Move/copia: `5x` = 5 copie alla stessa distanza; `/5` = 5 copie distribuite nello spazio.
  Vale anche per Rotate (array polari).
- Cerchi/archi/poligoni: `24s` = 24 segmenti (dopo il clic, prima di confermare il raggio).
  Per i render usare 24–48 segmenti; nei componenti ripetuti meno segmenti.
- Push/Pull, Offset, Move: digitare la distanza subito dopo l'azione, senza cliccare nella VCB.
- Coordinate assolute/relative in Move: `[x,y,z]` assolute, `<x,y,z>` relative.

## Novità della 2022 (da usare)
- **Search** (Shift+S): cerca comandi nativi ed estensioni installate e li attiva. È anche il modo
  più rapido per verificare se una funzione esiste nella 2022.
- **Lasso Select** (Shift+Spazio): selezione a mano libera; utile per piante dense senza cambiare
  vista.
- **Tag tool**: applica tag cliccando sugli oggetti; tag scelto nel pannello Tags o campionato con
  il modificatore Sample.
- Filtro di ricerca delle scene accanto alle tab (con almeno 2 scene).
- Revit Importer (Pro) per portare file `.rvt` (vedi `05-interoperabilita.md`).
- Altre migliorie minori (selezione, Outliner, LayOut): verificare nelle release notes ufficiali
  (help.sketchup.com › Release Notes › SketchUp Desktop 2022.0).

## Strumenti avanzati
- **Follow Me**: selezionare prima il percorso, poi lo strumento e cliccare il profilo. Per
  cornicioni, battiscopa, corrimano e solidi di rotazione (profilo + cerchio come percorso). Il
  profilo va posato perpendicolare all'inizio del percorso.
- **Intersect Faces** (tasto destro › *Intersect Faces › With Model / With Selection / With
  Context*): crea gli spigoli di intersezione e poi si cancella il superfluo. È la base delle
  operazioni booleane "manuali".
- **Solid Tools** (Pro): Outer Shell, Union, Subtract, Trim, Intersect, Split. Funzionano solo su
  **solidi** (gruppi/componenti manifold: Entity Info deve mostrare "Solid Group"). Se non è
  solido, cercare spigoli liberi e facce interne (vedi Solid Inspector² in `06-estensioni-ruby.md`).
  Subtract/Trim sono ideali per bucature di muri, scavi e incastri.
- **Sandbox** (*View › Toolbars › Sandbox*): From Contours (terreno da curve di livello DWG), From
  Scratch, Smoove, Stamp (impronta dell'edificio sul terreno), Drape (proietta percorsi), Flip Edge.
  Le curve di livello devono essere alle quote Z giuste.
- **Match Photo**: modellare da una foto (camera da allineare ai punti di fuga). Utile per rilievi
  speditivi e inserimenti fotografici.
- **Section Plane**: sezioni attive con *Section Fill* (disponibile dalla 2018; colore nello stile).
  Una sezione per ogni contesto (gruppo) è attivabile separatamente.
- **Soften/Smooth Edges** (*Window › Soften Edges*): angolo 20–30° per superfici curve importate.

## Buone pratiche di modellazione
- Ogni elemento costruttivo è un gruppo o componente; si modifica entrando nel contesto (doppio
  clic), non esplodendo.
- Muri: o pianta → Push/Pull in un unico gruppo per livello, oppure un gruppo per muro se servono
  quantità e IFC. Bucature con componenti *Cut opening* (finestre/porte che tagliano un solo strato
  di facce) oppure con Solid Tools.
- Facce: il lato bianco (front) verso l'esterno. Con *Monochrome* nello stile si vedono le facce
  invertite (blu-grigio) → *Reverse Faces* / *Orient Faces*. È fondamentale per Lumion e per i
  render engine.
- Niente geometria duplicata sovrapposta (z-fighting). Si controlla con *X-ray* e Outliner.
