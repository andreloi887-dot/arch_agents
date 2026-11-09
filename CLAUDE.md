# Istruzioni per Claude in questo repository

Rispondi in italiano. Procedimento di progetto: [PROCEDIMENTO.md](PROCEDIMENTO.md).

## Scelta del modello in base al compito

Andrea ha chiesto che sia Claude a scegliere il modello giusto per ogni compito. Questa sezione è
l'autorizzazione permanente a delegare ai subagent e ai modelli gratuiti secondo le regole sotto.
Non serve chiedere conferma caso per caso. Nella risposta va detto in una riga quale livello si è usato e perché.

### Come decidere

Valuta tre cose: quanto ragionamento serve, quanto costa un errore, quanti dati ci sono da elaborare.
**Se il dubbio è tra due livelli, scegli quello più alto.** Un errore in una fase della filiera costa
più del risparmio.

| Livello | Modello | Quando | Esempi in questo repo |
|---|---|---|---|
| **0 – gratuito esterno** | `strumenti/llm_gratis/` (Groq, Gemini, NVIDIA, Mistral, OpenRouter, Cerebras) | Lavori **di massa, ripetitivi e non riservati**, quando i volumi rendono Claude sprecato. L'uscita la controlla sempre Claude | tradurre o normalizzare centinaia di nomi di materiali, didascalie di foto di rilievo, prime classificazioni di elenchi OSM, bozze di testi descrittivi generici |
| **1 – Haiku** | subagent con `model: "haiku"` | Ricerche e letture meccaniche con regole chiare, nessuna decisione di progetto | trovare file e chiamate, estrarre valori da JSON/IFC, controllare formati, riassumere un log, rinominare in serie |
| **2 – Sonnet** | subagent con `model: "sonnet"` | Lavoro standard ben definito | domande alle knowledge base (Lumion, SketchUp, Comfy), script Python e Blender con specifica chiara, editing di testi, sintesi di ricerche web |
| **3 – Opus** | sessione principale, o subagent con `model: "opus"` | Ragionamento difficile, ambiguità, decisioni che vincolano le fasi successive | architettura del motore di contesto, georeferenziazione e punto base, debug difficili, revisione del codice, verifica di rilievi, scelte di filiera, testi a nome di Andrea verso terzi |

Regole pratiche:
- **Compiti piccoli: falli direttamente.** Avviare un subagent ha un costo fisso, perché parte senza contesto.
  Delega quando il compito è lungo, separabile o ripetuto molte volte.
- **Gli agenti del repo** (`.claude/agents/`) hanno un modello predefinito. Il parametro `model` della
  chiamata lo sostituisce: alza il livello quando la domanda va oltre la consultazione.
  - `lumion-expert`, `sketchup-expert`, `comfy-render-expert`: predefinito `sonnet`; `opus` per diagnosi difficili
    o critiche di render.
  - `rilievo-urbano`: eredita il modello della sessione (lavoro su immagini, misure e verifiche).
- **Il modello della sessione principale non si cambia da solo**: lo sceglie Andrea con `/model`. Se un compito
  è chiaramente sotto o sopra il livello della sessione, delega oppure segnalalo.
- **Livello 0: limiti rigidi.**
  - **Mai** dati di clienti, dati personali, documenti catastali nominativi, email, codice con chiavi o
    password: i piani gratuiti possono usare i dati per l'addestramento.
  - **Mai** come unica fonte di una decisione o di un numero che entra nel progetto.
  - Se manca la chiave o tutti i provider sono esauriti, si ripiega su Haiku e lo si dice.
  - Uso e regole del livello per complessità: [strumenti/llm_gratis/LEGGIMI.md](strumenti/llm_gratis/LEGGIMI.md).
