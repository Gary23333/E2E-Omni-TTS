# Contributing

Use a focused branch and a draft pull request. Describe the problem, changed
behavior, tests, and limits. Keep credentials and user data out of commits.

## Offline validation

Python 3.10 or newer and Node.js 22.12 or newer are required for the current
source/toolchain. The CI jobs use Python 3.10/3.12 and Node.js 22.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements-core.txt
(cd backend && python -m unittest discover -s tests -v)
python -m compileall -q backend

cd frontend
npm ci
npm run build
node --test tests/*.test.mjs
```

The core dependency set is enough for mocked unit/transport tests. A full app or
live RAG run needs `backend/requirements.txt`; VoxCPM has separate upstream model
and runtime requirements. Tests never need production keys or model downloads.

The `backend/test_*.py` files outside `backend/tests/` are manual service probes,
not the offline suite. Do not point them at someone else's services or private
data. Document actual endpoint/hardware validation separately.

For UI changes, include browser checks when available. Do not describe mocked
component tests or a successful build as a real microphone/audio session.
