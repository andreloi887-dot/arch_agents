# Interoperabilità

## IFC
- Edificius è certificato buildingSMART per l'export IFC (verifica la versione e la Model View
  Definition supportate nella tua release: IFC2x3 CV 2.0 / IFC4 RV).
- Prima dell'export: oggetti con classe IFC corretta (IfcWall, IfcSlab, IfcRoof, IfcWindow…),
  piani = IfcBuildingStorey, proprietà compilate (Pset). Oggetti generici "proxy" = dati persi.
- Verifica il file esportato in un viewer indipendente (usBIM.viewer+, BIMcollab Zoom, Solibri) prima
  di inviarlo.
- Import IFC da altri software (Revit, Archicad): utile come riferimento/federazione; la conversione in
  oggetti nativi editabili non è mai perfetta.

## CAD e mesh
- DWG/DXF: import come base (pulito, origine vicina a 0,0), export per consulenti.
- SKP/OBJ/3DS/FBX: per oggetti e per esportare verso motori di render esterni. Verifica i formati
  effettivamente disponibili nella tua versione.

## Ecosistema ACCA
- **PriMus**: computo metrico dal modello (voci collegate agli oggetti/stili).
- **TerMus**: energetica (Legge 10, APE); servono stratigrafie, infissi con dati termici, locali
  chiusi e ben definiti, ubicazione.
- **EdiLus**: strutture; modello strutturale coerente (pilastri, travi, solai, fili fissi). Il
  passaggio può essere bidirezionale tra prodotti ACCA: verifica le opzioni.
- **usBIM**: piattaforma cloud (archiviazione, viewer, collaborazione, issue/BCF, render AI).

## Verso Lumion o altri motori
Export in FBX/OBJ/COLLADA con materiali separati per tipo (vetro, intonaco, legno), normali
corrette e geometria pulita. Vedi anche la skill `lumion-pro-12-5` (file 01-preparazione-import).
