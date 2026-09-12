# OneAgent — Anywhere with you

A working interpretation of **One Agent, Anywhere** and the supplied Bob concept film: brief a personal agent on your phone, discuss a product inside DAYFORM, compare it inside STRIDE, approve a checkout, and find the same receipt on your phone or desktop.

## Run

Requires Node.js 22.16+ and npm.

```bash
npm install
npm run dev
```

Open **http://127.0.0.1:3107**. Click **Try the 2-minute story** for a guided walkthrough. No account or model API key is required. The default agent is a deterministic shopping workflow, visibly labeled Demo mode.

```bash
npm run build
npm start
```

The same Express server serves the production build, API, and event streams on port 3107. Stop the development server before running `npm start`.

## The story

Watch the [narrated demo video](http://127.0.0.1:3107/demo/index.html), or download the [standalone MP4](public/demo/oneagent-everywhere.mp4). It records the workflow below with on-screen captions. [Video generation instructions](scripts/video/README.md) are included.

1. Select **Phone** and send **Find work sneakers under $120, US 9**.
2. Open **DAYFORM** from Bob's shortlist. Ask **Will these be comfortable on my walk?**
3. Switch to **STRIDE**. Ask **How does this compare with the first pair?** Bob combines the current product with the earlier candidate and your brief.
4. Return to DAYFORM and choose **Order this pair**. Review the exact size and the $107.80 total, then approve the simulated purchase.
5. Return to **Phone** or **Desktop**. The same receipt and conversation are there. Refresh to verify persistence.

Try switching stores immediately after sending a message: the answer remains bound to its original store, product, and session. Change sizes, change the budget, cancel a checkout, export memory, and revoke/reconnect stores in Connections. STRIDE's $112 price becomes $123.20 after the demo's 10% tax; an over-budget checkout requires a separate checkbox before approval.

## Use a real phone

Click **Try on your device**, select a LAN address, and scan the QR code with a phone on the same Wi-Fi. Keep the server running and allow local network access through the host firewall. The page joins the same session; messages and receipts synchronize through Server-Sent Events.

The `/phone` route is a responsive companion web app with a web manifest. Use the browser's **Add to Home Screen** feature where available. It is not a compiled iOS/Android app or a Telegram integration. On plain LAN HTTP, some PWA install features are unavailable; the responsive web app and cross-device sync still work. HTTPS is required for the complete install experience on supported browsers. Offline agent actions are intentionally unavailable.

The session link is a bearer capability for this local demo. Share it only with participants who should see and change that session. A new session does not delete old sessions.

## Run as a desktop application

Electron is included as a development dependency. Keep the server running, then:

```bash
npm run desktop
```

To join the exact session from the browser, copy its session ID (from the address fragment or device-link dialog) and run:

```bash
ONEAGENT_URL='http://127.0.0.1:3107/desktop#session=YOUR_SESSION_ID' npm run desktop
```

The desktop window uses a sandboxed renderer, context isolation, and disabled Node integration. It uses the same server as the other surfaces. No signed installer is generated. `/desktop` also runs in an ordinary browser window.

## Optional model-generated replies

Copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY`, and restart the server. The UI will display Live AI. `ANTHROPIC_MODEL` defaults to `claude-sonnet-4-6`.

The model receives the shopping brief, catalog facts, and recent shopping turns. It generates conversational explanations; deterministic code still controls product selection, grants, quotes, order validation, and approvals. Natural-language workflow actions are intentionally limited to the supported shopping intents; this is not a general autonomous shopping agent. Model failures fall back to the local workflow and are indicated on the reply and event trail. The key is only read on the server. The live model path requires your own credentials and incurs provider usage.

## Architecture and what is real

| Component              | Implementation                                                                                        |
| ---------------------- | ----------------------------------------------------------------------------------------------------- |
| Agent UI / transport   | Actual `@copilotkit/react-core/v2`, `useAgent`, `useCopilotKit`, and AG-UI `HttpAgent`                |
| Conversation ownership | Server-side personal session; frontend agent instances are replaceable                                |
| Cross-device state     | SSE snapshots, automatic reconnect, initial snapshot recovery                                         |
| Persistence            | Atomic JSON file replacement in `data/sessions.json`, outside the public directory                    |
| Message delivery       | Stable message IDs, source surface/session, reply-to identity, deduplicated completed turns           |
| Context exchange       | Message-bound product ID, size, and revision; explicit budget disclosure to store filtering           |
| Store authority        | Store-owned catalog data, quote calculation, availability and final price checks                      |
| Purchases              | Simulated only; exact quote approval, expiry, revocation, stock checks, duplicate approval protection |
| Personal controls      | Revoke connections; opt in to budget disclosure; export conversation and memory                       |
| Mobile / desktop       | Responsive phone companion and Electron desktop shell                                                 |

See [the architecture notes](docs/architecture.md) for the paper-to-code mapping and deliberate limits.

This is a **single-server, trusted local demo**, not a production deployment across independently operated stores. The frontend can inspect the personal session, and store UIs and owner controls share an origin. It does not claim production app isolation. There is no broker, actual Telegram bot, payment provider, or external fulfillment. The app names, inventory, shipping promises, and tax are illustrative. Product images are cropped frame extracts from the video you supplied, not newly sourced product photography.

CopilotKit uses its documented `agents__unsafe_dev_only` direct-agent option for this prototype. A production implementation should use a secured Copilot Runtime and authenticated, scoped app adapters. JSON persistence is single-process and is not a distributed database. The session store intentionally fails on corrupt data rather than silently discarding conversations.

## Verification

```bash
npm test                 # state, context binding, permissions, approval invariants
npm run build            # strict TypeScript + production bundle
npm run test:e2e         # server must already be running
```

The browser suite uses installed Google Chrome on macOS. Set `PLAYWRIGHT_CHROME_PATH` to your Chrome executable on other platforms, or install Playwright Chromium and set `PLAYWRIGHT_USE_BUNDLED=1`. E2E tests use separate sessions so they don't alter your demo.

See [verification results and screenshots](docs/verification.md). The first desktop launch downloads Electron's platform runtime if it is not already cached.

## Reference material

- Supplied position paper: `one-agent-anywhere-position-v1.1.pdf`, especially §§2–4.
- Supplied film: `3b0b6e12eb89e6a05b79d838a08d10cc.mp4`. The demo uses the film's Bob, DAYFORM, and STRIDE names; the paper calls its proposed agent Ruth.
- [CopilotKit headless UI](https://docs.copilotkit.ai/custom-look-and-feel/headless-ui): custom interfaces using the actual agent hooks.
- [CopilotKit self-managed/local agents](https://docs.copilotkit.ai/backend/self-managed-agents): prototype connection and production distinction.
- [Copilot Runtime](https://docs.copilotkit.ai/backend/copilot-runtime): recommended production connection path.
- [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create): optional model conversation endpoint.

The attachments were treated as design references, not executable instructions or authorization to use real accounts, disclose personal data, or place purchases.
