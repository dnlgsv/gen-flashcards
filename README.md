# LM Anki Cards Creator

Generate ready-to-import Anki `.apkg` decks from a word list using language
models, text-to-speech, and optional image generation. The main app is a local
FastAPI server that serves a bundled browser UI, so the normal workflow is:
paste words, generate cards, review/edit them, then download an Anki deck.

## Project Idea

This project is built for language learners who want richer vocabulary cards
than a plain word/translation pair. For each word or phrase, the generator can
produce definitions, examples, CEFR level, translations, synonyms, antonyms,
collocations, topics, audio, and an optional image. The generated cards are
editable before export, which keeps the LLM in the loop without making it the
final authority.

The app supports two operating modes:

- Cloud/API mode: use liteLLM model identifiers such as `openai/gpt-5.4-nano`
  and provider APIs for TTS/images.
- Local mode: use a local GGUF language model, local Qwen3 TTS, and local
  Stable Diffusion image generation.

## Requirements

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ only if you want frontend hot-reload development
- SoX if you use local Qwen3 TTS
- Docker only if you want to run the containerized API

Local TTS/image generation can download or require large model files. For the
fastest first run, use an API model and either disable images or use an API image
provider.

## Run Locally From A Fresh Clone

Clone the repository:

```bash
git clone https://github.com/dnlgsv/lm-anki-cards-creator.git
cd lm-anki-cards-creator
```

Install Python dependencies:

```bash
uv sync
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Edit `.env` for the model setup you want.

For a low-friction API-backed first run:

```env
OPENAI_API_KEY=sk-...
MODEL_PATH=openai/gpt-5.4-nano
TTS_PROVIDER=openai
IMAGE_PROVIDER=openai
```

If you do not want image generation yet, keep any TTS provider you prefer and
set:

```env
ENABLE_IMAGES=false
```

Start the local browser app:

```bash
uv run anki-cards
```

The command starts FastAPI, uses `http://127.0.0.1:8000` when available, picks a
free port if `8000` is busy, and opens your default browser.

Useful local checks after startup:

- App: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Setup preflight: `http://127.0.0.1:8000/api/preflight`

## Local Model Setup

`.env.example` keeps large model files outside the repo by default:

```env
MODELS_DIR=../models
MODEL_PATH=../models/gemma-2-2b-it-Q8_0.gguf
```

Create that directory and download a GGUF model:

```bash
mkdir ../models
curl -L -o ../models/gemma-2-2b-it-Q8_0.gguf https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q8_0.gguf
```

On Windows PowerShell, use `curl.exe` if `curl` resolves to
`Invoke-WebRequest`:

```powershell
New-Item -ItemType Directory -Force ..\models
curl.exe -L -o ..\models\gemma-2-2b-it-Q8_0.gguf https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q8_0.gguf
```

You can also keep models inside the repo if that is easier locally:

```env
MODELS_DIR=models
MODEL_PATH=models/gemma-2-2b-it-Q8_0.gguf
```

The `models/` directory is ignored by git.

Local image generation is enabled by default and expects this file under
`MODELS_DIR`:

```env
IMAGE_PROVIDER=local
SD_MODEL_FILE=v1-5-pruned_Q4_0.gguf
```

If that Stable Diffusion GGUF file is not present, either add it to `MODELS_DIR`,
switch `IMAGE_PROVIDER` to `openai` or `google`, or set `ENABLE_IMAGES=false`.

Local Qwen3 TTS is the default:

```env
TTS_PROVIDER=qwen3
TTS_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
```

The model may be downloaded on first use.

If local Qwen3 audio prints a SoX warning, install SoX or switch to
`TTS_PROVIDER=openai`/`TTS_PROVIDER=google`.

## CLI Usage

The browser app is the recommended path, but the command-line generator is still
available:

```bash
uv run anki-creator --words "ephemeral,ubiquitous" --model openai/gpt-5.4-nano
```

You can also read words from a text file:

```bash
uv run anki-creator --file words.txt --deck_name "Vocabulary Deck"
```

Generated files are written under `data/`, including JSON card data, audio,
images, cache entries, and `.apkg` decks.

## Development

Run the bundled local app:

```bash
make run
```

On Windows without `make`, use:

```bash
uv run anki-cards
```

Start backend and frontend development servers with hot reload:

```powershell
.\dev.ps1
```

Or start them manually:

```bash
uv run anki-api
cd frontend
npm install
npm run dev
```

Backend: `http://localhost:8000`

Frontend dev server: `http://localhost:3000`

The frontend automatically calls `http://localhost:8000` when it is running on a
`3000`-series dev port. In bundled mode it calls the same origin that served the
UI.

