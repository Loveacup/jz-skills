# Structured Parsing with Marker

Documents → structure-preserving **Markdown / JSON / HTML / chunks** (layout, reading order, tables, equations, images, OCR). Engine: upstream [Marker v2.0.0](https://github.com/datalab-to/marker/releases/tag/v2.0.0) + Surya 0.22.1, run through `scripts/marker_runner.py` in its own venv. Batch, LLM, Python API, GUI and HTTP API: `references/marker-advanced.md`.

Use this chain only when the task needs structure (PDF → Markdown/JSON/chunks, complex/scanned tables, equations, Office/EPUB parsing). Plain text/table dumps stay on `references/pdf-operations.md`. Typeset PDF output stays on `scripts/md2pdf_chrome.py`.

## 1. Environment (independent of the typesetting engine)

```bash
# From shared/2pdf. Creating the venv needs Python >=3.10,<4 (here: Homebrew python3.12).
python3.12 scripts/marker_runner.py setup              # PDF + images
python3.12 scripts/marker_runner.py setup --full       # + DOCX/PPTX/XLSX/HTML/EPUB (marker-pdf[full])
python3.12 scripts/marker_runner.py setup --gui        # + Streamlit GUI deps
python3.12 scripts/marker_runner.py setup --server     # + FastAPI/uvicorn HTTP deps
python3 scripts/marker_runner.py preflight [--full] [--gui] [--server] [--json]
```

- venv: `~/.venvs/2pdf-marker` (override with `JZ2PDF_MARKER_VENV`; empty value, the typesetting venv `~/.venvs/pdf-skill`, its parents/children, and the global Python are refused). Versions pinned in `scripts/requirements-marker.txt`.
- `setup` never touches `~/.venvs/pdf-skill`, never deletes a directory, never installs Homebrew/Docker/CUDA, never downloads models. It refuses a non-empty directory that is not a venv, and refuses to run pip when the target interpreter's real `sys.prefix` is not the target venv.
- Missing Marker deps → run the Marker `setup` above. **Never** re-run `md2pdf_chrome.py --setup` for Marker problems, and never fall back to the typesetting engine.
- `preflight` is read-only: checks venv isolation, exact Marker/Surya versions, selected extras and entrypoints; reports whether `llama-server`/`docker` are on PATH and whether `SURYA_INFERENCE_URL` / `FAST_LAYOUT_SERVER_URL` / `OCR_ERROR_SERVER_URL` are set (values not printed). It does **not** verify model cache, service reachability, or WeasyPrint native libraries — only a real conversion does. Exit 1 = fail; 0 with `overall: degraded` = optional system condition missing.
- Models download on the first conversion (network required; offline first run cannot work). OCR, equations and `balanced` mode use a Surya VLM served by a local inference server that Surya spawns itself: `llama-server` (macOS: `brew install llama.cpp`, or `LLAMA_CPP_BINARY`) on non-NVIDIA machines, vLLM via Docker on NVIDIA.
- `--full` formats render through WeasyPrint → temporary PDF → parse. If WeasyPrint's native libs (pango etc.) are missing, the conversion error names them; install them per WeasyPrint docs. Office styling/animations/formulas are not converted losslessly.
- Licensing: Marker code is Apache-2.0; **model weights** use a modified AI Pubs Open RAIL-M license ([MODEL_LICENSE](https://github.com/datalab-to/marker/blob/947d7688c0739297a7b9eb08b1a463e3a6853981/MODEL_LICENSE)): commercial use is excluded above $5M revenue or funding (personal/research use excepted), for anyone offering a product competing with Datalab, and outputs/distribution carry attribution duties. Flag this when the user's use is commercial.

## 2. Before converting: data destination and output directory

Do this every time:

1. **Where does the data go?** Check the actual CLI args, any `--config_json` file / Python config (`use_llm`, `llm_service`), and the env vars `SURYA_INFERENCE_URL`, `FAST_LAYOUT_SERVER_URL`, `OCR_ERROR_SERVER_URL`. No `--use_llm` on the CLI is not proof of local-only processing. Remote destination without user consent → stop and ask.
2. **Output directory**: for `single`/`batch` always pass `--output_dir` pointing at a new, empty directory. If a previous result with the same stem exists, keep it and pick a new directory with an incrementing suffix (`out`, `out-2`, …). Reuse a directory (with `--skip_existing`) only when explicitly resuming the same input/mode/format job.
3. **Mode choice**: leave `--mode` unset to let upstream pick (CPU/MPS → `fast`, CUDA → `balanced`). `--disable_ocr` never calls the VLM: faster, but scanned pages and equations are lost. Never add it silently after a failure; say so if you use it.

## 3. Convert one file

```bash
R="python3 scripts/marker_runner.py"          # any python3 works; Marker runs in its own venv

$R single -- INPUT --output_format markdown --output_dir OUT     # markdown | json | html | chunks
$R single -- --help                                               # every native option (dynamic)
$R single -- config --help                                        # every builder/processor/converter setting
```

Everything after `--` goes to upstream `marker_single` unchanged. Common native options:

| Need | Options |
|---|---|
| Pages | `--page_range "0,5-10,20"` (0-based) |
| Speed vs quality | `--mode fast\|balanced` |
| OCR | `--force_ocr` (garbled/scanned text), `--strip_existing_ocr`, `--disable_ocr` (no VLM at all) |
| Inline math in fast mode | `--ocr_inline_math` or `--force_ocr` |
| Images | `--disable_image_extraction` |
| Page headers/footers | `--keep_pageheader_in_output`, `--keep_pagefooter_in_output` |
| Paginated text | `--paginate_output` |
| Extra settings | `--config_json FILE`, `--processors a.B,c.D` |
| Tables only | `--converter_cls marker.converters.table.TableConverter` (+ `--force_layout_block Table` to treat each page as a table) |
| OCR only | `--converter_cls marker.converters.ocr.OCRConverter` (+ `--keep_chars` for digital PDFs) |

Inputs: PDF and images need the base install; DOCX/PPTX/XLSX/HTML/EPUB need `setup --full`.

Converter notes:
- `TableConverter` emits only table blocks (HTML `<table>`; `json` adds page bounding boxes). Scanned tables come from OCR — verify them separately; a digital-table success is not evidence for scans.
- `OCRConverter` always renders OCR JSON (`OCRJSONRenderer`); `--output_format markdown` does not change that. VLM-OCR'd pages return block-level HTML without character boxes.
- `--disable_ocr` is not "no models": the fast layout model still loads.

## 4. Output contract and acceptance

`single` writes `OUT/<stem>/`:

| File | When |
|---|---|
| `<stem>.md` / `<stem>.html` | markdown / html |
| `<stem>.json` | json, chunks, OCRConverter (all `.json`) |
| `<stem>_meta.json` | always (table of contents, per-page stats; may be `null` for OCR output) |
| images (`*.jpeg` by default) | markdown/html with extracted images, linked relatively |

Upstream overwrites files in `OUT/<stem>/` without asking — hence the new-directory rule. Same stem with different inputs (e.g. `a.pdf` and `a.docx`) needs separate output roots.

Acceptance (a zero exit code is not delivery):
1. The expected `<stem>.<ext>` and `<stem>_meta.json` exist for the requested format.
2. Open the output and compare with the input: title, body text, table values, requested page range only. JSON is a page → block tree (`children`, `block_type`, `polygon`, `html`); chunks is a flat block list with `page_info`.
3. Markdown/HTML image links resolve inside `OUT/<stem>/`.
4. Report: output path, mode/flags used, which content checks failed, and whether any external service (LLM or remote inference URL) received data. Structure recognition and OCR are lossy; report what you checked instead of claiming "high accuracy".

Failure modes seen in local smoke runs (Marker 2.0.0, macOS, fast mode), so check for them explicitly:
- A simple vector drawing can be classified as a `Form` block and replaced by a VLM description with an **empty image link** `![…]()` and no image file. Photo-like figures were extracted as `_page_N_Picture_M.jpeg`.
- CJK full-width punctuation may come back as ASCII (`，` → `,`, `：` → `:`).
- HTML tables may flatten into headings/text; XLSX title rows can merge into the table header.

## 5. Combining with the typesetting engine

Explicit two-step hand-off through files only:

```bash
python3 scripts/marker_runner.py single -- in.pdf --output_format markdown --output_dir OUT
python3 scripts/md2pdf_chrome.py "$(pwd)/OUT/in/in.md" OUT/in-retypeset.pdf --verify
```

Pass the absolute path of the `.md` *inside* `OUT/<stem>/` (the typesetting engine resolves images relative to the Markdown file). Do not move the `.md` out alone. The result is a re-typeset document, not a lossless copy of the source; `$$…$$` LaTeX from Marker is not rendered as math by the typesetting engine.

## 6. Errors

| Symptom | Action |
|---|---|
| runner exits 1 “Marker 环境未就绪” | Run the printed Marker `setup` command |
| runner exits 2 | Fix the runner operation name, `JZ2PDF_MARKER_VENV`, or `JZ2PDF_MARKER_PYTHONPATH` |
| Upstream traceback / non-zero exit | Report it verbatim; do not retry with another engine or silently change flags |
| `llama-server binary not found` | OCR/equations need the inference server: install llama.cpp, set `LLAMA_CPP_BINARY`, or point `SURYA_INFERENCE_URL` at a user-approved server |
| Model download failure | Network prerequisite; keep the raw error, do not disable TLS or switch indexes |
| WeasyPrint / `libgobject` / pango errors on Office/HTML/EPUB | Install WeasyPrint native libraries; do not drop those formats |
