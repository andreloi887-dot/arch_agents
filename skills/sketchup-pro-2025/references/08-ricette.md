# Ricette (workflow pronti)

## Edificio da rilievo DWG
1. Pulire il DWG in CAD (Z=0, purge, solo i layer utili) e importarlo in mm.
2. Gruppo `RIF_Pianta_PT` su `00_Riferimenti`, bloccato; uno per livello alle quote Z corrette
   (Move con `[0,0,3200]`).
3. Ricalcare i muri in un gruppo per livello e Push/Pull all'altezza netta.
4. Solai come gruppi separati, scale come componenti.
5. Serramenti come componenti *Cut opening* su `40_Serramenti`.
6. Scene: piante (sezione a 1,30 m), sezioni, prospetti, viste 3D → LayOut.

## Edificio da IFC (novità 2025)
1. Import IFC: la geometria arriva già divisa in componenti con tag per classe.
2. Riorganizzare i tag IFC in una cartella, nascondere le classi inutili (IfcSpace, IfcOpeningElement
   se presenti).
3. Lavorare sopra (arredi, contesto, viste) senza esplodere i componenti, così si mantiene la
   classificazione per un eventuale riesportazione.

## Concept / massing rapido
- Volumi come gruppi, materiali piatti per funzione, stile con profili e AO leggero.
- Geo-location + ombre per lo studio solare (scene a ore diverse).
- Export delle immagini con lo script "Esporta ogni scena come PNG".

## Vista photoreal rapida in SketchUp (senza render esterno)
Vedi `09-visualizzazione.md`. In breve: materiali PBR (libreria o *Generate Textures*) →
environment HDRI coerente con l'ora → stile Photoreal con AO e spigoli spenti → ombre ON con la
direzione del sole allineata all'HDRI → export 2D a 4000 px.

## Interni
- Muri esistenti come gruppi, arredi come componenti (3D Warehouse: controllare il peso).
- Camera a 1,50–1,60 m, FOV 60–70° oppure *Camera › Two-Point Perspective*.
- Per la presentazione rapida: environment da interno o HDRI esterno luminoso, PBR su pavimenti e
  legni; per la qualità finale meglio un motore di render.

## Modello pronto per Lumion 12.5
1. Purge + CleanUp³.
2. Facce orientate (stile Monochrome).
3. Un materiale per ogni superficie da trattare, con nomi chiari (script "Report dei materiali").
4. Niente entourage pesante; terreno semplice o fatto in Lumion.
5. Export **DAE o FBX** (o `.skp` salvato in una versione precedente) perché Lumion 12.5 potrebbe
   non leggere lo `.skp` 2025: vedi `05-interoperabilita.md`. Per gli aggiornamenti usare *Import &
   Update* in Lumion mantenendo gli stessi nomi di file e materiali.

## Modello per IFC / Edificius / BIM
- Un oggetto = un gruppo/componente classificato (IfcWall, IfcSlab, IfcWindow…).
- Nessuna geometria grezza al livello radice; tag per piano o categoria.
- Export IFC4 (oppure IFC 2x3 da Windows) e verifica in un viewer prima dell'invio.

## Stampa 3D di un plastico
- Modello separato e semplificato, scalato, spessori minimi rispettati; Outer Shell, Solid
  Inspector² e poi export STL in mm.

## Presentazione AR per il cliente
- Modello alleggerito (Skimp, entourage spento), materiali PBR, export **USDZ** → apertura su
  iPhone/iPad in Quick Look.

## Tavola LayOut tipo (A1, 1:100)
- Template A1 con cartiglio Auto-Text; pianta e sezioni in Vector o Hybrid 1:100; assonometria o
  vista photoreal in Raster; render inserito come immagine.
- Quote in LayOut con stile 1:100, testi a 2,5–3,5 mm, line weight 0,35 pt.
