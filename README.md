# Berserk Color Archive

Archivio personale locale delle illustrazioni raccolte da Fr0stiFusionZ. La cartella era vuota all’inizio del lavoro: questa è una nuova implementazione statica, senza dipendenze di esecuzione, account, analytics o servizi esterni.

## Aprire la galleria

La versione compatta completa del sito è in **`dist/`**: apri `dist/index.html`. Il file `index.html` nella radice serve anche come anteprima di sviluppo. Puoi usare `Apri-archivio.cmd`. Il sito è progettato per funzionare senza connessione e senza server: usa script e immagini locali, senza fetch. Il funzionamento nel browser è stato verificato tramite un server temporaneo su loopback; l’automazione del browser non consente di verificare URL file direttamente. Per una verifica facoltativa con HTTP: `python -m http.server 8765 --bind 127.0.0.1`, poi apri `http://127.0.0.1:8765`; interrompi con Ctrl+C.

Il segnalibro iniziale è **Non ho ancora iniziato**. Ogni nuovo lettore parte da zero; il suo progresso viene salvato solo sul suo browser. Per riprendere la lettura di Daniele, seleziona **Collection 5 · L’età dell’oro (8), REVENGE 16**: gli episodi 001 e successivi dello stesso volume rimangono futuri. Le immagini non sono inserite nel documento finché non premi “Mostra”. Per i capitoli futuri e tutti gli extra serve anche la conferma spoiler. Il viewer integrato permette di passare tra le tavole dello stesso capitolo con i pulsanti o le frecce della tastiera; non passa automaticamente al capitolo successivo. Esc chiude il viewer. Le aperture non persistono; il segnalibro sì, quando il browser consente localStorage. Su file locali il comportamento di localStorage può dipendere dal browser.

La protezione riguarda la galleria, non l’accesso diretto a cartelle, cataloghi e file. Questi contengono nomi e riferimenti completi. Gli extra non vengono dichiarati sicuri in base alla sola data.

## Contenuto e fonti

