# Programma degli interni: dall'IFC di Edificius alle immagini di anteprima

Scritto il 2026-11-15 sulla villa A di Via della Menta. È la parte "interni" delle fasi 3 e 4 di
[PROCEDIMENTO.md](PROCEDIMENTO.md): chi riprende il lavoro parte da qui.

**Stato.** Villa A approvata da Andrea come anteprima il 2026-11-15 (finiture, porte, controsoffitto, arredi, cucina,
luci). Import in Unreal 5.8 provato e verificato sul PC il 2026-11-15 (sezione 10): prossimo passo la resa in Unreal.
Ville B, C, D: ferme per scelta di Andrea (2026-11-15), si riprendono quando la A è approvata.

## 1. Cosa serve da Andrea

| Cosa | Dove va | Note |
|---|---|---|
| IFC4 di Edificius con i vani (IfcSpace) nominati | `rilievi/<zona>/edificius/progetto.ifc` | porte e finestre comprese; gli arredi non servono |
| Planimetria PDF **vettoriale** con gli ingombri degli arredi colorati | allegata in chat | giallo e arancio pieni; un rettangolo per mobile |
| Risposte alle domande sotto | `lotto.json → progetto_ifc → finiture`, `arredi.json` | una volta per progetto |

Domande da fare subito, tutte insieme (sulla villa A sono arrivate una alla volta e ogni risposta ha richiesto un giro):
1. **Soffitti**: piani o a falde? Struttura a vista? Sezioni e passo di travi e travetti, colore.
2. **Pavimenti**: prodotto, formato, direzione di posa, fughe; uguale in tutte le stanze? Sempre continuo tra le stanze.
3. **Battiscopa**: materiale, altezza, vani esclusi.
4. **Porte interne**: stile, colore, coprifilo; ci sono scorrevoli a scomparsa?
5. **Controsoffitti e impianti a vista**: dove, a che quota, faretti, griglie, bocchette, split.
6. **Arredi**: stile in tre parole; pezzi obbligati; dove va il tavolo e per quanti posti; cosa non deve stare davanti alle porte.
7. **Cucina**: elettrodomestici voluti, a vista o a scomparsa.

## 2. Ambiente

