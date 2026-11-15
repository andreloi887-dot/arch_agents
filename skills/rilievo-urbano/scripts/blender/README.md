# Script Blender (fase 3 della filiera)

Tutti senza interfaccia: `blender -b [file.blend] -P <script> -- <cartella modello> [opzioni]`.
**Di solito non si lanciano uno per uno**: `python ../filiera.py <modello>` li esegue in ordine con i controlli e il
confronto in Unreal (skill `filiera-progetto`). Cycles va da solo sulla GPU (OptiX) se c'è: `comune.cycles`.
Mai `read_factory_settings()` / `read_homefile()` negli script (cancella le librerie di Bonsai: vedi
`../../references/08-lezioni-apprese.md`).

| Script | Cosa fa | Uscita |
|---|---|---|
| `importa_contesto.py` | contesto da `contesto.json`: superfici, muri, edifici, dettagli, arredo, verde, materiali della libreria (`libreria/`), sole NOAA (`--data --ora --fuso`), camere delle riprese, viste fisse da `lotto.json → viste_aeree` | `uscita_blender/contesto.blend`, con `--render` `viste/` |
| `allinea_ifc.py <ifc> [--scrivi]` | rotazione, traslazione e quota di un IFC non georiferito sul lotto | valori per `lotto.json → progetto_ifc` |
| `importa_progetto.py` (da aprire su `contesto.blend`) | IFC nella scena: ville alla quota dei cancelli, terreno nel perimetro, muraglioni, marciapiede di progetto, contesto tolto o nascosto sotto il progetto | `contesto_progetto.blend`, `perimetro_progetto.json`, con `--render` `viste_progetto/` |
| `finiture_interni.py` (su `contesto_progetto.blend`, che riscrive) | ciò che l'IFC non porta: pavimento continuo, battiscopa, perlinato e orditura a vista, porte interne rifatte con il verso di apertura, controsoffitto del disimpegno con faretti, griglie e bocchette; valori in `lotto.json → progetto_ifc → finiture` | `contesto_progetto.blend` |
| `arredi_interni.py` (su `contesto_progetto.blend`, che riscrive) | mobili parametrici dagli ingombri di `arredi.json` (planimetria di Andrea): armadi, letti, comodini, scrivanie, parete TV, cucina; divano e tavolo disposti con le regole | `contesto_progetto.blend` |
| `percorsi_camera.py` (su `contesto_progetto.blend` o `contesto.blend`) | camere animate dalle regole: giro del drone attorno al lotto, camminata lungo le strade che lo toccano, visita degli interni stanza per stanza (`--solo interni --villa N`); controlli di ostacoli e quota; valori in `lotto.json → percorsi` | `scena_percorsi.blend`, `percorsi.json`, con `--render` `anteprime/<percorso>.mp4` |
| `esporta_usd.py` (su `scena_percorsi.blend`) | export verso Unreal: scena e camere in due file (fps delle camere allineato), riferimento per il controllo in Unreal con l'impronta della geometria | `usd/scena.usdc`, `usd/camere.usdc`, `usd/riferimento.json`, `usd/impronta_mesh.json` |
| `comune.py` | `avvio` (argomenti, cartelle, `--blend`, log), `lin` (colore), quota su un triangolo, `resa` (EEVEE, AgX), `cycles` (GPU OptiX o CPU), render delle camere | modulo |

Ordine dopo una modifica al contesto o al progetto:
1. `contesto/contesto.py <modello>` e `verifica_contesto.py <modello>`;
2. `importa_contesto.py`;
3. `importa_progetto.py` (riscrive `perimetro_progetto.json`: se il perimetro cambia, ripetere da 1).
4. `finiture_interni.py`, poi `arredi_interni.py`;
5. `percorsi_camera.py --render` (anteprime da far approvare ad Andrea), poi `esporta_usd.py`.

Anteprime: `--motore EEVEE` (predefinito, sole e materiali) oppure `--motore WORKBENCH` (animatic per giudicare solo
il movimento); `--scala 50` (percentuale della risoluzione), `--passo 2` (un fotogramma ogni due), `--solo drone,strada`.
Il render riprende dai fotogrammi già scritti.

Senza Blender installato (sessione cloud): `pip install bpy==5.2.4 ifcopenshell shapely` e, per EEVEE senza scheda
grafica, `apt-get install libegl1 libgl1-mesa-dri`; poi `python <script> -- <modello> --blend <file.blend>`.
Su CPU: ~30 s per immagine EEVEE 1280×720, ~3 s per fotogramma WORKBENCH 960×540.

Opzioni comuni: `--render`, `--viste SV-08,VISTA_angolo` (solo alcune camere), `--samples 16`.


Script di servizio in `controlli/`: `apri.py` (solo cloud: apre un .blend e lancia uno script con Blender come modulo), `viste.py` (viste Cycles di controllo, `blender -b -P viste.py -- <blend> <cartella> <campioni> nome:...`), `pianta_arredi.py`, `pianta_orditura.py`, `arredi_da_pdf.py` (ingombri da una planimetria PDF vettoriale). Uso in [PROGRAMMA_INTERNI.md](../../../../PROGRAMMA_INTERNI.md).
