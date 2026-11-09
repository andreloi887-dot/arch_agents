# llm_gratis: modelli gratuiti per i lavori di massa

È il **livello 0** della scelta del modello descritta in [CLAUDE.md](../../CLAUDE.md). Claude lo usa da solo
quando un compito è ripetitivo, voluminoso e non riservato. Lo puoi usare anche tu da terminale.

Il catalogo dei provider viene da [awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis)
(stato dell'8 nov 2026). Tre correzioni rispetto al repo originale:
- la base URL di Gemini è sbagliata (punta ad Aion Labs);
- molti "Model ID" sono in realtà gli slug del sito;
- le istruzioni per Claude Code mandano un client Anthropic a endpoint OpenAI, quindi non funzionano.

## Installazione

Serve Python 3.9 o successivo. Non ci sono dipendenze.

1. Crea almeno una o due chiavi gratuite. Bastano email e nessuna carta:
   - **Groq**: https://console.groq.com/keys. Molto veloce, per i livelli semplice e medio.
   - **Gemini**: https://aistudio.google.com/app/apikey. Contesto da 1M token, unico affidabile per le immagini.
   - Facoltative:
     - NVIDIA NIM (https://build.nvidia.com/settings/api-keys, chiede verifica del telefono): i modelli più forti per il livello complesso;
     - Mistral, OpenRouter, Cerebras.
2. Copia `.env.esempio` in `.env` (cartella ignorata da git) e incolla le chiavi.
3. Verifica:
   ```bash
   python strumenti/llm_gratis/llm_gratis.py --stato
   ```
   Il comando mostra quali chiavi funzionano. Per ogni modello del catalogo segna `ok` se esiste ancora presso il provider e `??` se è stato ritirato: in quel caso va corretto `modelli.json`.

## Livelli

| Livello | A cosa serve | Primo candidato |
|---|---|---|
| `semplice` | tradurre, normalizzare, classificare righe brevi | Groq Llama 3.1 8B |
| `medio` | riassunti, bozze di testo, estrazione strutturata | Groq gpt-oss-120b |
| `complesso` | testi lunghi e ragionati, quando i volumi non giustificano Claude | NVIDIA GLM-5.2 |
| `visione` | descrivere immagini (si attiva da solo con `--immagine`) | Gemini Flash |

Se un candidato manca di chiave, ha superato il limite o è stato ritirato, lo script passa al successivo.
Su stderr scrive quale modello ha risposto.

## Uso

```bash
python strumenti/llm_gratis/llm_gratis.py --livello semplice "Traduci in inglese: intonaco a calce"
```

```bash
python strumenti/llm_gratis/llm_gratis.py --immagine foto.jpg "Elenca materiali e colori della facciata"
```

```bash
python strumenti/llm_gratis/llm_gratis.py --livello semplice --per-riga materiali.txt --sistema "Normalizza il nome del materiale, una riga" > materiali.jsonl
```

## Limiti, da rispettare

- **Riservatezza.** I piani gratuiti possono usare i dati per l'addestramento. Quindi niente dati di clienti,
  nominativi catastali, email o codice con chiavi.
- **Affidabilità.** Questi modelli sbagliano più spesso di Claude. L'uscita va verificata prima che entri nel progetto.
- **Catalogo.** Modelli e limiti cambiano ogni settimana. Lancia `--stato` di tanto in tanto e aggiorna
  `modelli.json` guardando il README del repo originale.
- **Claude Code con modelli gratuiti.** È sconsigliato come motore principale: servono un proxy (LiteLLM o
  claude-code-router) oppure OpenRouter (`ANTHROPIC_BASE_URL=https://openrouter.ai/api`), e l'uso dei tool
  degrada molto.
