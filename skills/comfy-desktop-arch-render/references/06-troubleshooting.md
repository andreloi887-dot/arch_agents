# Troubleshooting

## Memoria e prestazioni
- **OOM / "Allocation on device":** usa una quantizzazione più leggera (FP8 → GGUF Q5 → Q4), abbassa la
  risoluzione, riduci batch e numero di ControlNet. Carica gli encoder in FP8. Chiudi altre app GPU (Lumion
  aperto mangia VRAM!).
- **Lentissimo al primo avvio, poi veloce:** è il caricamento dei modelli dal disco. Tieni i modelli su NVMe.
- **Lentezza costante con VRAM piena:** i pesi vanno in offload sulla RAM. Usa una quantizzazione più piccola
  o aumenta la RAM (32–64 GB).
- **Il PC si blocca durante il VAE Decode a risoluzioni alte:** usa *VAE Decode (Tiled)*.

## Qualità architettonica
| Sintomo | Causa probabile | Fix |
|---|---|---|
| Linee e verticali storte | Controllo debole o assente sulle rette; prospettiva del 3D a 3 punti | MLSD 0.5–0.7; correggi la camera nel 3D |
| Aperture o piani inventati | Solo depth, denoise alto | Aggiungi lineart/MLSD; abbassa il denoise; in editing esplicita "keep openings unchanged" |
| Look plastico e cartoon | Strength alta fino alla fine | Abbassa l'end a 0.6–0.75; strength −0.1 |
| Bordi neri dove c'erano le linee | Lineart troppo forte | Strength 0.4–0.5 o passa a softedge |
| Colori slavati o dominante | CFG errato per il modello (per esempio CFG > 1 con Lightning) o quantizzazione troppo bassa | Rispetta il CFG del modello; prova 8 step invece di 4 |
| Dominante rossa con Qwen-Edit Lightning a 4 step | Problema noto, segnalato dalla community | 8 step o niente Lightning |
| Ringhiere, serramenti e testi deformati | Limiti del modello e risoluzione bassa | Inpaint locale ad alta risoluzione; modello Qwen (migliore sul testo) |
| Elementi ripetuti dopo l'upscaling | USDU a denoise troppo alto | Denoise 0.2 o SeedVR2 |
| Aloni intorno alle zone inpaintate | Maschera senza margine | GrowMask 8–24 px + blur |
| Ombre incoerenti con il cielo | Cielo sostituito senza rifare la luce | Editing della luce globale oppure cielo coerente con l'azimut |

## Nodi e installazione
- **Nodi rossi in un workflow scaricato:** mancano custom node, quindi installali dal Manager in un'istanza di
  test. Se il nodo è ormai nativo, sostituiscilo con quello del core.
- **Il workflow si rompe dopo un aggiornamento:** ripristina lo snapshot (non disponibile per le installazioni
  "tracked") e segnala o aspetta il fix del nodo.
- **Modello non visibile nel loader:** cartella sbagliata (vedi la tabella in `01`), formato GGUF senza nodo
  GGUF, oppure percorso extra non letto. Premi *Refresh* o riavvia l'istanza.
- **"Error while deserializing header" / file corrotto:** download incompleto, quindi riscarica e confronta
  dimensione e hash.
- **Mismatch di dimensioni nel ControlNet:** ControlNet o patch di un'altra famiglia (SDXL con Flux, patch
  Qwen-Image 2.1 su Qwen-Image 1.x). Deve essere della stessa famiglia e versione del modello.
