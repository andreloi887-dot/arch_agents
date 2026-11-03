# Interoperabilità (fonte: acca.it/integrazione-bim, novembre 2026)

## IFC
- Import/export **IFC 2x3, 4.0, 4.3**. Certificazioni buildingSMART: IFC 2x3 Coordination View 2.0
  (import ed export) e import IFC 4.0.
- Creazione di un progetto da IFC di altri software (Revit, Archicad…) con **riconoscimento automatico
  degli oggetti**: utile, ma controlla sempre muri, solai e aperture riconosciuti.
- Prima dell'export: classi IFC corrette (IfcWall, IfcSlab, IfcRoof, IfcWindow…), piani =
  IfcBuildingStorey, Pset compilati. Oggetti generici/proxy = dati persi.
- Verifica l'IFC in un viewer indipendente (usBIM.viewer+, BIMcollab Zoom, Solibri) prima dell'invio.

## Formati
- **Import**: DXF/DWG, SKP, DAE (Collada), RVT/RFT, 3DS/ASE, OBJ, PLY, IFC, STL, DGN, LWO/LWS, LXO,
  MS3D e altri formati mesh; immagini (JPG, PNG, TGA, DDS, HDR, PSD…).
- **Export**: DXF/DWG, SVG, OBJ, SKP, DAE, STL, PLY, IFC. Elaborati in DXF/DWG/DWF, relazioni in RTF.
  **Niente FBX in export**: per motori esterni usa DAE, OBJ o SKP.
- Nuvole di punti (via usBIM.pointcloud): LAS, LAZ, E57, PLY, PTS, XYZ, XYZCIRN, ASC, LGS/LGSx (Leica),
  RCP/RCS (ReCap).

## Modellatori esterni
- **Edificius-CAD** integrato: CAD DWG nativo 2D/3D (linee, polilinee, blocchi, retini, spline,
  mesh, solidi, nuvola di punti, fumetto di revisione). Usalo per pulire i DWG prima di modellare.
- **Da 2D a 3D**: da DWG/DXF importati, riconoscimento e disegno automatico di muri, pilastri, scale,
  solette. Pulisci prima layer e blocchi, o il riconoscimento sbaglia.
- **SketchUp**: integrazione dinamica per creare/modificare blocchi 3D dalla vista 3D o dalla
  Libreria di Progetto; salvi e chiudi SketchUp e l'oggetto si aggiorna in Edificius.
- **Blender** per oggetti complessi; **Rhino/Grasshopper** per import/modifica di forme parametriche
  e nuvole di punti senza chiudere Edificius.
- **Revit**: famiglie .RFA convertite in blocchi 3D tramite usBIM (carichi in cloud → nascondi ciò
  che non serve → converti e importi nella libreria).
- **Google Maps**: terreno con curve di livello dai dati altimetrici dell'area selezionata.

## Ecosistema ACCA
- **PriMus**: computo dinamico. Selezioni l'elemento (2D o 3D), associ la voce di listino con
  drag&drop, selezioni tutti gli elementi dello stesso tipo; il computo si aggiorna col modello e si
  rielabora in PriMus. Il computo automatico esiste anche dentro Edificius senza altri software.
- **TerMus**: via formato **"IFCzip ottimizzato per ACCA"** (stratigrafie, materiali, infissi, vani).
  In TerMus sostituisci le stratigrafie generiche con quelle d'archivio, definisci telai/vetri, zone e
  confini termici, generatore e impianto → Legge 10, APE.
- **EdiLus**: modello architettonico nell'ambiente di integrazione, riconoscimento automatico di
  pilastri/travi/scale, calcolo → carpenterie, armature, relazioni; la struttura torna in Edificius.
- **CerTus** (PSC, fasi di lavoro sugli oggetti), **ManTus** (piano di manutenzione, drag&drop
  dall'Archivio degli Elementi Manutenibili), **SuoNus** (requisiti acustici), **Impiantus-ELETTRICO**.
- **usBIM**: CDE cloud, condivisione via link e browser, lavoro collaborativo simultaneo, render AI.

## Verso Lumion o altri motori
Export **DAE o OBJ** (o SKP) con materiali separati per tipo (vetro, intonaco, legno), normali
corrette, geometria pulita, nessuna superficie coplanare. Vedi la skill `lumion-pro-12-5` (01-preparazione-import).
