# Security and deployment scope

OmniVoice is a local development application. It does not implement user
accounts, authentication, tenant isolation, or a production authorization model.
Do not expose it to a LAN, the public Internet, a tunnel, or a reverse proxy.

## Current boundaries

- The backend and bundled TTS launcher bind to `127.0.0.1` by default.
- HTTP and WebSocket requests require a loopback peer and a localhost/loopback
  Host header. Browser origins are restricted to local ports 5173 and 8900.
- Browser requests with a foreign or `null` Origin are rejected, including
  WebSocket handshakes. Native clients without an Origin are permitted locally.
- The app trusts local processes. A local proxy can defeat peer-based isolation;
  this middleware is not authentication. Do not relax forwarded-header trust or
  host/origin checks to publish the app.
- Configuration responses omit stored LLM and embedding key values. Empty key
  fields preserve saved keys; explicit clear flags remove them. Changing a
  provider endpoint without a replacement key clears that endpoint's saved key.
- Uploads have a 10 MiB file limit and HTTP request bodies have a 12 MiB limit.
  Accepted names cannot escape the upload directory. Audio decoding and document
  parsing still process untrusted formats; use trusted local inputs.

## Sensitive local files

Provider credentials are stored as plaintext in the ignored local file
`backend/data/configs/global_config.json`. Conversation transcripts are stored in
`backend/data/configs/sessions.json`; uploaded documents and their indexes are
also local. Protect the user account, disk, backups and directory permissions.
There is no encryption-at-rest feature or automatic retention policy.

Never commit real provider keys, transcripts, private documents, audio samples or
environment files. Revoke and rotate a key if it is accidentally shared.

## Reporting

Do not publish credentials, personal conversations or exploit-ready private data
in a public issue. Use GitHub's private vulnerability reporting option if it is
available for this repository. Otherwise, ask the maintainer for a private
reporting channel without including sensitive details.

Offline tests and passing CI do not establish production security or validate
real model/audio services. Dependency and deployment review remain necessary
before expanding this application's trust boundary.