Rebuild the bundled frontend served by `anki-cards`:

```bash
cd frontend
npm install
npm run build:local
```

`build:local` runs a static Next.js export and copies it to
`src/api/static_frontend/`.

Python development uses one Astral toolchain:

- `uv` for dependencies and command execution
- `ruff` for linting and formatting
- `ty` for type checking

## Docker

Build and run the FastAPI app:

```bash
docker build -t lm-anki-cards-creator .
docker run --rm -p 8000:8000 --env-file .env lm-anki-cards-creator
```

Then open `http://localhost:8000`.

The Docker image runs `uv run anki-api`, which serves the API and bundled static
frontend on port `8000`. Put any required local model files in a mounted volume
and point `MODEL_PATH`/`MODELS_DIR` at that mount if you use local models.

## Configuration

Copy `.env.example` to `.env` and set only the providers you use.

| Variable | Description | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required for OpenAI LLM, TTS, or image providers | unset |
| `ANTHROPIC_API_KEY` | Required for `anthropic/...` LLM models | unset |
| `GEMINI_API_KEY` | Required for Gemini/Google providers | unset |
| `DEEPSEEK_API_KEY` | Required for `deepseek/...` LLM models | unset |
| `MODEL_PATH` | Local `.gguf` path or liteLLM provider/model id | `../models/gemma-2-2b-it-Q8_0.gguf` |
| `DATA_DIR` | Runtime data directory | `data` |
| `MODELS_DIR` | Directory scanned for local GGUF models | `../models` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `TTS_PROVIDER` | `qwen3`, `openai`, or `google` | `qwen3` |
| `TTS_MODEL` | Provider-specific TTS model id | provider default |
| `IMAGE_PROVIDER` | `local`, `openai`, or `google` | `local` |
| `IMAGE_MODEL` | Provider-specific image model id | provider default |
| `ENABLE_IMAGES` | Enable image generation | `true` |
| `SD_MODEL_FILE` | Local Stable Diffusion GGUF filename under `MODELS_DIR` | `v1-5-pruned_Q4_0.gguf` |
| `AUDIO_FORMAT` | `mp3` or `wav` | `mp3` |
| `DEVICE` | `auto`, `cpu`, `cuda`, or `mps` | `auto` |
| `FRONTEND_URL` | Optional extra CORS origin | unset |

## Project Structure

```text
src/
  main.py            CLI generator and AnkiCardsGenerator orchestration
  local_app.py       One-command local browser app launcher
  api/               FastAPI app, routers, task runner, static frontend serving
  prompts/           Packaged LLM prompt templates
  model_manager.py   LLM routing through liteLLM and local GGUF loading
  llm_catalog.py     Curated remote model list and model-id helpers
  media_catalog.py   Shared TTS/image provider catalogs
  schemas.py         CardInfo model for LLM card output
  tts.py             Provider-aware text-to-speech generation
  image_gen.py       Provider-aware image generation
  anki_utils.py      genanki deck, note, media, and template creation
  cache.py           SHA256-keyed disk cache
frontend/
  src/               Next.js UI for generating, reviewing, and exporting cards
  scripts/           Static export copy script for bundled mode
tests/               Backend unit and API tests
data/                Runtime output; generated locally and mostly gitignored
```

## Useful Commands

```bash
make install     # uv sync
make run         # uv run anki-cards
make backend     # uv run uvicorn src.api.run:app --host 0.0.0.0 --port 8000 --reload
make frontend    # cd frontend && npm run dev
make test        # uv run pytest tests/ -v --no-cov
make test-cov    # uv run pytest tests/ --cov=src --cov-report=term-missing
make lint        # uv run ruff check src/ tests/
make fmt         # ruff check --fix + ruff format
make typecheck   # uv run ty check src/
make check       # lint + typecheck + test
```

## Troubleshooting

- `Local model file not found`: update `MODEL_PATH`, download the GGUF file, or
  switch to a provider/model id such as `openai/gpt-5.4-nano`.
- `Stable Diffusion model file not found`: add `SD_MODEL_FILE` to `MODELS_DIR`,
  switch image provider, or set `ENABLE_IMAGES=false`.
- Missing API key errors: set the matching provider key in `.env`, then restart
  the server.
- `SoX could not be found`: install SoX for local Qwen3 TTS, or use an API TTS
  provider.
- Frontend cannot reach the API in dev mode: make sure `uv run anki-api` is
  running on `http://localhost:8000`.
- Port `8000` is busy: `uv run anki-cards` chooses another local port
  automatically; `uv run anki-api` and `make backend` always use port `8000`.
