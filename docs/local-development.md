# Local development

## Docker

```powershell
Copy-Item .env.example .env
docker compose -f docker-compose.yml -f docker-compose.video.yml up --build
```

Open `http://localhost:5173`. Demo authentication is intentionally enabled only by environment configuration. Uploaded files and generated outputs are written to `data/`.

## Real transcription

Build the worker and run it against an audio file:

```powershell
docker build -t echoscript-worker services/transcribe-worker
docker run --rm -v ${PWD}:/work echoscript-worker --input /work/sample.mp3 --output /work/results --language auto
```

The first run downloads the configured faster-whisper model. The default is the multilingual `tiny` model with CPU `int8`; use a persistent `/models` volume for the model cache.

## Windows commands

Use `docker compose up --build`, `npm run build`, and `pytest -q` directly when GNU Make is unavailable.

