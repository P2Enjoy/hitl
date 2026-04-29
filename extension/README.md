# extension/ — HITL Browser Extension

Browser extension (Chrome + Firefox, Manifest V3) that manages the user's Ed25519 keypair and signs HITL challenge requests.

## Security Model

- **Keypair**: Ed25519, generated with `extractable: false` via Web Crypto API. The private key never leaves the browser's internal key store.
- **Storage**: `chrome.storage.session` — in-memory only, automatically cleared when the browser closes. No data ever written to disk.
- **Signing**: Only the user's explicit "Approve" click triggers signing. The AI agent has no way to trigger a signature without user interaction.

## Architecture

```
signing-host/index.js   ← Node.js native messaging host
        │                  listens on localhost:7331 (HTTP)
        │ NativeMessaging stdio protocol
        ▼
src/background/index.ts ← MV3 service worker
        │                  routes messages, manages state
        ├── crypto.ts      Ed25519 operations
        ├── keystore.ts    chrome.storage.session wrapper
        ├── oauth.ts       PKCE login with OAuth server
        ├── pubkey-register.ts  register public key in OAuth server
        └── signing-server.ts  pending challenge queue
        │
        ▼
src/popup/popup.ts      ← User-facing approval UI
```

## Development

```bash
npm install
npm run dev          # watch mode, rebuilds to dist-chrome/ on change
npm run build        # production build (both targets)
npm test             # Vitest unit tests
npm run typecheck    # TypeScript strict type check
npm run lint         # ESLint
```

## Loading in Chrome

1. `npm run build`
2. Open `chrome://extensions`
3. Enable "Developer mode"
4. Click "Load unpacked" → select `extension/dist-chrome/`
5. Note the extension ID shown — you'll need it for the native messaging host

## Loading in Firefox

1. `npm run build`
2. Open `about:debugging` → "This Firefox"
3. Click "Load Temporary Add-on"
4. Select `extension/dist-firefox/manifest.json`

## Native Messaging Host

The extension cannot listen on TCP ports directly. A small Node.js script bridges HTTP (for tools) and the NativeMessaging stdio protocol (for the extension).

```bash
# Install after loading the extension
EXTENSION_ID=your_chrome_extension_id node src/signing-host/install.js
```

This writes wrapper scripts and native messaging host manifests to the correct OS locations.

## API

The signing host exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /sign` | body: `ChallengeRequest` JSON | Request user approval + signature |
| `GET /health` | — | Check if the host is running |

`POST /sign` blocks until the user approves or denies (up to `CHALLENGE_TTL_SECONDS`).

### ChallengeRequest

```json
{
  "nonce": "64-char hex string",
  "timestamp": 1700000000,
  "action": "Human-readable action description",
  "tool_name": "name of requesting tool",
  "version": "1"
}
```

### SignedResponse

```json
{
  "signature": "base64url Ed25519 signature (64 bytes)",
  "access_token": "OAuth server JWT",
  "user_id": "OAuth server sub claim",
  "nonce": "echo of challenge nonce",
  "timestamp": 1700000000
}
```
