# Prestazioni e troubleshooting

## Hardware (indicativo per Lumion 12.x – verificare la pagina ufficiale dei requisiti)
- Solo Windows 10/11 64-bit (Mac non supportato, se non via Boot Camp/PC remoto).
- GPU è il fattore dominante: VRAM ≥ 8 GB minimo pratico, 11–24 GB per scene grandi e risoluzioni Poster. NVIDIA RTX serie 30/40 ottime.
- RAM 32 GB consigliati, SSD NVMe per progetto e libreria.
- Driver GPU: versione *Studio* stabile; evitare driver beta.

## Ottimizzazione scena
- Qualità editor F1–F2 mentre lavori, layer pesanti nascosti.
- Erba 3D e Mass placement di alberi = principali killer di FPS: limitali al campo visivo.
- Modelli importati: dividi in più file (edificio, arredi, contesto) per update rapidi.
- Texture importate > 4K: riduci a 2K se non in primo piano.
- Planar reflection e luci con ombre: solo dove servono.

## Problemi frequenti
| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| Superfici nere/mancanti | Normali invertite | Correggi nel CAD o *Two-sided* nel materiale |
| Sfarfallio superfici | Z-fighting | Elimina facce duplicate / sposta di qualche mm |
| Luce che filtra negli angoli interni | Geometria non chiusa, muri senza spessore | Chiudi spigoli, dai spessore; *Shadow › Omni shading* / *Interior* |
| Modello lontano o enorme | Unità/origine errate | Riesporta in metri vicino all'origine |
| Texture stirate | UV assenti | Nel materiale cambia mapping (Box), o UV nel CAD |
| Crash al render Poster/4K | VRAM esaurita | Riduci risoluzione, erba, riflessi; chiudi altre app GPU |
| "Your graphics card doesn't have enough memory" | VRAM | Come sopra; render a 3840 e upscaling |
| LiveSync non si connette | Versioni plugin/Lumion incompatibili, firewall | Reinstalla plugin corretto per 12.5, avvia Lumion prima del CAD |
| Update model perde materiali | Nomi materiali sorgente cambiati | Mantieni nomi; usa *Save/Load materials* |
| Video con sfarfallio | Shadow range/qualità bassa, motion blur | Aumenta qualità ombre, render image sequence |
| File .ls12 non si apre in altra versione | Salvato in 12.5 | Apertura solo in 12.5 o successive |

## Diagnostica
- Log e file utente: `Documenti/Lumion 12.5/` (Library, Import, Exports).
- In caso di crash ricorrenti: test con progetto vuoto → se ok, il problema è un oggetto/modello: reimporta per parti per isolarlo.
