# Render e realtà virtuale (fonte: acca.it, novembre 2026)

## Motori disponibili
| Strumento | Cosa è | Note |
|---|---|---|
| Render integrato | AMD Radeon ProRender (ray tracing) + denoiser ML, materiali PBR, IBL | Incluso |
| **RTBIM** | Real-time su **Unreal Engine 5 con Lumen**: GI dinamica, ray/path tracing DXR | Abbonamento opzionale |
| **AIrBIM** | Render fotorealistico con AI | Non compatibile con GPU Intel ARC |
| **usBIM.codesign AI** | Plug-in AI: concept, varianti di stile, virtual staging | A crediti |
| **VRiBIM** | VR immersiva con modifica real-time del modello | Abbonamento opzionale |
| BIM Video Studio | Montaggio su timeline di render, viste, tavole, camere | Video legati al modello |
| Fotoinserimento | Prospettiva da foto, linee di fuga, ombre, fotoritocco | Incluso |

## RTBIM: flusso consigliato
Ubicazione e nord → materiali PBR (texture in scala reale) → contesto e vegetazione animata → meteo
dinamico (nuvole, pioggia, sole) → luci artificiali → camere → anteprima Lumen → still in path tracing →
video / 360°. Usa il real-time per decidere camera e luce, il path tracing solo per l'output finale.

## AI (AIrBIM / codesign)
Ottimo per concept, interior styling e varianti per il committente. Controlla sempre che l'AI non
aggiunga o modifichi elementi architettonici o dimensioni: non è una rappresentazione di progetto
vincolante. Etichetta come "immagine indicativa" nelle pratiche.

## Requisiti GPU (pagina requisiti ACCA, versione usBIM(s))
| Scena | Edificius base | RTBIM / AIrBIM | RAM |
|---|---|---|---|
| Semplice | ≥4.000 PassMark, 4 GB | ≥8.000 PassMark, 6 GB (RTX 2060, Radeon Pro W6600) | 8 GB |
| Media | ≥8.000, 8 GB | ≥12.000, 12 GB (RTX 3070, RX 6700 XT) | 16 GB |
| Complessa | ≥15.000, 12 GB | ≥20.000, 16 GB (RTX 4070, RX 7800 XT) | 32 GB |
- Path tracing UE5: Windows 10+, ≥6 GB VRAM e ≥10.000 PassMark; consigliati >8 GB e DXR/DirectX 12
  (NVIDIA RTX, AMD RX 6000+).
- Schermo 1920×1080 a **DPI 100%**: scalature diverse causano problemi di interfaccia.

## VRiBIM
GPU consigliata RTX 3070 / RX 6700 o superiore, 16 GB RAM, DisplayPort 1.2+ o HDMI 1.4+. Visori:
Meta Quest 2/3 (consigliato Link cable), HTC Vive Pro / Pro 2 / Cosmos, Pico 4; Oculus Rift/Rift S
obsoleti.
