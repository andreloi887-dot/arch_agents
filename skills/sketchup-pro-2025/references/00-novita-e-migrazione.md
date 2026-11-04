# Novità 2023–2025 e migrazione dalla 2022

Fonti: release notes ufficiali (help.sketchup.com › Release Notes) e articoli di settore. Le voci
segnate *(da verificare)* non sono confermate dalle note ufficiali.

## Cosa trovi di nuovo rispetto alla 2022

### 2023
- **Flip tool**: sostituisce i comandi *Flip Along* del menu contestuale. Specchia la selezione
  lungo piani allineati agli assi del gruppo/componente (come Scale). Usa Ctrl/Option per
  specchiare una copia *(da verificare)*.
- **Overlays**: le estensioni possono restare visibili mentre usi altri strumenti; si
  accendono e si spengono dal pannello *Overlays*.
- **Revit Importer** nativo (funzione *Studio*, con trial dalla Pro).

### 2024
- **Nuovo motore grafico**: navigazione circa 2,4 volte più veloce nei casi tipici. Il motore
  classico resta selezionabile in *Preferences › Graphics* (serve un riavvio). SketchUp torna al
  classico da solo su hardware non supportato.
- **Ambient Occlusion**: impostazione di stile (*View › Ambient Occlusion* / pannello Styles) che
  scurisce gli incontri tra le facce; visibile anche nei viewport di LayOut.
- **Draft Mode**: nuova scheda *Preferences › Performance*. Riduce la qualità durante la
  navigazione dei modelli pesanti.
- **Add Location** rinnovato, con freccia del Nord vero visibile e opzioni di import migliori.
- **Finestra di errore delle estensioni**: indica quale estensione fallisce e propone di
  aggiornarla o disinstallarla.
- **glTF e USDZ** in import/export (non USD).
- **Scan Essentials – Ground Mesh** (Studio): terreno da nuvola di punti.
- **Ruby 3.2** (prima era 2.7): le estensioni compilate (C) vanno ricompilate, le Ruby pure di
  solito funzionano.
- **LayOut versionless**: i file `.layout` non sono più legati a una release.

### 2025
- **Photoreal Materials (PBR)**: nuovo stile di faccia; i materiali reagiscono a luce e riflessi.
  Tutte le librerie di default sono ora PBR. Richiedono il **nuovo motore grafico**.
- **Environments**: pannello per immagini 360° (HDRI) che fanno da fonte di luce e di riflessi, con
  la possibilità di mostrarle come sfondo (sky dome). Si caricano da file o da 3D Warehouse.
- **Generate Textures**: dall'editor dei materiali genera mappe PBR piastrellabili da un'immagine
  o da un materiale classico. Richiede la connessione a internet (AI lato server).
- **IFC**: import con geometria riutilizzata tra componenti (file fino all'85% più leggeri),
  tag automatici per classe IFC, oltre 180 classi supportate, conservazione della versione IFC 2x3 /
  IFC4. Nella 2025 l'**export IFC 2x3 è solo su Windows**.
- **Revit Importer** migliorato: conserva i dati Revit e identifica le classi IFC; controlli di
  selezione degli elementi da importare (Studio).
- **LayOut 2025**: Move, Rotate e Scale si comportano come in SketchUp (Move con modalità Copy e
  Stamp, click-move-click; Scale a 2 punti). Join/Split funzionano anche sulle linee. I viewport
  mostrano Environments, Photoreal Materials e AO.
- **Style Builder dismesso**: non è più incluso. Gli stili "schizzati" già creati restano
  utilizzabili; per crearne di nuovi serve la vecchia installazione (2023/2024).
- **3D Warehouse**: collezioni curate di materiali photoreal ed environments.

## Checklist di migrazione (2022 → 2025)
1. **Licenza**: verifica se hai Pro o Studio (Revit Importer, Scan Essentials, V-Ray sono Studio).
2. **Hardware/driver**: aggiorna i driver GPU e verifica in *Preferences › Graphics* che sia attivo
   il nuovo motore. Con la grafica integrata Intel datata può tornare al classico, e senza nuovo
   motore niente PBR, Environments né AO.
3. **Preferenze e scorciatoie**: esporta da 2022 (*Preferences › Shortcuts › Export*) e importa
   nella 2025. Controlla i conflitti con i nuovi strumenti (Flip, Search, Lasso).
4. **Estensioni**: reinstallale dalla 2025, una alla volta, verificando la compatibilità con
   2024/2025 (Ruby 3.2). Le librerie TT_Lib² e LibFredo6 vanno aggiornate per prime. Non copiare
   la cartella Plugins della 2022 in blocco.
5. **Template**: apri il template di studio nella 2025, decidi se i materiali di studio restano
   classici o diventano PBR (*Generate Textures*) e salva un nuovo template 2025.
6. **Materiali**: in *Preferences › Graphics* c'è un'opzione per convertire automaticamente i
   materiali in PBR *(posizione esatta da verificare)*. Disattivala se vuoi mantenere i materiali
   classici (per esempio per l'export verso Lumion 12.5).
7. **Stili**: AO e Photoreal sono impostazioni di stile, quindi aggiorna gli stili di studio
   (Tecnico senza AO, Presentazione con AO/Photoreal).
8. **LayOut**: riapri i template `.layout` e salvali nella 2025. Prova le nuove Move/Rotate/Scale
   prima di una consegna (nei forum si segnalano bug di Scale nelle prime build della 2025: tieni
   SketchUp aggiornato all'ultima patch 2025.0.x).

## Compatibilità dei file
- I file `.skp` dalla 2021 in poi sono *versionless*: un file 2025 si apre di norma anche in
  2021/2022, ma ciò che quelle versioni non conoscono (PBR, environments) si perde o viene
  ignorato *(verifica sul tuo caso prima di condividere con chi è rimasto sulla 2022)*.
- Per software di terze parti che leggono lo `.skp` (Lumion 12.5, vecchi importer CAD) vedi
  `05-interoperabilita.md`.
