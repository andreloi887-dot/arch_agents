# Preparazione del modello e import

## Regole di modellazione (a monte)
- **Unità e origine**: modella in metri, vicino all'origine (coordinate geografiche enormi → jitter e ombre instabili). In Revit/Archicad esporta con origine di progetto, non survey point georiferito.
- **Materiali = unità di lavoro**: Lumion assegna materiali per *materiale/colore sorgente*, non per oggetto. Separa nel CAD tutto ciò che deve avere materiali diversi (vetro, telaio, intonaco, pavimento esterno…). Superfici con lo stesso materiale sorgente non sono separabili in Lumion.
- **Normali**: facce invertite = superfici nere/trasparenti. Nel CAD usa materiali bifacciali o correggi (SketchUp: *Reverse Faces*; Rhino: `Dir`/`Flip`). In Lumion: material *Standard › Settings › Two-sided rendering* come toppa.
- **Z-fighting**: superfici complanari sovrapposte sfarfallano. Elimina o separa di ≥ 1–2 mm (più a grandi distanze).
- **Spessori reali**: vetri con spessore (o piano singolo con materiale Glass), muri chiusi, solai con spessore: la luce "filtra" da fessure e spigoli aperti.
- **Poligoni**: decima arredi/vegetazione importati. Usa la libreria Lumion per alberi e persone invece di importare mesh pesanti.
- **UV mapping**: Lumion può usare UV del modello o proiezione propria (*Scale/Box mapping* nel materiale). Per legno/pietra direzionali conviene UV corrette a monte.

## Formati supportati (import)
`.dae` (Collada), `.fbx`, `.skp`, `.dwg/.dxf`, `.3ds`, `.obj`, `.max` (con 3ds Max installato), `.ifc` non nativo in 12.x → passare da Revit/Archicad/Edificius o convertire. Formato consigliato senza LiveSync: **COLLADA (.dae)** o **FBX**.

## LiveSync
Plugin ufficiali (Lumion 12.x): SketchUp, Revit, Archicad, Rhino, AutoCAD, Allplan, BricsCAD, Vectorworks, Autodesk FormIt (aggiunto con Lumion 12). Revit LT non supportato. **SketchUp 2025**: Lumion 12.5 è del 2022 e potrebbe non leggere gli `.skp` 2025 né avere un LiveSync compatibile; in caso di problemi esportare DAE/FBX da SketchUp (vedi `skills/sketchup-pro-2025/references/05-interoperabilita.md`).
- La versione del plugin deve essere compatibile sia con il CAD sia con Lumion 12.5: scaricarla da support.lumion.com.
- Flusso: avvia Lumion, apri/crea progetto → nel CAD *Start LiveSync* → in Lumion appare il modello aggiornato in tempo reale. Fine sessione: in Lumion il modello va **salvato** (resta come oggetto importato `.lsm` sincronizzabile).
- Sincronizzazione camera: utile per impostare inquadrature dal CAD.
- Limite: modifiche di materiali fatte in Lumion restano associate al nome materiale sorgente → **non rinominare i materiali nel CAD** dopo averli impostati in Lumion.

## Import & Update (senza LiveSync)
1. *Import › Import new model* → posiziona.
2. Dopo modifiche nel CAD: riesporta con **stesso nome file/percorso** → seleziona il modello in Lumion → *Import › Update model* (o icona di aggiornamento nel menu oggetto). Materiali mantenuti se i nomi sorgente restano invariati.
3. *Save* / *Load* materiali (`.mts`) per riapplicare un set su modelli nuovi.

## Edificius (ACCA) → Lumion
Edificius non ha LiveSync. Opzioni: esportare **FBX/OBJ/DAE** (o via IFC → Revit/SketchUp → Lumion). Verificare scala, assi (Z-up) e che i materiali arrivino separati per tipologia. Considera che Edificius ha già un motore real-time (RTBIM): Lumion conviene per contesto, vegetazione, animazioni e qualità foto.

## Checklist pre-import
- [ ] Unità metri, origine vicina
- [ ] Layer/oggetti non necessari spenti (quotature, 2D, viste)
- [ ] Materiali sorgente rinominati in modo leggibile (`EST_Intonaco_Bianco`, `VET_Vetro_Facciata`)
- [ ] Normali corrette, niente superfici duplicate
- [ ] Terreno: meglio modellato come mesh separata se topografia reale
