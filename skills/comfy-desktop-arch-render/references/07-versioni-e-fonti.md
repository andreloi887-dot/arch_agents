# Versioni, date e fonti

Ultima revisione: **4 novembre 2026.** Fonti consultate tramite ricerca web; le docs ufficiali
(`docs.comfy.org`) non erano raggiungibili direttamente da questo ambiente al momento della stesura, quindi i
punti segnati "da verificare" vanno controllati lì.

## Date chiave
- 28/05/2026: Legacy Comfy Desktop v0.9.4, ultima versione; repository archiviato.
- 08/06/2026: annuncio del nuovo Comfy Desktop (multi-istanza, snapshot e rollback, aggiornamenti del core
  in giornata).
- 20/09/2026: Qwen-Image 2.1 (Hugging Face, ModelScope, GitHub), supporto nativo in ComfyUI dal primo giorno.
- 28/09/2026: Qwen-Image 2.1 Fun ControlNet Union integrato nel core.
- Qwen-Image-Edit-2509 e 2511: fine 2025. Z-Image Turbo e Fun ControlNet Union: dicembre 2025.

## Punti da verificare
- Licenze di Qwen-Image 2.1 (Research License), Z-Image e FLUX.2 Klein: controlla il LICENSE ufficiale.
- Supporto degli snapshot sulle installazioni "tracked" (le fonti sono in conflitto; quella ufficiale dice
  "non supportato").
- Migrazione Legacy in-place o per copia (PR docs #1899).
- Lettura di `extra_models_config.yaml` nel nuovo Desktop.
- Supporto Linux del nuovo Desktop.

## Fonti
- Docs Comfy Desktop: https://docs.comfy.org/installation/desktop/overview ·
  FAQ: https://docs.comfy.org/installation/desktop/faq ·
  Istanze: https://docs.comfy.org/installation/desktop/usage/instance-management ·
  Migrazione: https://docs.comfy.org/installation/desktop/usage/migrate
- Annuncio: https://x.com/ComfyUI/status/2064093003590111314
- Repository: https://github.com/Comfy-Org/Comfy-Desktop · PR docs migrazione: https://github.com/Comfy-Org/docs/pull/1899
- Issue sui percorsi extra: https://github.com/Comfy-Org/desktop/issues/1736
- Requisiti di sistema: https://docs.comfy.org/installation/system_requirements
- Qwen-Image-Edit-2511: https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511 ·
  Lightning: https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning
- Qwen-Image 2.1: https://github.com/QwenLM/Qwen-Image-2.1 · https://blog.comfy.org/p/qwen-image-21-in-comfyui-open-weight ·
  Union: https://comfyui-wiki.com/en/news/2026-09-24-qwen-image-2-1-fun-controlnet-union
- Qwen ControlNet/DiffSynth: https://blog.comfy.org/p/comfyui-now-supports-qwen-image-controlnet
- Z-Image Turbo Union: https://comfy.org/templates/image_z_image_turbo_fun_union_controlnet
- FLUX.2 dev: https://huggingface.co/black-forest-labs/FLUX.2-dev
- SeedVR2: https://docs.comfy.org/tutorials/utility/seedvr2
- Pipeline per architetti (blog commerciale, da leggere criticamente):
  https://archigenai.com/qwen-flux-zimage-comfyui-architecture-render-2026.html
