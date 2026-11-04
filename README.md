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

## SketchUp Pro 2022

| Percorso | Cosa è |
|---|---|
| `skills/sketchup-pro-2022/` | Skill (SKILL.md + knowledge base in `references/`: setup, modellazione, organizzazione, LayOut, interoperabilità, estensioni/Ruby, troubleshooting, ricette) |
| `.claude/agents/sketchup-expert.md` | Subagent per Claude Code che usa la stessa knowledge base |

Uso identico a Lumion: zip di `skills/sketchup-pro-2022/` su claude.ai, oppure "usa l'agente
sketchup-expert per …" in Claude Code. Gli snippet Ruby in `references/06-estensioni-ruby.md`
sono per Ruby 2.7 (SketchUp 2022): provali prima su una copia del file.
