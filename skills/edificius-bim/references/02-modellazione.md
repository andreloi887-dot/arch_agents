# Modellazione

## Punti di partenza
- Da zero in pianta o direttamente in 3D; da **DWG/DXF** con riconoscimento automatico (muri,
  pilastri, scale, solette) dopo pulizia in Edificius-CAD; da **IFC** di altri software; da **nuvola di
  punti** (ambiente Nuvole di punti: allinea la nuvola a X/Y, definisci i piani col *Manager SdRA*,
  sezioni orizzontali per piano, poi modella con gli snap sulla nuvola).

## Muri
- Inserimento per linea d'asse o filo (interno/esterno): scegli il riferimento coerente con la quota
  di progetto (di solito filo esterno grezzo per involucro).
- Altezza vincolata a piano superiore (+/- offset) anziché valore fisso.
- Incroci: controlla le giunzioni a T e L; stratigrafie diverse richiedono attenzione alle priorità
  degli strati (isolante continuo, cappotto che gira l'angolo).
- Muri curvi/inclinati: verificane l'impatto su computo e abachi.

## Solai e pavimenti
- Separa elemento strutturale (solaio) e finiture (pavimento/massetto) se serve computarli a parte o
  passarli a EdiLus/TerMus con ruoli diversi.
- Contorno per selezione dei muri o per disegno; aperture (cavedi, scale) come fori, non come buchi
  disegnati in 2D.

## Coperture
- Falde da contorno con pendenza (%, °) e sporti; per tetti complessi lavora falda per falda e poi
  tagli muri sotto la copertura (funzione di adattamento muri alla falda).
- Lucernari e abbaini come oggetti dedicati, non come fori generici.

## Scale e rampe
- Usa gli oggetti scala parametrici (rampe, pianerottoli, alzata/pedata): verifica 2a+p ≈ 62–64 cm e
  i limiti normativi locali. Foro nel solaio collegato alla scala.

## Infissi
- Da libreria parametrica: dimensioni luce netta vs vano, davanzale, controtelaio, verso apertura.
  I dati termici (Uw) servono a TerMus: compilali.

## Stratigrafie
Nell'ultima release le stratigrafie hanno una **nuova gestione e rappresentazione 3D**: controlla in 3D
continuità dell'isolante, risvolti e attacchi prima di passare a TerMus. Nomi parlanti e materiali con
dati termici e acustici (servono anche a SuoNus).

## Oggetti BIM e librerie
- Usa gli oggetti della libreria ACCA/usBIM o i BIM object dei produttori (spesso IFC). Controlla
  peso poligonale: mobili e sanitari pesanti rallentano viste e render.
- Oggetti personalizzati: modellali come solidi/oggetti generici e assegna classe IFC e proprietà;
  per forme complesse usa SketchUp, Blender o Rhino/Grasshopper in integrazione dinamica.
- Catalogo online gratuito (texture HD, blocchi CAD, modelli 3D di produttori); file di libreria **BOL**.

## Impianti (Edificius-MEP)
Modellatore "Smart MEP" in pianta, sezione o 3D con porte di connessione che adattano diametri e
raccordi; LOD progressivo (oggetto parametrico → oggetto commerciale). Gli oggetti architettonici
(sanitari, cucine, radiatori) possono diventare oggetti MEP. Calcolo e dimensionamento con i tool usMEP.

## HBIM
Ambiente dedicato agli edifici storici (con AmiCus): parti dalla nuvola di punti e modella elementi
irregolari come oggetti generici con proprietà, non forzarli in muri standard.

## Terreno ed esterni
- Terreno da curve/punti o da rilievo; scavi e riporti per computo. *Edificius-LAND* (modulo)
  per sistemazioni esterne, verde, percorsi, recinzioni.
