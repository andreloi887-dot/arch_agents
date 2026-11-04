# Interoperabilità: import/export (2025)

## Formati principali
| Direzione | Formati | Note |
|---|---|---|
| Import | DWG/DXF, IFC, 3DS, DAE, DEM, STL, KMZ, **glTF/GLB, USDZ** (2024), immagini; **RVT** con Revit Importer (Studio) | Il 3D da DWG arriva spesso sporco |
| Export 3D | DWG/DXF 3D, IFC (IFC4; **IFC 2x3 solo su Windows** nella 2025), FBX, OBJ, DAE, 3DS, STL, KMZ, **glTF/GLB, USDZ** | |
| Export 2D | DWG/DXF 2D, PDF/EPS, PNG/JPG/TIFF | Per il 2D tecnico vero meglio LayOut |

## DWG (rilievo o pianta di base)
1. In CAD: PURGE/AUDIT, tutto a Z=0, solo i layer utili, unità controllate.
2. Import in mm; *Preserve drawing origin* solo se serve la georeferenziazione.
3. Il DWG diventa un **gruppo** su `00_Riferimenti`, bloccato, da ricalcare con le inferenze.
4. Per chiudere le facce: *Make Faces* (TIG) o *Eneroth Face Creator* (verificare la compatibilità
   con la 2025).

## IFC (molto migliorato nella 2025)
- **Import**: geometria riutilizzata tra componenti uguali (file fino all'85% più leggeri e import
  più veloce), **tag automatici per classe IFC**, oltre 180 classi riconosciute, versione 2x3/IFC4
  conservata. È diventato realistico usare un IFC (es. da Edificius o Revit) come base di lavoro,
  non solo come riferimento.
- **Export**: classificare gruppi/componenti (*Entity Info › Type*: IfcWall, IfcSlab, IfcWindow…).
  Un elemento per oggetto. Su **macOS** la 2025 esporta solo IFC4 (l'export IFC 2x3 su Mac è
  arrivato con la 2026).
- **Edificius (ACCA)**: scambio via IFC. Verificare quale versione IFC chiede il destinatario e,
  se serve 2x3, esportare da Windows. Controllare il risultato in un viewer (usBIM.viewer+,
  BIMcollab Zoom) prima dell'invio.

## Revit
- **Revit Importer** (*File › Import*, `.rvt`): funzione **Studio** (o add-on), non della Pro
  base. Nella 2025 conserva i dati Revit, identifica le classi IFC e permette di scegliere quali
  elementi importare. Ogni release di SketchUp supporta specifiche versioni di Revit: verificare
  in caso di errore.
- Con la sola Pro: farsi mandare un IFC o un DWG 3D dal progettista Revit.

## glTF / USDZ (dal 2024)
- **glTF/GLB**: scambio con il web, Blender, configuratori e motori real-time; porta i materiali
  PBR meglio di OBJ/DAE.
- **USDZ**: AR su iPhone/iPad (Quick Look). Utile per presentare al cliente.

## Verso i render engine
- **Lumion 12.5** (vedi anche la skill Lumion): Lumion 12.5 è del 2022 e **potrebbe non leggere
  correttamente gli `.skp` salvati dalla 2025 né avere un LiveSync compatibile con la 2025**
  *(verificare sul proprio sistema)*. Strade sicure:
  1. export **COLLADA (.dae)** o **FBX** da SketchUp 2025 e import in Lumion;
  2. *File › Save As* scegliendo una versione precedente dello `.skp` (se offerta);
  3. aggiornare Lumion a una versione con LiveSync per SketchUp 2025.
  I **Photoreal Materials non passano a Lumion come PBR**: in Lumion i materiali si rifanno comunque.
  Conta che arrivino separati e con nomi chiari, e che le texture diffuse siano corrette.
- **V-Ray / Enscape / Twinmotion / D5**: usare plugin aggiornati per la 2025. Verificare come
  ognuno legge i nuovi materiali PBR: alcuni li convertono, altri usano solo la diffusa.
- Curve con segmenti sufficienti e *Soften* sulle superfici curve.

## Stampa 3D / maquette
- STL o 3MF/OBJ dai **solidi** (Solid Inspector² per verificare). Spessori minimi reali in scala.

## Immagini e video
- *File › Export › 2D Graphic*: risoluzione fissa (es. 4000 px). Con lo stile Photoreal +
  Environment si ottengono immagini presentabili senza render esterno (vedi `09-visualizzazione.md`).
- *File › Export › Animation*: le scene diventano keyframe; per video di qualità meglio Lumion o
  Enscape.
