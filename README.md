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
Contenuti scritti da conoscenza generale di Lumion 12/12.5: scorciatoie e alcune voci di menu vanno
verificate in-app. Aggiorna i file `references/` con le tue preferenze e i tuoi preset di studio.
