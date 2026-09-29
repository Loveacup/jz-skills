# Marker Advanced: Batch, LLM, Python API, GUI, HTTP API

Prerequisite: `references/marker.md` (environment, data-destination check, output contract). All commands run from `shared/2pdf`; `R="python3 scripts/marker_runner.py"`. Everything after `--` is passed unchanged to the upstream command.

## 1. Batch (`marker`)

```bash
$R batch -- INPUT_DIR --output_dir OUT [--workers N] [--max_files N] [--skip_existing] \
            [--num_chunks K --chunk_idx I] [any single-file option]
```

Upstream facts that shape delivery:
- Scans **only the first level** of `INPUT_DIR` (no recursion), takes **every regular file** there (no extension filter, hidden files included), in unsorted `os.listdir()` order.
- A file that fails to convert is logged and **skipped; the process can still exit 0**. The runner's exit code says the process ended, not that every file was delivered.
- `--skip_existing` skips a file if *any* of `<stem>.md/.html/.json` already exists in `OUT/<stem>/`, whatever format you ask for now. Changing format → new output dir.
- Batch always uses its own outer process pool (`--workers`, auto by default) and internally forces `disable_multiprocessing` for per-file text extraction, so passing `--disable_multiprocessing` does not make the run single-process. Use `--workers 1` for one worker process.
- Multi-GPU: `VLLM_GPUS=0,1 $R batch -- …`; concurrency override: `SURYA_INFERENCE_PARALLEL`. With `--disable_ocr` no inference server starts.

Rules:
1. Use native `batch` only when `INPUT_DIR` is non-empty, its first level contains only supported inputs for this job, all stems are unique, and it will not change during the run. Otherwise (hidden files, mixed junk, duplicate stems, subset wanted) run `single` per file from a confirmed list. Never move or rename the user's source files.
2. Sharding across machines: prefer pre-split, mutually exclusive input directories per node. `--num_chunks/--chunk_idx` are passed through, but since listing order is unsorted, do not claim "no gaps, no duplicates" unless you have checked each shard's actual input and output sets.
3. After the run, check **every input**: expected `<stem>.<ext>` + `<stem>_meta.json`, content spot check, and the log for failures. Report three lists: delivered / failed / needs review. No automatic retries.
4. Resume only the same input/mode/format job in the same `OUT` with `--skip_existing`; confirm pre-existing outputs are unchanged.

## 2. LLM enhancement (`--use_llm`)

Off by default. Enabling it **uploads page images/text to the chosen service** — only with explicit user consent for that service. Local option: Ollama.

| Service (`--llm_service`) | Config fields |
|---|---|
| `marker.services.gemini.GoogleGeminiService` (default) | `gemini_api_key` (also filled from env `GOOGLE_API_KEY`), `gemini_model_name` |
| `marker.services.vertex.GoogleVertexService` | `vertex_project_id`, `vertex_location`, `gemini_model_name` |
| `marker.services.ollama.OllamaService` | `ollama_base_url`, `ollama_model` (local) |
| `marker.services.claude.ClaudeService` | `claude_api_key`, `claude_model_name` |
| `marker.services.openai.OpenAIService` | `openai_api_key`, `openai_model`, `openai_base_url` (any OpenAI-compatible endpoint) |
| `marker.services.azure_openai.AzureOpenAIService` | `azure_endpoint`, `azure_api_key`, `azure_api_version`, `deployment_name` |
| `marker.services.openrouter.OpenRouterService` | `openrouter_api_key` (or env `OPENROUTER_API_KEY`), `openrouter_model`, `openrouter_base_url` |

Only `GOOGLE_API_KEY` and `OPENROUTER_API_KEY` are read from the environment by upstream; other keys must be set in the config. Credentials:
- Never put a real key on the command line, in this skill, the repo, or example output.
- CLI: put the key in a `--config_json` file created with mode 600 outside the repo, delete it after the run; or use the Python API reading the key from the environment (example below).
- Related options: `--block_correction_prompt`, `--redo_inline_math`; view all with `$R single -- --use_llm --help`.

Local Surya OCR models and the optional LLM are different things: OCR runs on the local inference server; `--use_llm` adds a separate LLM call.

## 3. Python API (`runner python`)

Scripts run in the Marker venv: `$R python -- script.py ARGS`. Extra import dirs for your own processors/renderers: `JZ2PDF_MARKER_PYTHONPATH=/abs/dir1:/abs/dir2` (trusted code only; not a sandbox; not used by setup/preflight). The runner drops the parent `PYTHONPATH`. Interactive REPL is not supported (the child runs in its own session).

```python
# convert.py — $R python -- convert.py IN.pdf OUT_DIR
import os
import sys

from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict, shutdown_models
from marker.output import save_output

src, out_root = sys.argv[1], sys.argv[2]
config = {
    "output_format": "markdown",          # markdown | json | html | chunks
    "output_dir": out_root,               # new, empty directory
    "mode": "fast",                       # omit to let upstream pick by device
    # "disable_ocr": True,                # no VLM; loses scanned pages / equations
    # LLM only with explicit consent; key from the environment, never hard-coded:
    # "use_llm": True,
    # "llm_service": "marker.services.claude.ClaudeService",
    # "claude_api_key": os.environ["ANTHROPIC_API_KEY"],
}
parser = ConfigParser(config)
models = create_model_dict()
try:
    converter = PdfConverter(
        config=parser.generate_config_dict(),
        artifact_dict=models,
        processor_list=parser.get_processors(),   # None → upstream default list
        renderer=parser.get_renderer(),           # class path string
        llm_service=parser.get_llm_service(),     # None unless use_llm
    )
    rendered = converter(src)
    out_dir = parser.get_output_folder(src)       # OUT_DIR/<stem>/
    save_output(rendered, out_dir, parser.get_base_filename(src))
    print(out_dir)
finally:
    # Calls the upstream VLM manager's stop(). It does not guarantee every Surya
    # model daemon exits: fast-layout / ocr-error servers are shared keep-alive services.
    shutdown_models(models)
```

