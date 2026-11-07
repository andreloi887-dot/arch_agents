# Script Blender (fase 3 della filiera)

Tutti senza interfaccia: `blender -b [file.blend] -P <script> -- <cartella modello> [opzioni]`.
Mai `read_factory_settings()` / `read_homefile()` negli script (cancella le librerie di Bonsai: vedi
`../../references/08-lezioni-apprese.md`).

| Script | Cosa fa | Uscita |
|---|---|---|
| `importa_contesto.py` | contesto da `contesto.json`: superfici, muri, edifici, dettagli, arredo, verde, materiali della libreria (`libreria/`), sole NOAA (`--data --ora --fuso`), camere delle riprese | `uscita_blender/contesto.blend`, con `--render` `viste/` |
| `allinea_ifc.py <ifc> [--scrivi]` | rotazione, traslazione e quota di un IFC non georiferito sul lotto | valori per `lotto.json → progetto_ifc` |
| `importa_progetto.py` (da aprire su `contesto.blend`) | IFC nella scena: ville alla quota dei cancelli, terreno nel perimetro, muraglioni, marciapiede di progetto, contesto tolto o nascosto sotto il progetto | `contesto_progetto.blend`, `perimetro_progetto.json`, con `--render` `viste_progetto/` |
| `comune.py` | argomenti, log, quota su un triangolo, resa (AgX), render delle camere | modulo |

Ordine dopo una modifica al contesto o al progetto:
1. `contesto/contesto.py <modello>` e `verifica_contesto.py <modello>`;
2. `importa_contesto.py`;
3. `importa_progetto.py` (riscrive `perimetro_progetto.json`: se il perimetro cambia, ripetere da 1).

Opzioni comuni: `--render`, `--viste SV-08,VISTA_angolo` (solo alcune camere), `--samples 16`.
