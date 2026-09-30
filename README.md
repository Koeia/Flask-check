# Dental Considerations (Flask)

A Flask port of the Express + React "Dental Considerations" drug lookup tool.
Enter a patient's medication list and get oral side effects (with prevalence)
and dental precautions for each drug. Anything not in the database links to Drugs.com.

## Run

```bash
pip install -r requirements-dev.txt
python app.py                       # dev server on http://localhost:5000
pytest                              # tests
gunicorn app:app                    # production
docker build -t dental . && docker run -p 5000:5000 dental
```

## Layout

```
app.py               Flask app: page routes + JSON API
drugs.py             Loads data/drugData.json into memory; search/autocomplete
data/drugData.json   The drug database (unchanged from the original)
templates/           Jinja templates (base, index, drug card, changelog, 404, icons)
static/css/style.css The original stylesheet (Tailwind directives removed)
static/js/app.js     Small vanilla-JS enhancement layer
tests/               pytest suite
```

## How it maps from the original

| Express + React | Flask |
| --- | --- |
| SQLite + Drizzle, wiped and reseeded from JSON on every boot | JSON loaded into memory once (same data, no DB needed) |
| React SPA calls `POST /api/drugs/search` | Server renders results from `GET /?drug=A&drug=B`, so result pages can be bookmarked and shared |
| Autocomplete: debounced fetch per keystroke | Filters the drug list already in the page, with no network calls |
| Collapsible cards via React state | Native `<details>`/`<summary>` |
| `DisclaimerModal`, chips, use filter, copy button | `static/js/app.js` |
| lucide-react icons | Inline SVG macro (`templates/_icons.html`) |
| `/api/drugs`, `/api/drugs/names`, `/api/drugs/autocomplete`, `POST /api/drugs/search` | Same endpoints, same response shapes |

Search and results still work with JavaScript turned off. Without JavaScript you
lose the disclaimer popup, adding and removing rows, autocomplete, and chip picking.

Also from the original TODO: pressing Tab in the last filled row adds a new row, and
autocomplete supports the arrow keys and Enter.