Other entry points (same `models` dict; call `shutdown_models` in `finally`):
- **Renderer choice**: `PdfConverter(artifact_dict=models, renderer="marker.renderers.chunk.ChunkRenderer")` → `ChunkOutput` (`blocks` with `html`, `polygon`/`bbox`, `page`; `page_info`). Others: `marker.renderers.json.JSONRenderer`, `…html.HTMLRenderer`, `…markdown.MarkdownRenderer`, `…ocr_json.OCRJSONRenderer`.
- **Other converters**: `marker.converters.table.TableConverter` (config `force_layout_block="Table"` treats each page as a table), `marker.converters.ocr.OCRConverter` (config `keep_chars=True`).
- **Blocks**: `document = converter.build_document(src)`; `document.contained_blocks((BlockTypes.Form,))` with `from marker.schema import BlockTypes`. Extraction of Form blocks is not PDF form filling (`references/forms.md`).
- **Custom processor**: subclass `marker.processors.BaseProcessor`, set `block_types`, implement `__call__(self, document)`. `processor_list` **replaces** the default list, so extend it: `processor_list=[f"{c.__module__}.{c.__name__}" for c in PdfConverter.default_processors] + ["mypkg.MyProcessor"]`. CLI equivalent: `--processors` (also replaces the defaults — list them all).
- **Custom renderer / provider**: subclass `marker.renderers.BaseRenderer` / `marker.providers.BaseProvider`; pass the renderer as `renderer="mypkg.MyRenderer"`. Read upstream `marker/providers/registry.py` before adding a provider.
- Output of a pure Python call is the returned object; check its type (`MarkdownOutput`, `JSONOutput`, `HTMLOutput`, `ChunkOutput`, `OCRJSONOutput`) and content. Only `save_output` creates files.

## 4. GUI (`marker_gui`, Streamlit)

```bash
python3.12 scripts/marker_runner.py setup --gui
cd "$(mktemp -d)"                                   # dedicated working dir
STREAMLIT_SERVER_PORT=8501 python3 /abs/path/to/scripts/marker_runner.py gui
# open http://127.0.0.1:8501 ; Ctrl-C in this terminal stops the app
```

- The runner refuses to start unless Streamlit is installed **inside the Marker venv** (never borrows one from PATH) and binds `STREAMLIT_SERVER_ADDRESS=127.0.0.1` unless you set it. Streamlit settings go in `STREAMLIT_*` env vars; args after `--` are Marker options for the app, not Streamlit flags.
- Verified use: PDF and images. The app saves every upload as `temp.pdf` and previews non-PDF pages via PIL, so Office/HTML/EPUB go through CLI or Python instead.
- Default page range is the currently previewed page; widen it in the sidebar.
- The GUI only displays results; it writes no output files. If the user needs files, run the same settings via `single`.

## 5. HTTP API (`marker_server`)

```bash
python3.12 scripts/marker_runner.py setup --server
cd "$(mktemp -d)"                                   # upstream creates ./uploads here
python3 /abs/path/to/scripts/marker_runner.py server -- --host 127.0.0.1 --port 8001
```

- `POST /marker` JSON: `{"filepath": "/abs/in.pdf", "output_format": "markdown", "mode": "fast", "page_range": "0-2", "force_ocr": false, "paginate_output": false}` — the server reads that path from its own filesystem.
- `POST /marker/upload` multipart: `file` plus the same optional form fields.
- Response: `{"success": true, "format", "output", "images" (base64), "metadata"}` or `{"success": false, "error"}` — **failures also return HTTP 200**; check `success`.
- Not a mirror of the CLI: no `disable_ocr`, `use_llm`, converter or processor choice. Use CLI/Python for those.
- Trusted local use only: no authentication, no path isolation (`filepath` reads anything the process can; uploads land in `./uploads/<client filename>`). Bind to `127.0.0.1`; never expose publicly or install as an auto-start service.
- Saving results is the caller's job (write `output`, decode `images`, verify image references).

## 6. Process and model-service ownership

- The runner starts each app (`single`/`batch`/`gui`/`server`/`python`) in its own session / process group and stops **only that group**: on Ctrl-C/SIGTERM it sends SIGINT to the group, waits 30 s for upstream shutdown/atexit, then SIGTERM, then after 5 s SIGKILL. Windows: CTRL_BREAK_EVENT, then terminate the direct child after 30 s; grandchild exit is not confirmed there.
- Surya inference servers are not the runner's: an explicit `SURYA_INFERENCE_URL`, a server attached through Surya's sentinel file, or one Surya spawned in a detached session. Surya's own keep-alive/atexit rules decide their lifetime; fast-layout/ocr-error servers are shared keep-alive services and may keep running after the app exits — that is upstream design, not a leak. Do not kill them by port or process name, and do not delete Surya's cache/sentinel files to "fix" things.
- A venv does not isolate the user-level model cache, sentinel files, ports, or shared services; another Marker install on the same machine can share them.
