# Comfy Desktop: installazione, istanze, modelli, nodi

## Cos'è (stato a nov 2026)
- **Comfy Desktop** è stata riscritta da zero e rilasciata l'8 giugno 2026 con lo stesso nome. Non è più un singolo
  ComfyUI incapsulato: è un **gestore di più istanze** di ComfyUI, ognuna con la sua versione, i suoi custom node
  e la sua configurazione. Offre snapshot automatici con rollback e aggiornamenti del core in giornata.
- La vecchia app ("Legacy Desktop") si è fermata alla v0.9.4 (28/05/2026) e il suo repository è archiviato.
  Al primo avvio Comfy Desktop rileva l'installazione Legacy e propone la migrazione.
- È open source, nel repository GitHub `Comfy-Org/Comfy-Desktop`.

## Requisiti
- **Windows** 10+ (x64 o ARM64); GPU NVIDIA o AMD dedicata raccomandata. **macOS** solo Apple Silicon.
  **Linux**: nessuna build Desktop secondo le docs consultate, quindi installazione manuale di ComfyUI.
- Almeno 4,85 GB per installazione, più i modelli (realisticamente da 50 a 200 GB). RAM: minimo 8 GB,
  consigliati 16 GB; per Qwen e Flux in pratica 32–64 GB, perché l'offload dei pesi passa dalla RAM.
- **Installa e tieni i modelli su SSD (NVMe):** il caricamento dei modelli da 10–20 GB è un collo di bottiglia reale.
- Per l'uso architettonico la VRAM decide tutto: 8 GB = SDXL o modelli moderni molto quantizzati; 12–16 GB =
  GGUF Q4–Q5 di Qwen o Flux; 24 GB = FP8; 32 GB o più = margine per BF16, risoluzioni alte e più ControlNet.

## Istanze: come usarle in pratica
- **Un'istanza "produzione" stabile** con i soli nodi che usi davvero; **un'istanza "test"** per provare nodi o
  modelli nuovi. Un nodo che rompe le dipendenze Python rompe solo la sua istanza.
- I **modelli sono condivisi** tra le istanze per default. Le cartelle condivise si configurano in
  *Desktop Settings › Storage*. Percorso di default su Windows: `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared`
  (oppure `%USERPROFILE%\ComfyUI-Shared`).
- **Snapshot:** salvano versione di ComfyUI, custom node e pacchetti Python; si ripristinano dal menu della card
  dell'istanza (*Restore Snapshot*). Secondo la pagina ufficiale *Instance Management* **non sono supportati per le
  installazioni "tracked"** (cioè quelle esistenti adottate). Fai uno snapshot manuale prima di ogni aggiornamento
  o installazione di nodi.

## Modelli: dove vanno
Struttura standard (vale per ogni installazione ComfyUI):

| Cartella | Contenuto |
|---|---|
| `models/diffusion_models` (o `unet`) | Pesi del modello (Qwen-Image, Flux, Z-Image) in safetensors o GGUF |
| `models/checkpoints` | Checkpoint all-in-one (SDXL, varianti AIO) |
| `models/text_encoders` (o `clip`) | Encoder di testo (Qwen2.5-VL / Qwen3-VL, T5, CLIP-L, Mistral per Flux.2) |
| `models/vae` | VAE (per esempio `qwen_image_vae.safetensors`, `ae.safetensors` per Flux e Z-Image) |
| `models/controlnet` | ControlNet classici (SDXL, Flux) |
| `models/model_patches` | Patch ControlNet di tipo DiffSynth/Fun (Qwen-Image, Z-Image), caricate con *ModelPatchLoader* |
| `models/loras` | LoRA (Lightning, stili, LoRA di studio) |
| `models/upscale_models` | Upscaler ESRGAN e simili |

- Modelli già presenti altrove (per esempio da un'installazione A1111 o Forge): usa `extra_models_config.yaml`.
  Con Desktop su Windows il file sta in `C:\Users\<utente>\AppData\Roaming\ComfyUI\extra_models_config.yaml`
  (se manca va creato). Attenzione: un report su GitHub dice che il download manager ignora questi percorsi,
  quindi è preferibile configurare le cartelle da *Desktop Settings › Storage*. Questo vale per la versione Legacy
  e va verificato sulla nuova.
- I **template ufficiali** (menu *Workflow › Browse Templates*) indicano i file mancanti e li scaricano: è il
  modo più sicuro per avere nomi e cartelle corretti.

## Custom node
- Installa dal Manager o registry integrato, mai copiando cartelle a caso. Prima dell'installazione: **snapshot**.
- Nodi utili per l'architettura (da verificare sul registry per nome e manutenzione):
  - preprocessori ControlNet (*comfyui_controlnet_aux*: Depth Anything, Lineart, MLSD, Canny, Normal);
  - **ComfyUI-GGUF** (city96), necessario per i modelli quantizzati GGUF;
  - **Ultimate SD Upscale**, per l'upscaling a tile;
  - Impact Pack o nodi equivalenti per segmentazione e maschere automatiche (opzionale).
- Molte funzioni prima "custom" ora sono **native** nel core (Qwen-Image e Edit, Z-Image, patch DiffSynth,
  SeedVR2). Preferisci sempre il nodo nativo: meno rotture agli aggiornamenti.
- Workflow scaricato con nodi rossi (mancanti): installali dal Manager (*Install Missing Custom Nodes*) **in
  un'istanza di test**.

## Migrazione dalla Legacy
- Fai **prima un backup** della cartella dati (modelli, `user/`, `custom_nodes/`, `input`, `output`).
- La pagina Windows delle docs dice che la migrazione riusa in-place la cartella dati e l'ambiente Python
  esistenti; una PR sulle docs (#1899) parla invece di migrazione per copia. Il comportamento è quindi da
  considerare in evoluzione.

## Aggiornamenti
- Il core di ComfyUI esce molto spesso e i modelli nuovi (per esempio Qwen-Image 2.1) richiedono il core
  aggiornato. Regola: aggiorna l'istanza di test, prova i tuoi 2–3 workflow di riferimento, poi aggiorna
  quella di produzione.
