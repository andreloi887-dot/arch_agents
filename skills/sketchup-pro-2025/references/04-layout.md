# LayOut 2025: tavole

## Cosa è cambiato dalla 2022
- **Versionless** (2024): i file `.layout` non sono più legati a una release.
- **Move, Rotate, Scale** (2025) con la stessa logica di SketchUp: attivabili da toolbar e
  scorciatoia; Move click-move-click con modalità *Copy* e *Stamp*; Scale a 2 punti. Nelle prime
  build sono stati segnalati bug di Scale (proporzionale): usare l'ultima patch.
- **Join/Split** anche su segmenti di linea, non solo sulle forme.
- **Viewport** con AO, Environments e Photoreal Materials, coerenti con SketchUp.

## Workflow base
1. In SketchUp: una **scena per ogni vista**, Parallel Projection per le viste in scala. Salvare.
2. LayOut: *File › New* da template di studio › *File › Insert* il `.skp`.
3. Pannello *SketchUp Model*: **Scena**, **Ortographic** + **Scale**, *Preserve Scale on Resize*
   ON, **Render mode**.
4. Viewport bloccati dopo l'impaginazione; layer LayOut separati per cartiglio, quote, testi e
   viewport.
5. Quote e annotazioni **in LayOut**, agganciate ai punti del modello.

## Render mode dei viewport
| Modalità | Uso | Nota |
|---|---|---|
| Raster | Viste photoreal/AO, prospettive | Unico modo per mostrare bene PBR e environment; impostare la risoluzione di output |
| Vector | Piante, sezioni, prospetti tecnici | Linee nitide; ignora gli effetti di shading |
| Hybrid | Viste tecniche con texture/ombre | Compromesso |
- Viste photoreal pesanti: impaginare in Raster a bassa qualità e alzare la risoluzione solo per
  l'export. In alternativa esportare un'immagine da SketchUp (o da Lumion) e inserirla come
  immagine.

## Aggiornamento modello
- *Document Setup › References › Update* o tasto destro sul viewport › *Update Model Reference*.
- Non modificare camera/stile del viewport in LayOut senza necessità (override "modified" che si
  perde al prossimo update): correggere la scena in SketchUp.

## Template e scrapbook
- Template di studio con cartiglio Auto-Text (`<PageName>`, `<PageNumber>`, `<Date>`, `<File>`),
  stili di quota per 1:100 e 1:50. Risalvarlo nella 2025.
- Scrapbook di studio: nord, frecce di sezione, campiture.
- *Scaled Drawing* per il disegno 2D in scala direttamente in LayOut.

## Export
- **PDF**: qualità immagine Alta per i raster; controllare la compressione.
- **DWG/DXF**: i viewport Vector diventano linee, quelli Raster diventano immagini.
- PNG/JPG per pagina.

## Problemi tipici
- Viewport lento → modello pesante o viewport photoreal in alta qualità: scene con tag nascosti,
  Raster a bassa qualità durante l'editing, Draft Mode in SketchUp non incide su LayOut.
- Linee troppo spesse/sottili in Vector → *Line Weight* nel pannello SketchUp Model (0,25–0,5 pt).
- Section Fill assente → solido non chiuso o stile della scena non aggiornato.
