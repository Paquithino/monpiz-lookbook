# MonPiz Lookbook

Generatore del lookbook MonPiz in PDF. I contenuti (testi, prodotti, colori,
rivenditori) stanno in file YAML; il codice si occupa solo dell'impaginazione.
Aggiornare il catalogo significa modificare `content/`, non Python.

```bash
pip install -e .
monpiz-lookbook build                      # dist/MonPiz-Lookbook.pdf, 300 dpi (stampa)
monpiz-lookbook build --dpi 150 -o dist/MonPiz-Lookbook-web.pdf   # versione leggera per email
monpiz-lookbook check                      # valida contenuti e immagini senza generare
monpiz-lookbook watch                      # anteprima live: rigenera a ogni salvataggio (150 dpi)
```

### Anteprima live

`monpiz-lookbook watch` controlla `content/`, `assets/` e il codice in `src/` e rigenera
il PDF a ogni file salvato; in caso di errore lo mostra e resta in ascolto. Aperto in
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
- **Struttura**: sezione (`sections`, es. Donna) → modelli (`models`, es. Cortina) →
  prodotti (`products`). Ogni sezione genera una pagina divisoria; ogni modello una
  pagina di presentazione (foto, descrizione, fino a 4 materiali) seguita da una pagina
  per ciascun prodotto.
- **Prodotto**: `name`, `description` e `variants` obbligatori, `sizes` facoltativo. Ogni
  variante ha `color` e, quando c'è la foto, `image`. Massimo due varianti per pagina,
  impilate a tutta larghezza. Le foto restano intere: il fondale da studio viene esteso
  ai lati fino ai bordi della pagina, quindi vanno scattate su fondale uniforme.
- **Foto mancanti**: ovunque manchi `image` (modello, materiali, varianti) compare il
  segnaposto "Foto in arrivo".
- **Rivenditori**: pagina facoltativa, attiva quando in `lookbook.yaml` sono presenti
  i blocchi `retailers` e `closing` (insieme). L'elenco sta in `content/retailers.yaml`;
  le regioni vengono distribuite su tre colonne minimizzando la colonna più alta.

Se un contenuto non entra nella pagina la build si ferma con un errore esplicito,
invece di tagliare il testo in silenzio. Un errore di battitura in una chiave
YAML (es. `colours` invece di `colors`) viene segnalato, non ignorato.

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
