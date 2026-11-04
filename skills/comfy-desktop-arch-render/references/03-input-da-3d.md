# Preparare l'input dal modello 3D

Principio: **più il controllo è "pulito" e nativo del 3D, meno il modello AI deve indovinare.** Un preprocessore
(Depth Anything, Lineart) applicato a uno screenshot va bene per concept e schizzi; per le viste di progetto
esporta i pass dal 3D.

## Quale controllo per quale scopo

| Controllo | Cosa vincola | Quando usarlo in architettura | Note |
|---|---|---|---|
| **Depth** | Volumi, profondità, distanze | Massing, esterni, interni: è il controllo base | Da solo lascia libere le partizioni di facciata: aggiungi linee |
| **MLSD** (rette) | Linee rette e spigoli | Facciate, interni ortogonali, serramenti | Ignora le curve; ottimo con depth |
| **Lineart / Canny** | Tutti i contorni | Schizzi, export a linee CAD | Canny su render fotografici è rumoroso: alza le soglie |
| **Softedge / HED** | Contorni morbidi | Schizzi a mano libera, acquerelli | Più tollerante, ma meno preciso |
| **Normal** | Orientamento delle superfici | Interni con molte superfici inclinate | Utile quando la depth "appiattisce" i dettagli |
| **Material ID / segmentazione** | Zone di materiale | Maschere per inpaint mirati (vetro, verde, cielo) | Non è un controllo diretto: va trasformato in maschere |

Combinazione standard per una vista architettonica: **Depth (forte) + MLSD o Lineart (medio)**.

## Export per software

### Lumion Pro 12.5 (il modo più rapido per ottenere controlli perfetti)
- In *Photo mode* la versione Pro esporta i **render pass**: profondità, normali, sky alpha, Material ID,
  illuminazione e riflessioni (vedi la skill Lumion, `05-render-output.md`).
- **Depth pass:** controllo depth già pronto. Verifica che il bianco sia vicino; se è invertito, usa *Invert Image*.
- **Sky alpha:** maschera perfetta per sostituire o generare il cielo.
- **Material ID:** da qui ricavi maschere per vetro, verde e pavimentazioni (*Image Color To Mask* o selezione
  per colore).
- **Render base:** input per img2img o Qwen-Image-Edit.
- Tutti i pass vanno esportati **dalla stessa camera e alla stessa risoluzione**.

### Edificius (ACCA)
- Esporta la vista dalla stessa camera in due modalità: una **ombreggiata o monocromatica** (base per img2img o
  per ricavare la depth con Depth Anything) e una **a sole linee**, se la modalità di visualizzazione lo consente
  (base per lineart e MLSD).
- In alternativa, esporta IFC e passa a Lumion o Blender per ottenere un depth pass vero.
- Se serve un'immagine RTBIM o AIrBIM come partenza, trattala come un render: img2img o editing a denoise basso.

### SketchUp, Revit, Archicad, Rhino
- **SketchUp:** stile *Hidden Line*, senza texture, con profili sottili, per il controllo lineart; vista
  monocromatica per la depth (oppure stimata con Depth Anything V2).
- **Revit / Archicad:** viste 3D in *Hidden Line* (linee) e *Shaded* (base); disattiva ombre e annotazioni.
- **Rhino:** *ZBuffer* (`ShowZBuffer`) o la vista *Arctic* per la depth; *Technical* o *Pen* per le linee.
- **Blender:** pass Z o Mist normalizzato. È la depth più controllabile di tutte.

## Regole di preparazione
1. **Stessa proporzione dell'output** e risoluzione vicina a quella nativa del modello (vedi `02`). Non chiedere
   all'AI di ricampionare controlli piccoli.
2. **Prospettiva corretta già nel 3D:** verticali dritte (2 punti) e focale scelta lì. Il modello AI non
   raddrizza le verticali, al massimo le peggiora.
3. **Pulisci il controllo:** togli quote, testi, griglie e assi. Il modello li trasforma in oggetti.
4. **Persone e alberi:** decidi se inserirli nel 3D (posizione e scala controllate) o lasciarli generare (più
   naturali, ma con scala casuale). Per i render al cliente conviene inserirli nel 3D, anche come semplici
   sagome.
5. **Uno schizzo a mano** va acquisito con buon contrasto, carta bianca e linee scure, ritagliato e raddrizzato.
   Usa *Softedge* o *Lineart* con preprocessore, non Canny.