**PC di Andrea (preferito)**: Blender 5.2 (con Bonsai: ifcopenshell, shapely e pxr ci sono già), Unreal 5.8, Quadro RTX
6000 24 GB. Cycles usa da solo la scheda grafica con OptiX (`comune.cycles`); `FILIERA_CPU=1` o `--cpu` forza la CPU.
Tempi misurati il 2026-11-15, vista 960×540 a 32 campioni: **4–10 s su GPU** (la prima vista paga l'avvio di OptiX), 23–27 s sulla CPU del PC, ~55 s sulla
CPU del cloud.

**Sessione cloud** (senza Blender, senza scheda grafica, senza Unreal): Blender come modulo Python,
`pip install bpy==5.2.4 ifcopenshell shapely usd-core matplotlib` e
`apt-get install -y libegl1 libgl1-mesa-dri libegl-mesa0 libgles2 poppler-utils`; gli script si lanciano con
`python <script> -- <modello> --blend <file>` (o `controlli/apri.py`). Il PC dal cloud non si raggiunge.

## 3. Sequenza

**Un comando** fa tutto e stampa un riepilogo (esito, tempi, avvisi nuovi, confronto Blender ↔ Unreal):

```bash
python skills/rilievo-urbano/scripts/filiera.py rilievi/<zona>/modello --villa 1 --viste rilievi/<zona>/modello/viste_controllo.txt
```

`--da finiture --fino usd` per farne una parte; i render si chiedono con `--fino render` (o `--da prepara`). Avvisi accettati: `<modello>/avvisi_noti.txt` (testo esatto); gli
altri escono come NUOVO. Riepilogo anche in `uscita_blender/riepilogo_filiera.json`: non serve cercare nei log.

| Passo filiera | Script | Cosa fa | Tempo sul PC |
|---|---|---|---|
| contesto | `importa_contesto.py` | contesto.json → `contesto.blend` | 12 s |
| progetto | `importa_progetto.py` | IFC nella scena, vani nascosti, dati delle porte | 32 s |
| finiture | `finiture_interni.py` | pavimento, battiscopa, porte, controsoffitto, perlinato e orditura | 10 s |
| arredi | `arredi_interni.py` | mobili parametrici, cucina a moduli, divano e tavolo | 11 s |
| percorsi | `percorsi_camera.py --solo interni --villa N` | percorso stanza per stanza e luci → `scena_percorsi.blend` | 15 s |
| usd | `esporta_usd.py` | `usd/scena.usdc`, `usd/camere.usdc`, `usd/riferimento.json` | 25 s |
| viste | `controlli/viste.py` | viste Cycles di controllo → `uscita_blender/viste_controllo/` | 4–5 s l'una (GPU) |
| unreal | `unreal/importa_usd.py` | import in UE, controllo → `usd/controllo_unreal.json` | 3–10 min |
| libreria | `unreal/sostituisci_arredi.py` | modelli di libreria al posto dei mobili parametrici, se `arredi_unreal.json` ha delle scelte | 15–35 s |
| prepara | `unreal/prepara_render.py` | Nanite, luce (`--luce giorno\|sera`, `--ev`), gres e legno, camere dalle viste, sequenza e configurazione MRQ | 17 s (23 min la prima volta, per Nanite) |
| render | Movie Render Queue (`-game`) | un PNG 1920×1080 per camera in `uscita_blender/render_unreal/` | 40 s per 4 viste |

Passi a mano, prima della filiera, solo per un progetto nuovo:
- ingombri dalla planimetria: `pdftocairo -svg planimetria.pdf p.svg`, poi
  `python $S/controlli/arredi_da_pdf.py p.svg $M <villa> bozza.json`; completare `arredi.json` (tipo di ogni
  ingombro, stile, zona giorno) leggendo misure e posizione;
- pianta di controllo: `python $S/controlli/pianta_arredi.py $M/uscita_blender/contesto_progetto.blend 1 pianta.png`.

(`S=skills/rilievo-urbano/scripts/blender`, `M=rilievi/<zona>/modello`.) I passi Blender si rilanciano: cancellano
e rifanno le proprie collezioni. Dopo "progetto" vanno rifatti tutti quelli successivi.

## 4. Dove stanno i valori

- **`lotto.json → progetto_ifc → finiture`**: `soffitto` (colore, doga, `travetti`: sezione, interasse, trave d'incontro,
  arretro sopra gli infissi), `pavimento` (colore, formato, fuga, `per_vano`), `battiscopa`, `porte`, `controsoffitto`.
  I predefiniti sono in `PRED` dentro `finiture_interni.py`.
- **`arredi.json`**: `stile` (colori), `arredi` (un ingombro per mobile, con `tipo`), voce `zona_giorno`
  (`posti_tavolo`, `distanza_porte_m`, `tavolo_contro_vano`).
- Nessun valore del singolo progetto dentro gli script.

## 5. Regole fissate da Andrea (villa A, 2026-11-15)

**Tetto in legno a vista**
- Una trave lungo ogni colmo, displuvio e compluvio; i travetti delle due falde vi arrivano nello stesso punto, alla
  stessa quota (incastro a coda di rondine).
- Passo e sezione dei travetti identici ovunque (70 cm, 10×16; travi d'incontro 14×22). La differenza di misura va in
  un solo campo di compensazione, al centro di ogni campata.
- Un travetto non appoggia mai sopra un infisso: si ferma 25 cm prima su una trave perpendicolare della stessa
  sezione, che scarica sui travetti ai due lati. Se da un lato manca il travetto (infisso al bordo della falda), lo
  script ne aggiunge uno a un passo di distanza solo se la posizione è pulita (dentro la falda, senza sovrapposizioni,
  non sopra un altro infisso); altrimenti resta così e il log dice perché (Andrea, 2026-11-15). Nella villa A i 4 casi
  restano così: a un passo la falda è già finita, o il travetto uscirebbe dal bordo o sarebbe lungo 25 cm.
- Perlinato e travi avorio chiaro (#EFE8D6).
- Perlinato a doghe continue: nessuna giunzione trasversale in vista, i tagli stanno sopra le travi (Andrea, 2026-11-16).
  Vale in Blender (`finiture_interni.py`) e in Unreal (`prepara_render.py`).

**Pavimento e battiscopa**
- Marazzi Room Beige 100×100, fughe parallele ai muri, mai in diagonale.
- Una superficie continua in tutta la casa: nessuna soglia o riga sotto le porte.
- Battiscopa dello stesso gres, 7 cm, ovunque tranne nei bagni.

**Porte**
- Moderne, anta liscia, coprifilo discreto (5 cm, piatto).
- Versi di apertura come in planimetria. Stanno nell'IFC: l'anta apre verso +y locale, cerniera a x = larghezza,
  oppure a x = 0 se `IFC_Pset_Geometria → Inverti (dx/sx)` è vero (verificato su 9 porte).
- In cucina doppia scorrevole a scomparsa.
- Le ante si vedono, aperte: non si nascondono per far passare la camera. **Tutte le porte restano in scena**, ingresso
  compreso (Andrea, 2026-11-15): se un passaggio non c'è, si cambia la traiettoria. Il percorso interno parte dentro,
  90 cm oltre la porta d'ingresso chiusa; `filiera.py` controlla "porte nascoste 0" e va in errore se ne manca una.

**Disimpegno e clima**
- Controsoffitto in cartongesso a 2,40 m con faretti LED tondi a incasso e griglie di ripresa: sopra c'è la macchina.
- Una bocchetta di immissione in ogni stanza, sopra la porta, tra 2,45 e 2,60 m (quota confermata da Andrea); bagni
  e cucina senza.

**Arredi**
- Stile caldo, naturale, minimale: rovere chiaro, laccato avorio, lino, un accento terracotta.
- Ingombri dalla planimetria; il resto (divano, tavolino, tavolo, sedie) lo dispone lo script.
- Tavolo da 4 allungabile, addossato al muro tra soggiorno e camera singola; parete TV, divano e tavolino spostati
  verso la vetrata di quanto serve. Passaggio libero davanti alla porta del disimpegno.
- Cucina: frigo, colonna forno e microonde, lavello, lavastoviglie, piano cottura con cappa; pensili con la parte
  bassa a 1,45 m e la parte alta sotto la trave più bassa.
- Armadi: altezza unica, sotto il punto più basso di travi, travetti e falde sopra il loro ingombro, con 2 cm d'aria,
  al massimo 2,40 m (Andrea, 2026-11-16: scelta tra gradini per anta, altezza unica e cima inclinata). Villa A:
  matrimoniale 1,84 m, camera singola 1,87 m; sotto 1,60 m il log dà un AVVISO.
- Comodini: il fronte guarda dove guarda il letto accanto (dalla testata ai piedi), non verso il letto.
- Punti luce: una sospensione per stanza, due in zona giorno (tavolo e tavolino), luce sotto i pensili, faretti nel
  disimpegno; luce calda.

## 6. Controlli prima di mostrare qualcosa ad Andrea

1. Riepilogo di `filiera.py` senza ERR e senza avvisi NUOVO (o ognuno spiegato), confronto Unreal tutto ✓.
2. Pianta arredi: nessun mobile nelle battute delle ante, tavolo e divano dove chiesto.
3. Una vista Cycles per stanza, guardata davvero: porte, battiscopa, soffitto, mobili che non bucano muri o tetto.
4. Le immagini si mandano con l'elenco di ciò che non va ancora. Mai dire "fatto" senza averle guardate.

## 7. Limiti noti

- **Tetto**: nell'IFC sette linee d'incontro della villa A non sono a 45° con falde di pari pendenza. Lì passo costante
  e incontro esatto dei travetti non stanno insieme: va corretto il tetto in Edificius.
- **Muri interni**: alcuni non arrivano al tetto; sopra la porta della cucina si vede il vano accanto.
- **Mobili**: volumi parametrici. Vanno bene armadi, cucina e parete TV; divano, sedie, letti e tessili sono da
  sostituire con modelli di libreria (Poly Haven ha poco di moderno: Fab/Megascans in Unreal).
- **Materiali**: procedurali di Blender; in Unreal vanno rifatti dalla libreria di studio. Il gres esce troppo chiaro.
  **847 mesh non hanno UV** (su 899; 1494 con le istanze) (esporta_usd lo segnala): in Unreal le texture non si applicano finché non si
  generano le UV (in Blender prima dell'export, o in Unreal per i materiali di libreria a proiezione).
- **Peso**: la scena esportata ha 62 milioni di triangoli (1494 mesh con le istanze, quasi tutti nel prato a
  particelle e nel contesto). In Unreal va attivato Nanite sulle mesh pesanti prima della resa.
- **Percorso di camera**: nato per le stanze vuote. Controlla gli ostacoli solo ad altezza d'occhio, guarda spesso
  un muro, e ha 13 avvisi di passaggio stretto (12 al 2026-11-15). Le viste fisse del passo 8 rendono meglio.
- **Video interno**: non rifatto dopo arredi e porte. In Cycles: ~30 ore sulla CPU del cloud, ~3 ore sulla GPU
  del PC (1847 fotogrammi al 2026-11-16, erano 1965; × ~5 s, stima dalle viste). Il video finale si fa comunque in Unreal.

## 8. Prossimi passi, in ordine

1. Giudizio di Andrea sulle viste della villa A; correzioni.
2. Percorso interno ripensato sui mobili: una o due inquadrature per stanza, movimenti lenti tra punti scelti.
3. Tarare esposizione e colori su una foto di riferimento del gres e del legno.
4. Correzione del tetto in Edificius (Andrea) e nuovo IFC.
5. Ville B, C, D: stesse regole, più ingressi e scale.
6. Unreal sul PC di Andrea: import USD fatto e verificato (sezione 10); restano materiali e arredi di libreria,
   Nanite, Movie Render Queue.
7. Contesto esterno dalle foto del sopralluogo.
8. ~~Trasformare questo programma in una skill con il suo agente~~: fatto il 2026-11-15
   (`skills/filiera-progetto/`, agente `filiera-progetto`).

## 9. Livello di modello

Decisioni su regole, disposizioni e letture dell'IFC: sessione principale. Rilanci, estrazioni e controlli di log:
direttamente, sono compiti piccoli. Niente livello 0 sui contenuti tecnici.

## 10. Passaggio a Unreal (sul PC desktop di Andrea)

**Fatto e verificato il 2026-11-15** in una sessione di Claude Code sul PC (dal cloud il PC non si raggiunge).
Progetto Unreal: `Documenti/Unreal Projects/ViaDellaMenta/ViaDellaMenta.uproject` (plugin USDImporter,
PythonScriptPlugin, EditorScriptingUtilities; Lumen e ombre virtuali in `Config/DefaultEngine.ini`). Fuori da git:
se manca, `filiera.py` ne crea uno vuoto uguale.

Esito del controllo (filiera, passo unreal), Blender → Unreal: luci 1 sole, 29 punti, 16 faretti, 3 rettangolari ✓;
62 059 121 triangoli contro 62 060 177 (Unreal scarta i degeneri, 0,002 %) ✓; 73 materiali distinti ✓ (Unreal
accorpa i materiali uguali: 87 in USD, 84 usati, 73 diversi); ingombro in cm uguale, con l'asse y ribaltato ✓;
camera e Level Sequence `LS_camere` a 25 fps, fotogrammi 1–1965 ✓ (1–1847 dal 2026-11-16, percorso rifatto). Livello: `/Game/Progetto/Scena`.

Lezioni (già negli script):
1. `-run=pythonscript -script="file argomenti"` spezza gli argomenti agli spazi: lo script li riunisce.
2. Senza `-FullStdOutLogOutput` i messaggi di Python non arrivano su stdout.
3. **USD Stage Actor: no.** In commandlet non espone le mesh, gli asset restano transitori e il livello si ricarica in
   3–8 minuti a ogni apertura. Si importa con `AssetImportTask` + `UsdStageImportOptions`: asset veri in
   `/Game/Progetto/scena`, camere in `/Game/Progetto/camere` con la Level Sequence.
4. Rilancio: in commandlet il `.umap` cancellato resta su disco e `new_level` rifiuta il percorso; gli asset usati dal
   livello salvato non si cancellano. Ordine giusto: aprire il livello, svuotarlo, salvarlo, poi cancellare gli asset.
   Il registro degli asset continua a elencare quelli cancellati: il controllo si fa sul disco.
5. Blender scrive `timeCodesPerSecond` ma lascia `framesPerSecond` a 24, e Unreal fa la sequenza a 24 fps:
   `esporta_usd.py` li allinea al fps della scena.
6. Il sole esportato da Blender arriva come DirectionalLight: diventa il sole dell'atmosfera (niente secondo sole).
7. **Impronta della geometria** (`usd/riferimento.json → impronta`): hash di vertici al mm, trasformazioni, materiali
   legati e valori degli shader. `filiera.py` dice se è uguale al giro prima: una pulizia del codice che non deve
   cambiare il risultato si accetta solo con l'impronta uguale (provato il 2026-11-15 sulla revisione degli script).
   L'export USD di Blender scrive i prim in un ordine che cambia a ogni giro: l'impronta li ordina per percorso.
8. Il commandlet gira senza scheda grafica (NullRHI): va bene per importare e controllare, **non per rendere**. Le
   immagini e la Movie Render Queue si lanciano con `UnrealEditor.exe` (non `-Cmd`), sulla GPU.

**Arredi e luci di qualità** (richiesta di Andrea, 2026-11-15: niente blocchi squadrati; solo risorse gratuite).
Meccanismo pronto e provato: `arredi_interni.py` scrive `uscita_blender/arredi_posati.json` (47 pezzi: centro, asse
lungo, fronte, misure); `sostituisci_arredi.py` legge la scelta in `<modello>/arredi_unreal.json` (tipo o nome → asset
del progetto, `adatta`, `ruota_gradi`, `appoggio`), toglie il volume parametrico e mette il modello nello stesso punto,
segnalando gli scarti di misura oltre il 15 %. Provato con una forma di prova: scarto del centro 0,0 cm, lampade appese
dalla cima. `spawn_actor_from_object` in commandlet restituisce None: si crea uno StaticMeshActor e gli si assegna la mesh.

**Primo pacchetto (2026-11-15)**: *Modern Japanese Furniture Pack* di Nimikko, da Fab (plugin Fab nell'editor, filtro
prezzo "Gratis"), licenza Standard livello **Personale**: gratis solo sotto i 100.000 dollari di ricavi negli ultimi 12
mesi (confermato da Andrea; l'accordo Fab l'ha accettato lui sul suo account). In `Content/JapaneseFurniture_Modern`
(194 MB, fuori da git). Modelli leggeri (500–1000 triangoli) ma con texture vere. In `arredi_unreal.json`: letti
(`SM_Bed_01_*` + materasso a +20 cm, ruotati di 90° perché la testata sta a −Y), comodini (+ lampada da tavolo a
+40 cm), sospensioni (`SM_CeilingLight_01`, scala "altezza"). Esito: 36 pezzi di libreria, 11 ancora parametrici.
**Mancano**: divano (quello del pacchetto è largo 126 cm, ne servono 230), tavolo da pranzo con sedie, tavolino con
tappeto, scrivanie; armadi, cucina, parete TV e madia restano parametrici (su misura).

Lezioni dalla prima scena guardata nell'editor (2026-11-15):
- L'import USD mette tutte le mesh come componenti di un solo attore `scena` (880), con nomi un po' diversi da quelli
  di Blender; le luci delle lampade hanno il nome del pezzo. Cercando per nome dell'attore si erano **cancellate le 29
  luci a punto** e i volumi restavano. Ora `sostituisci_arredi.py` nasconde solo i componenti mesh che cominciano con il
  nome del pezzo e stanno nel suo ingombro; `filiera.py` controlla che le luci in scena non cambino (50) e che ogni
  volume sia stato trovato.
- Le luci importate sono "stazionarie": l'editor chiede di calcolare l'illuminazione e la scena è nera. `importa_usd.py`
  le rende mobili (Lumen). L'esposizione manuale predefinita (ISO 100, 1/60, f/4) è da esterno: ora è automatica; il
  valore fisso per i render va scelto guardando la scena.
- I controlli numerici non bastano: la scena va aperta e guardata. Per farlo: `UnrealEditor.exe <progetto>
  /Game/Progetto/Scena`, poi nella riga Cmd `py "<file>.py"` con `set_level_viewport_camera_info`. L'editor va chiuso
  prima di rilanciare i passi `unreal` e `libreria`.
- All'apertura l'editor avvisa che per le ombre virtuali serve Shader Model 6 (impostazioni di progetto › Windows ›
  formati shader D3D12): da attivare prima dei render.

Rilancio dei passi Blender: gli oggetti tolti lasciano dati orfani e i nuovi prendevano nomi con suffisso diverso a
ogni giro (fino in Unreal); `comune.svuota` li elimina subito e i nomi restano stabili (impronta uguale ai rilanci).

**Primi render (2026-11-15)**: viste di giorno, solo luce naturale (richiesta di Andrea), Movie Render Queue sulla
GPU: `filiera.py <modello> --da prepara` → 4 PNG 1920×1080 in 40 s. Progetto con Shader Model 6, DX12, ray tracing per
Lumen, Nanite (in `Config/DefaultEngine.ini`; `filiera.py` crea così anche un progetto nuovo).
- **Nanite**: i 62 milioni di triangoli sono quasi tutti nei 36 alberi di libreria (1,76 milioni l'uno, una mesh per
  albero). Costruzione: 23 minuti, una volta; **si rifà a ogni passo `unreal`**, perché il reimport ricrea le mesh.
  Da migliorare a monte: in Blender gli alberi uguali devono uscire come istanze di una mesh sola.
- **Luce di giorno**: luci artificiali spente (48), sole fisico a 100 000 lux con la direzione di Blender, cielo
  dall'atmosfera. **Esposizione fissa** (EV 10 di giorno): nel render quella automatica non si adatta e l'immagine
  esce bianca. EV 10 va bene in soggiorno; le camere con una sola portafinestra restano più scure: da decidere se
  dare un EV per vista.
- **Materiali**: gres del pavimento rifatto in Unreal dalle UV in metri (formato e fuga di `lotto.json`), legno degli
  arredi con la venatura di una texture del pacchetto proiettata nello spazio e la tinta di `arredi.json`. Gli altri
  restano tinte unite: mancano tessuti, laccati con riflessi veri, intonaco. Mobili parametrici senza UV.
- **Movie Render Queue da riga di comando**: configurazione salvata nel progetto (`export_config_to_asset`, primo
  argomento = percorso completo del pacchetto) e `UnrealEditor-Cmd.exe <progetto> <mappa> -game -LevelSequence=...
  -MoviePipelineConfig=...`: usa la GPU e si chiude da solo. **Non** `-ExecutePythonScript`: l'editor esegue lo script
  ed esce subito. Una Level Sequence con un'inquadratura di un fotogramma per camera = uno scatto per camera, ognuno
  con il suo riscaldamento (96 + 64 fotogrammi) perché Lumen si assesti.
- In commandlet: `StaticMeshEditorSubsystem` è None (Nanite si imposta con la proprietà `nanite_settings`);
  `list_assets` non elenca gli asset importati (le mesh si prendono dai componenti del livello); dopo Nanite
  `get_num_triangles(0)` dà la mesh di ripiego.
- Da Git Bash un argomento `/Game/...` diventa `C:/Program Files/Git/Game/...`: serve `MSYS_NO_PATHCONV=1`. Da
  `filiera.py` (Python) il problema non c'è: è un altro motivo per usare sempre il comando unico.

**Controllo da vicino (2026-11-16)**, con le viste `griglia_disimpegno`, `comodini_matrimoniale`, `armadio_matrimoniale`,
`armadio_singola` in `viste_controllo.txt`:
- Gli armadi da 2,40 m bucavano il tetto: nella camera singola la falda è a 2,21 m e i travetti a 2,10 (fino a 1,89).
  Misura: raggi verso l'alto ogni 5 cm (un travetto è largo 10) partendo da 1 m dal pavimento, così il primo
  ostacolo è il fondo della trave e non la falda sopra. Ora `h_armadio` in `arredi_interni.py` (regola in §5).
- Comodini: `telaio()` su un ingombro quasi quadrato sceglie l'asse lungo a caso, e 3 su 4 guardavano il letto. Ora
  si posano dopo i letti e ne prendono il verso.
- Luci delle sospensioni: Blender le mette 3 cm sotto il bordo del paralume parametrico. Con il modello di libreria
  restavano fuori dalla sfera (27 su 29 da 3 a 16 cm sotto il fondo; 2 a 21 cm sopra, non al centro). `sostituisci_arredi.py` le sposta al centro del
  paralume (in pianta al centro del modello, in quota a metà larghezza sopra il fondo) e le elenca in
  `usd/controllo_arredi.json → luci_nei_paralumi`. Di giorno sono spente: si controllano con un render `--luce sera`.
- La griglia di ripresa del disimpegno c'è ed è al suo posto, tra i due faretti.
- Progetto Unreal: la sessione precedente usava la variabile `UE_PROGETTO`. In una sessione nuova, senza la variabile,
  `filiera.py` ha creato un progetto vuoto accanto a `ViaDellaMenta`: 0 modelli di libreria, nessun avviso che lo
  fermasse. Ora il nome sta in `lotto.json → progetto_ue`; se manca, la filiera lo scrive in chiaro.
- Al rilancio del passo `unreal` in un progetto già preparato, il controllo dei fotogrammi leggeva `Viste/LS_viste` (uno
  scatto per vista, `[0, 4]`) invece della sequenza delle camere importate: `importa_usd.py` ora la esclude.
- Sera (`--luce sera`): con le luci dentro le sfere di rattan la trama del paralume si stampa su muri e soffitto, come
  nella realtà. EV 5 (predefinito per la sera) dà immagini quasi nere; EV 3 si legge, ma le stanze restano buie
  (14 W/m² di Blender) e le lampade da comodino di libreria non hanno luce: da tarare con l'esposizione (§8 punto 3).
  Immagini: `uscita_blender/render_unreal/` (giorno, aggiornate), `render_unreal_sera_ev5/`, `render_unreal_sera_ev3/`.
- Aperto: la sospensione `Bagno v1 1.001` (e `Rip v4 1`) con il modello di libreria alla scala minima 0,6 pende più in basso
  del previsto: fondo a 1,87 m dal pavimento. Da decidere: lampada più corta o plafoniera nei bagni.
- Asset `SM_Nightstand_01`: il fronte (cassetti) è su +Y, come vuole `sostituisci_arredi.py`, senza `ruota_gradi`
  (render `comodini_matrimoniale`).
- **Perlinato del soffitto assente in Unreal (errore trovato da Andrea, 2026-11-16).** In Blender il perlinato è un Brick
  procedurale sulle UV in metri dell'intradosso; l'USD porta solo la tinta, e `prepara_render.py` rifaceva gres e legno
  ma non il perlinato: tutti i render Unreal fino a quel giorno avevano il soffitto liscio. Ora `prepara_render.py` crea
  `M_Perlinato` con lo stesso disegno di Blender (doga `soffitto.doga_m`, fuga 4 mm al 70 %, due toni) e lo mette su ogni `MI_Perlinato*`; controllo `perlinato_parti` in `controllo_render.json` (villa A: 18,
  come le falde del log di finiture) e AVVISO se è 0. **Regola:** ogni materiale procedurale di Blender che conta va rifatto
  in Unreal, e ogni render Unreal va confrontato con la vista Blender omonima anche per le finiture, non solo per la
  geometria. Ancora da rifare: travi con venatura se servono.
- **Vetro a specchio in Unreal (2026-11-16).** I vetri dell'IFC arrivano come istanze di `UsdPreviewSurface` con Opacity 0,2,
  ma il materiale base è opaco e l'opacità si perde: lastra bianca lucida che riflette la stanza (vista `armadio_singola`,
  sembrava un armadio fuori dalla camera). Ora `prepara_render.py` mette `M_Vetro` (traslucido, opacità 0,06–0,5 con il
  Fresnel, ruvidità 0,02, senza ombra) su ogni istanza importata con 0 < Opacity < 0,99: villa A 30 parti, tutte
  `Finestra_*`; controllo `vetro_parti` e AVVISO se è 0. Il nome dell'enum del modo di luce del traslucido cambia tra le
  versioni di Unreal: si cerca tra quelli disponibili. Le istanze con Opacity 0 (`Involucro_fittizio`) restano come sono.
- **Abat-jour senza luce (2026-11-16).** Nessuno script aveva mai messo una sorgente nelle lampade dei comodini. Ora
  `arredi_interni.py` mette una luce a punto (`luci.abatjour_w`, 25 W) nel paralume parametrico e `sostituisci_arredi.py`
  la porta nel paralume della lampada di libreria (`con` con "lamp" nel nome); controllo in `luci_nei_paralumi`
  (villa A: 4 × 1). Luci a punto 33 = 29 sospensioni + 4 abat-jour.
- **"Sera" con il sole del giorno (2026-11-16).** `prepara_render.py` lasciava il sole acceso anche di sera: finché i vetri
  erano opachi non si vedeva, con i vetri veri la sera era giorno pieno. Ora di sera il sole è spento. Il render di sera va
  in `render_unreal_sera/`, quello di giorno in `render_unreal/`: prima la sera sovrascriveva il giorno.
- **Esposizione per vista (2026-11-16).** `filiera.py --taratura`: dopo il render misura la chiave di ogni immagine (media
  geometrica della luminanza lineare, senza i pixel bruciati), scrive l'EV di ogni vista in
  `uscita_blender/ev_viste_<luce>.json` e rifà prepara e render (al massimo 3 giri); `prepara_render.py` mette l'EV nella
  camera, che vince sul volume. Chiave voluta: giorno 0,20 (converge in 2 giri, EV da 8,96 a 11,28), sera 0,09 (partendo da
  EV 5 servono 3 giri e l'ultimo corregge ancora fino a 1 EV: il tone mapping non è lineare). Le EV di sera trovate a sole
  acceso (da 9,7 a 11,2) erano sbagliate e sono state cancellate. Di sera, con poca luce, Lumen lascia macchie sui muri: da
  affinare (qualità di Lumen o più campioni).

**Arredo sui riferimenti di Andrea (2026-11-16/17).** Cucina, tavolo e sedie, divano, lampadari a ciottolo, letti, comodini e
armadi (due versioni) modellati in `arredi_interni.py` sulle sue foto (`modello/riferimenti_arredo/`, fuori da git), senza
modelli di libreria. Dopo il suo giudizio ("tutto squadrato, lontano dai riferimenti"): tessuti simulati (`tessili.py`: piumone,
guanciali, plaid, cuscini del divano), superfici lisce per sedie e lampadari, texture CC0 vere (`libreria_materiali/`, scaricate
con `strumenti/materiali/`), viste di controllo in Full HD (`filiera.py --scala 100`) e confronto affiancato col riferimento.
Metodo, scelte dei materiali e lezioni: skill [arredo-da-riferimento](skills/arredo-da-riferimento/SKILL.md). In Unreal
`arredi_unreal.json` non usa più la libreria per letti, comodini e lampadari del soggiorno.

**Secondo giudizio di Andrea (2026-11-17): rifiniture.** Tessuti e cuscini del letto e cuscini del divano "troppo rigidi e
tutti uguali"; camicie morbide appese nell'armadio della matrimoniale; legno dei letti "plasticoso"; nella matrimoniale le
sospensioni sottili del riferimento al posto delle abat-jour; nodi e venatura leggerissimi nel legno pitturato del soffitto.
Fatto: ricette dei tessili condivise tra filiera e banco (`blender/ricette_arredo.py`, materiali in `blender/materiali_arredo.py`)
e banco in scena (`skills/arredo-da-riferimento/scripts/banco_scena.py`); cuscini a bordo cucito, ognuno diverso, assestati
con la gravità; camicie simulate su grucce (`tessili.camicia`); rovere opaco (ruvidità 0,70 nel file) con la fibra lungo il
lato lungo; due sospensioni sfalsate sopra il comodino di destra, come nel riferimento (tipo `lampada_letto`, lampadina
emissiva in Unreal); legno pitturato del soffitto da `blender/legno_dipinto.py` (venatura ±1,5-2 %, un nodo ogni 3 m di doga
circa, rilievo leggero), stessa immagine in Blender e in Unreal (`M_Perlinato`, `M_Travetti`). Il soffitto è comune a
tutte le ville, come il perlinato del 2026-11-16. Lezioni nella skill. Poi plaid e piumone: plaid che cade da vicino con poco attrito
e piega di un plaid in maglia, piumone meno gonfio e senza bozze. Verificato in Unreal di giorno e di sera (confronti
`uscita_blender/confronti/rifinito_*.jpg`; viste ravvicinate aggiunte a `viste_controllo.txt`, viste solo Blender in
`viste_controllo_arredi.txt`). Aperti: plaid dei letti singoli accartocciato, chiave della cache incompleta (skill).

Prossimi passi in Unreal, in ordine: divano, tavolo con sedie e scrivanie di libreria; materiali per tessuti, laccati
e intonaco; EV per vista; alberi come istanze; viste verso le vetrate e dall'esterno; poi il video (percorso interno,
Sequencer) e il montaggio con FFmpeg. Ogni cosa imparata va scritta qui.

**Arredi del 2026-11-17 sera (foto di Andrea in `riferimenti_arredo/`).** Mobile TV della matrimoniale come `mobile_tv.jpg`
(cassettiera laccata greige, due colonne × tre file, estremo libero arrotondato; la TV e la parete restano com'erano);
sospensione a tre paralumi neri (`sospensione_camere.webp`) in tutte le camere, al posto della plafoniera in rattan; abat-jour in
travertino con tamburo in lino (`abatjour_travertino.jpg`) nelle singole e a sinistra nella matrimoniale; due globi in vetro fumé
(`sospensioni_letto_vetro.jpg`) a destra; nei due bagni mobile in noce, piano in pietra, catino da appoggio, rubinetto a parete,
specchio con LED (`bagno.jpg`) al posto del lavabo IFC, e rivestimento in lastre di pietra beige 75 × 75 cm fino a 1,50 m, nella
doccia fino a 2,10 m (`finiture_interni.py`). Il vetro della doccia resta quello dell'IFC (lo sceglie Andrea).
Poi (Andrea, stessa sera): mobile TV con la curva dal lato della porta, allungato fino al muro del comodino e 10 cm meno
profondo, TV da 55" appesa al muro con lo schermo lucido; doccia con vetro temperato chiaro e montanti in acciaio lucido (il
blocco IFC si divide in parti: lastre semplici e sottili = vetro, il resto = acciaio, il piatto resta); maniglie delle porte
interne in acciaio satinato (rosetta tonda, leva cilindrica) con la bocchetta della chiave sulle due facce. La porta d'ingresso
è quella dell'IFC e non ha ancora maniglia e bocchetta nuove.
Ultimi ritocchi ai bagni (stessa sera): pietra del rivestimento ricavata dalla foto (`strumenti/materiali/pietra_sabbia.py`),
rivestimento su tutto il perimetro fino al coprifilo delle porte; catino dal lato della doccia e specchio dentro il mobile;
miscelatore sul bidet, placca di scarico, portarotolo e portascopino a muro (sul muro laterale se accanto al wc non c'è posto),
barra con asciugamano in spugna simulato sopra il bidet (`tessili.asciugamano`); maniglie delle porte in un oggetto liscio a
parte. Tutto dichiarato in `arredi.json` (tipi `lavabo`, `rubinetto_bidet`, `accessori_wc`, con il blocco IFC di riferimento).
