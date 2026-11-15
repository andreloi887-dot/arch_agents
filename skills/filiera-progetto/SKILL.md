---
name: filiera-progetto
description: Usa quando Andrea vuole portare un progetto Edificius (IFC) dentro il contesto del lotto e fino alle immagini e ai video - finiture e arredi degli interni, percorsi di camera, viste di controllo in Blender, export USD, import e resa in Unreal Engine 5.8 - o rilanciare e controllare la filiera dopo una modifica.
---

# Filiera di progetto: IFC → Blender → Unreal

Linea generale: [`PROCEDIMENTO.md`](../../PROCEDIMENTO.md) (fasi 1-6). Stato, regole fissate da Andrea e limiti del
progetto in corso: [`PROGRAMMA_INTERNI.md`](../../PROGRAMMA_INTERNI.md). Il contesto del lotto (fase 2) è della skill
`rilievo-urbano`; questa parte da `contesto.json` già verificato.

## Un comando

```bash
python skills/rilievo-urbano/scripts/filiera.py rilievi/<zona>/modello --villa 1 --viste rilievi/<zona>/modello/viste_controllo.txt
```

Passi: `contesto → progetto → finiture → arredi → percorsi → usd → viste → unreal → libreria → prepara → render`
(gli ultimi due solo con `--fino render` o `--da prepara`: Nanite, luce `--luce giorno|sera --ev N`, materiali, camere,
Movie Render Queue sulla GPU → `uscita_blender/render_unreal/<camera>.png`) (`--da`, `--fino` per una
parte; dopo `progetto` si rifà tutto). Stampa per ogni passo esito, tempo, avvisi noti e **NUOVO**, i tempi delle
viste e il confronto Blender ↔ Unreal (luci, triangoli, materiali, ingombro, camere, fps, fotogrammi). Tutto anche in
`uscita_blender/riepilogo_filiera.json`. **Non cercare nei log a mano**: si leggono solo se un passo è ERR.

- Avvisi accettati: `<modello>/avvisi_noti.txt`, una riga per avviso, testo esatto. Ci va solo ciò che Andrea ha
  visto o che è un limite documentato in PROGRAMMA_INTERNI §7.
- Viste di controllo: `<modello>/viste_controllo.txt`, `nome:x,y,h,tx,ty,th[,focale]` (h sul pavimento). Le immagini
  vanno **guardate** (Read) prima di dire che una cosa va.
- Valori del progetto solo in `lotto.json → progetto_ifc` e `arredi.json`: mai nel codice.
- **Impronta della geometria**: il riepilogo dice se è uguale al giro prima. Pulizie e rifattorizzazioni che non
  devono cambiare il risultato si accettano solo con l'impronta uguale; se cambia, `usd/impronta_mesh.json` dice quali
  mesh (confrontare come dizionari: l'ordine delle chiavi cambia).

## Ambiente

- **PC di Andrea** (preferito): Blender 5.2 con Bonsai, UE 5.8, Quadro RTX 6000. Eseguibili trovati da soli
  (variabili `BLENDER`, `UE_EDITOR`, `UE_PROGETTO` per forzarli). Cycles va su GPU OptiX da solo (`comune.cycles`):
  5-10 s a vista contro 23-27 s di CPU. `FILIERA_CPU=1` forza la CPU.
- **Cloud**: niente Blender, GPU né Unreal. Blender come modulo (`pip install bpy==5.2.4 ...`, PROGRAMMA_INTERNI §2),
  solo passi Blender, viste a ~55 s l'una. Il PC dal cloud non si raggiunge: Unreal si fa solo sul PC.

## Unreal (lezioni verificate il 2026-11-15)

- Import con `AssetImportTask` + `UsdStageImportOptions` (`scripts/unreal/importa_usd.py`), **non** USD Stage Actor.
- Commandlet (`UnrealEditor-Cmd.exe -run=pythonscript`) solo per importare e controllare: è NullRHI, senza GPU.
  **Render e Movie Render Queue con `UnrealEditor.exe`**, sulla scheda grafica.
- Sempre `-FullStdOutLogOutput`; `-script="file argomenti"` spezza agli spazi (lo script riunisce).
- Rilancio: aprire il livello, svuotarlo, salvarlo, poi cancellare gli asset; controllare il disco, non il registro.
- fps: `esporta_usd.py` allinea `framesPerSecond` al fps della scena (Blender lo lascia a 24).
- Arredi e lampade di qualità: `<modello>/arredi_unreal.json` (tipo o nome → asset gratuito già nel progetto) e passo
  `libreria` (`sostituisci_arredi.py`, posizioni da `arredi_posati.json`); `--prova` per controllare senza salvare.
  Solo risorse gratuite; i download e l'accesso a Fab li autorizza Andrea.
- Nessuna porta si nasconde: il riepilogo deve dire "porte nascoste 0".
- Render: esposizione **fissa** (quella automatica brucia l'immagine), MRQ con `-game` e configurazione salvata, mai
  `-ExecutePythonScript`. Dopo il passo `unreal` vanno rifatti `libreria` e `prepara` (Nanite: 23 minuti).
- I controlli numerici non bastano: ogni render va **guardato** (Read) prima di dire che va; i primi erano neri, poi
  bianchi, con i numeri tutti giusti.
- Scena di Via della Menta: 62 M triangoli, 847/899 mesh senza UV → Nanite e UV prima dei materiali di libreria.

## Regole di lavoro

1. Prima di riprendere: PROGRAMMA_INTERNI (stato, §5 regole di Andrea, §7 limiti, §8 prossimi passi).
2. Ogni modifica a uno script: rilancio con `filiera.py` dal passo toccato e riepilogo pulito prima di dire "fatto".
3. Regole generali, mai eccezioni per il singolo lotto. Una lezione nuova va nello script **e** in PROGRAMMA_INTERNI
   (§10 per Unreal) nella stessa modifica.
4. Ad Andrea: immagini con l'elenco di ciò che non va ancora; decisioni di progetto (quote, disposizioni, stile) le
   prende lui. Domande di §1 tutte insieme, all'inizio di un progetto.
5. Mai `read_factory_settings()`/`read_homefile()` in Blender (cancella le librerie di Bonsai: `rilievo-urbano`,
   references/08).

## File

| Dove | Cosa |
|---|---|
| `skills/rilievo-urbano/scripts/filiera.py` | il comando unico |
| `skills/rilievo-urbano/scripts/blender/` | passi Blender (README), `comune.py` (argomenti, log, resa, `cycles`) |
| `skills/rilievo-urbano/scripts/blender/controlli/` | `viste.py`, `pianta_arredi.py`, `arredi_da_pdf.py`, `apri.py` (solo cloud) |
| `skills/rilievo-urbano/scripts/unreal/importa_usd.py` | import e controllo in UE |
| `skills/rilievo-urbano/scripts/unreal/sostituisci_arredi.py` | modelli di libreria al posto dei volumi parametrici |
| `skills/rilievo-urbano/scripts/unreal/prepara_render.py` | Nanite, luce ed esposizione, gres e legno, camere, sequenza e configurazione MRQ |
| `rilievi/<zona>/modello/` | `lotto.json`, `arredi.json`, `avvisi_noti.txt`, `viste_controllo.txt`; uscite in `uscita_blender/` (fuori da git) |
