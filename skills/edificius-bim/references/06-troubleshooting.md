# Troubleshooting

| Sintomo | Causa probabile | Fix |
|---|---|---|
| Muri che non si uniscono / giunti sporchi | Riferimenti (asse/filo) diversi, estremi non coincidenti | Riallinea, usa i comandi di giunzione, controlla snap |
| Muri che bucano la copertura | Altezza fissa, non adattata alla falda | Comando di adattamento muri alla copertura; vincola al piano |
| Superfici locali errate | Locali non chiusi o muri con altezze diverse | Chiudi i contorni, rigenera i locali |
| Computo/abachi incoerenti | Stili senza stratigrafia, oggetti duplicati | Pulisci duplicati, compila gli stili |
| IFC "vuoto" di dati nel software ricevente | Oggetti generici, Pset mancanti, MVD sbagliata | Riclassifica, compila proprietà, riesporta |
| DWG importato lontano/illeggibile | Coordinate geografiche lontane dall'origine | Sposta su origine locale nel CAD prima dell'import |
| Lentezza viste | Oggetti pesanti, DWG grandi, troppe viste 3D aperte | Alleggerisci, disattiva layer, chiudi viste |
| Render nero / crash RTBIM | Driver GPU, GPU sotto requisiti | Aggiorna driver, verifica requisiti (05-render-vr.md), riduci qualità |
| AIrBIM non parte | GPU Intel ARC | Non supportata: usa RTBIM o usBIM.codesign AI |
| Interfaccia sfocata o tagliata | Scala di Windows ≠ 100% | Imposta DPI 100% (requisito ACCA) |
| Non riesco a modificare in collaborativo | Semaforo giallo (operazione esclusiva) o rosso | Attendi o coordina chi tiene l'editor |
| MEP/HBIM/Nuvole di punti assenti | AmiCus non attivo | Rinnova AmiCus |
| Export FBX mancante | Non previsto | Usa DAE, OBJ o SKP |
| Su Mac la chiave USB non funziona | Dispositivo non associato alla VM | Associa la chiave a Windows a ogni avvio; su Mac ARM servono driver e chiave recenti |

Per bug persistenti: aggiornamento all'ultima build (AmiCus), assistente **Sibilla**, Smart Support
(assistenza in remoto), forum ACCA.
