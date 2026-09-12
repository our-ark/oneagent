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

## Travel demo website

Browse flights and hotels with the same personal agent alongside each app.
Save selections, compare options across apps, and track budget and arrival fit.

```sh
npm --prefix examples/travel/web ci
npm --prefix examples/travel/web run build
ONEAGENT_PYTHON="$PWD/.venv/bin/python" bin/oneagent-travel
```

Open `http://127.0.0.1:8080`. See the [travel walkthrough](docs/travel-demo.md)
for installation, the recording story, model setup, and prototype boundaries.
