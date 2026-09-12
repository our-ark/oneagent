# OneAgent Travel

A working local website with three connected applications: trip home, Airside
(flights), and Staywell (hotels). Each app has its own message database and
loopback HTTP feed. OneAgent connects outbound to those feeds and answers through
the same visitor-specific runtime session. Browser routes share a gateway for
simple local setup; they are controlled integrations, not external travel sites.

## Run

Requires Python 3.11+, Node 20.19+ or 22.12+, Git, and OneAgent's authenticated
runtime (Codex by default). From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
npm --prefix examples/travel/web ci
npm --prefix examples/travel/web run build
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel
```

Open http://127.0.0.1:8080. `--port`, `--root`, and `--web-root` are configurable.
The launcher provides the repository source path. The CLI never offers canned
agent responses; the runtime must be configured and logged in. When the runtime
is unavailable, the UI shows a recoverable error rather than a fake answer.

The default catalog contains one-way SFO → Tokyo flights departing Nov 5 and
arriving Nov 6, 2026, and three-night stays for Nov 6–9. All providers, properties,
prices, reviews, availability, tax treatment, and transfer estimates are fictional.
The room image is illustrative. There is no booking, payment, or address API.

## Try the story yourself

1. On trip home, set a $1,500 flight/hotel budget and preferences such as “quiet
   neighborhoods and a relaxed first day.” Update the brief.
2. In Airside, select Pacific Air PA 101. Ask “Would this flight work for my trip?”
3. Save the flight. A saved selection is separate from the currently viewed item.
4. In Staywell, select Kumo House and ask “Does this work with my saved flight?”
5. Select Aoi Central and ask “Is this better than the previous hotel?”
6. Ask to save your preferred hotel and confirm the agent's proposal, or use the
   explicit Save stay button. Review the saved total on trip home.
7. Optional: save the late Horizon Pacific flight and Kumo House to expose the
   after-midnight reception conflict. The warning comes from app-owned rules.

The story is a recording guide, not a programmed agent sequence. Visitors can
choose different options, change the brief, and ask their own questions. Use New
trip to start a new browser identity and conversation for another recording.
The required two-minute submission video is recorded separately.

## Boundaries and implementation

- `oneagent.collaboration` is the reusable core already merged in PR #1.
- `travel/domain.py` owns catalog enrichment, trip calculations, argument
  validation, and idempotent save operations.
- `travel/agent.py` implements a bounded five-step model/tool loop. Read tools can
  run directly. Budget/preference changes proposed in chat update the brief only
  after confirmation. State-changing suggestions become buttons for explicit user
  confirmation. App-owned handlers validate all selections.
- `travel/server.py` connects the three app feeds, serves authenticated browser
  sessions, and serializes turns for each visitor through the collaboration core.
- `examples/travel/web` is the React/TypeScript UI. The selected object is captured
  when sending; replies appear in the originating app's session. A pending answer
  continues processing if the user changes apps.
- The saved trip is shared private agent state. App databases receive local
  context and their own replies. An optional checkbox grants per-message
  structured disclosure of budget/preferences; it does not share all memory.

State is stored beneath ignored `.travel-demo/`. Every visitor has its own
conversation journal and Git-backed runtime workspace. App messages and domain
records are account-scoped. Browser cookies are HttpOnly and SameSite; writes
require the exact configured origin and a per-visitor CSRF token. App connection
credentials stay on the backend.

This is a local hackathon prototype. The Python reference server and inherited
CLI runtime are not a hardened public multi-tenant hosting platform. For a public
version, add process-level runtime isolation, an authenticated/rate-limited
production gateway, resource limits, and a lifecycle for expiring visitor state.
A reverse proxy may set `--public-origin https://your-host` (Secure cookies), but
TLS alone does not supply those missing controls. No remote site is deployed by
the repository implementation.

## Frontend development

For live frontend editing, run the backend with
`--public-origin http://127.0.0.1:5173`, then run
`npm --prefix examples/travel/web run dev`. Vite proxies `/api` to port 8080.
Use the exact configured host and port so the origin/CSRF checks remain active.
Rebuild the frontend before returning to the standalone Python server.

## Verify

```sh
.venv/bin/python -m unittest tests.test_travel tests.test_collaboration -v
npm --prefix examples/travel/web run build
```

HTTP tests use deterministic test-only responders and isolated temporary storage.
They verify continuity and mechanics, not model quality. Separately exercise the
real-model flow above and inspect desktop/mobile layouts before recording.

## Image credits

- Tokyo: [Enes on Unsplash](https://unsplash.com/photos/a-view-of-a-large-city-with-tall-buildings-dyF1Q8kc0Fw).
- Illustrative room: [Pranav Kumar Jain on Unsplash](https://unsplash.com/photos/white-bed-linen-on-bed-pHcLOc_RzQ0).

Both images are used under the [Unsplash License](https://unsplash.com/license).
Local copies avoid third-party image requests during a demo. They are reference
photography, not evidence of any fictional hotel's appearance.
