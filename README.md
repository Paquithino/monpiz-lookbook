# MonPiz Lookbook

Generatore del lookbook MonPiz in PDF. I contenuti (testi, prodotti, colori,
rivenditori) stanno in file YAML; il codice si occupa solo dell'impaginazione.
Aggiornare il catalogo significa modificare `content/`, non Python.

```bash
pip install -e .
monpiz-lookbook build                      # dist/MonPiz-Lookbook.pdf, 300 dpi, con abbondanza (stampa)
monpiz-lookbook build --crop-marks         # come sopra, con i segni di taglio
monpiz-lookbook build --no-bleed --dpi 150 -o dist/MonPiz-Lookbook-web.pdf   # versione per email/online
monpiz-lookbook check                      # valida contenuti e immagini senza generare
monpiz-lookbook watch                      # anteprima live: rigenera a ogni salvataggio (150 dpi)
monpiz-lookbook web                        # rivista digitale in site/ (sito statico)
monpiz-lookbook web --watch                # anteprima su http://localhost:8000, rigenerata a ogni modifica
```

### Anteprima live

`monpiz-lookbook watch` controlla `content/`, `assets/` e il codice in `src/` e rigenera
il PDF (senza abbondanza, come lo si vedrà rifilato) a ogni file salvato; in caso di errore lo mostra e resta in ascolto. Aperto in
VS Code con l'estensione *vscode-pdf* (affiancato al codice), il PDF si ricarica da solo.
Ogni rebuild gira in un processo Python nuovo, così anche le modifiche al codice
(`theme.py`, le pagine) hanno effetto senza riavviare il watch.

Richiede Python ≥ 3.11. Nessuna dipendenza di sistema: ReportLab è puro Python.

## Struttura

```
content/
  lookbook.yaml        copertina, marchio, sezioni (Donna, Uomo), chiusura
  retailers.yaml       rivenditori per regione
assets/
  fonts/               Fraunces e Inter (istanze statiche, licenza OFL)
  images/              brand/, details/, products/
src/monpiz_lookbook/
  models.py            schema dei contenuti (Pydantic, chiavi sconosciute rifiutate)
  content.py           caricamento YAML + verifica che ogni immagine esista
  theme.py             design token: palette, stili di testo, griglia
  geometry.py          funzioni di layout pure (box, crop, a capo, colonne)
  surface.py           primitive di disegno sopra ReportLab, origine in alto a sinistra
  images.py            ricampionamento al DPI di uscita, ritaglio, tinta delle maschere
  pages/               una classe per tipo di pagina
  builder.py           sequenza delle pagine, numerazione, scrittura del PDF
  web/                 rivista digitale: template HTML, CSS, immagini responsive, font web
  cli.py               comandi build e check
scripts/
  instance_fonts.py    rigenera i TTF statici dai variable font di Google Fonts
tests/
```

Il flusso è lineare: `YAML → modelli validati → pagine → PDF`.

## Modificare i contenuti

- **Copertina**: logo a colori (`identity.logo`), foto prodotto su fondo bianco
  (`cover.photo`) e un massiccio dolomitico vettoriale disegnato nel codice
  (`src/monpiz_lookbook/mountain.py`). La foto è fusa in modalità Moltiplica: il suo
  bianco sparisce e gli scarponi stanno davanti alle montagne; la posizione si basa
  sull'ingombro della scarpa nella foto, quindi va bene qualsiasi scatto su fondo bianco.
- **Sequenza**: copertina → marchio → indice (generato) → per ogni sezione un'apertura
  a tutta pagina, poi per ogni modello la pagina di presentazione, l'eventuale pagina
  di dettaglio (`feature`) e una pagina per prodotto → rivenditori → quarta di copertina.
- **Struttura**: sezione (`sections`, es. Donna) → modelli (`models`, es. Cortina) →
  prodotti (`products`).
- **Prodotto**: `name`, `description` e `variants` obbligatori, `sizes` facoltativo. Ogni
  variante ha `color` e, quando c'è la foto, `image`. Da 1 a 4 varianti per pagina (una
  foto grande, affiancate o in griglia 2×2); in alternativa una foto e la cartella
  colori (`colors`), che si adatta al numero di colori.
- **Foto mancanti**: ovunque manchi `image` (modello, materiali, varianti) compare il
  segnaposto "Foto in arrivo".
- **Rivenditori**: attivi quando in `lookbook.yaml` sono presenti i blocchi `retailers`
  e `closing` (insieme). L'elenco sta in `content/retailers.yaml`. I negozi con
  coordinate (`at: [lat, lon]`) compaiono come punti sulla mappa; sotto, l'elenco
  "Negozio — Città" scorre su tre colonne e, se serve, su altre pagine.

### Campi facoltativi

Tutti opzionali: senza, la pagina usa una versione tipografica.

