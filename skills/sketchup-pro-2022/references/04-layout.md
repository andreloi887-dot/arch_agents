# LayOut 2022: tavole

## Workflow base
1. In SketchUp: una **scena per ogni vista** di tavola (pianta, sezione, prospetto, assonometria),
   con Parallel Projection per le viste in scala. Salvare il `.skp`.
2. LayOut: *File › New* da template (A3/A1 con cartiglio di studio) › *File › Insert* il `.skp`.
3. *SketchUp Model panel*: scegliere la **Scena**, **Ortographic** + **Scale** (1:100, 1:50…),
   *Preserve Scale on Resize* ON, **Render mode**.
4. Ancorare: viewport bloccati dopo l'impaginazione (tasto destro › *Lock*), layer di LayOut
   separati per cartiglio, quote, testi e viewport.
5. Quote e annotazioni **in LayOut** (*Dimension tool*, Label, Auto-Text), agganciandosi alla
   geometria del modello: si aggiornano con il modello se agganciate ai punti.

## Render mode dei viewport
| Modalità | Uso | Nota |
|---|---|---|
| Raster | Viste con texture, ombre, render-like | Pesante; impostare *Output resolution* adeguata |
| Vector | Piante, sezioni, prospetti tecnici | Linee nitide in PDF/DWG; lento su modelli pesanti |
| Hybrid | Viste tecniche con texture/ombre | Vettore per linee + raster per facce; buon compromesso |
- Per i PDF di stampa: Hybrid per le prospettive, Vector per i tecnici. Il rendering a bassa qualità
  in editing (*Preferences › Rendering*) velocizza il lavoro.

## Aggiornamento modello
- Modifiche al `.skp` → in LayOut *Document Setup › References › Update* (o tasto destro sul
  viewport › *Update Model Reference*).
- **Non** modificare camera/stile del viewport in LayOut senza necessità: crea "override" (la
  scena risulta "modified") che si sovrascrivono al prossimo update. Meglio correggere la scena in
  SketchUp.

## Template e scrapbook
- Template di studio: formato, margini, cartiglio con Auto-Text (`<PageName>`, `<PageNumber>`,
  `<Date>`, `<File>`), stili di quota per 1:100 e 1:50.
- Scrapbook di studio: simboli nord, frecce di sezione, campiture, cartigli parziali.
- *Scaled Drawing*: disegno 2D in scala direttamente in LayOut (verificare la disponibilità e il
  comportamento nella 2022: è stato introdotto nelle versioni recenti).

## Export
- **PDF**: *File › Export › PDF* con qualità immagine Alta per i raster; controllare la
  compressione JPEG.
- **DWG/DXF** (Pro): esporta pagine o layer in CAD; i viewport Vector diventano linee, i Raster
  diventano immagini.
- Immagini PNG/JPG per pagina: utili per i social o le presentazioni.

## Problemi tipici
- Viewport vuoto o lento → modello troppo pesante: creare scene con tag nascosti, ridurre il
  contesto, usare Raster durante l'editing.
- Linee troppo spesse/sottili in Vector → *Line Weight* nel pannello SketchUp Model (a 0,25–0,5 pt).
- Section Fill assente in LayOut → solido non chiuso nel modello, oppure stile della scena non
  aggiornato.
