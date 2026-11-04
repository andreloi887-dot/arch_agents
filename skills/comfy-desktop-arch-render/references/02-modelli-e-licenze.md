# Modelli per render architettonici: scelta, VRAM, licenze

> Stato a novembre 2026. Il panorama cambia ogni mese: per modelli più recenti cerca sul web.
> **Le licenze vanno sempre verificate sul model card ufficiale** prima di un uso commerciale.

## Mappa rapida

| Modello | Punto di forza in architettura | Controllo geometrico | Licenza pesi (verificare) |
|---|---|---|---|
| **Qwen-Image-Edit-2509 / 2511** | Editing guidato da istruzione su un'immagine esistente (render Lumion, foto, massing): materiali, contesto, luce, stagione. Ottimo con il testo e le scritte | Controlli depth/edge/keypoint integrati (dalla 2509); geometria preservata dall'immagine di partenza | Apache 2.0 (famiglia Qwen-Image originale) |
| **Qwen-Image (t2i) + patch DiffSynth** | Generazione da depth/canny con resa fotografica alta | Patch canny/depth/inpaint; LoRA union per lineart/softedge/normal | Apache 2.0 |
| **Qwen-Image 2.1** (20/09/2026) | Generazione ed editing più recenti; trasparenza; nativo in ComfyUI dal primo giorno | **Fun ControlNet Union**: 8 controlli + inpaint in un solo file (~7,5 GB), nel core dal 28/09/2026 | **Qwen Research License**: risulta non commerciale, verifica il LICENSE ufficiale |
| **Z-Image Turbo** | Velocissimo (~9 step), buon fotorealismo, VRAM moderata (Qwen3 4B come encoder) | *Z-Image-Turbo-Fun-Controlnet-Union* (Canny, HED, Depth, Pose, MLSD); template ufficiale | Apache 2.0 (da verificare) |
| **FLUX.1 dev / Kontext dev** | Ecosistema LoRA ampio; Kontext per l'editing | ControlNet e adapter (FLUX.1-Depth-dev, Canny-dev) | Pesi non commerciali; output usabili commercialmente secondo la licenza dev |
| **FLUX.2 dev** | Qualità alta, multi-reference | Da verificare | **Non commerciale** (output commercialmente usabili secondo il model card); molto pesante (≥24 GB anche quantizzato) |
| **FLUX.2 Klein 4B** | Versione leggera | Da verificare | Permissiva (Apache 2.0 secondo fonti terze) |
| **SDXL + ControlNet** | Fallback per 8 GB; ecosistema maturo (MLSD, depth, tile) | ControlNet classici molto prevedibili | CreativeML OpenRAIL++ (commerciale ammesso con restrizioni d'uso) |

## Come scegliere (raccomandazione netta)
- **Hai già un render Lumion o Edificius e vuoi più realismo o varianti:** Qwen-Image-Edit-2511. Lavora
  sull'immagine, quindi la geometria resta per costruzione. È la scelta migliore per il 70% dei casi di studio.
- **Hai solo uno schizzo, linee CAD o un massing grigio:** generazione con ControlNet (depth + lineart/MLSD).
  Z-Image Turbo + Union per iterare veloce; Qwen-Image + DiffSynth (o 2.1 Union, se non serve l'uso commerciale)
  per la qualità finale.
- **GPU da 8 GB:** SDXL + ControlNet, oppure Z-Image Turbo quantizzato. Qwen-Image-Edit in GGUF Q2–Q3 gira ma
  perde qualità.
- **Uso commerciale certo** (render venduti al cliente): resta su pesi Apache 2.0 (famiglia Qwen-Image originale,
  Z-Image) o su modelli i cui termini coprono gli output; evita Qwen-Image 2.1 finché la licenza non è chiarita.

## Qwen-Image-Edit-2511: file e parametri di riferimento
- Pesi: `qwen_image_edit_2511_fp8mixed.safetensors` (24 GB VRAM) o `..._bf16` (precisione piena). Per 12–16 GB:
  GGUF Q4_K_M (~13 GB) o Q4_0 (~12 GB) con il nodo ComfyUI-GGUF.
- Encoder Qwen2.5-VL 7B (fp8) e `qwen_image_vae.safetensors`. Scarica dal template ufficiale per i nomi esatti.
- **Senza Lightning:** FP8 ~20 step e BF16 ~40 step, **CFG 4.0**.
- **Lightning LoRA** (`Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16`, ~850 MB): **CFG 1.0**, 4–8 step.
  A 4 step alcuni utenti segnalano dominanti rosse e perdita di dettaglio: per le immagini finali usa 8 step.
  La LoRA 8 step della serie 2509 è compatibile.
- Un report segnala che con la 2511 serve il nodo *FluxKontextMultiReferenceLatentMethod* sulle condizioni
  positive e negative: usa il template ufficiale, che lo include già se necessario.

## Risoluzioni native (evita di generare fuori distribuzione)
- **Qwen-Image:** ~1,6 MP, per esempio 1328×1328, 1664×928 (16:9), 928×1664, 1472×1104 (4:3).
- **Flux, Z-Image, SDXL:** ~1 MP, per esempio 1024×1024, 1344×768 (16:9), 1216×832 (3:2). I lati vanno tenuti
  multipli di 64 per SDXL e di 16 per gli altri.
- Per i formati di tavola (A1, A3): genera a risoluzione nativa e poi fai l'upscaling, mai il contrario.

## Quantizzazioni: regola pratica
BF16 > FP8 ≈ GGUF Q8 > Q6 > Q5_K_M > Q4_K_M (minimo consigliato per i render finali) > Q3/Q2 (solo per test).
Le linee sottili come serramenti e ringhiere degradano per prime con le quantizzazioni aggressive.
