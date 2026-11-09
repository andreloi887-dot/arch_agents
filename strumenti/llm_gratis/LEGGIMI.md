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

**Scadenze.** La chiave NVIDIA vale 12 mesi dalla creazione: quella attuale scade intorno al 9 nov 2027.
Quando scade, lo script lo segnala con "chiave non valida o scaduta". Va rigenerata su build.nvidia.com e
salvata di nuovo, nel cloud come segreto dell'ambiente "Agenti" e sul PC in `.env`.

## Livelli

| Livello | A cosa serve | Primo candidato |
|---|---|---|
| `semplice` | tradurre, normalizzare, classificare righe brevi | Groq gpt-oss-20b |
| `medio` | traduzioni e normalizzazioni più lunghe o con contesto, estrazione strutturata da testi non tecnici | Groq gpt-oss-120b |
| `complesso` | testi lunghi da tradurre o normalizzare, quando i volumi non giustificano Claude | NVIDIA Nemotron 3 Ultra |
| `visione` | descrivere immagini (si attiva da solo con `--immagine`) | Gemini 3.5 Flash |

Se un candidato manca di chiave, ha superato il limite o è stato ritirato, lo script passa al successivo.
Su stderr scrive quale modello ha risposto.

## Nelle sessioni cloud di Claude Code

Nel cloud le chiavi non stanno in `.env`: sono segreti di rete dell'ambiente, che il proxy aggiunge alle richieste.
Lo script se ne accorge da solo (variabile `CLAUDE_CODE_REMOTE`) e manda un segnaposto al posto della chiave.
Per collegare un nuovo provider basta chiedere a Claude di salvarne la chiave: salvarla abilita anche il sito.
I provider senza segreto vengono saltati e lo script dice perché.

Nel cloud c'è anche un limite di circa 30 secondi per risposta. I modelli che ragionano a lungo, come
`gemini-flash-latest` e `gemini-3.8-flash`, lo superano e danno errore 502. Per questo il catalogo usa `gemini-3.5-flash`.

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
- **Solo traduzioni, normalizzazioni e descrizioni di immagini.** Niente contenuti tecnici: nella prova del
  2026-11-09 il livello medio ha sbagliato due risposte tecniche su due (vedi [CLAUDE.md](../../CLAUDE.md)).
- **Risposte troncate.** Se la risposta raggiunge `--max-token`, lo script lo segnala su stderr. Con Gemini il
  limite conta anche il ragionamento interno: un valore basso (es. 400) lascia poche parole. Meglio toglierlo.
- **Catalogo.** Modelli e limiti cambiano ogni settimana. Lancia `--stato` di tanto in tanto e aggiorna
  `modelli.json` guardando il README del repo originale.
- **Claude Code con modelli gratuiti.** È sconsigliato come motore principale: servono un proxy (LiteLLM o
  claude-code-router) oppure OpenRouter (`ANTHROPIC_BASE_URL=https://openrouter.ai/api`), e l'uso dei tool
  degrada molto.
