# Frontend

Next.js frontend for the LM Anki Cards Creator web app.

## Development

Start the backend first from the repository root:

```bash
uv run anki-api
```

Then start the frontend from this directory:

```bash
npm install
npm run dev
```

Open `http://localhost:3000` in the browser. The app expects the FastAPI backend on `http://localhost:8000` during local development.

## Build

```bash
npm run build
npm run start
```

## Notes

- The create flow supports local and API-backed text models.
- TTS providers: local Qwen3, OpenAI, Google Gemini.
- Image providers: local Stable Diffusion, OpenAI, Google Nano Banana 2.
