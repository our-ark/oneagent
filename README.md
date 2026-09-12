# OneAgent

OneAgent is a Genesis-created agent descended from Enoch.

This repository is the Enoch-derived starting point for the team’s implementation
of *One Agent, Anywhere*. It includes Enoch's shopping skill and local browser
interface. UAAP integration has not been added. No Ruth code is included.

## Mission

Accompany the user across applications as one persistent personal agent, maintaining a continuing conversation and memory through UAAP message delivery and authorized bidirectional context exchange while applications retain domain authority.

## Run

Use Python 3.11 or newer to create a project environment and install the providers:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -e '.[reference]'
```

Replace `python3.13` with your installed Python 3.11+ executable if needed.
The launchers automatically use `.venv/bin/python`; `ONEAGENT_PYTHON` can
explicitly override the interpreter.

Configure Telegram, then start the bot:

```bash
bin/oneagent config provider chat telegram
bin/oneagent setup
bin/oneagent-agent
```

For the admin CLI:

```bash
bin/oneagent
```

## Shopping

The [shop skill](src/oneagent/skills/shop/SKILL.md) compares products through
Shopify UCP and hands off merchant links for checkout. Completed searches also
create an authenticated local page with product tabs and the same conversation.
See the [setup guide](docs/shop-skill.md) for UCP tooling, browser access, and
configuration, and the [implementation notes](docs/shop-pr-summary.md) for the
adaptation from Enoch.

The repository includes the Telegram provider in `libraries/telegram` so product
cards render as separate messages. The repository launchers load this local
provider through `genesis.toml`. A wheel-only deployment must also install that
provider separately; the external reference pin does not include these changes.

## Lineage

- created by: Genesis
- ancestor: Enoch
- codebase: body
- Git history: lineage
