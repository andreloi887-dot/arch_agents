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

## SketchUp Pro 2025

| Percorso | Cosa è |
|---|---|
| `skills/sketchup-pro-2025/` | Skill (SKILL.md + knowledge base in `references/`: novità e migrazione dalla 2022, setup, modellazione, organizzazione, LayOut, interoperabilità, estensioni/Ruby, troubleshooting, ricette, visualizzazione photoreal) |
| `.claude/agents/sketchup-expert.md` | Subagent per Claude Code che usa la stessa knowledge base |

Uso identico a Lumion: zip di `skills/sketchup-pro-2025/` su claude.ai (sostituisce la vecchia
skill 2022, da rimuovere), oppure "usa l'agente sketchup-expert per …" in Claude Code. Gli snippet
Ruby sono per Ruby 3.2 (SketchUp 2024+): provali prima su una copia del file.

Le voci segnate *(da verificare)* non sono confermate dalle release notes ufficiali: controllale
in-app e correggi i file quando le verifichi.