```yaml
index:                      # pagina indice
  title: Indice
  photo: images/mood/sabbia-bosco.jpg
sections:
  - name: Donna
    photo: images/mood/donna-indossate.jpg   # apertura a tutta pagina
    models:
      - name: Cortina
        specs:                               # tabella tecnica (max 4 righe)
          - {label: Suola, value: Vibram}
        feature:                             # pagina di dettaglio dopo il modello
          image: images/details/cortina-sottobosco.png
          title: Nata sulle Dolomiti
          text: Una riga o due.
          label: Dettaglio
          focus_x: 0.5                       # punto da tenere nel ritaglio (0-1)
          focus_y: 0.5
        products:
          - name: Cortina Dakar
            specs: [{label: Tomaia, value: Pelle scamosciata}]   # max 4
retailers:
  map:
    labels:                                  # città scritte sulla mappa
      - {name: Cortina, at: [46.54, 12.14]}
closing:
  photo: images/mood/lussari-foglie.png      # quarta di copertina con foto
```

## Stampa

- `build` produce il PDF per la tipografia: 3 mm di abbondanza su ogni lato, con
  TrimBox e BleedBox impostati. Tutto ciò che tocca il bordo (foto, fondi) prosegue
  nell'abbondanza; le foto vengono scalate in proporzione, mai deformate.
- `--crop-marks` aggiunge i segni di taglio, se la tipografia li vuole.
- Per la brossura a punto metallico le pagine devono essere un multiplo di 4: la
  build avvisa quante ne mancano.
- I colori sono RGB: la conversione in CMYK (profilo della carta lucida) va
  concordata con la tipografia.

Se un contenuto non entra nella pagina la build si ferma con un errore esplicito,
invece di tagliare il testo in silenzio. Un errore di battitura in una chiave
YAML (es. `colours` invece di `colors`) viene segnalato, non ignorato.

## Rivista digitale

`monpiz-lookbook web` genera dagli stessi YAML una rivista da sfogliare su telefono,
tablet e computer: una pagina HTML statica in `site/`, senza server né database.
Il PDF non viene pubblicato: la rivista si consulta, non si scarica.

- **Un libro da sfogliare**: ogni pagina occupa lo schermo e si gira con lo swipe, le
  frecce in basso, la tastiera o la rotella del mouse, con l'effetto della pagina che
  ruota sul dorso. Sul telefono si vede una pagina alla volta; sugli schermi orizzontali
  due pagine affiancate come una rivista aperta (copertina e aperture di sezione
  occupano la doppia pagina; `web/book.py` inserisce le pagine di raccordo necessarie).
  Il contatore in basso apre la panoramica di tutte le pagine.
- **Pagine**: modello con foto grande e materiali in una riga di piccoli tondi; prodotto
  con foto, specifiche e colori come pastiglie da toccare (mostrano il nome).
  Colori, caratteri e logo sono quelli della stampa.
- **Immagini**: ogni foto è pubblicata in WebP a più larghezze (480–1800 px); il
  browser scarica solo quella adatta allo schermo. I file hanno nel nome un'impronta
  del contenuto: una foto cambiata non resta mai vecchia nella cache del browser.
  La prima build ridimensiona tutto (circa un minuto e mezzo), le successive
  rigenerano solo ciò che è cambiato.
- **Rivenditori**: mappa con i punti toccabili; il nome del negozio apre lo shop online
  se c'è, altrimenti Google Maps; il telefono si chiama con un tocco.
- **Condivisione**: titolo, descrizione e immagine di anteprima (`share.jpg`) per
  Instagram e WhatsApp; icone per la schermata Home.

### Pubblicazione su GitHub Pages

1. Su GitHub: *Settings → Pages → Source: GitHub Actions* (una volta sola).
2. A ogni push il workflow `.github/workflows/rivista.yml` rigenera e pubblica il sito
   su `https://<utente>.github.io/monpiz-lookbook/`.
3. Dominio: su Aruba (DNS di monpiz.it) aggiungere un record **CNAME** `lookbook` →
   `<utente>.github.io`; poi in `lookbook.yaml` attivare
   `web: {url: https://lookbook.monpiz.it}` e, su GitHub, in *Settings → Pages* indicare
   lo stesso dominio e spuntare *Enforce HTTPS*.

## Scelte tecniche

- **ReportLab** invece di HTML→PDF (WeasyPrint, Chrome): nessuna dipendenza di
  sistema (Pango, Cairo, browser) e controllo esatto della posizione di ogni elemento.
- **Immagini ricampionate** al DPI richiesto per la dimensione a cui sono stampate,
  JPEG per le foto opache e PNG per quelle con trasparenza: il PDF a 300 dpi pesa
  circa 1,6 MB contro i 33 MB della bozza esportata dal browser.
- **Build riproducibile**: a parità di input il PDF è identico byte per byte, ed è
  scritto in un file temporaneo rinominato solo a build riuscita.
- **Logo e alberi di copertina come maschere** in scala di grigi, colorate in fase di
  rendering: lo stesso asset serve su fondo scuro e chiaro.

## Sviluppo

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
mypy
```

I test coprono solo il codice (calcoli di impaginazione e watch), mai i contenuti:
per validare il catalogo c'è `monpiz-lookbook check`.

## Font

Fraunces e Inter sono distribuiti con licenza SIL Open Font License
(`assets/fonts/OFL-*.txt`). ReportLab incorpora solo font TrueType statici, per cui
i variable font di Google Fonts sono istanziati con `scripts/instance_fonts.py`
(Fraunces opsz 48 e 14, peso 500; Inter opsz 14, peso 400).
