# OneAgent

Your personal agent, alongside the apps you use. OneAgent carries your
conversation and preferences between environments while each application keeps
its own interface, context, and chat.

The travel demo connects a private Telegram conversation to three independent
websites through a reusable application integration core.

## How the demo works

1. Send `/traveldemo` to your OneAgent Telegram bot to get personal website links.
2. Open a link and browse with OneAgent beside the page. The agent can use the
   catalog and the item you are viewing to answer questions.
3. Say things like “I want this hotel” in chat. The agent remembers preferences
   and choices through its existing Codex conversation.
4. Move to another site and continue planning with the same agent.

| Website | Environment | Default port |
| --- | --- | --- |
| Airside | Blue flight-search interface | 8080 |
| Staywell | Warm hotel site with distinct property photography | 8081 |
| Daylight | Dark activities guide with yellow accents | 8082 |

Telegram is your private home conversation. Website exchanges sync back there,
but each website displays only its own chat. Ordinary Telegram messages stay
private. The sites have separate catalogs and no shared trip total or itinerary
widgets; the agent's conversation connects the experience.

Choices are expressed naturally in chat, with no separate Save or Confirm step.
Restarting the agent or travel service clears visible website chats while
preserving the agent's memory. The demo uses fictional travel catalogs and does
not make bookings.

## Quick start

Requires Python 3.11+, Node 20.19+ or 22.12+, Git, and an authenticated OneAgent
runtime (Codex by default).

```sh
git clone https://github.com/our-ark/oneagent.git
cd oneagent
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[reference]"
npm --prefix examples/travel/web ci
npm --prefix examples/travel/web run build
```

Create a Telegram bot with [@BotFather](https://t.me/BotFather), then configure
its token and your private chat ID locally:

```sh
export ONEAGENT_TELEGRAM_BOT_TOKEN='your-bot-token'
export ONEAGENT_TELEGRAM_ALLOWED_CHAT_ID='your-private-chat-id'
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel --telegram
```

Keep that terminal running, send `/traveldemo` to the bot, and open the returned
links on the same computer. This command starts the normal bot and all three
websites. If your bot is already running, use the existing-daemon setup in the
[travel walkthrough](docs/travel-demo.md) instead of starting a second poller.

The walkthrough also covers finding your chat ID, runtime configuration, remote
access, troubleshooting, and a suggested recording story. Localhost links do not
work from another device without additional hosting or tunnels.

To launch the general OneAgent interface:

```sh
bin/oneagent
```

## Build another environment

The travel sites use the same application-owned message and context interfaces
available to other scenarios. See the [integration guide](docs/app-integration.md)
for scoped context, account isolation, runtime integration, and generic tools.
The notes example demonstrates a smaller integration:

```sh
.venv/bin/python examples/notes/roundtrip.py
.venv/bin/python -m unittest tests.test_collaboration -v
```

## Project provenance

OneAgent was created with Genesis from an Enoch-derived starting point. Its
runtime, identity, memory, and provider infrastructure are inherited building
blocks. The collaboration core and demo integrations were written for this
project. See [implementation provenance](docs/provenance.md) for the distinction
between inherited infrastructure and new work.
