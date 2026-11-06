# arch_agents

Agenti e skill per software di architettura.

**Procedimento di riferimento per i progetti:** [PROCEDIMENTO.md](PROCEDIMENTO.md).
La filiera è Edificius → contesto in Python → Blender → Unreal Engine 5 → FFmpeg, ed è valida per ogni lotto.

## Lumion Pro 12.5

| Percorso | Cosa è |
|---|---|
| `skills/lumion-pro-12-5/` | Skill (SKILL.md + knowledge base in `references/`), caricabile su claude.ai come skill personale (zip della cartella) |
| `.claude/agents/lumion-expert.md` | Subagent per Claude Code che usa la stessa knowledge base |

### Uso
- **claude.ai / app**: comprimi `skills/lumion-pro-12-5/` in zip e caricalo in *Impostazioni › Capacità › Skill*.
- **Claude Code**: apri il repo e chiedi "usa l'agente lumion-expert per …", oppure copia la cartella skill in `~/.claude/skills/`.

### Note sull'accuratezza
Contenuti verificati sulla Lumion Knowledge Base ufficiale (circa 320 articoli consultati, nov 2026; fonti in
`references/08-versioni-e-fonti.md`). I video tutorial sono indicizzati ma non trascritti. Aggiungi i tuoi preset di studio in `07-ricette.md`.

## SketchUp Pro 2022

| Percorso | Cosa è |
|---|---|
| `skills/sketchup-pro-2022/` | Skill (SKILL.md + knowledge base in `references/`: setup, modellazione, organizzazione, LayOut, interoperabilità, estensioni/Ruby, troubleshooting, ricette) |
| `.claude/agents/sketchup-expert.md` | Subagent per Claude Code che usa la stessa knowledge base |

Uso identico a Lumion: zip di `skills/sketchup-pro-2022/` su claude.ai, oppure "usa l'agente
sketchup-expert per …" in Claude Code. Gli snippet Ruby in `references/06-estensioni-ruby.md`
sono per Ruby 2.7 (SketchUp 2022): provali prima su una copia del file.

## Rilievo urbano (Google Maps / Street View / Earth → SketchUp)

| Percorso | Cosa è |
|---|---|
| `skills/rilievo-urbano/` | Skill: protocollo di rilievo, scheda (MD + JSON), materiali e colori, verifica, contratto con SketchUp |
| `skills/rilievo-urbano/scripts/` | `gmaps.py` (Street View, Maps Static, Geocoding, OSM), `annota.py` (mappe e foto annotate, palette, campionamento colore), `confronta.py` (verifica automatica + affiancamenti) |
| `skills/rilievo-urbano/scripts/sketchup/` | Ruby per SketchUp 2022: scene con camera uguale a Street View, inventario del modello |
| `.claude/agents/rilievo-urbano.md` | Subagent DESCRIVI / VERIFICA |

### Flusso in Claude Code
1. *"Usa rilievo-urbano per descrivere l'isolato tra via X e via Y, LOD2, viste da via X"* → pacchetto `zona-<nome>/`.
2. *"Passa la scheda a sketchup-expert"* → procedura di modellazione + script da lanciare in SketchUp.
3. *"Usa rilievo-urbano per verificare"* con `inventario.json` ed `export_verifica/` → verbale con correzioni (max 3 cicli).

Requisiti: Python 3.9+ con Pillow (per `catasto.py` anche numpy e `opencv-python-headless`); `GOOGLE_MAPS_API_KEY` con Street View Static, Maps Static e
Geocoding abilitate (senza chiave l'agente lavora su screenshot e il confronto è solo qualitativo).
I termini Google vietano di ricalcare o estrarre geometria: impronte e quote vengono da OSM, DBT,
catasto o LiDAR; le immagini Google restano in `_rif_google/` (ignorata da git).

## Comfy Desktop – render AI architettonici

| Percorso | Cosa è |
|---|---|
| `skills/comfy-desktop-arch-render/` | Skill (SKILL.md + knowledge base in `references/`): setup Comfy Desktop, modelli e licenze, input dal 3D, pipeline, ricette, troubleshooting |
| `.claude/agents/comfy-render-expert.md` | Subagent per Claude Code che usa la stessa knowledge base |

Uso identico alla skill Lumion (zip della cartella su claude.ai, oppure "usa l'agente comfy-render-expert per …").
Le due skill si parlano: i render pass di Lumion Pro (depth, Material ID, sky alpha) sono l'input ideale per ComfyUI.

### Note sull'accuratezza
Stato a nov 2026, da ricerca web; le docs ufficiali `docs.comfy.org` non erano raggiungibili dall'ambiente di stesura.
I punti incerti sono elencati in `references/07-versioni-e-fonti.md`. I valori nelle ricette sono d'esperienza: sostituiscili
con i tuoi preset testati.
