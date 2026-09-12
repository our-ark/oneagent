# Telegram → Airside → Staywell → Daylight

Start in Telegram with `/traveldemo`. OneAgent activates a private demo trip and
replies with personal links to three independent websites:

| Website | Default address | Application |
| --- | --- | --- |
| Airside | http://127.0.0.1:8080 | Flights |
| Staywell | http://127.0.0.1:8081 | Hotels |
| Daylight | http://127.0.0.1:8082 | Activities |

Airside uses a compact blue flight-search layout, Staywell uses warm editorial
typography and distinct hotel photography, and Daylight uses a dark city-guide
layout with bold yellow accents. The OneAgent panel remains visually consistent.

Each site has its own HTML entry point, origin, cookie, scoped catalog, and
application message feed. The companion uses the same personal agent, but each
website displays only its own conversation. Telegram is the private home chat:
all website exchanges sync back there, while ordinary Telegram messages and
other websites' threads stay hidden. Each website receives only its own catalog and
saved selection; it has no shared trip total, budget form, itinerary overview,
or warnings derived from another site. Ask about the object currently selected on a site,
then return to Telegram to discuss the combined itinerary.

## Install and build

Requires Python 3.11+, Node 20.19+ or 22.12+, Git, and OneAgent's authenticated
runtime (Codex by default). From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[reference]"
npm --prefix examples/travel/web ci
npm --prefix examples/travel/web run build
```

The CLI always uses the real configured model. Tests alone use deterministic
responders; a runtime failure is surfaced as a recoverable error.

## Option A: one command starts OneAgent and all three sites

Create a Telegram bot through [@BotFather](https://t.me/BotFather) using `/newbot`,
or use a bot that is not already being polled by another process. Set its token
and your own private Telegram chat ID locally, then launch:

```sh
export ONEAGENT_TELEGRAM_BOT_TOKEN='your-bot-token'
export ONEAGENT_TELEGRAM_ALLOWED_CHAT_ID='your-private-chat-id'
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel --telegram
```

The same settings may be stored in ignored `.oneagent/config.yaml` as
`telegram.bot_token` and `telegram.allowed_chat_id`. Never commit real tokens.
Only the configured private chat is accepted; group messages and other senders
are ignored. The command launches the normal OneAgent bot with its configured
runtime, identity, existing Telegram session, and durable notification service.
It requires the reference providers installed above.

If you do not know your chat ID, first send a message to your new bot, then call
Telegram's `getUpdates` locally before starting the poller and read
`message.chat.id`. Do not post your bot token or API response in a public issue.
See the [Telegram Bot API](https://core.telegram.org/bots/api#getupdates).

Open your bot in Telegram and send `/traveldemo`. Send your budget/preferences in
that chat, then open the returned links. Natural-language requests can propose
changes; `/travelconfirm tg-<message-id>` confirms a private Telegram proposal.
A website proposal can be confirmed on its originating site or through the exact
`/travelconfirm <site> <event-id>` command in its mirrored Telegram message. The agent
cannot silently save a selection or change the budget.

Keep the launching Terminal open. Control+C stops the demo. A server restart
clears the visible website chats. The private Telegram history, agent memory,
saved selections, browser sessions, and durable notification queue are preserved.

## Option B: use your existing OneAgent Telegram bot

Keep a single Telegram poller. Start the websites without `--telegram`:

```sh
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel
```

In the environment that launches your existing OneAgent Telegram daemon, set the
control-file path printed by the command:

```sh
export ONEAGENT_TRAVEL_CONTROL_FILE="$PWD/.travel-demo/control.json"
```

Then start/restart that daemon using its normal launch command. For an already
configured interactive agent, that is `bin/oneagent-agent` from the repo root.
If your daemon is managed by launchd or systemd, put the variable in that
service's environment and restart it; exporting it in another Terminal does not
change an existing process.

The existing daemon checks its normal chat authorization, then offers private
Telegram messages to the travel service. `/traveldemo` starts/resumes demo mode.
During that mode, ordinary text stays in the private Telegram conversation. Other
commands still use their usual handlers. `/traveldemo stop` returns ordinary
text to the existing agent. Website and Telegram reasoning use the running bot’s
original runtime, identity, working directory, and `telegram:<chat-id>` session.
A per-conversation lock serializes turns, including multi-step travel tool calls.
Preferences you mentioned before travel mode remain available on all three sites.
The private agent itinerary, application sessions, and existing connection links
stay intact. Budgets, preferences, combined totals, and timing checks remain
inside the agent conversation. A website can save only its own type of item.
Each companion displays only exchanges belonging to its website. Telegram
messages remain private unless you explicitly target a website with
`/traveldemo reply <flights|hotels|activities> <request>`. That command shares
only the request and the agent's answer with the chosen site. The response also
returns through the normal Telegram reply path, without a duplicate mirror.

The bridge listens only on an ephemeral loopback port, requires a random bearer
token, and writes its connection file with mode 0600. It is never a public browser
endpoint. Do not run Option A and your existing poller against the same bot.
Telegram permits one update consumer; an existing webhook also prevents polling.

## Links on your phone or another computer

The default loopback links work in Telegram Desktop and a browser on the machine
running the demo. On your phone, `127.0.0.1` refers to the phone.

For other devices, forward each site through a separate HTTPS tunnel/reverse
proxy and configure all three exact origins:

```sh
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel --telegram \
  --flights-origin https://flights.example.com \
  --hotels-origin https://hotels.example.com \
  --activities-origin https://activities.example.com
