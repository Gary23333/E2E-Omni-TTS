# PR #1 integration notes

This integration keeps the retry logic, dependency injection, public manager
accessors, WebSocket response lock, and version updates already present on main.
The older `.trae` review plan is not carried forward as current documentation.

## Included changes

- React Router navigation, including an unknown-route fallback.
- Audio callbacks registered before the WebSocket connection completes.
- The default backend binds to loopback, and CORS permits only the two local
  development frontend origins. This application still has no authentication;
  configuration APIs include provider keys and must not be exposed publicly.
- Agent tool allowlists applied to prompt/schema exposure and execution. An empty
  allowlist enables no tools.
- Text streaming on every tool round, with tool JSON and handoff markers withheld
  from visible tokens and TTS.
- Optional OpenAI-compatible tool definitions in `LLMClient.chat`; streamed tool
  arguments are assembled before parsing. The existing agent prompt-based tool
  protocol remains the default for compatibility. Parallel tool calls are not
  supported.
- Session upsert storage, UTC timestamps, and finalization on end or disconnect.
  Local transcripts are ignored by Git and are stored in
  `backend/data/configs/sessions.json`. No retention policy or transcript UI is
  included in this change.
- ASR retains raw PCM FunASR WebSocket support and retries, and stops on final
  results or a receive deadline. Explicit HTTP endpoints use a custom multipart
  `audio` WAV upload with a string `text` or `result` response. A bare HTTP origin
  uses `/asr`; an explicit path is preserved. This is not the Whisper API.
  Failures return no transcription, never a fabricated demo sentence, and never
  redirect WebSocket audio to a guessed HTTP endpoint.

## Reproducible checks

```sh
cd backend
python -m unittest discover -s tests -v
python -m compileall -q .

cd ../frontend
npm ci
npm run build
node --test tests/frontend-regressions.test.mjs
```

Validation on 2026-11-05: 26 backend offline tests, five frontend regressions,
Python compilation, and the TypeScript/Vite production build passed. Backend
checks were repeated with FastAPI 0.111.1, httpx 0.27.2, websockets 12.0,
NumPy 1.26.4, and Pydantic 2.13.4, within the repository's dependency ranges.

The tests use mocked transports and synthetic data. Live ASR recognition quality,
Omni model behavior, VoxCPM audio quality, and a browser microphone-to-speaker
session have not been verified. The frontend build reports an outdated
Browserslist database warning, not a build failure.
