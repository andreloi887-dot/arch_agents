# Render e output

## Photo mode
- Salva fino a molte inquadrature per pagina (slot camere): ogni foto ha stack effetti proprio o condiviso (copia/incolla).
- *Render › Photo*: risoluzioni Email (1280×720), Desktop (1920×1080), Print (3840×2160), Poster (7680×4320, Pro). Il poster quadruplica tempi e VRAM.
- Stelle qualità: render finale sempre a qualità massima; test a 1–2 stelle.
- *Render passes*: depth map, normal, sky alpha, material ID, lighting/reflection → compositing.

## Movie mode
- Clip con keyframe camera (aggiungi 4–8 keyframe, movimenti lenti e lineari: evita oscillazioni). Durata clip regolabile; *Smoothness* per curve.
- Effetti animati per clip: *Move* (oggetti), *Animated phasing* (costruzione progressiva per layer/ordine), *Layer visibility*, *Sun/time of day* animato, *Advanced move*.
- Output: 720p/1080p/4K; frame rate 25/30 fps (60 fps solo se richiesto). **Image sequence** consigliato per render lunghi: se crasha, riprendi dal frame.
- Montaggio: render a clip singole, monta in Premiere/DaVinci.

## 360 Panorama
- Panorama equirettangolare o stereo per VR/web viewer. Posiziona la camera a ~1.6 m (altezza occhi), *Two-point perspective* non applicabile.
- Condivisione via **MyLumion** (servizio web Lumion; verificare disponibilità attuale per la 12.5).

## Batch / tempi
- Lumion non ha una vera coda di rete: per notti di render metti tutte le foto in una pagina e lancia *Render all*.
- Disabilita screensaver/sospensione Windows e aggiornamenti GPU durante render lunghi.

## Specifiche consigliate
| Uso | Risoluzione | Note |
|---|---|---|
| Concorso/tavola A1 | 7680×4320 o 3840 + upscaling | Poster solo se VRAM ≥ 11 GB |
| Social/web | 1920×1080 / 1080×1350 | Crop in post |
| Video presentazione | 1920×1080, 30 fps | 4K solo se necessario |
| VR | 360 stereo 4K+ | Evita oggetti troppo vicini alla camera |
