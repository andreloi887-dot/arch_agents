# Ricette (workflow pronti)

## Edificio da rilievo DWG
1. Pulire il DWG in CAD (Z=0, purge, solo i layer utili) e importarlo in mm.
2. Gruppo `RIF_Pianta_PT` su tag `00_Riferimenti`, bloccato, eventualmente uno per livello alle
   quote Z corrette (Move con `[0,0,3200]`).
3. Ricalcare i muri con Line/Rectangle in un gruppo per livello e Push/Pull all'altezza netta.
4. Solai come gruppi separati (Push/Pull dello spessore), scale come componenti.
5. Serramenti come componenti *Cut opening* su tag `40_Serramenti`.
6. Scene: piante (sezione a 1,30 m), sezioni, prospetti, viste 3D → LayOut.

## Concept / massing rapido
- Volumi come gruppi, colori per funzione (materiali piatti), stile con profili e linee schizzate.
- Geo-location + ombre per lo studio solare (scene a ore diverse e solstizi).
- Export immagini con lo script "Esporta ogni scena come PNG".

## Interni
- Muri dall'interno: i muri esistenti come gruppi, arredi come componenti (3D Warehouse con
  controllo delle facce).
- Una camera per scena a 1,50–1,60 m di altezza, FOV 60–70° (oppure 2 punti di fuga con *Camera ›
  Two-Point Perspective*).
- Per i render: luci e materiali nel motore, non in SketchUp.

## Modello pronto per Lumion
1. Purge + CleanUp³ (rimuove facce duplicate e spigoli coplanari).
2. Facce orientate (stile Monochrome: niente lato blu verso la camera).
3. Un materiale per ogni superficie da trattare in Lumion, con nomi chiari (`Vetro_Facciata`,
   `Intonaco_Bianco`).
4. Niente entourage pesante in SketchUp; il terreno semplice o creato in Lumion.
5. LiveSync o salvataggio `.skp` e import; per gli aggiornamenti usare *Import & Update*
   mantenendo i nomi dei materiali.

## Modello per IFC / Edificius / BIM
- Un oggetto = un gruppo/componente classificato (IfcWall, IfcSlab, IfcWindow…).
- Nessuna geometria grezza al livello radice; tag per piano o categoria.
- Export IFC e verifica in un viewer (es. usBIM.viewer+, BIMcollab Zoom) prima dell'invio.

## Stampa 3D di un plastico
- Modello separato e semplificato, scalato alla scala del plastico, spessori minimi rispettati.
- Outer Shell per unire, Solid Inspector² per verificare e poi export STL in mm.

## Tavola LayOut tipo (A1, 1:100)
- Template A1 con cartiglio Auto-Text; viewport pianta (Vector o Hybrid, 1:100), sezioni (1:100),
  assonometria (Raster o Hybrid, senza scala), render inserito come immagine.
- Quote in LayOut con stile 1:100, testi a 2,5–3,5 mm, line weight 0,35 pt.
