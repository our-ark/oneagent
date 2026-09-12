# OneAgent

OneAgent is a Genesis-created agent descended from Enoch.

This repository is the Enoch-derived starting point for the team’s implementation
of *One Agent, Anywhere*. The inherited runtime is now joined by a reusable cross-application collaboration
core. No Ruth code is included. The travel demo integrates through
the same app-owned message and context interfaces available to other scenarios.

## Mission

Accompany the user across applications as one persistent personal agent, maintaining a continuing conversation and memory through UAAP message delivery and authorized bidirectional context exchange while applications retain domain authority.

## Run

```bash
bin/oneagent
```

## Lineage

- created by: Genesis
- ancestor: Enoch
- codebase: body
- Git history: lineage

## Build an application integration

See [the integration guide](docs/app-integration.md) for the API, account isolation,
runtime bridge, generic tools, and a runnable notes example.

```sh
.venv/bin/python examples/notes/roundtrip.py
.venv/bin/python -m unittest tests.test_collaboration -v
```

[Provenance](docs/provenance.md) distinguishes inherited infrastructure from new work.

## Telegram + three travel websites

Browse flights, hotels, and activities with the same personal agent alongside each app.
Save selections, compare options across apps, and track budget and arrival fit.

```sh
npm --prefix examples/travel/web ci
npm --prefix examples/travel/web run build
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel
```

Airside (flights), Staywell (hotels), and Daylight (activities) run at ports
8080, 8081, and 8082. Add `--telegram` with your bot configured, then send
`/traveldemo` to receive personal links that connect all three sites to the same
conversation and receive website exchanges back in Telegram. An existing
OneAgent Telegram daemon can use the local control
bridge instead of a second poller. See the [travel walkthrough](docs/travel-demo.md)
for installation, the recording story, model setup, and prototype boundaries.
