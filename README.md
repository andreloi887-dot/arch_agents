# arch_agents

Agenti e skill per software di architettura.

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
