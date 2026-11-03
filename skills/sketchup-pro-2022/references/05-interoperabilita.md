# Interoperabilità: import/export

## Formati principali (Pro 2022)
| Direzione | Formati | Note |
|---|---|---|
| Import | DWG/DXF, IFC, 3DS, DAE, DEM, STL, KMZ, immagini; **RVT** con Revit Importer | Il 3D da DWG arriva spesso sporco |
| Export 3D | DWG/DXF 3D, IFC (2x3; IFC4 da verificare nelle opzioni), FBX, OBJ, DAE, 3DS, STL, KMZ, VRML, XSI | |
| Export 2D | DWG/DXF 2D, PDF/EPS, PNG/JPG/TIFF | Per il 2D tecnico vero è meglio LayOut |

## DWG (rilievo o pianta di base)
1. In CAD: pulire (PURGE/AUDIT), portare tutto a Z=0, esplodere i blocchi annidati inutili,
   rimuovere retini/quote/testi non necessari, controllare le unità.
2. Import in SketchUp: *Options* › unità coerenti (mm), *Preserve drawing origin* solo se serve
   la georeferenziazione (altrimenti meglio spostare vicino all'origine).
3. Rendere il DWG un **gruppo** su tag `00_Riferimenti`, bloccarlo (*Lock*) e ricalcarlo con
   inferenze. Non costruirci sopra direttamente: le linee CAD raramente formano facce pulite.
4. Per chiudere le facce di un DWG pulito: estensioni come *Make Faces* (TIG) o *Eneroth Face Creator*.

## IFC
- **Export**: definire la classificazione IFC sui componenti/gruppi (*Entity Info › Type*:
  IfcWall, IfcSlab, IfcWindow, IfcDoor, IfcColumn…). Senza classificazione l'IFC è solo
  geometria. Gli oggetti vanno separati per elemento: un IfcWall per muro, non un gruppo unico.
- **Import**: utile per il coordinamento; la geometria arriva come componenti classificati e
  spesso pesante. Nascondere le categorie non necessarie.
- **Edificius (ACCA)**: lo scambio passa per IFC. In un senso: SketchUp → IFC classificato →
  Edificius (riconosce le entità se classificate). Per un concept spesso conviene importare il
  massing come oggetto e rimodellare in BIM.

## Revit (Pro 2022)
- *File › Import › Revit* (`.rvt`): converte la geometria in componenti, organizza per categorie
  e tag. Ideale per riferimento e visualizzazione, non per un round-trip.
- Le versioni `.rvt` supportate dipendono dall'importer: verificare in caso di errore.

## Verso i render engine
- **Lumion** (vedi anche la skill Lumion): materiali separati per ogni superficie con nomi
  chiari, facce orientate verso l'esterno, niente z-fighting, componenti per l'entourage o niente
  entourage (si mette in Lumion). Plugin **LiveSync for SketchUp** ufficiale oppure export `.skp`
  diretto (Lumion legge lo `.skp`; verificare la versione supportata dalla release di Lumion) o
  `.dae`/`.fbx`.
- **V-Ray / Enscape / Twinmotion**: plugin nativi o Datasmith. Materiali PBR applicati con UV
  corrette (gestire le texture con il clic destro › *Texture › Position*).
- In generale: segmenti dei cerchi sufficienti (24–48) e *Soften* sulle curve per uno shading
  continuo.

## Stampa 3D / maquette
- STL export (*File › Export › 3D Model › STL*) solo su **solidi** (Solid Inspector² per
  verificare). Spessori minimi reali in scala (es. 1:200 → un muro di 30 cm = 1,5 mm).
- Il trucco della scala serve anche qui per i dettagli piccoli.

## Immagini e video
- *File › Export › 2D Graphic*: impostare la risoluzione (es. 4000 px) e disattivare *Use view
  size*. Per le tavole: export a larghezza fissa con *Anti-alias*.
- *File › Export › Animation*: le scene diventano keyframe; impostare la transizione in *Model Info
  › Animation*. Per video di qualità meglio Lumion/Enscape.