- [Frosti’s Berserk Art Gallery](https://jojowiki.com/User:Fr0stiFusionZ/Berserk_Art_Gallery): illustrazioni e scansioni cronologiche, incluse quelle di altre opere in una sezione separata.
- [Berserk Gallery](https://jojowiki.com/User:Fr0stiFusionZ/Berserk_Gallery): copertine, note dell’autore, artbook e materiali supplementari.
- [Indice SkullKnight](https://www.skullknight.net/encyclopedia/merchandise/manga/index.html): corrispondenza episodi/volumi e numerazione originale REVENGE.
- [Indice Berserk Wiki](https://berserk.fandom.com/wiki/Releases_(Manga)): volume 43, episodi 374–382. Materiali successivi rimangono senza un volume assegnato; episodio 83 escluso dai tankobon.

La Collection segue i singoli tankobon. Non va confusa con Maximum, Deluxe o con i numeri del vecchio periodico italiano. La numerazione REVENGE dei primi fascicoli non coincide sempre con la numerazione moderna dei capitoli: alcuni episodi erano divisi in più uscite. Le etichette originali sono conservate per rendere il confronto verificabile.

Sono inclusi i file delle due gallerie indicate, comprese varianti editoriali, scansioni di origine e immagini nelle schede degli artbook. Le gallerie autonome TCG e Tribute non vengono percorse. Le icone dell’interfaccia di JoJo Wiki sono escluse. Il numero di file non coincide con il numero di opere uniche: varianti e riproduzioni editoriali distinte sono mantenute.

## Originali e metadati

`assets/originals/chapters/volume-NN/…` contiene le immagini inizialmente incontrate nelle tavole dei capitoli; `assets/originals/extras/ANNO/…` gli altri originali. Un’immagine condivisa da più sezioni viene salvata una volta sola e referenziata dal catalogo; il percorso indica la prima occorrenza, non limita i suoi usi.

Ogni immagine originale ha un file `.json` adiacente con URL originale, pagina del file, fonti delle occorrenze, attribuzione, dimensioni, formato, byte, SHA-256 e data del download. `data/catalog.json` conserva tutto; `data/site-catalog.js` contiene i dati selezionati necessari all’app, in modo da funzionare anche da file locale senza fetch. Le copie HTML consultate e robots.txt sono in `data/sources/`.

I percorsi originali sono derivati dalle miniature MediaWiki rimuovendo `/thumb/` e l’ultimo segmento della miniatura. Sono stati confrontati campioni con il collegamento “Original file”. Tutte le varianti vengono mantenute nell’archivio originale alla risoluzione del relativo upload, senza alterare i byte. **Il sito compatto usa copie WebP di qualità 88, lato lungo massimo 3200 px**, sufficienti per la consultazione nel viewer; non sono sostituti dei master. Non viene applicato alcun ingrandimento. I link alle fonti consentono di raggiungere gli originali in piena risoluzione e le versioni alternative. Non si presume l’esistenza di scansioni migliori su altri siti.

Le date della fonte sono mantenute, inclusi eventuali errori editoriali; quelle approssimative sono marcate. Per un materiale supplementare privo di data, si usa la stessa immagine nella galleria cronologica oppure la data documentata di pubblicazione della raccolta, dichiarandolo nei metadati. Negli altri casi resta “Data non documentata”.

## Download e verifica

Il peso effettivo e il numero delle tavole del sito compatto sono in `reports/site-package.json`; le scelte automatiche per tavola sono in `reports/selection-audit.json`. I risultati numerici finali e i file mancanti sono in `reports/SUMMARY.md`, `reports/download-report.json` e `reports/image-inventory.csv`.

L’importatore usa un identificativo esplicito, controlla robots.txt, effettua richieste sequenziali con intervallo minimo di un secondo (o il Crawl-delay maggiore), rispetta Retry-After e non accede agli endpoint vietati. I file già scaricati vengono mantenuti alla ripresa. I quattro riferimenti rossi della fonte non vengono trasformati in richieste alle pagine di upload.

Per riprendere un download dal catalogo esistente, in PowerShell nella cartella del progetto:

```powershell
.\.venv\Scripts\python scripts\import_archive.py
.\.venv\Scripts\python scripts\finalize_catalog.py
.\.venv\Scripts\python scripts\build_site.py
```

Se manca l’ambiente di importazione:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

`--build` ricostruisce il catalogo dalle copie HTML locali e riutilizza i file scaricati. Non aggiorna automaticamente le fonti online e non va eseguito contemporaneamente al downloader. Al termine esegui sempre `finalize_catalog.py` e poi `build_site.py`. Il secondo genera il pacchetto `dist/` e verifica il limite di 1.000.000.000 byte.

Verifiche:

```powershell
node --test scripts\model.test.cjs
.\.venv\Scripts\python scripts\verify_archive.py
```

## Attribuzione

Curatela delle gallerie: **Fr0stiFusionZ / @Frosti811**, con scansioni e contributi secondo le singole fonti. Berserk: **Kentaro Miura / Hakusensha**; continuazione di **Studio Gaga**, supervisionata da **Kouji Mori**. Altri autori e staff per opere, adattamenti e materiali specifici come indicato nelle fonti. Nessuna attribuzione automatica di tutte le immagini a un unico autore o scanner. Le opere restano dei rispettivi titolari; la disponibilità nella galleria non implica una licenza di redistribuzione.

Gli originali master rimangono locali. Il sito compatto viene pubblicato su GitHub Pages con il workflow descritto sotto.

## Deduplicazione e pacchetto da condividere

La selezione sceglie una sola immagine principale per voce della galleria di Frosti. Privilegia i nomi `JP_BSK_` (scansioni piatte delle pagine), quindi le versioni `Clean`, gli artbook e le altre scansioni. Le fotografie e le immagini del contenitore editoriale non sono mostrate come ulteriori tavole quando esiste una versione pulita. A parità di famiglia si preferisce la maggiore risoluzione. Le altre versioni restano link espliciti, senza caricamenti remoti automatici. Le occorrenze della stessa immagine in più raccolte sono aggregate; la deduplicazione non presume che immagini semplicemente simili siano identiche. Per esempio il primo capitolo contiene tre tavole principali invece degli undici file dell’archivio.

**GitHub Pages pubblica solo il contenuto di `dist/`**, che è autonomo e sotto 1 GB. Gli originali in `assets/originals/`, le sorgenti HTML e l’ambiente Python rimangono solo nell’archivio locale e sono esclusi dal tracciamento tramite `.gitignore`. L’intera cartella di lavoro pesa quindi più del sito.

## Pubblicazione su GitHub Pages

Sito: **https://danielepassabi.github.io/berserk-color-archive/**

Repository: https://github.com/DanielePassabi/berserk-color-archive

Il workflow `.github/workflows/pages.yml` controlla i test anti-spoiler e l’integrità del pacchetto, poi pubblica esclusivamente `dist/`. Parte quando i file del sito cambiano su `main`, oppure manualmente dalla scheda Actions. Il sito rimane accessibile anche con il computer spento.

Per aggiornare le immagini, ricostruisci prima il pacchetto con `scripts/build_site.py`, quindi includi i cambiamenti di `dist/` nel commit. Gli originali privati e l’ambiente Python non servono alla pubblicazione. Il solo controllo del pacchetto si esegue con `python scripts/verify_site.py`.