```

Replace the example domains with the actual origins forwarding to ports 8080,
8081, and 8082. The repo does not create tunnels or deploy sites. Use HTTPS so
browser features and Secure cookies work. Each origin serves both its own
frontend and same-origin `/api` requests. No wildcard CORS or shared-domain
cookies are needed. `--host`, `--port` (first of three consecutive ports),
`--root`, and `--web-root` are configurable.

This is a local hackathon prototype, not a hardened public multi-tenant host.
Before exposing it broadly, add gateway authentication, request limits, runtime
isolation, and visitor-state cleanup. Use controlled demo access for a recording.

## Try the story

1. Before starting travel mode, tell OneAgent “I prefer quiet neighborhoods and
   a relaxed first day.” Then send `/traveldemo` and “My trip budget is $1,500.”
   Confirm the proposed brief update. Ask for recommendations on each site to
   check that the earlier preferences carry over.
2. Open Airside from Telegram. Select Pacific Air PA 101 and ask whether it fits.
   Save it. The model sees that flight's authoritative facts.
3. Open Staywell from Telegram. Its chat is separate from Airside's. Select Kumo
   House and ask “Does this work with my flight?” The agent remembers the flight
   and your preferences without copying the Airside conversation into Staywell.
   Save the stay after comparing.
4. Open Daylight. Select “Yanaka, one slow morning.” Ask whether it fits the
   schedule and remaining budget, then save it.
5. Website exchanges also arrive in Telegram, labeled with the site and selected
   item. Back in Telegram, ask “What have we planned, and how much is left?” The
   agent can report a combined total of $1,235: $720 flight, $480 hotel, and $35
   activity, leaving $265.

All data is fictional: one-way SFO → Tokyo flights on Nov 5 arriving Nov 6, stays
Nov 6–9 (three nights), and activities during the same trip in 2026. Catalog
prices include mock taxes. Saved selections are not bookings or purchases. A
late-arriving flight can prompt the agent to flag hotel reception and activity
timing conflicts in chat. These checks do not appear as shared website widgets.
The story is a recording guide, not a scripted agent sequence. Film the final
two-minute submission video separately.

## Resume, reset, and leave

- `/traveldemo` resumes the current trip and returns fresh links.
- `/traveldemo reply hotels Compare the quiet stays` sends that request and its
  answer to Staywell only. Use `flights` or `activities` for the other sites.
  Ordinary Telegram messages never automatically appear on a website.
- `/traveldemo reset` creates a fresh trip and website transcript. It revokes old
  links and browser sessions; open the new links in each website. The normal
  Telegram conversation and its earlier preferences remain available.
- `/traveldemo stop` leaves travel mode in Telegram. Saved trip state remains.
- Restarting the travel service clears all visible website chats. Restarting the
  attached agent clears the website chats for that Telegram owner when it
  reconnects. Refreshing a page or requesting fresh links does not clear chats.
  Existing browser tabs can keep sending messages without reconnecting.
  Previous exchanges remain in private agent history and Telegram, and queued
  deliveries still recover. Old website proposals can still be confirmed using
  their exact Telegram commands.
- Each connection link expires after 15 minutes and works once. If it has already
  been opened or expired, request new links. Link previews cannot consume it.
- Website sessions last 24 hours. Once connected, refresh the site's plain URL or
  use the companion's “Open…” buttons to continue elsewhere. These buttons issue
  a fresh connection link rather than changing a route in the same website.
- Opening a site directly creates an independent visitor. To join your Telegram
  trip, use your Telegram link; browser sessions are not matched by IP address.

## Implementation and extension points

- `oneagent.collaboration.HandoffStore` is reusable across demos: the trusted host
  maps an authenticated principal to a private conversation, issues app-scoped
  handoffs, and exchanges them for independent browser sessions. Bearer hashes
  are persisted, with atomic single-use redemption and reset revocation.
- `travel/telegram.py` adds the `/traveldemo` mode controller and existing-daemon
  bridge. `travel/bot_bridge.py` executes website turns inside that running bot. A private durable reply outbox prevents model work
  or reset commands repeating after a failed network delivery; the outbox contains
  the returned links. A cached response also makes bot-bridge retries idempotent.
- `travel/server.py` serves three fixed applications. Each can submit only to its
  own feed and directly save only its own item type. `/api/session` and
  `/api/selection` return that site’s saved ID, never the combined trip or
  personal preferences. The old `/api/trip` and `/api/preferences` routes are
  denied on the independent sites. Structured preference sharing is disabled.
  `/api/conversation` and `/api/transcript` expose only the fixed site's visible
  thread, never private Telegram or other site exchanges. Website confirmations
  accept only proposals visible in that site's current chat. Confirming returns
  only an acknowledgement to the browser. Per-site cursor cutoffs clear the
  visible chats after a service or bot restart without deleting private history,
  queued notifications, or idempotency receipts.
- `travel/domain.py` owns catalog facts, site-scoped selection views, and the
  agent’s private itinerary, totals, warnings, and idempotent changes.
  `travel/agent.py` uses the existing runtime with bounded tool calls.
- `examples/travel/web/src/CompanionPanel.tsx` is the reusable UI. Hosts supply
  context, conversation data, and action callbacks. The three entry points mount
  the shared travel integration with a fixed site ID.

State lives in ignored `.travel-demo/`. Per-application cookies are HttpOnly and
SameSite. Writes check the exact origin and a CSRF token. Connection tokens
travel in URL fragments, are removed before API calls, and exchange via POST;
link previews and referrer headers do not receive them. The Telegram Bot API
token stays server-side. Reset makes prior demo state inaccessible through old
links but does not delete its files.

## Website replies in Telegram

After a website reply is saved, a durable travel outbox queues the user’s message
and agent response with the source site and selected item. The normal bot delivers
it through `NotificationDeliveryService`. Stable IDs derived from the owner, app,
and event make repeated delivery requests reuse the saved notification; they do
not re-run the model or change the itinerary. Telegram-originated turns use the
normal reply path and are never mirrored back a second time.
An explicit `/traveldemo reply` also uses that normal reply path; its reserved
event namespace cannot be submitted by a website. Mirrored proposals include
their source-specific Telegram confirmation commands.

Both processes can restart: callback registration refreshes automatically, saved
outbox entries retry, and the bot recovers its existing notification journal.
Retries follow the existing service’s attempt limits and handling of ambiguous
provider failures. Telegram does not provide an exactly-once send guarantee.
Website replies remain available even while Telegram delivery is unavailable.

## Verify and develop

```sh
PYTHONPATH=src .venv/bin/python -m unittest tests.test_travel tests.test_travel_telegram tests.test_travel_bot_bridge tests.test_collaboration tests.test_oneagent_notifications -v
npm --prefix examples/travel/web run build
```

Tests use temporary HTTP servers and a fake Telegram transport. They cover a
Telegram → three websites → Telegram round trip, separate origins, owner isolation,
link scope/expiry/replay, reset revocation, sessions after restart, site data
isolation, separate visible conversations, explicit Telegram routing, restart
clearing, blocked cross-site reads/writes, chat-only budget
confirmations, pre-travel preferences in the real bot session, concurrent turns,
and notification recovery after bot and backend restarts. Exercise your configured bot and real model
before recording; automated fixtures do not prove Telegram delivery or model quality.

For frontend development, set the selected site's public origin to
`http://127.0.0.1:5173`, point the Vite `/api` proxy at its backend port in
`vite.config.ts`, run `npm --prefix examples/travel/web run dev`, and open
`http://127.0.0.1:5173/<site>/index.html`. Production builds are the recommended
way to exercise all three origins together.

## Image credits

- Tokyo: [Enes on Unsplash](https://unsplash.com/photos/a-view-of-a-large-city-with-tall-buildings-dyF1Q8kc0Fw).
- Kumo House illustration: [Pranav Kumar Jain on Unsplash](https://unsplash.com/photos/white-bed-linen-on-bed-pHcLOc_RzQ0).
- Aoi Central illustration: [Sung Jin Cho on Unsplash](https://unsplash.com/photos/modern-hotel-room-with-city-view-through-window-pRAs34PRUuU).
- Sora Retreat illustration: [Wemel Wood on Unsplash](https://unsplash.com/photos/minimalist-bedroom-with-a-neatly-made-bed-uhQHGyLungI).
- Machi Stay illustration: [Jessica Martins on Unsplash](https://unsplash.com/photos/a-simple-bedroom-with-a-single-bed-and-wooden-furniture-zq3NlBqPTGA).

Local images are used under the [Unsplash License](https://unsplash.com/license).
They illustrate the demo; the properties and activities are fictional.
